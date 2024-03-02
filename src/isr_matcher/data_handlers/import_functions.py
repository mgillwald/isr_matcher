# Utility functions to be used in TrackSegment instances

from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar, Union, Tuple, overload
from requests import post
from requests.exceptions import RequestException
from json import dump as json_dump
from pathlib import Path
from shapely import MultiLineString, Point
from shapely.geometry.base import BaseGeometry
from isr_matcher.geometry.operational_point import OperationalPoint
from isr_matcher.ops._preprocessing import ISRPreprocessor
import numpy as np
from isr_matcher._constants._properties import ISR_PROPERTIES_TRACK_SEGMENTS
from isr_matcher._constants._parse import extract_station_names
from copy import deepcopy

# Type T: only instances of class BaseGeometry or subclasses (Point, Linestring, etc.)
T = TypeVar("T", bound="BaseGeometry")

project_path = Path(__file__).parent.parent.parent.parent


def query_track_segment(
    args: list[str | int | float],
    to_km: str | None = None,
    allow_previous: bool = True,
    enhance_kilometrage: bool = True,
    return_track_type: str | None = None,
) -> Tuple | None:
    """Queries ISR according for track segment."""

    from isr_matcher._constants._filters import ISR_FILTERS
    from requests import post

    # check input
    filter_name = 'EQUALS_TRACK_SEG'
    special_chars = ["Ä", "Ö", "Ü", "ä", "ö", "ü", "ß"]

    # create filter string
    filter_str = ISR_FILTERS[filter_name]
    for i, arg in enumerate(args):
        # replace special chars by wildcard
        new_arg = arg
        for char in special_chars:
            if isinstance(new_arg, str) and char in new_arg:
                new_arg = new_arg.replace(char, '*')
        filter_str = filter_str.replace(f"$arg{i + 1}", str(new_arg))

    # send the request
    try:
        response = post(
            "https://geovdbn.deutschebahn.com/pgv-map/geoserver.action",
            data=filter_str,
            headers={"Content-Type": "application/xml"},
        )
    except Exception:
        response = None

    if response is not None and response.status_code == 200:
        # The request was successful
        features = response.json()['features']
        if len(features) > 0:
            if return_track_type:  # if we want specifically 'Richtungsgleis', 'Gegengleis', or 'einglesig'
                i = 0
                for element in features:
                    if element['properties']['INF_GLEISANZAHL'] == return_track_type:
                        break
                    i += 1
                else:
                    return None
                return features[i]

            else:
                if to_km:
                    for i in range(len(features)):
                        if features[i]['properties']['ISR_KM_BIS'] == to_km:
                            break
                    else:
                        return None
                else:
                    i = 0

                return track_segment_from_json_dict(
                    isr_feature=features[i], allow_previous=allow_previous, enhance_kilometrage=enhance_kilometrage
                )
        else:
            return None
    else:
        # request was not successful
        return None


def query_op(
    filter_name: str,
    args: list[str | int | float],
) -> dict | None:
    """Queries ISR according for track segment."""

    from isr_matcher._constants._filters import ISR_FILTERS
    from requests import post

    # check input
    args[0] = '*'
    special_chars = ["Ä", "Ö", "Ü", "ä", "ö", "ü"]

    # create filter string
    filter_str = ISR_FILTERS[filter_name]
    for i, arg in enumerate(args):
        # replace special chars by wildcard
        new_arg = arg
        for char in special_chars:
            if isinstance(new_arg, str) and char in new_arg:
                new_arg = new_arg.replace(char, '*')
        filter_str = filter_str.replace(f"$arg{i + 1}", str(new_arg))

    # send the request
    try:
        response = post(
            "https://geovdbn.deutschebahn.com/pgv-map/geoserver.action",
            data=filter_str,
            headers={"Content-Type": "application/xml"},
        )
    except Exception:
        response = None

    if response is not None and response.status_code == 200:
        # The request was successful
        return response.json()
    else:
        # request was not successful
        return None


