from isr_matcher._constants._filters import ISR_FILTERS
from isr_matcher._constants._parse import INT_TYPES, FLOAT_TYPES
from isr_matcher.geometry.track_segment import TrackSegment
from isr_matcher.geometry.operational_point import OperationalPoint
from isr_matcher.data_handlers.transformer import Transformer
from isr_matcher.ops._preprocessing import ISRPreprocessor
from isr_matcher._constants._parse import extract_station_names
from isr_matcher._constants._properties import (
    ISR_PROPERTIES_OPERATIONAL_POINT,
    ISR_PROPERTIES_JUNCTION,
    ISR_PROPERTIES_TRACK_SEGMENTS,
)
from isr_matcher._constants._filters import ISR_EXCEPTIONAL_STATION_NAMES
from isr_matcher._constants.logging import setup_logger
from pathlib import Path
from requests import post
from requests.exceptions import RequestException
import json
from json import dump as json_dump, loads as json_load
from typing import Literal, Union, Tuple, TypeVar, overload
from shapely.geometry.base import BaseGeometry
from shapely import Point, LineString, MultiLineString
import numpy as np
import pickle
from copy import deepcopy
import logging

# Type T: only instances of class BaseGeometry or subclasses (Point, Linestring, etc.)
T = TypeVar("T", bound="BaseGeometry")

# Create logger for the current module
setup_logger()
logger = logging.getLogger(__name__)


