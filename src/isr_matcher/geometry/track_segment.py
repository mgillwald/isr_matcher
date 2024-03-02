from __future__ import annotations
from shapely import Point, LineString, MultiLineString, affinity
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points, split
from typing import Tuple, Dict, Union, TypedDict, TYPE_CHECKING, TypeVar, Literal, overload
from isr_matcher.geometry.operational_point import OperationalPoint
from isr_matcher.geometry.rail import Rail
from isr_matcher.geometry.kilometrage import Kilometrage
from isr_matcher._constants._km_directions import KM_DIR_DICT
from isr_matcher.ops._preprocessing import ISRPreprocessor
from isr_matcher._constants._parse import km_to_db_km, db_km_to_km, extract_station_names
from isr_matcher._constants._filters import ISR_EXCEPTIONAL_STATION_NAMES
from isr_matcher.ops._functions import (
    angle_between,
    flatten_list,
    lines_are_parallel,
    only_km_db,
)
from isr_matcher.data_handlers.import_functions import query_track_segment
import numpy as np
from pathlib import Path
import json
from copy import deepcopy
import pickle
import bisect
from isr_matcher._constants.logging import setup_logger
import logging


# Type T: only instances of class BaseGeometry or subclasses (Point, Linestring, etc.)
T = TypeVar("T", bound="BaseGeometry")


# TypedDict
class Layout(TypedDict):
    """TypedDict for type hinting"""

    direction_1: list[list[int]]  # all paths in direction 1
    direction_2: list[list[int]]  # all paths in direction 2
    monorails: list[int]  # all monorails (bidrectional)
    direction_1_rails: list[int]  # all rails with direction 1 (one-directional)
    direction_2_rails: list[int]  # all rails with direction 2 (one-directional)
    parallel: list[Tuple[int, int]]  # all rails which are parallel
    siding: list[Tuple[int, int]]
    lines: list[LineString]


# Create logger for the current module
setup_logger()
logger = logging.getLogger(__name__)