def export_json(
    response: dict | None,
    args: list[str | int | float],
) -> None:
    """TODO"""

    if response:
        # set filename
        export_path = project_path / f'cache/operational_points/ops_track_{args[1]}.json'

        # save JSON
        with open(export_path, "w", encoding="utf-8") as f:
            json_dump(response, f, ensure_ascii=False, indent=4, sort_keys=True)

    else:
        # request failed
        raise RequestException(f"Given response is None. Export aborted.")


def op_from_file(
    filepath: Path, name: str, track_nr: int, closest_to_geometry: Union[T, None] = None
) -> OperationalPoint:
    """TODO"""

    import json
    from typing import Union
    from isr_matcher._constants._properties import ISR_PROPERTIES_OPERATIONAL_POINT

    # filepath must exist
    assert filepath.exists(), f'No file found for path: {filepath}'

    if 'Leipzig-Semmelweiss' in name and track_nr == 6376:
        # query ISR for operational points / junction with matching name and track number
        # TODO: check for file with track 6377
        # station affiliated with 6376 and 6377 but in isr only exists with track nr 6377
        response = query_op(args=[f"{name}", track_nr + 1])
    else:
        response = {'features': []}
        # read file
        with open(filepath, encoding='utf-8') as f:
            json_dict = json.load(fp=f)
        # entries with fitting track and number
        for i in range(len(json_dict['features'])):
            json_feature = json_dict['features'][i]
            properties = json_feature['properties']

            if properties['BST_STELLENART'] == 'Stub':
                equals_track = (
                    True
                    if int(properties['STRECKE1']) == track_nr or int(properties['STRECKE2']) == track_nr
                    else False
                )
            else:
                equals_track = True if int(properties['STRNR']) == track_nr else False

            if name == properties['BST_STELLE_NAME'] and equals_track == True:
                response['features'].append(json_feature)
            elif 'Berlin-Moabit' in properties['BST_STELLE_NAME'] and track_nr == 6020:
                response['features'].append(json_feature)

    assert isinstance(response, dict)

    if len(response['features']) == 0:
        # empty properties dict for op's that don't exist in ISR
        isr_properties_op = ISR_PROPERTIES_OPERATIONAL_POINT
        keys = isr_properties_op.keys()
        properties = {key: [] for key in keys if len(isr_properties_op[key]) > 0}
        properties_info = {key: isr_properties_op[key] for key in keys if len(isr_properties_op[key]) > 0}

        if 'Frankfurt-Zehn Ruten' in name and len(name) == len('Frankfurt-Zehn Ruten'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3474918, 5557118), properties=properties, properties_info=properties_info
            )

        elif 'Berlin-Spandau' in name and len(name) == len('Berlin-Spandau'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3787180, 5830196), properties=properties, properties_info=properties_info
            )

        elif 'Wustermark Rbf Wot' in name and len(name) == len('Wustermark Rbf Wot'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3773494, 5831247), properties=properties, properties_info=properties_info
            )

        elif 'Ohrstedt' in name and len(name) == len('Ohrstedt'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3514734, 6041428), properties=properties, properties_info=properties_info
            )

        elif 'Maschen Rbf, W 1219' in name and len(name) == len('Maschen Rbf, W 1219'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3568773, 5921582), properties=properties, properties_info=properties_info
            )

        elif 'StrUeb1401_1500' in name and len(name) == len('StrUeb1401_1500'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3488287, 5883095), properties=properties, properties_info=properties_info
            )

        elif 'StrUeb1401_1412' in name and len(name) == len('StrUeb1401_1412'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3485942, 5885359), properties=properties, properties_info=properties_info
            )

        elif 'StrUeb1422_1425' in name and len(name) == len('StrUeb1422_1425'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3481499, 5890017), properties=properties, properties_info=properties_info
            )

        elif 'StrUeb1570_1573' in name and len(name) == len('StrUeb1570_1573'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3385896, 5926982), properties=properties, properties_info=properties_info
            )

        elif 'StrUeb1702_1703' in name and len(name) == len('StrUeb1702_1703'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3547178, 5807445), properties=properties, properties_info=properties_info
            )

        elif 'Bremerhaven-Speckenbüttel, W 5' in name and len(name) == len('Bremerhaven-Speckenbüttel, W 5'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3473047, 5940039), properties=properties, properties_info=properties_info
            )

        elif 'StrUeb1630_1744' in name and len(name) == len('StrUeb1630_1744'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3487038, 5838159), properties=properties, properties_info=properties_info
            )

        elif 'StrUeb2140_2146' in name and len(name) == len('StrUeb2140_2146'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3384633, 5706248), properties=properties, properties_info=properties_info
            )

        elif 'Essen-Steele, W 79' in name and len(name) == len('Essen-Steele, W 79'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3367746, 5702063), properties=properties, properties_info=properties_info
            )

        elif 'Essen-Steele, W 106' in name and len(name) == len('Essen-Steele, W 106'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3366687, 5702678), properties=properties, properties_info=properties_info
            )

        elif 'Gelsenkirchen Streckenw. 2172/2230' in name and len(name) == len('Gelsenkirchen Streckenw. 2172/2230'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3365341, 5710866), properties=properties, properties_info=properties_info
            )

        elif 'StrUeb2236_2246' in name and len(name) == len('StrUeb2236_2246'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3365980, 5713508), properties=properties, properties_info=properties_info
            )

        elif 'W 62' in name and len(name) == len('W 62'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3355085, 5671747), properties=properties, properties_info=properties_info
            )

        elif 'Wuppertal-Vohwinkel, W 88' in name and len(name) == len('Wuppertal-Vohwinkel, W 88'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3366224, 5679958), properties=properties, properties_info=properties_info
            )

        elif 'Vellmar-Obervellmar, W 16' in name and len(name) == len('Vellmar-Obervellmar, W 16'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3531788, 5691557), properties=properties, properties_info=properties_info
            )

        elif 'Rommerskirchen DB-Grenze' in name and len(name) == len('Rommerskirchen DB-Grenze'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3339604, 5658327), properties=properties, properties_info=properties_info
            )

        elif 'StrUeb2650_2658' in name and len(name) == len('StrUeb2650_2658'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3360062, 5651676), properties=properties, properties_info=properties_info
            )

        elif 'StrUeb2700_2705' in name and len(name) == len('StrUeb2700_2705'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3377964, 5673811), properties=properties, properties_info=properties_info
            )

        elif 'Meinerzhagen, W 3' in name and len(name) == len('Meinerzhagen, W 3'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3404502, 5664591), properties=properties, properties_info=properties_info
            )

        elif 'Bönen, W 51' in name and len(name) == len('Bönen, W 51'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3414759, 5720685), properties=properties, properties_info=properties_info
            )

        elif 'StrUeb1630_2982' in name and len(name) == len('StrUeb1630_2982'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3479662, 5821488), properties=properties, properties_info=properties_info
            )

        elif 'Ludwigshafen (Rh) BASF Südtor, W 529' in name and len(name) == len(
            'Ludwigshafen (Rh) BASF Südtor, W 529'
        ):
            operational_point = OperationalPoint(
                coords_epsg31467=(3459473, 5484127), properties=properties, properties_info=properties_info
            )

        elif 'StrUeb3520_3687' in name and len(name) == len('StrUeb3520_3687'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3473778, 5548119), properties=properties, properties_info=properties_info  #
            )

        elif 'Schlüchtern, W 233' in name and len(name) == len('Schlüchtern, W 233'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3536336, 5578482), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb3683_3687' in name and len(name) == len('StrUeb3683_3687'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3474194, 5551324), properties=properties, properties_info=properties_info  #
            )

        elif 'Eppingen, W 61' in name and len(name) == len('Eppingen, W 61'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3495730, 5446222), properties=properties, properties_info=properties_info  #
            )

        elif 'Seckach, W 624' in name and len(name) == len('Seckach, W 624'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3524634, 5478312), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb4250_4661' in name and len(name) == len('StrUeb4250_4661'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3480155, 5310931), properties=properties, properties_info=properties_info  #
            )

        elif 'Abzw Lindau-Aeschach, W 2' in name and len(name) == len('Abzw Lindau-Aeschach, W 2'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3551608, 5269004), properties=properties, properties_info=properties_info  #
            )

        elif 'Stuttgart Hbf, W 117' in name and len(name) == len('Stuttgart Hbf, W 117'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3513838, 5405859), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb4701_4861' in name and len(name) == len('StrUeb4701_4861'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3513577, 5405533), properties=properties, properties_info=properties_info  #
            )

        elif 'Stuttgart-Zazenhausen, W 666 --Rbf--' in name and len(name) == len(
            'Stuttgart-Zazenhausen, W 666 --Rbf--'
        ):
            operational_point = OperationalPoint(
                coords_epsg31467=(3513299, 5412039), properties=properties, properties_info=properties_info  #
            )

        elif 'Stuttgart-Zazenhausen, W 655' in name and len(name) == len('Stuttgart-Zazenhausen, W 655'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3513299, 5412039), properties=properties, properties_info=properties_info  #
            )

        elif 'Stuttgart-Zazenhausen, W 656 --Rbf--' in name and len(name) == len(
            'Stuttgart-Zazenhausen, W 656 --Rbf--'
        ):
            operational_point = OperationalPoint(
                coords_epsg31467=(3513299, 5412039), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb4801_4861' in name and len(name) == len('StrUeb4801_4861'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3513585, 5405536), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb4812_4820' in name and len(name) == len('StrUeb4812_4820'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3513244, 5412066), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb5360_5361' in name and len(name) == len('StrUeb5360_5361'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3620449, 5324405), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb5420_5421' in name and len(name) == len('StrUeb5420_5421'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3552268, 5268420), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb5554_5604' in name and len(name) == len('StrUeb5554_5604'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3695500, 5336394), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb5556_5557' in name and len(name) == len('StrUeb5556_5557'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3703347, 5360591), properties=properties, properties_info=properties_info  #
            )

        elif 'Bft Regensburg Hafen Abzw, W 100' in name and len(name) == len('Bft Regensburg Hafen Abzw, W 100'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3729230, 5435556), properties=properties, properties_info=properties_info  #
            )

        elif 'Berlin Warschauer Straße, W 618' in name and len(name) == len('Berlin Warschauer Straße, W 618'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3802631, 5828460), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6007_6143' in name and len(name) == len('StrUeb6007_6143'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3806507, 5823149), properties=properties, properties_info=properties_info  #
            )

        elif 'Berlin-Schöneweide                S-Bahn, W 44' in name and len(name) == len(
            'Berlin-Schöneweide                S-Bahn, W 44'
        ):
            operational_point = OperationalPoint(
                coords_epsg31467=(3806507, 5823149), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6035_6172' in name and len(name) == len('StrUeb6035_6172'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3796418, 5821864), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6050_6346' in name and len(name) == len('StrUeb6050_6346'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3707554, 5710690), properties=properties, properties_info=properties_info  #
            )

        elif 'Halle Saalebrücke, W 8' in name and len(name) == len('Halle Saalebrücke, W 8'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3703809, 5705910), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6053_6346' in name and len(name) == len('StrUeb6053_6346'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3707536, 5708930), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6078_6525' in name and len(name) == len('StrUeb6078_6525'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3867136, 5839522), properties=properties, properties_info=properties_info  #
            )

        elif 'Strausberg                        S-Bahn, 75W53' in name and len(name) == len(
            'Strausberg                        S-Bahn, 75W53'
        ):
            operational_point = OperationalPoint(
                coords_epsg31467=(3828647, 5833109), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6081_6141' in name and len(name) == len('StrUeb6081_6141'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3798358, 5833578), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6109_6185' in name and len(name) == len('StrUeb6109_6185'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3786974, 5830222), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6110_6410' in name and len(name) == len('StrUeb6110_6410'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3686016, 5783410), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6118_6436' in name and len(name) == len('StrUeb6118_6436'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3692434, 5759143), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6126_6147' in name and len(name) == len('StrUeb6126_6147'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3810235, 5819898), properties=properties, properties_info=properties_info  #
            )

        elif 'Glasower Damm Süd, W 313' in name and len(name) == len('Glasower Damm Süd, W 313'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3800940, 5809833), properties=properties, properties_info=properties_info  #
            )

        elif 'Glasower Damm Süd, W 317' in name and len(name) == len('Glasower Damm Süd, W 317'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3800894, 5809989), properties=properties, properties_info=properties_info  #
            )

        elif 'Doberlug-Kirchhain Nord, 45W3' in name and len(name) == len('Doberlug-Kirchhain Nord, 45W3'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3816094, 5730576), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6142_6145' in name and len(name) == len('StrUeb6142_6145'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3809572, 5820264), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6145_6146' in name and len(name) == len('StrUeb6145_6146'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3809955, 5819092), properties=properties, properties_info=properties_info  #
            )

        elif 'Horka Gbf, W 9506' in name and len(name) == len('Horka Gbf, W 9506'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3809955, 5819092), properties=properties, properties_info=properties_info  #
            )

        elif 'Knappenrode, W 1' in name and len(name) == len('Knappenrode, W 1'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3871843, 5711437), properties=properties, properties_info=properties_info  #
            )

        elif 'Dresden-Neustadt, W 726' in name and len(name) == len('Dresden-Neustadt, W 726'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3832075, 5669419), properties=properties, properties_info=properties_info  #
            )

        elif 'Dresden Hbf, W 244' in name and len(name) == len('Dresden Hbf, W 244'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3832487, 5666543), properties=properties, properties_info=properties_info  #
            )

        elif 'Dresden Freiberger Straße, W 526' in name and len(name) == len('Dresden Freiberger Straße, W 526'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3830931, 5667798), properties=properties, properties_info=properties_info  #
            )

        elif 'Dresden Mitte, W 562' in name and len(name) == len('Dresden Mitte, W 562'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3831337, 5668691), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6243_6258' in name and len(name) == len('StrUeb6243_6258'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3830740, 5667075), properties=properties, properties_info=properties_info  #
            )

        elif 'Dresden-Altstadt, W 119' in name and len(name) == len('Dresden-Altstadt, W 119'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3830740, 5667075), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6248_6251' in name and len(name) == len('StrUeb6248_6251'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3821607, 5675481), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6248_6274' in name and len(name) == len('StrUeb6248_6274'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3830259, 5668401), properties=properties, properties_info=properties_info  #
            )

        elif 'Glauchau-Schönbörnchen, W 42' in name and len(name) == len('Glauchau-Schönbörnchen, W 42'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3746681, 5637534), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6274_6363' in name and len(name) == len('StrUeb6274_6363'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3810873, 5691604), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6321_6954' in name and len(name) == len('StrUeb6321_6954'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3793377, 6050754), properties=properties, properties_info=properties_info  #
            )

        elif 'Abzw Plaaz, 66W 1' in name and len(name) == len('Abzw Plaaz, 66W 1'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3719554, 5972423), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6325_6929' in name and len(name) == len('StrUeb6325_6929'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3706058, 5996997), properties=properties, properties_info=properties_info  #
            )

        elif 'Halle (Saale) Hbf, 92W224' in name and len(name) == len('Halle (Saale) Hbf, 92W224'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3707435, 5709289), properties=properties, properties_info=properties_info  #
            )

        elif 'Halle (Saale) Gbf, 95W446' in name and len(name) == len('Halle (Saale) Gbf, 95W446'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3707524, 5709397), properties=properties, properties_info=properties_info  #
            )

        elif 'Halle (Saale) Gbf Nord, 95W408' in name and len(name) == len('Halle (Saale) Gbf Nord, 95W408'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3709125, 5711250), properties=properties, properties_info=properties_info  #
            )

        elif 'Halle (Saale) Gbf, 96W460' in name and len(name) == len('Halle (Saale) Gbf, 96W460'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3708829, 5707515), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6376_6377' in name and len(name) == len('StrUeb6376_6377'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3736342, 5692099), properties=properties, properties_info=properties_info  #
            )

        elif 'Leipzig-Semmelweisstraße, 97W193' in name and len(name) == len('Leipzig-Semmelweisstraße, 97W193'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3736342, 5692099), properties=properties, properties_info=properties_info  #
            )

        elif 'Köthen Süd, 05W507' in name and len(name) == len('Köthen Süd, 05W507'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3707407, 5736537), properties=properties, properties_info=properties_info  #
            )

        elif 'Abzw Halle (Saale) Leuchtturm, W 6' in name and len(name) == len('Abzw Halle (Saale) Leuchtturm, W 6'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3709376, 5707046), properties=properties, properties_info=properties_info  #
            )

        elif 'Halle (Saale) Hbf, W 355' in name and len(name) == len('Halle (Saale) Hbf, W 355'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3707606, 5708948), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6403_6434' in name and len(name) == len('StrUeb6403_6434'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3679821, 5779401), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6422_6436' in name and len(name) == len('StrUeb6422_6436'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3692866, 5760802), properties=properties, properties_info=properties_info  #
            )

        elif 'Rostock Gbf, Gl 8' in name and len(name) == len('Rostock Gbf, Gl 8'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3706024, 5997711), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6785_6942' in name and len(name) == len('StrUeb6785_6942'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3771146, 5921609), properties=properties, properties_info=properties_info  #
            )

        elif 'StrUeb6953_6954' in name and len(name) == len('StrUeb6953_6954'):
            operational_point = OperationalPoint(
                coords_epsg31467=(3795593, 6050510), properties=properties, properties_info=properties_info  #
            )

        else:
            # no match: error
            raise ValueError(f"No operational point found with name = {name} for track = {track_nr}")

    elif len(response['features']) == 1:
        # one match: perfect

        operational_point = op_from_feature_isr(isr_feature=response['features'][0])

    else:
        # multiple match:
        # if 'closest_to_geometry' is given, compute nearest OperationalPoint to that geometry
        if closest_to_geometry:
            distances_list_m = [
                closest_to_geometry.distance(Point(feature['geometry']['coordinates']))
                if not isinstance(feature['geometry'], type(None))
                else np.inf
                for feature in response['features']
            ]
            operational_point = op_from_feature_isr(isr_feature=response['features'][np.argmin(distances_list_m)])
        # else take first OperationalPoint
        else:
            operational_point = op_from_feature_isr(isr_feature=response['features'][0])

    return operational_point