class RailDataImport:

    """
    Class that manages the aquisition of railway infrastructure data from ISR and other from file formats.

    Attributes
    ----------
    filters: list[str]
        List that contains the keys for available filters.

            "EQUALS_TRACK": Returns all tracks that match the given track number(s).
            "TRACKS_IN_BBOX": Returns all tracks within a bounding box.
            "OP_IN_BBOX": Returns all service points within a bounding box.
            "TRANSITIONS_IN_BBOX": Returns all transition points within a bounding box.
            "BBOX": Returns all tracks, service points and transition points within a bounding box.
            TODO: expand list

    """

    def __init__(self):
        self._filters = [
            "EQUALS_TRACK",
            "EQUALS_OP",
            "EQUALS_TRANSITION",
            "EQUALS_TRACK_SEG",
            "TRACKS_IN_BBOX",
            "OP_IN_BBOX",
            "TRANSITIONS_IN_BBOX",
            "TUNNEL_IN_BBOX",
            "BBOX",
            "TRACKS_IN_BOUNDARY",
            "OP_IN_BOUNDARY",
            "TRANSITIONS_IN_BOUNDARY",
            "TUNNEL_IN_BOUNDARY",
            "BOUNDARY",
        ]
        self._project_path = Path(__file__).parent.parent.parent.parent
        self._special_chars = ["Ä", "Ö", "Ü", "ä", "ö", "ü", "ß"]

    # define attributes as read-only
    @property
    def filters(self):
        return self._filters

    @property
    def project_path(self):
        return self._project_path

    def query_isr(
        self,
        filter_name: Literal[
            "EQUALS_TRACK",
            "EQUALS_OP",
            "EQUALS_TRANSITION",
            "EQUALS_TRACK_SEG",
            "TRACKS_IN_BBOX",
            "OP_IN_BBOX",
            "TRANSITIONS_IN_BBOX",
            "TUNNEL_IN_BBOX",
            "BBOX",
            "TRACKS_IN_BOUNDARY",
            "OP_IN_BOUNDARY",
            "TRANSITIONS_IN_BOUNDARY",
            "TUNNEL_IN_BOUNDARY",
            "BOUNDARY",
        ],
        args: list[str | int | float],
    ) -> dict | None:
        """
        Queries ISR based on the specified filter and arguments.

        Parameters
        ----------
        filter_name: Literal
            The type of filter to be applied. Choose from: TODO: UPDATE
                - 'EQUALS_TRACK': Query by track. 'args' is a tuple of (<track_nr>).
                - 'EQUALS_OP': Query by operational point. 'args' is a tuple of (<name>, <track_nr>).
                - 'EQUALS_TRACK_SEG': Query by track segment. 'args' is a tuple of (<track_nr>, <name>).
                - 'TRACKS_IN_BBOX': Query tracks within a bounding box. 'args' is a tuple of (<lon_min>, <lat_min>, <lon_max>, <lat_max>).
                - 'OP_IN_BBOX': Query operational points within a bounding box. 'args' is a tuple of (<lon_min>, <lat_min>, <lon_max>, <lat_max>).
                - 'TRANSITIONS_IN_BBOX': Query transitions within a bounding box. 'args' is a tuple of (<lon_min>, <lat_min>, <lon_max>, <lat_max>).
                - 'BBOX': Query using a general bounding box. 'args' is a tuple of (<lon_min>, <lat_min>, <lon_max>, <lat_max>).
                - 'BOUNDARY': Query using a boundary (LinearRing). 'args' is a tuple of (<string of coordinates seperated by space: "lon_1 lat_1 lon_2 lat_2 ... ">).

        args: list
            A list of arguments corresponding to the chosen filter. The interpretation of arguments depends on the selected filter.

        Returns
        -------
            response: dict
                A dictionary in JSON format if the query is successful; otherwise, returns None.

        Notes
        -----
        - The method validates the input parameters before creating the filter string.
        - Special characters in arguments are replaced by wildcards.
        - The method sends a request to the ISR API and returns the JSON response if the request is successful.
        - If the request fails or encounters an exception, None is returned.

        """

        # check input
        self._check_input_for_query(filter_name=filter_name, args=args)

        # create filter string
        filter_str = ISR_FILTERS[filter_name]
        for i, arg in enumerate(args):
            # replace special chars by wildcard
            new_arg = arg
            for char in self._special_chars:
                if isinstance(new_arg, str) and char in new_arg:
                    new_arg = new_arg.replace(char, '*')
            filter_str = filter_str.replace(f"$arg{i + 1}", str(new_arg))

        # send the request
        try:
            response = post(
                "https://geovdbn.deutschebahn.com/pgv-map/geoserver.action",
                data=filter_str,
                headers={"Content-Type": "application/json"},
            )
        except Exception:
            response = None

        if response is not None and response.status_code == 200:
            # The request was successful
            return response.json()
        else:
            # request was not successful
            return None

    @overload
    def query(
        self,
        filter_name: Literal["EQUALS_TRACK"],
        args: list[str | int | float],
        enhance_kilometrage: bool,
        cache_preprocessed_segments: bool,
    ) -> list[TrackSegment]:
        ...

    @overload
    def query(
        self,
        filter_name: Literal["EQUALS_TRACK_SEG"],
        args: list[str | int | float],
        enhance_kilometrage: bool,
        cache_preprocessed_segments: bool,
    ) -> TrackSegment:
        ...

    @overload
    def query(
        self,
        filter_name: Literal["EQUALS_OP"],
        args: list[str | int | float],
        enhance_kilometrage: bool,
        cache_preprocessed_segments: bool,
    ) -> OperationalPoint:
        ...

    @overload
    def query(
        self,
        filter_name: Literal["TRACKS_IN_BBOX"],
        args: list[str | int | float],
        enhance_kilometrage: bool,
        cache_preprocessed_segments: bool,
    ) -> list[TrackSegment]:
        ...

    @overload
    def query(
        self,
        filter_name: Literal["OP_IN_BBOX"],
        args: list[str | int | float],
        enhance_kilometrage: bool,
        cache_preprocessed_segments: bool,
    ) -> list[OperationalPoint]:
        ...

    @overload
    def query(
        self,
        filter_name: Literal["TRANSITIONS_IN_BBOX"],
        args: list[str | int | float],
        enhance_kilometrage: bool,
        cache_preprocessed_segments: bool,
    ) -> list[OperationalPoint]:
        ...

    @overload
    def query(
        self,
        filter_name: Literal["BBOX"],
        args: list[str | int | float],
        enhance_kilometrage: bool,
        cache_preprocessed_segments: bool,
    ) -> list[OperationalPoint | TrackSegment]:
        ...

    @overload
    def query(
        self,
        filter_name: Literal["BOUNDARY"],
        args: list[str | int | float],
        enhance_kilometrage: bool,
        cache_preprocessed_segments: bool,
    ) -> list[OperationalPoint | TrackSegment]:
        ...

    def query(
        self,
        filter_name: Literal[
            "EQUALS_TRACK",
            "EQUALS_OP",
            "EQUALS_TRANSITION",
            "EQUALS_TRACK_SEG",
            "TRACKS_IN_BBOX",
            "OP_IN_BBOX",
            "TRANSITIONS_IN_BBOX",
            "TUNNEL_IN_BBOX",
            "BBOX",
            "TRACKS_IN_BOUNDARY",
            "OP_IN_BOUNDARY",
            "TRANSITIONS_IN_BOUNDARY",
            "TUNNEL_IN_BOUNDARY",
            "BOUNDARY",
        ],
        args: list[str | int | float],
        enhance_kilometrage: bool = True,
        cache_preprocessed_segments: bool = True,
    ) -> Union[TrackSegment, list[TrackSegment], OperationalPoint, list[OperationalPoint]]:
        """
        Queries for objects according to 'filter_name' and 'args'. Objects are read from cache, if possible. If the object does not exist in the cache, a query is sent to ISR, and the object is created from the response.
        For filters BBOX and BOUNDARY, a query is sent to ISR with the geometric constraint. For each feature in the response, it is checked if the object can be read from the cache or if it must be created from the feature.

        Parameters
        ----------
        filter_name: Literal
            The type of filter to be applied. Choose from: TODO: Update
                - 'EQUALS_TRACK': Query by track. 'args' is a tuple of (<track_nr>).
                - 'EQUALS_OP': Query by operational point. 'args' is a tuple of (<name>, <track_nr>).
                - 'EQUALS_TRACK_SEG': Query by track segment. 'args' is a tuple of (<track_nr>, <name>).
                - 'TRACKS_IN_BBOX': Query tracks within a bounding box. 'args' is a tuple of (<lon_min>, <lat_min>, <lon_max>, <lat_max>).
                - 'OP_IN_BBOX': Query operational points within a bounding box. 'args' is a tuple of (<lon_min>, <lat_min>, <lon_max>, <lat_max>).
                - 'TRANSITIONS_IN_BBOX': Query transitions within a bounding box. 'args' is a tuple of (<lon_min>, <lat_min>, <lon_max>, <lat_max>).
                - 'BBOX': Query using a general bounding box. 'args' is a tuple of (<lon_min>, <lat_min>, <lon_max>, <lat_max>).
                - 'BOUNDARY': Query using a boundary (LinearRing). 'args' is a tuple of (<string of coordinates separated by space: "lon_1 lat_1 lon_2 lat_2 ... ">).

        args: list
            A list of arguments corresponding to the chosen filter. The interpretation of arguments depends on the selected filter.

        Returns
        -------
        response: Union[TrackSegment, list[TrackSegment], OperationalPoint, list[OperationalPoint]]
            Returns the queried objects. The return type depends on the chosen filter:
                - 'EQUALS_TRACK': Returns a list of TrackSegments.
                - 'EQUALS_OP': Returns an OperationalPoint.
                - 'EQUALS_TRACK_SEG': Returns a TrackSegment.
                - 'TRACKS_IN_BBOX': Returns a list of TrackSegments.
                - 'OP_IN_BBOX': Returns a list of OperationalPoints.
                - 'TRANSITIONS_IN_BBOX': Returns a list of TrackSegments.
                - 'BBOX': Returns a list of TrackSegments and OperationalPoints.
                - 'BOUNDARY': Returns a list of TrackSegments and OperationalPoints.

        Notes
        -----
        - The method validates the input parameters before creating the filter string.
        - Special characters in arguments are replaced by wildcards.
        - The method sends a request to the ISR API and returns the corresponding objects if the request is successful.
        - If the request fails or encounters an exception, an error is raised.
        """

        # check input
        self._check_input_for_query(filter_name=filter_name, args=args)

        # TRACKS
        if filter_name == 'EQUALS_TRACK':
            track_nr = args[0]
            names_and_track = []

            # query isr for json dict of all track segments
            response = self.query_isr(filter_name='EQUALS_TRACK', args=args)

            if response:
                track_segments = []
                # iterate over features
                for track_seg in response['features']:
                    # extract name and skip if name was already read (skips double entries)
                    # check for exceptional names
                    name = track_seg['properties']['ISR_STRECKE_VON_BIS']
                    if any([ex_name in name for ex_name in ISR_EXCEPTIONAL_STATION_NAMES]):
                        from_name, to_name = extract_station_names(track_name_string=name)
                        name = f'{from_name} - {to_name}'
                    name_ = name.replace('/', ' ')

                    km_type = 'raw' if enhance_kilometrage == False else 'enh'
                    file_path_1 = self.project_path / f'cache/track_segments/{track_nr}_{name}_{km_type}.pickle'
                    file_path_2 = (
                        self.project_path / f'cache/track_segments_continued/{track_nr}_{name}_{km_type}.pickle'
                    )

                    if file_path_1.exists():
                        track_segment = self._track_segment_from_pickle(file_path=file_path_1)

                    elif file_path_2.exists():
                        track_segment = self._track_segment_from_pickle(file_path=file_path_2)
                    else:
                        # query isr
                        name_ = name.replace('/', '*')

                        response = self.query_isr(filter_name='EQUALS_TRACK_SEG', args=[track_nr, name])
                        if response and len(response['features']) > 0:
                            track_segment = self._track_segment_from_feature_isr(
                                isr_feature=response['features'][0], enhance_kilometrage=enhance_kilometrage
                            )

                        else:
                            # request failed
                            # raise RequestException(f"An error occured while handling the request to ISR.")
                            continue

                    # skip double track segments (direction / opposite rail contains same geometry)
                    if (name, track_nr) in names_and_track and track_segment.properties[
                        'INF_GLEISANZAHL'
                    ] != 'eingleisig':
                        continue
                    names_and_track.append((name, track_nr))

                    track_segments.append(track_segment)

                return track_segments

            else:
                # request failed
                raise RequestException(f"An error occured while handling the request to ISR.")

        # TRACK SEGMENTS
        elif filter_name == 'EQUALS_TRACK_SEG':
            # filepath
            track_nr = args[0]
            name: str = args[1]  # type: ignore
            if any([ex_name in name for ex_name in ISR_EXCEPTIONAL_STATION_NAMES]):
                from_name, to_name = extract_station_names(track_name_string=name)
                name = f'{from_name} - {to_name}'
            name_ = name.replace('/', ' ')
            km_type = 'raw' if enhance_kilometrage == False else 'enh'
            file_path_1 = self.project_path / f'cache/track_segments/{track_nr}_{name}_{km_type}.pickle'
            file_path_2 = self.project_path / f'cache/track_segments_continued/{track_nr}_{name}_{km_type}.pickle'

            if file_path_1.exists():
                track_segment = self._track_segment_from_pickle(file_path=file_path_1)

            elif file_path_2.exists():
                track_segment = self._track_segment_from_pickle(file_path=file_path_2)

            else:
                # query isr
                args[1] = name.replace('/', '*')
                response = self.query_isr(filter_name='EQUALS_TRACK_SEG', args=args)

                if response:
                    track_segment = self._track_segment_from_feature_isr(
                        isr_feature=response['features'][0],
                        enhance_kilometrage=enhance_kilometrage,
                        cache_preprocessed_segments=cache_preprocessed_segments,
                    )
                else:
                    # request failed
                    raise RequestException(f"An error occured while handling the request to ISR.")

            return track_segment

        # OPERATIONAL POINTS
        elif filter_name == 'EQUALS_OP':
            track_nr = args[1]
            filepath = self.project_path / f'cache/operational_points/ops_track_{track_nr}.json'

            if not filepath.exists():
                # query ops for track and export json
                # have to query for betriebsstellen and streckenübergänge seperately
                # beacuse the API of ISR has changed and sending two queries in one
                # request is not working anymor
                response1 = self.query_isr(filter_name='EQUALS_OP', args=['*', track_nr])
                response2 = self.query_isr(filter_name='EQUALS_TRANSITION', args=['*', track_nr])

                if response1 and response2:
                    response = response1
                    response['features'] += response2['features']
                    self.export_json(response=response, filter_name='EQUALS_OP', args=['*', track_nr])
                else:
                    # request failed
                    raise RequestException(f"An error occured while handling the request to ISR.")

            operational_point = self._op_from_file(filepath, name=str(args[0]), track_nr=int(track_nr))

            return operational_point

        elif 'BBOX' in filter_name or 'BOUNDARY' in filter_name:
            # query isr for json dict of all track segments

            # have to query each feature type seperately (streckenabschnitte, betriebsstellen, streckenübergänge, tunnel)
            match filter_name:
                case 'BBOX':
                    subfilters = [filt for filt in self.filters if 'BBOX' in filt and filt != 'BBOX']
                case 'BOUNDARY':
                    subfilters = [filt for filt in self.filters if 'BOUNDARY' in filt and filt != 'BOUNDARY']
                case _:
                    subfilters = [filter_name]

            responses = []
            for filt in subfilters:
                response_ = self.query_isr(filter_name=filt, args=args)  # type: ignore
                responses.append(response_)

            if all(responses):
                logger.info('Query successful.')

                if len(responses) > 1:  # merge responses
                    response = responses[0]
                    for response_ in responses[1:]:
                        response['features'] += response_['features']

                names_and_track = []
                track_segments: list[TrackSegment] = []
                operational_points: list[OperationalPoint] = []
                transitions: list[OperationalPoint] = []
                # tunnels: list[Tunnel] TODO
                for feature in response['features']:
                    ID = feature['id']

                    if 'ISR_V_GEO_TEN_KLASSIFIZIERUNG' in ID:
                        # track segment

                        # extract attributes and format name (wildcard *)
                        track_nr = feature['properties']['ISR_STRE_NR']
                        name = feature['properties']['ISR_STRECKE_VON_BIS']
                        if any([ex_name in name for ex_name in ISR_EXCEPTIONAL_STATION_NAMES]):
                            from_name, to_name = extract_station_names(track_name_string=name)
                            name = f'{from_name} - {to_name}'
                        name = name.replace('/', '*')

                        km_type = 'raw' if enhance_kilometrage == False else 'enh'
                        filepath = self.project_path / f'cache/track_segments/{track_nr}_{name}_{km_type}.pickle'
                        matching_files = sorted(filepath.parent.glob(f'{track_nr}_{name}_{km_type}.pickle'))

                        if len(matching_files) == 1:
                            filepath = matching_files[0]
                            # load from file
                            track_segment = self._track_segment_from_pickle(file_path=filepath)
                            logger.info(f'Loaded from file: {track_nr} {name}.')

                        elif len(matching_files) > 1:
                            raise NotImplementedError('Not Implemented')

                        else:
                            # query isr
                            response = self.query_isr(filter_name='EQUALS_TRACK_SEG', args=[int(track_nr), str(name)])

                            if response:
                                logger.info(f'Preprocessing: {track_nr} {name}.')
                                track_segment = self._track_segment_from_feature_isr(
                                    isr_feature=response['features'][0],
                                    enhance_kilometrage=enhance_kilometrage,
                                    cache_preprocessed_segments=cache_preprocessed_segments,
                                )
                            else:
                                # request failed
                                raise RequestException(f"An error occured while handling the request to ISR.")

                        # skip double track segments (direction / opposite rail contains same geometry)
                        if (name, track_nr) in names_and_track and track_segment.properties[
                            'INF_GLEISANZAHL'
                        ] != 'eingleisig':
                            continue
                        names_and_track.append((name, track_nr))

                        track_segments.append(track_segment)

                    elif 'ISR_V_GEO_BETRIEBSSTELLEN_PUNKT' in ID:
                        # operational point
                        track_nr = feature['properties']['STRNR']
                        name = feature['properties']['BST_STELLE_NAME']
                        filepath = self.project_path / f'cache/operational_points/ops_track_{track_nr}.json'

                        if not filepath.exists():
                            # query ops for track and export json
                            response = self.query_isr(filter_name='EQUALS_OP', args=['*', track_nr])
                            if response:
                                self.export_json(response=response, filter_name='EQUALS_OP', args=['*', track_nr])
                            else:
                                # request failed
                                raise RequestException(f"An error occured while handling the request to ISR.")

                        operational_point = self._op_from_file(filepath, name=name, track_nr=int(track_nr))

                        operational_points.append(operational_point)

                    elif 'ISR_V_GEO_STRECKENUEBERGAENGE' in ID:
                        # operational point
                        track_nrs = [feature['properties']['STRECKE1'], feature['properties']['STRECKE2']]
                        name = feature['properties']['BST_STELLE_NAME']

                        for track_nr in track_nrs:
                            filepath = self.project_path / f'cache/operational_points/ops_track_{track_nr}.json'

                            if not filepath.exists():
                                # query ops for track and export json
                                response = self.query_isr(filter_name='EQUALS_OP', args=['*', track_nr])
                                if response:
                                    self.export_json(response=response, filter_name='EQUALS_OP', args=['*', track_nr])
                                else:
                                    # request failed
                                    raise RequestException(f"An error occured while handling the request to ISR.")

                            try:
                                transition = self._op_from_file(filepath, name=name, track_nr=int(track_nr))
                                transitions.append(transition)
                            except:
                                pass

                if 'TRACKS' in filter_name:
                    return track_segments

                elif 'OP' in filter_name:
                    return operational_points + transitions

                elif 'TRANSITION' in filter_name:
                    return transitions

                # elif 'TUNNEL' in filter_name:
                #    return tunnels

                else:  # all
                    return track_segments + operational_points + transitions  # + tunnels

            else:
                # request failed
                raise RequestException(f"An error occured while handling the request to ISR.")

        else:
            raise ValueError(f'Unknown filter: {filter_name}')

    def export_json(
        self,
        response: dict | None,
        filter_name: Literal[
            "EQUALS_TRACK",
            "EQUALS_OP",
            "EQUALS_TRACK_SEG",
            "TRACKS_IN_BBOX",
            "OP_IN_BBOX",
            "TRANSITIONS_IN_BBOX",
            "BBOX",
            "BOUNDARY",
        ],
        args: list[str | int | float],
        export_path: Path | None = None,
    ) -> dict | None:
        """
        Exports the response from an ISR query to a JSON file.

        Parameters
        ----------
        response: dict | None
            The response from the ISR query in JSON format. If None, raises a RequestException.

        filter_name: Literal
            The type of filter used in the ISR query. Choose from:
                - 'EQUALS_TRACK'
                - 'EQUALS_OP'
                - 'EQUALS_TRACK_SEG'
                - 'TRACKS_IN_BBOX'
                - 'OP_IN_BBOX'
                - 'TRANSITIONS_IN_BBOX'
                - 'BBOX'
                - 'BOUNDARY'

        args: list
            A list of arguments corresponding to the chosen filter. The interpretation of arguments depends on the selected filter.

        export_path: Path | None, optional
            The path to save the exported JSON file. If None, the default path is determined based on the filter and arguments.

        Returns
        -------
        None
            Exports the response to a JSON file at the specified path.

        Raises
        ------
        RequestException
            If the given response is None, indicating a failed request.

        ValueError
            If an unknown filter_name is provided.

        Notes
        -----
        - If export_path is not provided, it is determined based on the filter and arguments.
        - The exported JSON file is saved with utf-8 encoding and indented formatting for better readability.
        """

        if response:
            # set export path if no export path is given
            if not export_path:
                if filter_name == "EQUALS_TRACK":
                    export_path = self.project_path / f'cache/tracks/{args[0]}.json'

                elif filter_name == "EQUALS_TRACK_SEG":
                    export_path = self.project_path / f'cache/temp/track_segment_{args[0]}_{args[1]}.json'

                elif filter_name == 'EQUALS_OP':
                    if args[0] == '*':
                        export_path = self.project_path / f'cache/operational_points/ops_track_{args[1]}.json'
                    else:
                        export_path = self.project_path / f'cache/temp/{args[0]}_{args[1]}.json'

                elif filter_name == "TRACKS_IN_BBOX":
                    export_path = (
                        self.project_path / f'cache/temp/bbox_tracks_{args[0]}_{args[1]}_{args[2]}_{args[3]}.json'
                    )

                elif filter_name == "OP_IN_BBOX":
                    export_path = (
                        self.project_path / f'cache/temp/bbox_ops_{args[0]}_{args[1]}_{args[2]}_{args[3]}.json'
                    )

                elif filter_name == "TRANSITIONS_IN_BBOX":
                    export_path = (
                        self.project_path / f'cache/temp/bbox_transitions_{args[0]}_{args[1]}_{args[2]}_{args[3]}.json'
                    )

                elif filter_name == "BBOX":
                    export_path = self.project_path / f'cache/temp/bbox_{args[0]}_{args[1]}_{args[2]}_{args[3]}.json'

                elif filter_name == "BOUNDARY":
                    export_path = self.project_path / f'cache/temp/boundary_{args[0]}.json'

                else:
                    raise ValueError(f"Unkown Filter: {filter_name}")

            # save JSON
            with open(export_path, "w", encoding="utf-8") as f:
                json_dump(response, f, ensure_ascii=False, indent=4, sort_keys=True)

        else:
            # request failed
            raise RequestException(f"Given response is None. Export aborted.")

    def _check_input_for_query(
        self,
        filter_name: Literal[
            "EQUALS_TRACK",
            "EQUALS_OP",
            "EQUALS_TRACK_SEG",
            "TRACKS_IN_BBOX",
            "OP_IN_BBOX",
            "TRANSITIONS_IN_BBOX",
            "BBOX",
            "BOUNDARY",
        ],
        args: list[str | int | float],
    ):
        """
        Checks the validity of input parameters for an ISR query.

        Parameters
        ----------
        filter_name: Literal
            The type of filter to be applied. Choose from:
                - 'EQUALS_TRACK': Query by track. 'args' is a tuple of (<track_nr>).
                - 'EQUALS_OP': Query by operational point. 'args' is a tuple of (<name>, <track_nr>).
                - 'EQUALS_TRACK_SEG': Query by track segment. 'args' is a tuple of (<track_nr>, <name>).
                - 'TRACKS_IN_BBOX': Query tracks within a bounding box. 'args' is a tuple of (<lon_min>, <lat_min>, <lon_max>, <lat_max>).
                - 'OP_IN_BBOX': Query operational points within a bounding box. 'args' is a tuple of (<lon_min>, <lat_min>, <lon_max>, <lat_max>).
                - 'TRANSITIONS_IN_BBOX': Query transitions within a bounding box. 'args' is a tuple of (<lon_min>, <lat_min>, <lon_max>, <lat_max>).
                - 'BBOX': Query using a general bounding box. 'args' is a tuple of (<lon_min>, <lat_min>, <lon_max>, <lat_max>).
                - 'BOUNDARY': Query using a boundary (LinearRing). 'args' is a tuple of (<string of coordinates separated by space: "lon_1 lat_1 lon_2 lat_2 ... ">).

        args: list
            A list of arguments corresponding to the chosen filter. The interpretation of arguments depends on the selected filter.

        Raises
        ------
        ValueError
            If the filter_name is unknown.
            If the type of args is not a list.
            If the elements in args do not meet the expected types for the specified filter.
            If the number of elements in args is incorrect for the specified filter.
            If a 'BOUNDARY' filter is used, and args does not contain exactly one element: a string of coordinates separated by spaces.

        Notes
        -----
        - The method performs specific checks based on the filter_name to ensure the validity of input parameters for an ISR query.
        - Specific checks include verifying the types and number of elements in args based on the selected filter.
        - Raises a ValueError if any of the checks fail.
        """

        # check filter
        if not filter_name in self.filters:
            raise ValueError(f"Unknown filter: {filter_name}")
        # check type of args
        if not isinstance(args, list):
            raise ValueError(f"args must be of type list, passed type was {type(args)}")

        # check args for filter "EQUALS_TRACK"
        if filter_name == "EQUALS_TRACK":
            if not all([isinstance(val, (INT_TYPES, str)) for val in args]):
                raise ValueError(
                    f"When using filter 'EQUALS_TRACK', all elements in list args must be of typ int or str."
                )

        # check args for filter "EQUALS_OP"
        elif filter_name == "EQUALS_OP":
            if not isinstance(args[0], (INT_TYPES, str)):
                raise ValueError(
                    f"When using filter 'EQUALS_OP', first element in args must be of type str (name of operational point)."
                )
            if not isinstance(args[1], (INT_TYPES, str)):
                raise ValueError(
                    f"When using filter 'EQUALS_OP', second element in args must be of type int or str (track number)."
                )

        elif filter_name == "EQUALS_TRANSITION":
            if not isinstance(args[0], (INT_TYPES, str)):
                raise ValueError(
                    f"When using filter 'EQUALS_TRANSITION', first element in args must be of type str (name of transition)."
                )
            if not isinstance(args[1], (INT_TYPES, str)):
                raise ValueError(
                    f"When using filter 'EQUALS_TRANSITION', second element in args must be of type int or str (track number)."
                )

        # check args for filter "EQUALS_TRACK_SEG"
        elif filter_name == "EQUALS_TRACK_SEG":
            if not isinstance(args[0], (INT_TYPES, int)):
                raise ValueError(
                    f"When using filter 'EQUALS_TRACK_SEG', first element in args must be of type int (track number)."
                )
            if not isinstance(args[1], (INT_TYPES, str)):
                raise ValueError(
                    f"When using filter 'EQUALS_TRACK_SEG', second element in args must be of type str (track segment name)."
                )

        # check args for filters using "BBOX"
        elif "BBOX" in filter_name:
            if not len(args) == 4:
                raise ValueError(
                    "When using a 'BBOX' filter, the list args must contain exactly 4 elements: latitude_min, longitude_min, latitude_max and longitude_max."
                )

            if not all([isinstance(val, (FLOAT_TYPES, INT_TYPES)) for val in args]):
                raise ValueError(f"When using a 'BBOX' filter, all elements in list args must be of type float.")

        elif "BOUNDARY" in filter_name:
            if not (len(args) == 1) or type(args[0]) != str:
                raise ValueError(
                    "When using a 'BOUNDARY' filter, args must contain exactly one element: a string of coordinates seperated by spaces."
                )

            for val in args[0].split():
                try:
                    float(val)
                except:
                    raise ValueError(
                        "String coordinates can not be cast to float. Perhaps you used a comma instead of a point for decimals?"
                    )

        else:
            raise ValueError(f'Unknown filter: {filter_name}')

    # Operational Point methods

    @classmethod
    def _op_from_feature_isr(cls, isr_feature: dict) -> OperationalPoint:
        """
        Creates an OperationalPoint instance from ISR feature data.

        Parameters
        ----------
        isr_feature: dict
            The feature data obtained from the ISR API response.

        Returns
        -------
        OperationalPoint
            An instance of the OperationalPoint class representing the ISR feature.

        Raises
        ------
        ValueError
            If the feature type in the ISR data is unknown or unsupported.

        Notes
        -----
        - This method is used internally to create an OperationalPoint instance from ISR feature data.
        - It checks the feature type in the ISR data and extracts the relevant information.
        - The feature data is expected to contain 'id', 'properties', and 'geometry' keys.
        - The 'properties' key should contain a dictionary with property names as keys and their corresponding values as values.
        - The 'geometry' key should contain a dictionary with 'coordinates' key and the coordinates of the point.
        - The coordinates are transformed from WGS84 (EPSG:4326) to UTM (EPSG:31467).
        - The extracted information is used to create an OperationalPoint instance.
        """

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

    def _op_from_name_and_track_isr(
        self, name: str, track_nr: int, closest_to_geometry: Union[T, None] = None
    ) -> OperationalPoint:
        """
        Retrieves or creates an OperationalPoint instance based on the given name and track number.

        Parameters
        ----------
        name: str
            The name of the operational point.
        track_nr: int
            The track number associated with the operational point.
        closest_to_geometry: Union[T, None], optional
            An optional geometry (e.g., Point) used to find the closest OperationalPoint.
            If provided, the method calculates distances and selects the closest operational point.
            Default is None.

        Returns
        -------
        OperationalPoint
            An instance of the OperationalPoint class representing the specified operational point.

        Raises
        ------
        ValueError
            If no operational point is found with the given name and track number.

        Notes
        -----
        - This method queries the ISR API for operational points with the specified name and track number.
        - If there is a match, it creates an OperationalPoint instance from the ISR feature data.
        - If no match is found, it creates a placeholder OperationalPoint instance with limited information.
        - If there are multiple matches, the method selects the closest one based on the provided geometry or uses the first one if no geometry is provided.
        """

        # query ISR for operational points with matching name and track number

        if 'Leipzig-Semmelweiss' in name and track_nr == 6376:
            # station affiliated with 6376 and 6377 but in isr only exists with track nr 6377
            response = self.query_isr(filter_name="EQUALS_OP", args=[f"{name}", track_nr + 1])
            assert isinstance(response, dict)
            response['features'][0]['properties']['STRNR'] = 6376
        elif 'Köthen Süd' in name:
            response = self.query_isr(filter_name="EQUALS_OP", args=[f"{name}", 6403])
            assert isinstance(response, dict)
            response['features'][0]['properties']['STRNR'] = 6421
        else:
            response = self.query_isr(filter_name="EQUALS_OP", args=[f"{name}", track_nr])
            assert isinstance(response, dict)

        if len(response['features']) == 0:
            # empty properties dict for op's that don't exist in ISR
            isr_properties_op = ISR_PROPERTIES_OPERATIONAL_POINT
            keys = isr_properties_op.keys()
            properties = {key: [] for key in keys if len(isr_properties_op[key]) > 0}
            properties['STRNR'] = track_nr
            properties_info = {key: isr_properties_op[key] for key in keys if len(isr_properties_op[key]) > 0}

            if 'Frankfurt-Zehn Ruten' in name and len(name) == len('Frankfurt-Zehn Ruten'):
                properties['BST_STELLE_NAME'] = 'Frankfurt-Zehn Ruten'
                operational_point = OperationalPoint(
                    coords_epsg31467=(3474918, 5557118), properties=properties, properties_info=properties_info
                )

            elif 'Berlin-Spandau' in name and track_nr == 6107 and len(name) == len('Berlin-Spandau'):
                properties['BST_STELLE_NAME'] = 'Berlin-Spandau'
                operational_point = OperationalPoint(
                    coords_epsg31467=(3787180, 5830196), properties=properties, properties_info=properties_info
                )

            elif 'Wustermark Rbf Wot' in name and len(name) == len('Wustermark Rbf Wot'):
                properties['BST_STELLE_NAME'] = 'Wustermark Rbf Wot'
                operational_point = OperationalPoint(
                    coords_epsg31467=(3773494, 5831247), properties=properties, properties_info=properties_info
                )

            else:
                # no match: error
                raise ValueError(f"No operational point found with name = {name} for track = {track_nr}")

        elif len(response['features']) == 1:
            # one match: perfect

            operational_point = self._op_from_feature_isr(isr_feature=response['features'][0])

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
                operational_point = self._op_from_feature_isr(
                    isr_feature=response['features'][np.argmin(distances_list_m)]
                )
            # else take first OperationalPoint
            else:
                operational_point = self._op_from_feature_isr(isr_feature=response['features'][0])

        return operational_point

    def _op_from_file(
        self, filepath: Path, name: str, track_nr: int, closest_to_geometry: Union[T, None] = None
    ) -> OperationalPoint:
        """
        Retrieves or creates an OperationalPoint instance based on the given file path, name, and track number.

        Parameters
        ----------
        filepath: Path
            The file path to the JSON file containing the ISR features.
        name: str
            The name of the operational point.
        track_nr: int
            The track number associated with the operational point.
        closest_to_geometry: Union[T, None], optional
            An optional geometry (e.g., Point) used to find the closest OperationalPoint.
            If provided, the method calculates distances and selects the closest operational point.
            Default is None.

        Returns
        -------
        OperationalPoint
            An instance of the OperationalPoint class representing the specified operational point.

        Raises
        ------
        ValueError
            If no operational point is found with the given name and track number.

        Notes
        -----
        - This method reads the JSON file specified by the file path and searches for operational points with the given name and track number.
        - If there is a match, it creates an OperationalPoint instance from the ISR feature data.
        - If no match is found, it creates a placeholder OperationalPoint instance with limited information.
        - If there are multiple matches, the method selects the closest one based on the provided geometry or uses the first one if no geometry is provided.
        """

        # filepath must exist
        assert filepath.exists(), f'No file found for path: {filepath}'

        if 'Leipzig-Semmelweiss' in name and track_nr == 6376:
            # query ISR for operational points / junction with matching name and track number
            # TODO: check for file with track 6377
            # station affiliated with 6376 and 6377 but in isr only exists with track nr 6377
            response = self.query_isr(filter_name="EQUALS_OP", args=[f"{name}", track_nr + 1])
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

            # operational points that are not included in ISR (only by name in track segment name)
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

            elif 'Gelsenkirchen Streckenw. 2172/2230' in name and len(name) == len(
                'Gelsenkirchen Streckenw. 2172/2230'
            ):
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
                    coords_epsg31467=(3479662, 5821488), properties=properties, properties_info=properties_info  #
                )

            elif 'Ludwigshafen (Rh) BASF Südtor, W 529' in name and len(name) == len(
                'Ludwigshafen (Rh) BASF Südtor, W 529'
            ):
                operational_point = OperationalPoint(
                    coords_epsg31467=(3459473, 5484127), properties=properties, properties_info=properties_info  #
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

            elif 'Abzw Halle (Saale) Leuchtturm, W 6' in name and len(name) == len(
                'Abzw Halle (Saale) Leuchtturm, W 6'
            ):
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

            operational_point = self._op_from_feature_isr(isr_feature=response['features'][0])

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
                operational_point = self._op_from_feature_isr(
                    isr_feature=response['features'][np.argmin(distances_list_m)]
                )
            # else take first OperationalPoint
            else:
                operational_point = self._op_from_feature_isr(isr_feature=response['features'][0])

        return operational_point

    # Track Segment methods

    def _track_segment_from_pickle(self, file_path: Path) -> TrackSegment:
        """
        Read a TrackSegment from a pickle file.

        Parameters
        ----------
        file_path : Path
            The file path to the pickle file containing the serialized TrackSegment.

        Returns
        -------
        TrackSegment
            An instance of the TrackSegment class read from the pickle file.

        Raises
        ------
        ValueError
            If the given filepath does not exist or does not point to a pickle file.

        Notes
        -----
        - This method reads a TrackSegment instance serialized in a pickle file.
        - The file path must exist, and the file extension must be '.pickle'.
        - If successful, it returns the deserialized TrackSegment instance.
        - If the file path is invalid or the file is not a pickle file, a ValueError is raised.
        """

        if file_path.exists() and file_path.suffix == '.pickle':
            with open(file_path, "rb") as file:
                track_segment: TrackSegment = pickle.load(file)

            return track_segment

        else:
            raise ValueError(f'Given filepath does not exist or does not point to a pickle file: {file_path}')

    def _track_segment_from_track_and_name(
        self, track: int, name: str, allow_previous: bool = True, cache_preprocessed_segments: bool = True
    ) -> TrackSegment:
        """
        Create a TrackSegment instance from a track number and name.

        Parameters
        ----------
        track : int
            The track number for which the TrackSegment is to be created.
        name : str
            The name of the track segment.
        allow_previous : bool, optional
            If True, allows an TrackSegment instance to load previous track segments (used to compute kilometrage offset). If False, it does not allow. Default value should be used, which is True.

        Returns
        -------
        TrackSegment
            An instance of the TrackSegment class created from the specified track number and name.

        Notes
        -----
        - This method checks the cache for a previously saved TrackSegment.
        - If found in the cache, it loads and returns the TrackSegment from the pickle file.
        - If not found, it queries the ISR API for the specified track and name to create a new TrackSegment.
        """

        file_path_1 = self.project_path / f'cache/track_segments/{track}_{name}.pickle'
        file_path_2 = self.project_path / f'cache/track_segments_continued/{track}_{name}.pickle'

        if file_path_1.exists():
            track_segment = self._track_segment_from_pickle(file_path=file_path_1)

        elif file_path_2.exists():
            track_segment = self._track_segment_from_pickle(file_path=file_path_2)

        else:
            response = self.query_isr(filter_name='EQUALS_TRACK_SEG', args=[track, name])
            assert isinstance(response, dict)
            track_segment = self._track_segment_from_feature_isr(
                isr_feature=response,
                allow_previous=allow_previous,
                cache_preprocessed_segments=cache_preprocessed_segments,
            )

        return track_segment

    def _track_segment_from_feature_isr(
        self,
        isr_feature: dict,
        allow_previous: bool = True,
        enhance_kilometrage: bool = True,
        cache_preprocessed_segments: bool = True,
    ) -> TrackSegment:
        """
        Create a TrackSegment instance from ISR response (JSON dictionary).

        Parameters
        ----------
        isr_feature : dict
            The ISR response containing information about the track segment in JSON dictionary format.
        allow_previous : bool, optional
            If True, allows an TrackSegment instance to load previous track segments (used to compute kilometrage offset). If False, it does not allow. Default value should be used, which is True.

        Returns
        -------
        TrackSegment
            An instance of the TrackSegment class created from the ISR response.

        Notes
        -----
        - This method extracts relevant information from the ISR response to create a TrackSegment instance.
        - It checks if the feature in the response corresponds to a track segment based on its feature ID.
        - It parses the properties and creates a dictionary of track segment properties with their corresponding values.
        - It retrieves operational points (stations) associated with the start and end of the track segment.
        - It preprocesses the track segment lines using an ISR preprocessor.
        - It creates a TrackSegment instance with processed lines, properties, and operational points.
        """

        # extract feature id and properties
        feature_id = isr_feature['id']
        properties = dict(sorted(isr_feature['properties'].items()))
        track_nr = int(properties['ISR_STRE_NR'])
        name = properties['ISR_STRECKE_VON_BIS']
        track_type = properties['INF_GLEISANZAHL']

        if any([ex_name in name for ex_name in ISR_EXCEPTIONAL_STATION_NAMES]):
            from_name, to_name = extract_station_names(track_name_string=name)
            name_ = f'{from_name} - {to_name}'
            name_ = name_.replace('/', '*')
        else:
            name_ = name

        # extract properties for opposite track (if double track)
        if track_type != 'eingleisig':
            # query with same track nr and name
            response = self.query_isr('EQUALS_TRACK_SEG', args=[track_nr, name_])
            n_elements = len(response['features'])  # number of found elements

            if n_elements == 0:
                raise ValueError('No elements found')
            elif n_elements == 1:
                raise ValueError(f'Found only one track but track type is {track_type}')
            else:
                for element in response['features']:
                    if (
                        element['properties']['ISR_STRECKE_VON_BIS'] == name
                        and element['properties']['INF_GLEISANZAHL'] != track_type
                    ):
                        properties_2 = dict(sorted(element['properties'].items()))
                        break

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

        # name of file with ops for track
        track_ops_file_path = (
            Path(__file__).parent.parent.parent.parent / f'cache/operational_points/ops_track_{track_nr}.json'
        )

        if not track_ops_file_path.exists():
            # query all operational points for track and write to cache
            response1 = self.query_isr(filter_name='EQUALS_OP', args=['*', track_nr])
            response2 = self.query_isr(filter_name='EQUALS_TRANSITION', args=['*', track_nr])
            response = response1
            response['features'] += response2['features']
            assert isinstance(response, dict)
            self.export_json(response=response, filter_name='EQUALS_OP', args=['*', track_nr])

        # get names of stations at start and end of track segment
        from_name, to_name = extract_station_names(track_name_string=name, split_only=True)

        # read operational points from cache
        operational_point_from = self._op_from_file(
            filepath=track_ops_file_path,
            name=from_name,
            track_nr=track_nr,
            closest_to_geometry=isr_original_lines_epsg31467,
        )
        operational_point_to = self._op_from_file(
            filepath=track_ops_file_path,
            name=to_name,
            track_nr=track_nr,
            closest_to_geometry=isr_original_lines_epsg31467,
        )

        # preprocess track segment lines
        isr_preprocessor = ISRPreprocessor(
            operational_point_from=operational_point_from, operational_point_to=operational_point_to
        )
        lines_processed = isr_preprocessor.process_track_segment_lines(lines=list(isr_original_lines_epsg31467.geoms))

        # create instance
        track_segment = TrackSegment(
            lines_processed,
            properties,
            properties_2,
            properties_info,
            operational_point_from,
            operational_point_to,
            enhance_kilometrage,
            allow_previous,
            cache_preprocessed_segments,
        )

        return track_segment