class TrackSegment:
    """TODO"""

    @staticmethod
    def read_track_km_dict():
        """Load supplementary kilometrage information. Dataset (db-geo-strecken) is preprocessed in script 'util_write_km_points_from_geo_strecken.py' and required information saved as dict to 'track_resources/tracks_kms.json'"""
        # paths
        project_path = Path(__file__).parent.parent
        filepath = project_path / f'_constants/tracks_kms.json'
        # read json file
        with open(filepath) as f:
            track_km_dict = json.load(fp=f)

        return track_km_dict

    @staticmethod
    def read_track_length_dict():
        """Load supplementary kilometrage information. Dataset (db-geo-strecken) is preprocessed in script 'util_write_km_points_from_geo_strecken.py' and required information saved as dict to 'track_resources/tracks_kms.json'"""
        # paths
        project_path = Path(__file__).parent.parent
        filepath = project_path / f'_constants/tracks_lengths.json'
        # read json file
        with open(filepath) as f:
            track_length_dict = json.load(fp=f)

        return track_length_dict

    track_km_dict = read_track_km_dict()
    track_length_dict = read_track_length_dict()

    def __init__(
        self,
        lines: list[LineString],
        properties: Dict[str, Union[str, float, int]],
        properties_2: Dict[str, Union[str, float, int]] | None,
        properties_info: Dict[str, Tuple[str, str]],
        operational_point_from: OperationalPoint,
        operational_point_to: OperationalPoint,
        enhance_kilometrage: bool = True,
        allow_previous: bool = True,
        cache_preprocessed_segments: bool = True,
    ):
        # set attributes
        self._properties = deepcopy(properties)
        self._properties_2 = deepcopy(properties_2)
        self._properties_info = properties_info
        self._operational_point_from = operational_point_from
        self._operational_point_to = operational_point_to
        self._km_from = properties["ISR_KM_VON"]
        self._km_to = properties["ISR_KM_BIS"]
        self._length = round(self.km_to - self.km_from, 3)
        self._id = properties["ID"]
        self._name = properties["ISR_STRECKE_VON_BIS"].replace('/', ' ')  # type: ignore
        self._track_nr = properties["ISR_STRE_NR"]
        try:  # track numbers not in GEO-STRECKENNETZ are missing in KM_DIR_DICT
            self._n_km_lines = 1 if KM_DIR_DICT[self.track_nr] == False else 2
        except KeyError:
            self._n_km_lines = 1 if properties['INF_GLEISANZAHL'] == 'eingleisig' else 2
        self._lines = lines
        self._enhance_kilometrage = enhance_kilometrage
        self._allow_previous = allow_previous

        # paths
        km_type = 'raw' if enhance_kilometrage == False else 'enh'
        self.project_path = Path(__file__).parent.parent.parent.parent
        self.cache_path = self.project_path / f'cache/track_segments/{self.track_nr}_{self.name}_{km_type}.pickle'

        # compute layout of rails in both directions (and identify monorails) (example: [r0, (r1,2), (r3,r4)] -> direction 1: r0-r1-r3, direction 2: r4-r2-r0)
        layout = self._compute_track_segment_layout(lines=lines)
        layout['lines'] = lines
        self._layout = layout

        # create rail instances
        self._rails = [Rail(line, [line.coords for line in lines], layout, self.name, self.track_nr) for line in lines]

        # consider special cases
        self._special_cases()

        # compute incline
        self._incline_dict = self.compute_incline()

        # compute kilometrage line(s)
        self._compute_kilometrage()

        # TODO: make integration of km points from db-geo-strecken data set optional
        # postprocess kilometrage lines: add km info from db-geo-strecken (including jumps)
        # also extends km lines if kilometrage points are placed accordingly
        self._integrate_kilometrage_points()

        if self._enhance_kilometrage:
            # offset: store km line error of previous track last segment (for identifying misaligned segment transitions in kilometer computation)
            self._compute_kilometrage_offset()

        # write preprocessed track segment to cache if it does not exist in cache
        if not self.cache_path.exists() and cache_preprocessed_segments == True:
            self.pickle_self_to_cache()

        # TODO: close gaps between lines (e.g 1120 Hamburg-Hasselbrook - Hamburg Hbf)

    # getter and setter methods
    @property
    def element_type(self) -> str:
        """Returns the type as string.

        Returns
        -------
        type: Layout
            The type as string."""
        return 'TrackSegment'

    @property
    def layout(self) -> Layout:
        """Computes the rail layout of track segment.

        Returns
        -------
        layout: Layout
            The rail layout of the track segment."""
        return self._layout

    @property
    def operational_point_from(self) -> OperationalPoint:
        """Returns the operational point at the start of track segment.

        Returns
        -------
        operational_point_from: OperationalPoint
            The operational point at the start of track segment."""
        return self._operational_point_from

    @property
    def operational_point_to(self) -> OperationalPoint:
        """Returns the operational point at the end of track segment.

        Returns
        -------
        operational_point_to: OperationalPoint
            The operational point at the end of track segment."""
        return self._operational_point_to

    @property
    def properties(self) -> Dict[str, str | float | int]:
        """Returns the properties dictionary. This dictionary contains all information for track segment (Richtungsgleis / eingleisig) from ISR.

        Returns
        -------
        properties: Dict[str, str | float | int]
            Dictionary with track segment information from ISR."""
        return self._properties

    @property
    def properties_2(self) -> Dict[str, str | float | int] | None:
        """Returns the properties dictionary. This dictionary contains all information for track segment (Gegengleis, if exists) from ISR.

        Returns
        -------
        properties: Dict[str, str | float | int] | None
            Dictionary with track segment information from ISR for Gegengleis. If track does not have a Gegengleis, None is returned.
        """
        return self._properties_2

    @properties.setter
    def properties(self, value: Dict[str, str | float | int]):
        """Sets properties dictionary for Richtungsgleis / eingleisig."""
        self._properties = value

    @properties_2.setter
    def properties_2(self, value: Dict[str, str | float | int]):
        """Sets properties dictionary for Gegengleis."""
        self._properties_2 = value

    @property
    def properties_info(self) -> Dict[str, Tuple[str, str]]:
        """Returns the properties info dictionary. This dictionary contains all information about attributes contained in 'properties'.

        Returns
        -------
        properties: Dict[str, str | float | int]
            Dictionary withinformation about attributes in 'properties'."""
        return self._properties_info

    @property
    def lines(self) -> list[LineString]:
        """Returns the lines of the track segment as list of LineString.

        Returns
        -------
        rails: list[LineString]
            The lines of the track segment.
        """
        return self._lines

    @property
    def lines_1(self):
        """Returns all rails of the track segment running in direction 1.

        Returns
        -------
        rails: list[LineString]
            All rails of the track segment running in direction 1.
        """
        layout = self.layout
        return [self.lines[i] for i in range(len(self.lines)) if i in layout['direction_1'][0]]

    @property
    def lines_2(self):
        """Returns all rails of the track segment running in direction 2.

        Returns
        -------
        rails: list[LineString]
            All rails of the track segment running in direction 2.
        """
        layout = self.layout
        return [self.lines[i] for i in range(len(self.lines)) if i in layout['direction_2'][0]]

    @property
    def rails(self) -> list[Rail]:
        """Returns the rails of the track segment as list of LineString.

        Returns
        -------
        rails: list[LineString]
            The rails of the track segment.
        """
        return self._rails

    @property
    def rails_1(self):
        """Returns all rails of the track segment running in direction 1.

        Returns
        -------
        rails: list[LineString]
            All rails of the track segment running in direction 1.
        """
        layout = self.layout
        return [self.rails[i] for i in range(len(self.rails)) if i in layout['direction_1'][0]]

    @property
    def rails_2(self):
        """Returns all rails of the track segment running in direction 2.

        Returns
        -------
        rails: list[LineString]
            All rails of the track segment running in direction 2.
        """
        layout = self.layout
        return [self.rails[i] for i in range(len(self.rails)) if i in layout['direction_2'][0]]

    @property
    def length_nominal(self) -> float:
        """The nominal length of track segment in kilometer according to official kilometrage, in km."""
        return self._length

    @property
    def length_nominal_isr(self) -> float:
        """The nominal length of track segment as stated in ISR, in km."""
        return self._properties['ALG_LAENGE_ABSCHNITT']

    @property
    def length_geometric(self) -> float:
        """The geometric length of track segment in kilometer according to actual geometry of track segment."""
        # TODO
        return self.kilometrage.length_nominal_km

    @property
    def length_geometric_nominal(self) -> float:
        """The nominal geometric length of track segment in kilometer according to Deutsche Bahn."""
        # TODO
        pass

    @property
    def length_nominal_m(self) -> float:
        """The nominal length of track segment in kilometer according to official kilometrage, in m."""
        return self._length * 1000

    @property
    def kilometrage(self) -> Kilometrage:
        """Returns the kilometrage instance."""
        return self._kilometrage

    @property
    def km_from_db(self) -> str:
        """Kilometrage value at operational_point_from, in DB format."""
        return str(self._km_from)

    @property
    def km_to_db(self) -> str:
        """Kilometrage value at operational_point_to, in DB format."""
        return str(self._km_to)

    @property
    def km_from(self) -> float:
        """Kilometrage value at operational_point_from, as float (float value includes overlength or underlength)."""
        return round(db_km_to_km(self.km_from_db), 3)

    @property
    def km_to(self) -> float:
        """Kilometrage value at operational_point_to, as float (float value includes overlength or underlength)."""
        return round(db_km_to_km(self.km_to_db), 3)

    @property
    def id(self) -> int:
        """ID of segment in ISR."""
        return int(self._id)

    @property
    def name(self) -> str:
        """Name of track segment (station_from - station_to)."""
        return str(self._name)

    @property
    def track_nr(self) -> int:
        """Track number the track segment belongs to."""
        return int(self._track_nr)

    @property
    def incline_dict(self) -> dict:
        """Returns dictionary with incline information."""
        return self._incline_dict

    @overload
    def km(self, point: Point, direction: Union[int, str], return_type: Literal['db']) -> str:
        ...

    @overload
    def km(self, point: Point, direction: Union[int, str], return_type: Literal['float']) -> float:
        ...

    def km(
        self, point: Point, direction: Union[int, str] = 0, return_type: Literal['db', 'float'] = 'float'
    ) -> Union[str, float]:
        """Compute the kilometrage for given coordinates 'point', direction 'direction' and in the desired format 'return_type'."""

        if direction in ['0', '1', '2']:
            direction = int(direction)
        elif direction in [0, 1, 2]:
            pass
        else:
            raise ValueError(f'Received direction={direction}, direction must be 0, 1 or 2.')

        # get attributes
        lines = self.rails

        # assert point is on rails
        distances_to_lines = [line.distance(point) for line in lines]
        min_distance_m = np.min(distances_to_lines)

        km = self.kilometrage.km(point=point, direction=direction, return_type=return_type)

        return km

    def point(self, km: float, direction: int) -> Point:
        """Compute the kilometrage for given coordinates 'point', direction 'direction' and in the desired format 'return_type'."""

        # assert km's are in range
        # assert (km >= self.km_from) and (km <= self.km_to), ValueError(f'Given kilometer must be in range of track segment: {self.km_from} - {self.km_to} km.')

        # find next smaller km value given 'km'
        km_values = self.kilometrage.values_in_direction(direction=direction)
        km_values = np.unique([round(db_km_to_km(km), 3) for km in km_values]).tolist()
        next_smaller_idx = bisect.bisect(km_values, km)

        # select corresponding kilometrage line
        idx_dir = 0 if direction < 2 else 1
        if idx_dir == len(self.kilometrage.lines):
            idx_dir = 0
        if km == km_values[-1] or (len(km_values) > 1 and km_values[-1] > self.km_to and km == km_values[-2]):
            next_smaller_idx -= 1
        if km < self.km_from:
            next_smaller_idx = 1

        if len(self.kilometrage.lines[idx_dir]) == 1:
            km_line = self.kilometrage.lines[idx_dir][0]
        else:
            if next_smaller_idx - 1 == len(self.kilometrage.lines[idx_dir]):
                km_line = self.kilometrage.lines[idx_dir][next_smaller_idx - 2]
            else:
                km_line = self.kilometrage.lines[idx_dir][next_smaller_idx - 1]

        # get diff: km_diff = km - smaller_km
        km_diff = km - km_values[next_smaller_idx - 1]
        if km_diff < 0:
            km_diff = 0

        # project
        p = km_line.interpolate(km_diff * 1000)

        # test_km = self.km(p, direction=direction, return_type='float')

        return p

    def distance(self, geom: T) -> float:
        """Returns the shortest distance of track segment to another shapely object 'geom'.

        Returns
        -------
        min_distance_m: float
            The shortest distance between 'self' and 'geom', in m.
        """
        rails = self.rails
        distances_m = []
        for rail in rails:
            distance_m = rail.distance(geom)
            distances_m.append(distance_m)
        min_distance_m = np.min(distances_m)
        return min_distance_m

    def _compute_kilometrage(self):
        """Computes kilometrage lines for track segment and uses them to instantiate instance of class Kilometrage, which is set as attribute and handles everything kilometrage related.

        Kilometrage lines are computed either as middle line of rail (monorails) or as middle line of two parallel rails (parallel rails). This is done for each segment of track segment seperately, afterwards the kilometrage lines are joined to one line.
        """

        # fetch attributes
        lines = self._lines
        layout = self._layout
        n_km_lines = self._n_km_lines

        if n_km_lines != 1 and n_km_lines != 2:
            raise ValueError(f'invalid value for n_km_lines: {n_km_lines} (must be 1 or 2)')

        # isr preprocessor
        isr_preprocessor = ISRPreprocessor(
            operational_point_from=self.operational_point_from, operational_point_to=self.operational_point_to
        )

        # all paths in direction 1
        layout_rails = layout['direction_1']
        n_paths = len(layout_rails)
        # all parallel rails
        index_parallel = layout['parallel']
        # all monorails
        index_monorail = layout['monorails']

        # path with least number of rails (= path without sidings)
        if n_paths >= 1:
            path = min(layout_rails, key=len)
        else:
            raise ValueError(f'Layout contains no path. Computing kilometrage line not possible.')

        if n_km_lines == 1:
            # if path is a single monorail
            if (len(path) == 1) and (path[0] in index_monorail):
                # take this rail as kilometrage line
                kilometrage_line = [lines[path[0]]]

            else:
                # for monorail: append as is
                # for parallel rails: compute middle line

                kilometrage_lines: list[LineString] = []
                for indice in path:
                    # parallel lines
                    if indice in flatten_list(index_parallel):
                        for index in index_parallel:
                            if indice in index:
                                # get parallel lines
                                line_1 = lines[index[0]]
                                line_2 = lines[index[1]]

                                difference_m = line_1.length - line_2.length
                                d_start_m = Point(line_1.coords[0]).distance(Point(line_2.coords[0]))
                                d_end_m = Point(line_1.coords[-1]).distance(Point(line_2.coords[-1]))

                                one_line_exists_with_length_close_to_km = (
                                    abs(self.length_nominal_m - line_1.length) < 3
                                    and abs(self.length_nominal_m - line_2.length) > 3
                                ) or (
                                    abs(self.length_nominal_m - line_2.length) < 3
                                    and abs(self.length_nominal_m - line_1.length) > 3
                                )  # for two lines only
                                if abs(difference_m) > 15 and (
                                    (d_start_m > 10)
                                    or (d_end_m) > 10
                                    or (len(lines) == 2 and one_line_exists_with_length_close_to_km)
                                ):
                                    # identify longer and shorter line
                                    if difference_m > 0:
                                        line_l = line_1
                                        line_s = line_2
                                    else:
                                        line_l = line_2
                                        line_s = line_1

                                    # if parallel lines have different lengths, take that line as km reference that results in less kilometrage error
                                    # testing is done by summing over all line lengths in path
                                    path_length_diff_longer_line = abs(
                                        self.length_nominal_m
                                        - line_l.length
                                        - sum(
                                            [lines[k].length for k in path if lines[k] != line_l and lines[k] != line_s]
                                        )
                                    )
                                    path_length_diff_shorter_line = abs(
                                        self.length_nominal_m
                                        - line_s.length
                                        - sum(
                                            [lines[k].length for k in path if lines[k] != line_s and lines[k] != line_l]
                                        )
                                    )

                                    if path_length_diff_longer_line <= path_length_diff_shorter_line:
                                        kilometrage_lines.append(line_l)
                                    else:
                                        kilometrage_lines.append(line_s)

                                else:
                                    # compute middle line
                                    middle_line = self._compute_middle_line(line_1=line_1, line_2=line_2)
                                    km_coords = middle_line.coords[:]
                                    angles = [
                                        angle_between(
                                            np.array(km_coords[i + 1]) - np.array(km_coords[i]),
                                            np.array(km_coords[i + 2]) - np.array(km_coords[i + 1]),
                                        )
                                        for i in range(len(km_coords) - 2)
                                    ]

                                    if len(angles) > 0:
                                        if max(angles) > 30 and len(index_parallel) == 1:
                                            offical_length_m = self.length_nominal_m
                                            diff1 = abs(offical_length_m - line_1.length)
                                            diff2 = abs(offical_length_m - line_2.length)
                                            min_diff = np.argmin([diff1, diff2])
                                            middle_line = [line_1, line_2][min_diff]

                                    # append
                                    kilometrage_lines.append(middle_line)

                                # special case: two monorails after another that are not connected (can be partly parralel, with one line continuing further than the other)
                                if (
                                    (path == [0, 1] or path == [1, 0])
                                    and lines[path[0]].length < self.length_nominal_m
                                    and lines[0].length + lines[1].length >= self.length_nominal_m
                                    and len(lines) == 2
                                ):
                                    # lines in path direction
                                    line_1 = lines[path[0]]
                                    line_2 = lines[path[1]]

                                    ep_projected_on_line_2 = nearest_points(Point(line_1.coords[-1]), line_2)[1]
                                    distance_along_line_2 = line_2.project(ep_projected_on_line_2, normalized=True)

                                    if distance_along_line_2 <= 0.9:
                                        line_2_segment = split(line_2, ep_projected_on_line_2)[1]
                                        kilometrage_lines.append(line_2_segment)

                    # monorails
                    else:
                        # append
                        kilometrage_lines.append(lines[indice])

                # kilometrage line: merge segments and smoothen links
                kilometrage_line = isr_preprocessor.merge_lines_and_smoothen_links(
                    lines=kilometrage_lines, merge_km_line=True
                )

            self._kilometrage = Kilometrage(km_lines=[kilometrage_line], enhance_kilometrage=self._enhance_kilometrage)

        if n_km_lines == 2:
            # merge segments in each direction to create two km lines
            layout_rails_1 = layout['direction_1']
            # path with least number of rails (= path without sidings)
            if len(layout_rails_1) >= 1:
                path1 = min(layout_rails_1, key=len)
            else:
                raise ValueError('Should not happen')  # TODO

            layout_rails_2 = layout['direction_2']
            if len(layout_rails_2) >= 1:
                path2 = min(layout_rails_2, key=len)
            else:
                raise ValueError('Should not happen')  # TODO
            if self.name in 'Mannheim Rbf Gr G, W 105 - Mannheim Rbf Gr K Kn, W 650':
                path1.reverse()
                path2.reverse()
            kilometrage_lines_1 = isr_preprocessor.merge_lines_and_smoothen_links(lines=lines, merge_index=[path1])
            kilometrage_lines_2 = isr_preprocessor.merge_lines_and_smoothen_links(
                lines=lines, merge_index=[path2[::-1]]
            )  # reverse due to sorting of lines

            self._kilometrage = Kilometrage(
                km_lines=[kilometrage_lines_1, kilometrage_lines_2], enhance_kilometrage=self._enhance_kilometrage
            )

    def incline(self, km: float, direction: int):
        """
        Returns incline of track segment at postion given by 'km'. Inclines are taken from ISR and are assumed piecewise constant, as stated in ISR.

        TODO
        """

        # if incline information is available for track segment
        if not isinstance(self.incline_dict['inclines_dir1'], type(None)):
            km = round(km, 3)

            # assert km is in range of track
            # assert km >= self.km_from, ValueError(f"'km' must be in range of track segment: {self.km_from} - {self.km_to}") # km <= self.km_to and

            # assert direction
            assert direction in [0, 1, 2], ValueError('Direction must be 0, 1 or 2.')

            # find next smaller km to 'km' in incline profile (index)
            if direction == 0 or direction == 1 or isinstance(self.incline_dict['inclines_dir2'], type(None)):
                # get incline value by index
                next_smaller_idx = bisect.bisect(self.incline_dict['incline_kms_dir1'], km)
                value = self.incline_dict['inclines_dir1'][next_smaller_idx - 1]
            else:
                # get incline value by index
                next_smaller_idx = bisect.bisect(self.incline_dict['incline_kms_dir2'], km)
                value = self.incline_dict['inclines_dir2'][next_smaller_idx - 1]

            if direction == 2:
                value = -value

        # no incline information available
        else:
            value = np.nan

        return value

    def incline_profile(self, km_from: float, km_to: float):
        """Returns the incline profile of track segment, starting from 'km_from' and ending at 'km_to'."""

        km_from = round(km_from, 3)
        km_to = round(km_to, 3)

        # assert km is in range of track
        #        assert km_from >= self.km_from, ValueError(f"'km' must be in range of track segment: {self.km_from} - {self.km_to}") # km_to <= self.km_to and

        # moving direction
        km_diff = km_to - km_from
        if km_diff > 0:
            direction = 1
        elif km_diff < 0:
            direction = 2
            km_from, km_to = km_to, km_from
        else:
            raise ValueError('Values for km_from and km_to are equal.')

        if direction == 1:
            # if incline information is available for track segment
            if not isinstance(self.incline_dict['inclines_dir1'], type(None)):
                # find next smaller km to 'km' in incline profile (index)

                # get incline profile for direction 1
                kms_dir1 = self.incline_dict['incline_kms_dir1']
                inclines_dir1 = self.incline_dict['inclines_dir1']
                if km_from < kms_dir1[0]:
                    next_smaller_idx = 1
                else:
                    next_smaller_idx = bisect.bisect(kms_dir1, km_from)
                next_higher_idx = bisect.bisect(kms_dir1, km_to)

                kms = [km_from] + kms_dir1[next_smaller_idx:next_higher_idx] + [km_to]
                inclines = inclines_dir1[next_smaller_idx - 1 : next_higher_idx]
                inclines += [inclines[-1]]

            elif not isinstance(self.incline_dict['inclines_dir2'], type(None)):
                # get incline profile for direction 1 if direction 2 is not available (-> "Auf Anfrage")
                kms_dir1 = self.incline_dict['incline_kms_dir2']
                inclines_dir1 = self.incline_dict['inclines_dir2']
                if km_from < kms_dir1[0]:
                    next_smaller_idx = 1
                else:
                    next_smaller_idx = bisect.bisect(kms_dir1, km_from)
                next_higher_idx = bisect.bisect(kms_dir1, km_to)

                kms = [km_from] + kms_dir1[next_smaller_idx:next_higher_idx] + [km_to]
                inclines = inclines_dir1[next_smaller_idx - 1 : next_higher_idx]
                inclines += [inclines[-1]]

            # no incline information available
            else:
                kms, inclines = [km_from, km_to], [np.nan, np.nan]

        else:  # direction = 2
            # if incline information is available for track segment
            if not isinstance(self.incline_dict['inclines_dir2'], type(None)):
                # get incline profile for direction 2 (negate and reverse)
                kms_dir2 = self.incline_dict['incline_kms_dir2']
                inclines_dir2 = self.incline_dict['inclines_dir2']
                if km_from < kms_dir2[0]:
                    next_smaller_idx = 1
                else:
                    next_smaller_idx = bisect.bisect(kms_dir2, km_from)
                next_higher_idx = bisect.bisect(kms_dir2, km_to)

                kms = [km_from] + kms_dir2[next_smaller_idx:next_higher_idx] + [km_to]
                inclines = [
                    -inc for inc in inclines_dir2[next_smaller_idx - 1 : next_higher_idx]
                ]  # negate to invert incline for opposite direction
                kms = kms[::-1]
                inclines = inclines[::-1]
                inclines += [inclines[-1]]

            elif not isinstance(self.incline_dict['inclines_dir1'], type(None)):
                # get incline profile for direction 1 if direction 2 is not available (-> "Auf Anfrage")
                kms_dir2 = self.incline_dict['incline_kms_dir1']
                inclines_dir2 = self.incline_dict['inclines_dir1']
                if km_from < kms_dir2[0]:
                    next_smaller_idx = 1
                else:
                    next_smaller_idx = bisect.bisect(kms_dir2, km_from)
                next_higher_idx = bisect.bisect(kms_dir2, km_to)

                kms = [km_from] + kms_dir2[next_smaller_idx:next_higher_idx] + [km_to]
                inclines = [
                    -inc for inc in inclines_dir2[next_smaller_idx - 1 : next_higher_idx]
                ]  # negate to invert incline for opposite direction
                kms = kms[::-1]
                inclines = inclines[::-1]
                inclines += [inclines[-1]]

            # no incline information available
            else:
                kms, inclines = [km_to, km_from], [np.nan, np.nan]

        return kms, inclines

    def compute_incline(self) -> dict:
        """
        Computes incline profile of track segment.

        TODO
        """

        # main direction
        if not (self.properties['INF_STEIGUNGSPROFIL'] == 'auf Anfrage'):
            if not ('(' in self.properties['INF_STEIGUNGSPROFIL']):  # single incline
                kms_incline_dir1 = [self.km_from]
                inclines_dir1 = [float(self.properties['INF_STEIGUNGSPROFIL'])]
            else:
                # extract kilometrage and incline values from track segment
                kms_incline_dir1 = [
                    float(string.split('(')[1].split(')')[0])
                    for string in self.properties['INF_STEIGUNGSPROFIL'].strip().split(';')
                ]
                inclines_dir1 = [
                    float(string.split('(')[0].strip())
                    for string in self.properties['INF_STEIGUNGSPROFIL'].strip().split(';')
                ]

        else:
            kms_incline_dir1 = None
            inclines_dir1 = None

        # if second direction exists
        if self.properties_2 and not (self.properties_2['INF_STEIGUNGSPROFIL'] == 'auf Anfrage'):
            if not ('(' in self.properties_2['INF_STEIGUNGSPROFIL']):  # single incline
                kms_incline_dir2 = [self.km_from]
                inclines_dir2 = [float(self.properties_2['INF_STEIGUNGSPROFIL'])]
            else:
                kms_incline_dir2 = [
                    float(string.split('(')[1].split(')')[0])
                    for string in self.properties_2['INF_STEIGUNGSPROFIL'].strip().split(';')
                ]
                inclines_dir2 = [
                    float(string.split('(')[0].strip())
                    for string in self.properties_2['INF_STEIGUNGSPROFIL'].strip().split(';')
                ]
        else:
            kms_incline_dir2 = None
            inclines_dir2 = None

        incline_dict = {
            'incline_kms_dir1': kms_incline_dir1,
            'inclines_dir1': inclines_dir1,
            'incline_kms_dir2': kms_incline_dir2,
            'inclines_dir2': inclines_dir2,
        }

        return incline_dict

    def _compute_middle_line(self, line_1: LineString, line_2: LineString) -> LineString:
        """Returns the middle line between two input LineStrings.

        Computes the middle line by finding orthogonal projections of start and end points,
        and interpolating points along the segments. Result is a LineString.

        Parameters
        ----------
        line_1 : LineString
            First input LineString.
        line_2 : LineString
            Second input LineString.

        Returns
        -------
        middle_line : LineString
            The middle line between 'line_1' and 'line_2'.
        """

        # compute mean of start points while considering orthogonality
        point1 = Point(line_1.coords[0])
        point2 = Point(line_2.coords[0])

        point12 = nearest_points(point1, line_2)[1]
        point21 = nearest_points(point2, line_1)[1]

        if point12 != point2:
            line = LineString([point1, point12])
        elif point21 != point1:
            line = LineString([point21, point2])
        else:
            line = LineString([point1, point2])
        start_point = line.interpolate(distance=0.5, normalized=True)

        # compute mean of end points
        point1 = Point(line_1.coords[-1])
        point2 = Point(line_2.coords[-1])
        point12 = nearest_points(point1, line_2)[1]
        point21 = nearest_points(point2, line_1)[1]

        # if orthagonal projection of line1's end point is not line2's end point (not orthagonal)
        if point12 != point2:
            # orthagonal line w.r.t. rail(s)
            line = LineString([point1, point12])

        # if orthagonal projection of line2's end point is not line1's end point (not orthagonal)
        elif point21 != point1:
            # orthagonal line w.r.t. rail(s)
            line = LineString([point21, point2])

        # else end points are on the orthagonal w.r.t rails (orthagonal)
        else:
            # orthagonal line w.r.t. rail(s)
            line = LineString([point1, point2])

        end_point = line.interpolate(distance=0.5, normalized=True)

        # initalize new coordinates with start point
        new_line_coords: list[Tuple[float, float]] = [start_point]

        # sampling points from first line
        line_1_coords = [Point(coord) for coord in line_1.coords[1:-1]]

        # nearest points on other line (done in segments avoid problems with circular rails)
        n_coords = len(line_1_coords)
        n = n_coords // 10
        all_points_line_1 = []
        line_2_nearest = []

        for i in range(0, n + 1):
            points_line_1 = [Point(coord) for coord in line_1_coords[i * 10 : (i + 1) * 10]]

            if n_coords - len(line_2.coords) > 50:
                line_2_segment = line_2
            else:
                line_2_segment = LineString(line_2.coords[max(i - 4, 0) * 10 : (i + 5) * 10])

            line_2_nearest_ = nearest_points(points_line_1, line_2_segment)[1]

            all_points_line_1 += points_line_1
            line_2_nearest += list(line_2_nearest_)
            assert len(line_2_segment.coords[:]) > 1, f'wrong window size for line segments (i = {i})'

        for point_1, point_2 in zip(all_points_line_1, line_2_nearest):
            # create linestring
            line_string = LineString([point_1, point_2])
            # get middle point
            middle_point = line_string.interpolate(distance=0.5, normalized=True)
            new_line_coords.append(middle_point)

        # add end point and create line string
        new_line_coords.append(end_point)
        middle_line = LineString(new_line_coords)

        return middle_line

    def _compute_track_segment_layout(self, lines: list[LineString]) -> Layout:
        """Computes the layout of a track segment based on input LineStrings.

        Adjusts for specific cases, calculates rail type indexes, and organizes rails
        into layout dictionaries for both directions.

        Parameters
        ----------
        lines : list[LineString]
            List of LineStrings representing track segments.

        Returns
        -------
        layout : Layout
            Dictionary containing layout information for the track segment.
        """

        # special case: wrong direction due to circular track
        if self.name == 'StrUeb_4410_4411 - StrUeb_4411_4413' and self.track_nr == 4411:
            self._lines = [line.reverse() for line in lines][::-1]
        # rail segment missing in ISR (6083: StrUeb_6081_6083 - Berlin-Karow West)
        if 'StrUeb_6081_6083' in self.name and self.track_nr == 6083:
            lines[0] = LineString([self.operational_point_from] + list(lines[0].coords))

        # compute indexes
        (
            index_parallel,
            index_monorail,
            index_siding,
            index_direction_1,
            index_direction_2,
        ) = self._compute_rail_type_indexes(lines=lines)

        # get rail layout in both directions
        layout_direction_1 = []
        layout_direction_2 = []
        for i in range(0, len(lines)):
            # monorails or sidings
            if not i in flatten_list(index_parallel):
                # sidings (Abzweigendes Gleis)
                if i in flatten_list(index_siding)[1::2]:
                    siding_array = np.array(index_siding)
                    idx = np.where(siding_array == i)[0][0]
                    layout_direction_1.append(index_siding[idx])
                    layout_direction_2.append(index_siding[idx][::-1])

                # monorails (eingleisig)
                else:
                    layout_direction_1.append(i)
                    layout_direction_2.append(i)

            # parallel rails
            else:
                # direction track (Richtungsgleis)
                if i in index_direction_1:
                    layout_direction_1.append(i)

                # opposite track (Gegengleis)
                elif i in index_direction_2:
                    layout_direction_2.append(i)

        # reverse layout for opposite track
        layout_direction_2 = layout_direction_2[::-1]

        # format lists
        layout_contains_list = any([True for val in layout_direction_1 if type(val) == list])
        if layout_contains_list:
            layout_direction_1_new = [[], []]
            for val in layout_direction_1:
                if type(val) != list:
                    if not (val in layout_direction_1_new[0]):
                        layout_direction_1_new[0].append(val)
                    if not (val in layout_direction_1_new[1]):
                        layout_direction_1_new[1].append(val)
                else:
                    if not (val[0] in layout_direction_1_new[0]):
                        layout_direction_1_new[0].append(val[0])
                    if not (val[1] in layout_direction_1_new[1]):
                        layout_direction_1_new[1].append(val[1])

        else:
            layout_direction_1_new = [layout_direction_1]

        layout_contains_list = any([True for val in layout_direction_2 if type(val) == list])

        if layout_contains_list:
            layout_direction_2_new = [[], []]

            for val in layout_direction_2:
                if type(val) != list:
                    if not (val in layout_direction_2_new[0]):
                        layout_direction_2_new[0].append(val)
                    if not (val in layout_direction_2_new[1]):
                        layout_direction_2_new[1].append(val)
                else:
                    if not (val[0] in layout_direction_2_new[0]):
                        layout_direction_2_new[0].append(val[0])
                    if not (val[1] in layout_direction_2_new[1]):
                        layout_direction_2_new[1].append(val[1])
                layout_direction_2_new.sort(key=len)
        else:
            layout_direction_2_new = [layout_direction_2]

        # another special case: #
        if self.name == 'Seelze Mitte - Ahlem' and self.track_nr == 1750:
            layout_direction_1_new = [[0, 3]]
            layout_direction_2_new = [[2, 1]]
            index_direction_1[0] = 0
            index_direction_2[0] = 1
            index_parallel[0] = (0, 1)

        # layout dict
        layout: Layout = {
            'direction_1': layout_direction_1_new,  # all paths in direction 1
            'direction_2': layout_direction_2_new,  # all paths in direction 2
            'monorails': index_monorail,  # all monorails (bidrectional)
            'direction_1_rails': index_direction_1,  # all rails with direction 1 (unidirectional)
            'direction_2_rails': index_direction_2,  # all rails with direction 2 (unidirectional)
            'parallel': index_parallel,  # all rails which are parallel
            'sidings': index_siding,  #
        }

        return layout

    def _compute_rail_type_indexes(
        self, lines: list[LineString]
    ) -> Tuple[list[Tuple[int, int]], list[int], list[Tuple[int, int]], list[int], list[int]]:
        """Computes indexes for different rail types within a track segment.

        Analyzes the relationships between lines to determine parallel tracks, sidings,
        and the direction of each track.

        Parameters
        ----------
        lines : list[LineString]
            List of LineStrings representing track segments.

        Returns
        -------
        indexes : Tuple[list[Tuple[int, int]], list[int], list[Tuple[int, int]], list[int], list[int]]
            Tuple containing indexes for parallel lines, monorails, sidings, and
            direction-specific tracks.
        """

        index_parallel = []  # index of parallel lines
        index_siding = []  # index of sidings
        index_direction_1 = []  # index of rails operating in direction 1
        index_direction_2 = []  # index of rails operating in direction 2

        if len(lines) == 0:
            raise ValueError(f'Input list "lines" is empty.')

        elif len(lines) == 1:
            index_monorail = [0]

        else:
            # iterate all combinations of lines
            for i in range(0, len(lines)):
                for j in range(0, len(lines)):
                    # only one combination of each two lines, and no same lines
                    if j > i:
                        # start and end points of lines i,j
                        i_start_point = Point(lines[i].coords[0])
                        j_start_point = Point(lines[j].coords[0])
                        i_end_point = Point(lines[i].coords[-1])
                        j_end_point = Point(lines[j].coords[-1])

                        # distance between start points and end points
                        distance_ij_start = i_start_point.distance(j_start_point)
                        distance_ij_end = i_end_point.distance(j_end_point)
                        if TYPE_CHECKING:  # for type hint only
                            distance_ij_start = float(distance_ij_start)
                            distance_ij_end = float(distance_ij_end)

                        # condition for sidings (assuming parallel)
                        # if lines are parallel, but have but touch at exactly one point: siding
                        d_start_m = Point(lines[i].coords[0]).distance(Point(lines[j].coords[0]))
                        d_end_m = Point(lines[i].coords[-1]).distance(Point(lines[j].coords[-1]))
                        siding_condition = lines[i].touches(lines[j]) and ((d_start_m > 10) and (d_end_m) > 10)

                        # parallel lines
                        if lines_are_parallel(line1=lines[i], line2=lines[j]):
                            # parallel tracks

                            # line string between start points
                            line_string_1 = LineString([i_start_point, j_start_point])
                            line_string_2 = LineString([j_end_point, i_end_point])

                            # extend line string by factor 1.5
                            line_string_extended_1 = affinity.scale(
                                geom=line_string_1, xfact=1.5, yfact=1.5, origin=i_start_point
                            )
                            line_string_extended_2 = affinity.scale(
                                geom=line_string_2, xfact=1.5, yfact=1.5, origin=j_end_point
                            )

                            # rotate line string clockwise by 10 degrees
                            line_string_rotated_1 = affinity.rotate(
                                geom=line_string_extended_1, angle=-10, origin=i_start_point
                            )
                            line_string_rotated_2 = affinity.rotate(
                                geom=line_string_extended_2, angle=-10, origin=j_end_point
                            )

                            line_i_direction = np.array(lines[i].coords[1]) - np.array(lines[i].coords[0])
                            line_1_direction = np.array(line_string_1.coords[1]) - np.array(line_string_1.coords[0])
                            line_j_direction = np.array(lines[j].coords[-1]) - np.array(lines[j].coords[-2])
                            line_2_direction = np.array(line_string_2.coords[1]) - np.array(line_string_2.coords[0])
                            angle_ij = angle_between(line_i_direction, line_1_direction)
                            angle_ji = angle_between(line_j_direction, line_2_direction)

                            special_1 = (
                                self.track_nr == 6145 and self.name == 'Grünauer Kreuz West - Grünauer Kreuz Süd'
                            )
                            special_2 = (
                                self.track_nr == 6072 and self.name == 'Biesdorfer Kreuz West - StrUeb_6070_6072'
                            )
                            special_case = True if special_1 or special_2 else False

                            # sidings
                            if siding_condition:
                                # line lengths
                                length_i = lines[i].length
                                length_j = lines[j].length
                                # shorter line is treated as siding of longer line
                                # longer line is represented by first indice in list
                                # shorter line is represented by second indice in list
                                if length_i >= length_j:
                                    index_siding.append([i, j])
                                else:
                                    index_siding.append([j, i])

                            elif (
                                (line_string_rotated_1.intersects(lines[j]) and abs(angle_ij - 90) < 20)
                                or (line_string_rotated_2.intersects(lines[i]) and abs(angle_ji - 90) < 20)
                                or (
                                    (np.isnan(angle_ji) and line_string_rotated_1.intersects(lines[j]))
                                    or (np.isnan(angle_ij) and line_string_rotated_2.intersects(lines[i]))
                                )
                                or special_case == True
                            ):
                                # i: direction track
                                # j: opposite track
                                index_direction_1.append(i)
                                index_direction_2.append(j)
                                index_parallel.append((i, j))

                            else:
                                # i: opposite track
                                # j: direction track
                                index_direction_2.append(i)
                                index_direction_1.append(j)
                                index_parallel.append((j, i))

            # index of monorails
            index_monorail = [i for i in range(0, len(lines)) if not i in flatten_list(index_parallel)]

        return index_parallel, index_monorail, index_siding, index_direction_1, index_direction_2

    def _find_index_of_parallel_rail(self, rail_indice: int, index_parallel: list[Tuple[int, int]]) -> int:
        """Finds the index of the parallel rail for a given rail index.

        Parameters
        ----------
        rail_indice : int
            Index of the rail for which the parallel rail index is sought.
        index_parallel : list[Tuple[int, int]]
            List of tuples representing indices of parallel rails.

        Returns
        -------
        parallel_index : int
            Index of the parallel rail for the given 'rail_indice'.
        """

        if rail_indice in flatten_list(index_parallel):
            for group in index_parallel:
                if rail_indice in group:
                    if rail_indice == group[0]:
                        i = group[1]
                    else:
                        i = group[0]
                    break
        else:
            raise ValueError(f"Rail for given indice 'rail_indice' = {rail_indice} does not have a parallel rail.")

        return i

    @classmethod
    def from_track_and_name(
        cls, track: int, name: str, to_km: float, allow_previous: bool = True, enhance_kilometrage: bool = True
    ) -> Union[TrackSegment, None]:
        """Creates a TrackSegment instance from track number and name.

        Attempts to load the TrackSegment from cache; if not found, queries the parameters and creates a new instance.

        Parameters
        ----------
        track : int
            Track number.
        name : str
            Name of the track segment.
        allow_previous : bool, optional
            Flag to allow loading from previous cache, by default True.

        Returns
        -------
        track_segment : Union[TrackSegment, None]
            The TrackSegment instance if found, else None.
        """

        # paths
        project_path = Path(__file__).parent.parent.parent.parent

        if any([ex_name in name for ex_name in ISR_EXCEPTIONAL_STATION_NAMES]):
            name = extract_station_names(track_name_string=name, is_op_name=True).replace('**', '*')
            if name[-1] == '*':
                name = name[:-1]
            # name = f'{from_name} - {to_name}'
        km_type = 'raw' if enhance_kilometrage == False else 'enh'
        if int(track) < 4930:
            file_path = project_path / f'cache/track_segments/{track}_{name}_{km_type}.pickle'
        else:
            file_path = project_path / f'cache/track_segments_continued/{track}_{name}_{km_type}.pickle'

        matching_files = sorted(file_path.parent.glob(f'{track}_{name}_{km_type}.pickle'))

        if len(matching_files) == 1:
            file_path = matching_files[0]
            # load from file
            with open(file_path, "rb") as file:
                track_segment: TrackSegment = pickle.load(file)

            return track_segment

        else:
            # query and create instance
            parameter_tuple = query_track_segment(
                args=[track, name], to_km=to_km, allow_previous=allow_previous, enhance_kilometrage=enhance_kilometrage
            )

            if parameter_tuple:
                return cls(*parameter_tuple)
            else:
                return None

    def pickle_self_to_cache(self):
        """Pickles self to cache."""
        if self.track_nr > 4929:
            self.cache_path = Path(self.cache_path.as_posix().replace('track_segments', 'track_segments_continued'))
        with open(self.cache_path, "wb") as file:
            pickle.dump(obj=self, file=file, protocol=pickle.HIGHEST_PROTOCOL)

    def _integrate_kilometrage_points(self):
        """
        Integrate kilometrage points and adjust geometric lengths for the track segment.

        This method performs the integration of kilometrage points obtained from 'db-geo-streckennetz'
        for the given track segment. It also adjusts the geometric lengths based on the integrated
        kilometrage points and updates the kilometrage information.

        Notes
        -----
        The method processes kilometrage points, adjusts geometric lengths, and integrates
        information into the kilometrage. It handles various edge cases, including merging
        points with the kilometrage line, eliminating double entries, and correcting nominal
        geometric lengths for split segments. There are serveral problems when combining
        geometric information from ISR with kilometrage information from 'db-geo-streckennetz',
        which this functions tries to handle.
        """

        # get values
        track_km_dict = deepcopy(self.track_km_dict)
        track_length_dict = deepcopy(self.track_length_dict)
        segment_ids = track_km_dict.keys()
        op_from = self.operational_point_from
        op_to = self.operational_point_to
        km_from_db = self.km_from_db
        km_to_db = self.km_to_db

        # special cases
        if self.track_nr == 2670 and self.name == 'Köln-Mülheim Berliner Straße - Köln-Stammheim':
            km_to_db = '7,6 + 1487'  # stated as 7.4 + 1687, but points 7.5 and 7.6 exist before (km values dont align)
        elif self.track_nr == 2670 and self.name == 'Köln-Stammheim - Leverkusen Chempark Hp':
            km_from_db = '7,6 + 1487'  # consistency with next segment
        nominal_segment_length = (self.km_to - self.km_from) * 1000

        # set ids for direction cases
        if (f'{self.id}-0' in segment_ids) and self._enhance_kilometrage == True:
            segment_id_0 = f'{self.id}-0'
            segment_id_1 = None
            segment_id_2 = None
            self.has_additional_km_info = True
        elif (f'{self.id}-1') in segment_ids and self._enhance_kilometrage == True:
            segment_id_0 = None
            segment_id_1 = f'{self.id}-1'
            segment_id_2 = f'{self.id}-2'
            if not (f'{self.id}-2' in segment_ids):
                track_km_dict[segment_id_2] = track_km_dict[segment_id_1]
                track_length_dict[segment_id_2] = track_length_dict[segment_id_1]
            self.has_additional_km_info = True
        else:
            # no kilometrage info from dataset geo-streckennetz available for track segment
            logger.debug('No additional kilometrage information for track segment available')
            self.has_additional_km_info = False
            if self._n_km_lines == 1:
                self.kilometrage.add_km_point(
                    point=op_from, value=km_from_db, length=nominal_segment_length, direction=0
                )
                self.kilometrage.add_km_point(point=op_to, value=km_to_db, length=0, direction=0)
                self.kilometrage._km_lengths = [[nominal_segment_length]]
                self.kilometrage._km_lengths_type = [['computed']]
                self.kilometrage._has_km_info = False
            else:
                self.kilometrage.add_km_point(
                    point=op_from, value=km_from_db, length=nominal_segment_length, direction=1
                )
                self.kilometrage.add_km_point(
                    point=op_from, value=km_from_db, length=nominal_segment_length, direction=2
                )
                self.kilometrage.add_km_point(point=op_to, value=km_to_db, length=0, direction=1)
                self.kilometrage.add_km_point(point=op_to, value=km_to_db, length=0, direction=2)
                self.kilometrage._km_lengths = [[nominal_segment_length], [nominal_segment_length]]
                self.kilometrage._km_lengths_type = [['computed'], ['computed']]
                self.kilometrage._has_km_info = False
            return

        # only keep information for current track segment
        segment_id_list = [segment_id_0, segment_id_1, segment_id_2]
        track_km_dict = {key: track_km_dict[key] for key in segment_id_list if not isinstance(key, type(None))}
        track_length_dict = {key: track_length_dict[key] for key in segment_id_list if not isinstance(key, type(None))}

        # convert coordinates to points
        for direction, segment_id in enumerate(segment_id_list):
            if not segment_id:
                continue

            for i in range(len(track_km_dict[segment_id])):
                # iterate points for km and convert to Point
                point_list: list[Point] = []
                for j in range(len(track_km_dict[segment_id][i][1])):
                    if type(track_km_dict[segment_id][i][1][j]) != Point:
                        p = Point(json.loads(s=track_km_dict[segment_id][i][1][j])['coordinates'])
                    else:
                        p = track_km_dict[segment_id][i][1][j]
                    point_list.append(p)

                # replace string point list by list of Point objects
                track_km_dict[segment_id][i][1] = point_list

            # and add operational points
            if self._n_km_lines == 1:
                # direction 0
                distances = [op_from.distance(rail) for rail in self.rails]
                min_index = np.argmin(distances)
                rail_from = self.rails[min_index]

                distances = [op_to.distance(rail) for rail in self.rails]
                min_index = np.argmin(distances)
                rail_to = self.rails[min_index]

            else:
                if int(segment_id[-1]) == 1:
                    # direction 1
                    distances = [op_from.distance(rail) for rail in self.rails_1]
                    min_index = np.argmin(distances)
                    rail_from = self.rails_1[min_index]

                    distances = [op_to.distance(rail) for rail in self.rails_1]
                    min_index = np.argmin(distances)
                    rail_to = self.rails_1[min_index]

                else:
                    # direction 2
                    distances = [op_from.distance(rail) for rail in self.rails_2]
                    min_index = np.argmin(distances)
                    rail_from = self.rails_2[min_index]

                    distances = [op_to.distance(rail) for rail in self.rails_2]
                    min_index = np.argmin(distances)
                    rail_to = self.rails_2[min_index]

            # ops projected on rail
            if op_from.distance(rail_from) > 10:
                rail_from_ext = affinity.scale(
                    geom=LineString(rail_from.coords[:2]), xfact=5, yfact=5, origin=rail_from.coords[1]
                )
            else:
                rail_from_ext = rail_from

            if op_to.distance(rail_to) > 10:
                rail_to_ext = affinity.scale(
                    geom=LineString(rail_to.coords[-2:]), xfact=5, yfact=5, origin=rail_to.coords[-2]
                )
            else:
                rail_to_ext = rail_to

            op_from_on_rail = nearest_points(op_from, rail_from_ext)[1]
            op_to_on_rail = nearest_points(op_to, rail_to_ext)[1]

            # set value lists
            if op_from_on_rail.distance(rail_from) > 20:
                merge_from = 'before'
            else:
                merge_from = None
            if op_to_on_rail.distance(rail_to) > 20:
                merge_after = 'after'
            else:
                merge_after = None
            if op_from_on_rail.distance(op_from) > 15:
                op_from_ = op_from
            else:
                op_from_ = op_from_on_rail
            if op_to_on_rail.distance(op_to) > 15:
                op_to_ = op_to
            else:
                op_to_ = op_to_on_rail
            if (
                self.track_nr == 6012
                and self.name == 'StrUeb_6011_6012 - Berlin Gehrenseestraße'
                and km_from_db == '8,9 + 56'
            ):
                merge_from = "before"
            if (
                self.track_nr == 1280
                and self.name == 'StrUeb_1280_1284_3 - StrUeb_1255_1280_1'
                and km_from_db == '21,8 + 6'
            ):
                merge_from, op_from = None, op_from_on_rail
            if (
                self.track_nr == 5382
                and self.name == 'Ingolstadt Hbf - Ingolstadt-Seehof'
                and km_from_db == '-0,7 + -43'
            ):
                merge_from = None
            if (
                self.track_nr == 1760
                and self.name == 'Hannover Hbf - Hannover Bismarckstraße'
                and km_to_db == '1,0 + 2230'
            ):
                km_to_db = '1,1 + 2130'
            if (
                self.track_nr == 4011
                and self.name == 'Mannheim-Luzenberg - Mannheim-Waldhof'
                and km_to_db == '6,4 + 36'
            ):
                km_to_db = '6,4 +-442'
            if (
                self.track_nr == 2400
                and self.name == 'Düsseldorf-Rath Mitte - Düsseldorf-Rath'
                and km_to_db == '7,0 + 139'
            ):
                km_to_db = '7,1 + 39'
            if self.track_nr == 1750 and self.name == 'Seelze Mitte - Ahlem' and km_from_db == '11,5 + 0':
                merge_from = None
            if (
                self.track_nr == 2505
                and self.name == 'Rheinhausen Ost - Duisburg-Hochfeld Süd               (Hp)'
                and km_to_db == '13,8 + 257'
            ):
                km_to_db = '14.0 +    56'
            if self.track_nr == 6139 and self.name == 'StrUeb_6139_6170 - StrUeb_6078_6139_2':
                op_from_ = Point(3803586.416, 5828532.18)

            value_list_from = [km_from_db, [op_from_], merge_from]  # need to append geometric length
            value_list_to = [km_to_db, [op_to_], merge_after]  # need to append geometric length

            # add to dict
            track_km_dict[segment_id] += [value_list_from]
            track_km_dict[segment_id] += [value_list_to]

            # sort list of value_lists according to km values
            sorted_index = self.kilometrage.argsort_km_values([val_list[0] for val_list in track_km_dict[segment_id]])
            sorted_list = [track_km_dict[segment_id][i] for i in sorted_index]

            # drop lists where km==km_from or km==km_to (we use op_from and op_to for these km values)
            new_list = []
            dropped = []
            for i, value_list in enumerate(sorted_list):
                if len(value_list) == 3:
                    # always keep op_from/op_to
                    new_list.append(value_list)
                else:
                    # distance to other km points
                    # if any distance < 1
                    points = value_list[1]
                    point = points[0]
                    distances = [
                        point.distance(other) if point != other else np.inf
                        for other in [vlist[1][0] for vlist in sorted_list]
                    ]
                    c1 = any([d < 5 for d in distances])

                    # and both merge type None
                    nearest_point_idx = np.argmin(distances)
                    other = track_km_dict[segment_id][nearest_point_idx][1][0]
                    c2 = isinstance(value_list[2], type(None)) and isinstance(
                        sorted_list[nearest_point_idx][2], type(None)
                    )

                    # and both projections on km line yield same point
                    if self._n_km_lines == 2:
                        direction_idx = direction - 1
                    else:
                        direction_idx = direction
                    km_line_distances = [point.distance(km_line) for km_line in self.kilometrage.lines[direction_idx]]
                    km_line = self.kilometrage.lines[direction_idx][np.argmin(km_line_distances)]
                    point_projected = nearest_points(km_line, point)[0]
                    other_projected = nearest_points(km_line, other)[0]
                    c3 = point_projected.distance(other_projected) < 1e-3

                    prev_length = sorted_list[i - 1][-1]
                    if (
                        (c1 == True)
                        and (c2 == True)
                        and (c3 == True)
                        and (not (value_list[0] == km_from_db) and not (value_list[0] == km_to_db))
                        and prev_length != 0
                    ):
                        dropped.append(value_list)

                    elif not (value_list[0] == km_from_db) and not (value_list[0] == km_to_db):
                        new_list.append(value_list)

                    elif self.id == 27297 and (value_list[0] == km_from_db):
                        new_list.append(value_list)

                    else:
                        km_current = value_list[0]
                        length = value_list[-1]
                        if i < len(sorted_list) - 1:
                            for j in range(len(sorted_list[i + 1 :])):
                                if len(sorted_list[i + j + 1]) == 4:
                                    break
                            else:
                                j = None

                            if j:
                                km_next = sorted_list[i + j + 1][0]

                            else:
                                km_next = None

                        else:
                            km_next = None

                        dropped.append((km_current, km_next, length))

            sorted_list = new_list

            # adjust geometric length due to adding op_from and op_to
            for i, val_list in enumerate(sorted_list):
                if val_list[0] == km_from_db and len(val_list) == 3:
                    length = nominal_segment_length
                    val_list.append(length)
                    sorted_list[i] = val_list

                elif val_list[0] == km_to_db and len(val_list) == 3:
                    length = 0
                    val_list.append(length)
                    sorted_list[i] = val_list

            track_km_dict[segment_id] = sorted_list

        # integrate information in kilometrage
        for key in track_km_dict.keys():
            kms_value_list = deepcopy(track_km_dict[key])
            kms_lengths_list = deepcopy(track_length_dict[key])
            km_from = self.km_from_db
            km_to = self.km_to_db

            # sort km_value_list according to merge order
            merge_before_index = []
            merge_after_index = []
            for i, val_list in enumerate(kms_value_list):
                if val_list[2] == 'before':
                    merge_before_index.append(i)

                elif val_list[2] == 'after':
                    merge_after_index.append(i)

            remaining_index = [
                i for i in range(len(kms_value_list)) if not (i in merge_before_index) and not (i in merge_after_index)
            ]
            sorted_index = merge_before_index[::-1] + merge_after_index + remaining_index
            kms_value_list = [kms_value_list[i] for i in sorted_index]

            n_iter = 0
            pre_km_values = [l[0] for l in kms_value_list]
            pre_km_points = [l[1][0] for l in kms_value_list]
            self.kilometrage._set_pre_values(points=pre_km_points, values=pre_km_values)

            # delete double entries
            for i, values_list in enumerate(kms_value_list):
                n_iter += 1
                # dont add point if exact km already exists
                km_val_exists_list = [
                    values_list[0].replace(',', '.').replace(' ', '') == km_val.replace(',', '.').replace(' ', '')
                    for km_val in self.kilometrage.values_in_direction(direction=int(key[-1]))
                ]

                dir_key = 0 if int(key[-1]) < 2 else 1
                km_lines = self.kilometrage.lines[dir_key]
                km_line_0, km_line_end = km_lines[0], km_lines[-1]
                op_from_project = km_line_0.project(op_from, normalized=True)
                op_to_project = km_line_end.project(op_to, normalized=True)
                point = values_list[1][0]
                point_from_project = km_line_0.project(point, normalized=True)
                point_to_project = km_line_end.project(point, normalized=True)

                if any(km_val_exists_list):
                    continue

                # dont add point if km is larger than km_to (km_to: at target station of track segment)
                # excecpt: if point is to be merged with km line or km point is exactly end point of rail (for cases where op are not exactly at one end of a rail)
                if (
                    only_km_db(values_list[0]) > only_km_db(km_to)
                    and db_km_to_km(values_list[0]) > db_km_to_km(km_to)
                    and (point_to_project > op_to_project and point_to_project > 0 and point_to_project < 1)
                    and isinstance(values_list[2], type(None))
                ):
                    continue

                # dont add point if km is smaller than km_from (km_from: at source station of track segment)
                # excecpt: if point is to be merged with km line
                if (
                    only_km_db(values_list[0]) < only_km_db(km_from)
                    and db_km_to_km(values_list[0]) < db_km_to_km(km_from)
                    and (point_from_project > op_from_project and point_from_project > 0 and point_from_project < 1)
                    and isinstance(values_list[2], type(None))
                ):
                    continue

                if i == 0:
                    first_val = True
                else:
                    first_val = False

                if i == len(kms_value_list) - 1:
                    last_val = True
                else:
                    last_val = False

                self.kilometrage.integrate_kilometrage_points(
                    values_list=values_list,
                    direction=int(key[-1]),
                    boundary_kms=(km_from, km_to),
                    last_val=last_val,
                    first_val=first_val,
                )

            # reiterate to adjust nominal geomtric lengths
            # get lengths for original segments
            km_values = self.kilometrage.values_in_direction(direction=int(key[-1]))
            km_lengths = [[] for _ in range(len(km_values) - 1)]
            km_lengths_type = [[] for _ in range(len(km_values) - 1)]
            leftover_value_list = []

            for value_list in kms_lengths_list:
                km_1 = value_list[1]
                km_2 = value_list[2]
                length = value_list[3]

                for i, (km_s, km_e) in enumerate(zip(km_values[:-1], km_values[1:])):
                    first_km_match = (km_s == km_1) or (
                        km_s.replace(',', '.').replace(' ', '') == km_1.replace(',', '.').replace(' ', '')
                    )
                    second_km_match = (km_e == km_2) or (
                        km_e.replace(',', '.').replace(' ', '') == km_2.replace(',', '.').replace(' ', '')
                    )

                    if first_km_match == True and second_km_match == True:
                        km_lengths[i].append(length)
                        km_lengths_type[i].append('nominal')
                        break

                else:
                    leftover_value_list.append(value_list)

            # get lengths for segments that were splitted
            for value_list in leftover_value_list:
                km_1 = value_list[1]
                km_2 = value_list[2]
                length = value_list[3]

                for i, km in enumerate(km_values):
                    if km == km_1:
                        j = i
                        break
                else:
                    j = None
                for i, km in enumerate(km_values):
                    if km == km_2:
                        k = i
                        break
                else:
                    k = None

                if j and k:
                    assert k > j + 1, f'k {k} j {j}'
                    for i in range(k - j):
                        kmvals = km_values[j + i + 1 : k + 1]
                        km_lengths[j + i] = [
                            length
                            - np.sum(km_lengths[j : j + i])
                            - np.sum(
                                [1000 * (db_km_to_km(b) - db_km_to_km(a)) for (a, b) in zip(kmvals[:-1], kmvals[1:])]
                            )
                        ]
                        km_lengths_type[j + i] = ['nominal']

                elif j:
                    # difference between next km value and km_2
                    if j < len(km_values) - 1:
                        # km values in between
                        next_km_vals = [
                            km_values[j + i + 1]
                            for i in range(len(km_values[j + 1 :]))
                            if db_km_to_km(km_values[j + i]) < db_km_to_km(km_2)
                        ]

                        # difference to value after
                        difference_m = (db_km_to_km(next_km_vals[-1]) - db_km_to_km(km_2)) * 1000
                        # add to nominal length
                        length += difference_m

                        if len(next_km_vals) == 0:
                            pass

                        elif len(next_km_vals) == 1:
                            km_lengths[j] = [length]
                            km_lengths_type[j] = ['nominal']
                            if (
                                self.track_nr == 2273
                                and self.name == 'Maria-Veen - Coesfeld (Westf)'
                                and km_1 == '58,1 + 25'
                            ):
                                km_lengths_type[j] = ['computed']

                        else:
                            next_km_vals = [
                                km_values[j + i + 1]
                                for i in range(len(km_values[j + 1 :]))
                                if db_km_to_km(km_values[j + i]) < db_km_to_km(km_2)
                            ]
                            substractive = 0

                            for i in range(km_values.index(next_km_vals[-1]), j + 1, -1):
                                segment_length = (db_km_to_km(km_values[i]) - db_km_to_km(km_values[i - 1])) * 1000
                                substractive += segment_length
                                km_lengths[i - 1] = [segment_length]
                                km_lengths_type[i - 1] = ['computed']
                            km_lengths[j] = [length - substractive]
                            km_lengths_type[j] = ['nominal']

            for i, (a, b) in enumerate(zip(km_values[:-1], km_values[1:])):
                if len(km_lengths[i]) == 0:
                    km_lengths[i] = [1000 * (db_km_to_km(b) - db_km_to_km(a))]
                    km_lengths_type[i] = ['computed']

            lengths = flatten_list(km_lengths)
            lengths_type = flatten_list(km_lengths_type)
            assert len(lengths) == len(km_values) - 1, f'{lengths} | {km_values}'

            self.kilometrage._set_lengths_for_direction(lengths=lengths, direction=int(key[-1]))
            self.kilometrage._set_lengths_type_for_direction(lengths_type=lengths_type, direction=int(key[-1]))

        # recompute segment lengths
        self.kilometrage.compute_geometric_length()
        self.kilometrage.correct_point_positions()
        self.kilometrage.compute_geometric_length()
        self.kilometrage.compute_nominal_length()
        self.kilometrage.compute_geometric_offset()

    def _compute_kilometrage_offset(self):
        """
        Compute kilometrage offset based on differences between actual rail lengths (in ISR) and nominal rail lengths (from geo-streckennetz). This offset is needed to correct kilometrage for some track segments, because integrating kilometrage from DB Geo-Streckennetz dataset into ISR is hardly optimal, as kilometrage and track segment lengths can differ between the two. The offset computation is solely based on empirical testing.

        Offset is computed while considering kilometrage errors of previous track segments, which makes it necessary to create instances of previous track segments. This is done recursively, which is extremely inefficient due to having to preprocess each track segment multiple times. However, for now there is no other option, as fixing this would require much refactoring of the class.
        """
        name = self.name.split(' - ')[0]

        if self.has_additional_km_info == False or self._allow_previous == True:
            # get previous track segment
            previous_track_segment = self.from_track_and_name(
                track=self.track_nr,
                name=f'*{name}',
                to_km=self.properties['ISR_KM_VON'],
                allow_previous=False,
                enhance_kilometrage=self._enhance_kilometrage,
            )

            # if previous track segment exists
            if not isinstance(previous_track_segment, type(None)):
                # compute previous km error from previous track segment
                if previous_track_segment._n_km_lines == 1:
                    l = min(
                        [
                            len(previous_track_segment.kilometrage.lines[0]),
                            len(previous_track_segment.kilometrage.lengths_in_direction(direction=0)),
                        ]
                    )
                    prev_km_error_m = np.sum(
                        [
                            previous_track_segment.kilometrage.lines[0][j].length
                            - previous_track_segment.kilometrage.lengths_in_direction(direction=0)[j]
                            for j in range(l)
                        ]
                    )

                else:
                    l = min(
                        [
                            len(previous_track_segment.kilometrage.lines[0]),
                            len(previous_track_segment.kilometrage.lengths_in_direction(direction=1)),
                        ]
                    )
                    prev_km_error_m_1 = np.sum(
                        [
                            previous_track_segment.kilometrage.lines[0][j].length
                            - previous_track_segment.kilometrage.lengths_in_direction(direction=1)[j]
                            for j in range(l)
                        ]
                    )
                    l = min(
                        [
                            len(previous_track_segment.kilometrage.lines[1]),
                            len(previous_track_segment.kilometrage.lengths_in_direction(direction=2)),
                        ]
                    )
                    prev_km_error_m_2 = np.sum(
                        [
                            previous_track_segment.kilometrage.lines[1][j].length
                            - previous_track_segment.kilometrage.lengths_in_direction(direction=2)[j]
                            for j in range(l)
                        ]
                    )
                    prev_km_error_m = np.mean([prev_km_error_m_1, prev_km_error_m_2], dtype=float)
                self.kilometrage._previous_km_error = prev_km_error_m

                # compute km error
                if self._n_km_lines == 1:
                    l = min([len(self.kilometrage.lines[0]), len(self.kilometrage.lengths_in_direction(direction=0))])
                    km_error_m = np.sum(
                        [
                            self.kilometrage.lines[0][j].length - self.kilometrage.lengths_in_direction(direction=0)[j]
                            for j in range(l)
                        ]
                    )

                else:
                    l = min([len(self.kilometrage.lines[0]), len(self.kilometrage.lengths_in_direction(direction=1))])
                    km_error_m_1 = np.sum(
                        [
                            self.kilometrage.lines[0][j].length - self.kilometrage.lengths_in_direction(direction=1)[j]
                            for j in range(l)
                        ]
                    )
                    l = min([len(self.kilometrage.lines[1]), len(self.kilometrage.lengths_in_direction(direction=2))])
                    km_error_m_2 = np.sum(
                        [
                            self.kilometrage.lines[1][j].length - self.kilometrage.lengths_in_direction(direction=2)[j]
                            for j in range(l)
                        ]
                    )
                    km_error_m = np.mean([km_error_m_1, km_error_m_2], dtype=float)

                # compute errors and ratio
                rng = [0] if self._n_km_lines == 1 else [0, 1]
                prev_segment_error_m = np.mean(
                    [
                        previous_track_segment.kilometrage.lines[i][-1].length
                        - previous_track_segment.kilometrage.lengths[i][-1]
                        for i in rng
                    ],
                    dtype=float,
                )
                ratio = abs(km_error_m / prev_km_error_m)

                # compute kilometrage offset

                # Negative KM error is propageted from one track segment to later track segments
                if (prev_segment_error_m < 0 and self.has_additional_km_info == False) and km_error_m < 0:
                    # add previous segment error to offset
                    self.kilometrage._offset_from_start_m += prev_segment_error_m
                    # plus offset of previous segment, if previous segment had no km info and segment error < 0
                    if (not previous_track_segment.has_additional_km_info) and km_error_m < 0:
                        self.kilometrage._offset_from_start_m += previous_track_segment.kilometrage._offset_from_start_m

                # KM errors of previous segment and current segment negate each other (e.g. first segment is 100m to long, second segment is 100m to short)
                elif km_error_m * prev_km_error_m < 0 and ratio < 1.05 and ratio > 0.95:
                    self.kilometrage._offset_from_start_m += prev_km_error_m

                else:
                    # set offest to zero
                    self.kilometrage._offset_from_start_m = 0

            else:
                # set offest to zero
                self.kilometrage._offset_from_start_m = 0

        else:
            # set offest to zero
            self.kilometrage._offset_from_start_m = 0

    def _special_cases(self):
        """Handles certain special cases"""

        if self.name == 'Neuss Hbf - Weißenberg' and self.track_nr == 2610:
            self._km_to = km_to_db_km(db_km_to_km(self.km_to_db))  # overlength not correct in ISR
        elif self.name == 'Weißenberg - Meerbusch-Osterath' and self.track_nr == 2610:
            self._km_from = km_to_db_km(db_km_to_km(self.km_from_db))  # overlength not correct in ISR