def track_segment_from_json_dict(
    isr_feature: dict, allow_previous: bool = True, enhance_kilometrage: bool = True
) -> Tuple:
    """Creates TrackSegment instance from isr response (json dict)."""

    # extract feature id and properties
    feature_id = isr_feature['id']
    properties = dict(sorted(isr_feature['properties'].items()))
    track_nr = int(properties['ISR_STRE_NR'])
    name = properties['ISR_STRECKE_VON_BIS']
    track_type = properties['INF_GLEISANZAHL']

    # extract properties for opposite track (if double track)
    if track_type != 'eingleisig':
        # query with same track nr and name
        return_track_type = 'Gegengleis' if track_type == 'Richtungsgleis' else 'Richtungsgleis'
        feature = query_track_segment(args=[track_nr, name], allow_previous=False, return_track_type=return_track_type)

        if feature:
            properties_2 = dict(sorted(feature['properties'].items()))
        else:
            properties_2 = None
    else:
        properties_2 = None

    # set var 'properties' for Richtungsgleis, and var 'properties_2' for Gegengleis
    # for monorails, only use 'properties', as 'properties_2' is None
    if properties_2:
        if track_type == 'Gegengleis':
            temp = deepcopy(properties)
            properties = deepcopy(properties_2)
            properties_2 = deepcopy(temp)

    # assert feature is a track segment
    assert "ISR_V_GEO_TEN_KLASSIFIZIERUNG" in feature_id, f"Unknown element type: {feature_id}."

    # set properties
    PROPERTIES = ISR_PROPERTIES_TRACK_SEGMENTS

    # parse properties
    properties = {
        key: l[2](value)
        for key, value, l in zip(PROPERTIES.keys(), properties.values(), PROPERTIES.values())
        if len(l) > 0
    }

    if properties_2:
        properties_2 = {
            key: l[2](value)
            for key, value, l in zip(PROPERTIES.keys(), properties_2.values(), PROPERTIES.values())
            if len(l) > 0
        }

    # create dict of type {'property': [property_description_short, property_description_long]}
    properties_info = {key: (l[0], l[1]) for key, l in zip(PROPERTIES.keys(), PROPERTIES.values()) if len(l) > 0}

    # get coordinates
    isr_original_lines_epsg31467 = MultiLineString(isr_feature['geometry']['coordinates'])
    track_nr = properties['ISR_STRE_NR']

    # name of file with ops for track
    track_ops_file_path = (
        Path(__file__).parent.parent.parent.parent / f'cache/operational_points/ops_track_{track_nr}.json'
    )

    if not track_ops_file_path.exists():
        # query all operational points for track and write to cache
        response1 = query_op(filter_name='EQUALS_OP', args=['*', track_nr])
        response2 = query_op(filter_name='EQUALS_TRANSITION', args=['*', track_nr])
        response = response1
        response['features'] += response2['features']
        assert isinstance(response, dict)
        export_json(response=response, args=['*', track_nr])

    # get names of stations at start and end of track segment
    from_name, to_name = extract_station_names(track_name_string=properties['ISR_STRECKE_VON_BIS'], split_only=True)

    # read operational points from cache
    operational_point_from = op_from_file(
        filepath=track_ops_file_path,
        name=from_name,
        track_nr=track_nr,
        closest_to_geometry=isr_original_lines_epsg31467,
    )
    operational_point_to = op_from_file(
        filepath=track_ops_file_path, name=to_name, track_nr=track_nr, closest_to_geometry=isr_original_lines_epsg31467
    )

    # preprocess track segment lines
    isr_preprocessor = ISRPreprocessor(
        operational_point_from=operational_point_from, operational_point_to=operational_point_to
    )
    lines_processed = isr_preprocessor.process_track_segment_lines(lines=list(isr_original_lines_epsg31467.geoms))

    #
    parameters = (
        lines_processed,
        properties,
        properties_2,
        properties_info,
        operational_point_from,
        operational_point_to,
        enhance_kilometrage,
        allow_previous,
    )

    return parameters


def op_from_feature_isr(isr_feature: dict) -> OperationalPoint:
    """TODO"""

    from isr_matcher._constants._properties import ISR_PROPERTIES_OPERATIONAL_POINT, ISR_PROPERTIES_JUNCTION
    from isr_matcher.data_handlers.transformer import Transformer

    # extract feature id and properties
    feature_id = isr_feature['id']
    properties = dict(sorted(isr_feature['properties'].items()))

    # stations
    if "ISR_V_GEO_BETRIEBSSTELLEN_PUNKT" in feature_id:
        PROPERTIES = ISR_PROPERTIES_OPERATIONAL_POINT
        if isinstance(isr_feature['geometry'], type(None)):
            # project geo location from WGS84 (EPSG:4326) to UTM (EPSG:31467)
            point_wgs84 = Point(PROPERTIES['ALG_GEO_LAGE'][2](isr_feature['properties']['ALG_GEO_LAGE']))
            transformer = Transformer(source_cs='epsg:4326', target_cs='epsg:31467')
            point_epsg31467 = transformer.transform('source_to_target', Point((point_wgs84.y, point_wgs84.x)))
            # TODO: inverted (change in Transformer)
            coords_epsg31467 = point_epsg31467.y, point_epsg31467.x
        else:
            coords_epsg31467 = isr_feature['geometry']['coordinates']

    # track transitions
    elif "ISR_V_GEO_STRECKENUEBERGAENGE" in feature_id:
        PROPERTIES = ISR_PROPERTIES_JUNCTION
        coords_epsg31467 = isr_feature['geometry']['coordinates'][0]

    else:
        raise ValueError(f"Unknown element type: {feature_id}.")

    # create dict of type {'property': value}, where value is transformed from string to desired type
    properties = {
        key: l[2](value)
        for key, value, l in zip(PROPERTIES.keys(), properties.values(), PROPERTIES.values())
        if len(l) > 0
    }

    # create dict of type {'property': [property_description_short, property_description_long]}
    properties_info = {key: [l[0], l[1]] for key, l in zip(PROPERTIES.keys(), PROPERTIES.values()) if len(l) > 0}

    return OperationalPoint(coords_epsg31467, properties, properties_info)
