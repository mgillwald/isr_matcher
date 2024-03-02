from __future__ import annotations
from shapely import Point, LineString
from shapely.ops import nearest_points
from typing import Tuple, Union, Literal
from isr_matcher._constants._parse import db_km_to_km, km_to_db_km
from isr_matcher.ops._functions import split_line_at_point, only_km_db, only_m_db
import numpy as np
from isr_matcher._constants.logging import setup_logger
import logging


# Create logger for the current module
setup_logger()
logger = logging.getLogger(__name__)


# class Kilometrage
class Kilometrage:
    """Class that manages and stores kilometrage information for TrackSegment instances.

    Parameter
    ---------
    km_lines: list[list[km_lines]]
        A list of kilometrage lines, one for each direction. A kilometrage line is represented as sequential list of (geometrically connected) LineString instances.

    Attributes
    ----------
    n_lines: int
        The number of kilometratge lines.
    length_m: float
        The geometric length of kilometrage lines in meter.
    length_km: float
        The geometric length of kilometrage lines in kilometer.
    length_nominal_m: float
        The nominal geometric length in meter for all directions.
    length_nominal_km: float
        The nominal geometric length in kilometer for all directions.
    line: list[list[float]]
        All kilometrage lines as a list which contains a list of LineString objects for each existing direction of kilometrage.
    points: list[list[Point]]
        All kilometrage points as a list which contains a list of Point objects for each existing direction of kilometrage.
    values: list[list[str]]
        All kilometrage values as a list which contains a list of values for each existing direction of kilometrage.
    lengths: list[list[float]]
        All nominal geometric lengths of kilometrage segments in meter
    """

    def __init__(self, km_lines: list[list[LineString]], enhance_kilometrage: bool = True):
        # verify input
        if len(km_lines) != 1 and len(km_lines) != 2:
            raise ValueError(
                f'list lines has {len(km_lines)} elements. It must contain exactly one or two LineStrings, representing the kilometrage line(s).'
            )

        if not isinstance(km_lines[0][0], LineString):
            raise TypeError(
                f'First elements of first list has wrong type: {type(km_lines[0][0])}. List lines must contain exactly one or two lists containing LineStrings, representing the kilometrage line(s).'
            )

        # set attributes
        self._n_km_lines: int = len(km_lines)  # number of kilometrage lines
        self._lines: list[list[LineString]] = km_lines  # kilometrage lines
        self._km_points: list[list[Point]] = [[] for _ in range(self._n_km_lines)]  # kilometrage points (coordinates)
        self._km_values: list[list[str]] = [[] for _ in range(self._n_km_lines)]  # kilometrage values at above points
        self._km_lengths: list[list[float]] = [
            [] for _ in range(self._n_km_lines)
        ]  # geometric length of segments between kilometrage points
        self._km_lengths_type: list[list[str]] = [
            [] for _ in range(self._n_km_lines)
        ]  # type of length ('nominal', 'computed')
        self._offset_m: list[list[float]] = [[] for _ in range(self._n_km_lines)]  # offsets at start of km segments
        self._previous_km_error: list[float] = [
            0.0 for _ in range(self._n_km_lines)
        ]  # last kilometrage segment length error of previous track segment
        self._enhance_kilometrage = enhance_kilometrage
        self._has_km_info = False  # flag whether km info from geo-strecken has been integrated
        self._offset_from_start_m: float = 0
        self.compute_geometric_length()  # computes geometric length of kilometrage line(s)
        if enhance_kilometrage:
            self.compute_geometric_offset()

    @property
    def n_lines(self) -> int:
        """Returns number of kilometratge lines."""
        return self._n_km_lines

    @property
    def length_m(self) -> list[list[float]]:
        """Returns the geometric length of kilometrage lines in meter."""
        return self._length

    @property
    def length_km(self) -> list[list[float]]:
        """Returns the geometric length of kilometrage lines in kilometer."""
        return [l / 1000 for l in self._length]

    @property
    def length_nominal_m(self) -> list[list[float]]:
        """Returns the nominal geometric length in meter for all directions."""
        return [np.sum([length for length in self._km_lengths[i]]) for i in range(self.n_lines)]

    @property
    def length_nominal_km(self) -> list[list[float]]:
        """Returns the nominal geometric length in kilometer for all directions."""
        return [np.sum([length / 1000 for length in self._km_lengths[i]]) for i in range(self.n_lines)]

    def line(self, direction: int = 0) -> list[LineString]:
        """Returns kilometrage line as list of lines for given direction.

        Parameter
        ---------
        direction: int
            The direction for which the kilometrage line(s) are returned.

        Returns
        -------
        line: The kilometrage line for the given directon.
        """
        if self.n_lines == 1:
            return self.lines[0]
        elif self.n_lines == 2:
            if direction == 1:
                return self.lines[0]
            elif direction == 2:
                return self.lines[1]
            else:
                msg = f'Received direction={direction} for track segment with two kilometrage lines. Set direction=1 for direction track or direction=2 for opposite track kilometrage.'
                raise ValueError(msg)
        else:
            raise NotImplementedError('Case not possible')

    @property
    def lines(self) -> list[list[LineString]]:
        """Returns all kilometrage lines as a list which contains a list of LineString objects for each existing direction of kilometrage."""
        return self._lines

    @property
    def points(self) -> list[list[Point]]:
        """Returns all kilometrage points as a list which contains a list of Point objects for each existing direction of kilometrage."""
        return self._km_points

    @property
    def values(self) -> list[list[str]]:
        """Returns all kilometrage values as a list which contains a list of values for each existing direction of kilometrage."""
        return self._km_values

    @property
    def lengths(self) -> list[list[float]]:
        """Returns all nominal geometric lengths of kilometrage segments in meter. Nominal geometric lengths are returned as a list which contains a list of lengths (m) for each existing direction of kilometrage."""
        return self._km_lengths

    @property
    def lengths_type(self) -> list[list[str]]:
        """Returns all lengths types (nominal, computed) of kilometrage segments in meter. Nominal geometric lengths are returned as a list which contains a list of lengths (m) for each existing direction of kilometrage."""
        return self._km_lengths_type

    @property
    def offset_m(self) -> list[list[float]]:
        """Returns all offsets of kilometrage segments in meter. Offsets are returned as a list which contains a list of offsets (m) for each existing direction of kilometrage."""
        return self._offset_m

    def points_in_direction(self, direction: int) -> list[Point]:
        """Returns kilometrage points for one direction. If track segment has only one km line for both directions, parameter direction is ignored."""
        if self.n_lines == 1:
            return self.points[0]
        elif self.n_lines == 2:
            if direction == 1:
                return self.points[0]
            elif direction == 2:
                return self.points[1]
            else:
                msg = f'Received direction={direction} for track segment with two kilometrage lines. Set direction=1 for direction track or direction=2 for opposite track kilometrage.'
                raise ValueError(msg)
        else:
            raise NotImplementedError('Case not possible')

    def values_in_direction(self, direction: int) -> list[str]:
        """Returns kilometrage values for one direction. If track segment has only one km line for both directions, parameter direction is ignored."""
        if self.n_lines == 1:
            return self.values[0]
        elif self.n_lines == 2:
            if direction == 1:
                return self.values[0]
            elif direction == 2:
                return self.values[1]
            else:
                msg = f'Received direction={direction} for track segment with two kilometrage lines. Set direction=1 for direction track or direction=2 for opposite track kilometrage.'
                raise ValueError(msg)
        else:
            raise NotImplementedError('Case not possible')

    def lengths_in_direction(self, direction: int) -> list[float]:
        """Returns nominal geometric lengths for one direction. If track segment has only one km line for both directions, parameter direction is ignored."""
        if self.n_lines == 1:
            return self.lengths[0]
        elif self.n_lines == 2:
            if direction == 1:
                return self.lengths[0]
            elif direction == 2:
                return self.lengths[1]
            else:
                msg = f'Received direction={direction} for track segment with two kilometrage lines. Set direction=1 for direction track or direction=2 for opposite track kilometrage.'
                raise ValueError(msg)
        else:
            raise NotImplementedError('Case not possible')

    def lengths_type_in_direction(self, direction: int) -> list[str]:
        """Returns type of geometric lengths for one direction ('computed', 'nominal'). If track segment has only one km line for both directions, parameter direction is ignored."""
        if self.n_lines == 1:
            return self.lengths_type[0]
        elif self.n_lines == 2:
            if direction == 1:
                return self.lengths_type[0]
            elif direction == 2:
                return self.lengths_type[1]
            else:
                msg = f'Received direction={direction} for track segment with two kilometrage lines. Set direction=1 for direction track or direction=2 for opposite track kilometrage.'
                raise ValueError(msg)
        else:
            raise NotImplementedError('Case not possible')

    def offset_in_direction(self, direction: int) -> list[float]:
        """Returns offset at the start of each kilometrage segment."""
        if self.n_lines == 1:
            return self.offset_m[0]
        elif self.n_lines == 2:
            if direction == 1:
                return self.offset_m[0]
            elif direction == 2:
                return self.offset_m[1]
            else:
                msg = f'Received direction={direction} for track segment with two kilometrage lines. Set direction=1 for direction track or direction=2 for opposite track kilometrage.'
                raise ValueError(msg)
        else:
            raise NotImplementedError('Case not possible')

    def _set_lengths_for_direction(self, lengths: list[float], direction: int):
        """Private method to set geometric lengths for one direction."""
        if self.n_lines == 1 and direction == 0:
            self._km_lengths[0] = lengths
        elif self.n_lines == 2 and direction == 1:
            self._km_lengths[0] = lengths
        elif self.n_lines == 2 and direction == 2:
            self._km_lengths[1] = lengths
        else:
            raise ValueError(
                f'Received direction = {direction} but track segment has {self.n_lines} direction(s). If one direction exists, direction must be 0. If two directions exist, direction must be 1 or 2'
            )

    def _set_lengths_type_for_direction(self, lengths_type: list[str], direction: int):
        """Private method to set geometric lengths type for one direction."""
        if self.n_lines == 1 and direction == 0:
            self._km_lengths_type[0] = lengths_type
        elif self.n_lines == 2 and direction == 1:
            self._km_lengths_type[0] = lengths_type
        elif self.n_lines == 2 and direction == 2:
            self._km_lengths_type[1] = lengths_type
        else:
            raise ValueError(
                f'Received direction = {direction} but track segment has {self.n_lines} direction(s). If one direction exists, direction must be 0. If two directions exist, direction must be 1 or 2'
            )

    def _set_km_lines_for_direction(self, km_lines: list[LineString], direction: int):
        """Private method to set kilometrage lines for one direction."""
        if self.n_lines == 1 and direction == 0:
            self._lines[0] = km_lines
        elif self.n_lines == 2 and direction == 1:
            self._lines[0] = km_lines
        elif self.n_lines == 2 and direction == 2:
            self._lines[1] = km_lines
        else:
            raise ValueError(
                f'Received direction = {direction} but track segment has {self.n_lines} direction(s). If one direction exists, direction must be 0. If two directions exist, direction must be 1 or 2'
            )

    def _set_pre_values(self, points: list[Point], values: list[str]):
        """Method to set kilometrage values for one direction."""
        sorted_index = self.argsort_km_values(values)
        self._pre_km_values = [values[i] for i in sorted_index]
        self._pre_km_points = [points[i] for i in sorted_index]

    def _pre_values(self) -> Tuple[list[str], list[Point]]:
        """Method which returns pre km values and points."""
        return self._pre_km_values, self._pre_km_points

    def add_km_point(self, point: Point, value: str, length: float, direction: int):
        """Method to add kilometrage points, values and geometric lengths to respective attributes for direction. Note that values are appended.

        Parameter
        ---------
        point: Point
            A new point to add to the kilometrage line (coordinates)
        value: str
            The kilometrage value at the new point as string (DB format)
        length: float
            The nominal geometric length from new point to next point (meter)
        direction: int
            The direction. For one kilometrage line (one direction) directionc can only be 0. For two kilometrage lines (two directions), it can be 1 or 2.
        """

        # get key (index of list)
        if (self.n_lines == 1 and direction == 0) or (self.n_lines == 2 and direction == 1):
            key = 0
        elif self.n_lines == 2 and direction == 2:
            key = 1
        else:
            raise ValueError(
                f'Received direction = {direction} but track segment has {self.n_lines} direction(s). If one direction exists, direction must be 0. If two directions exist, direction must be 1 or 2'
            )

        # append
        self._km_points[key].append(point)
        self._km_values[key].append(value)
        self._km_lengths[key].append(length)

        # sort and set
        sorted_index = self.argsort_km_values(self._km_values[key])

        self._km_points[key] = [self._km_points[key][i] for i in sorted_index]
        self._km_values[key] = [self._km_values[key][i] for i in sorted_index]
        self._km_lengths[key] = [self._km_lengths[key][i] for i in sorted_index]

    @staticmethod
    def argsort_km_values(values: list[str]) -> list[int]:
        """Sort kilometrage values in DB format.

        The function sorts kilometrage values in db format (strings) while considering overlength notation.

        Parameter
        ---------
        values: list[str]
            List of kilometrage values in db format (e.g. '3.6 + 53').
        """
        sorted_index = np.argsort([float(val.split('+')[0].replace(',', '.')) for val in values])
        for i in range(len(sorted_index) - 1):
            # sets correct order for same km values by comparing meter
            if only_km_db(values[sorted_index[i]]) == only_km_db(values[sorted_index[i + 1]]) and only_m_db(
                values[sorted_index[i]]
            ) > only_m_db(values[sorted_index[i + 1]]):
                temp = sorted_index[i]
                sorted_index[i] = sorted_index[i + 1]
                sorted_index[i + 1] = temp

            # same as above but now meter include overlength
            elif (
                only_km_db(values[sorted_index[i]]) == only_km_db(values[sorted_index[i + 1]])
                and only_m_db(values[sorted_index[i]]) == only_m_db(values[sorted_index[i + 1]])
                and only_m_db(values[sorted_index[i]], with_overlength=True)
                > only_m_db(values[sorted_index[i + 1]], with_overlength=True)
            ):
                temp = sorted_index[i]
                sorted_index[i] = sorted_index[i + 1]
                sorted_index[i + 1] = temp

        return sorted_index

    def compute_geometric_length(self):
        """Computes the geometric length in meter for each direction of track segment and set attribute."""

        # compute lengths for each direction
        if self.n_lines == 1:
            km_lines = self.lines[0]
            length = [np.sum([line.length for line in km_lines])]

        elif self.n_lines == 2:
            km_lines = self.lines
            length = [np.sum([line.length for line in km_lines[i]]) for i in range(2)]

        else:
            raise NotImplementedError(f'self.n_km_lines = {self.n_lines}. Possible values should only be 1 or 2.')

        # set attribute
        self._length = length

    def compute_nominal_length(self):
        """Computes the nominal geometric length in meter for each direction of track segment and set attribute."""
        directions = [0] if self.n_lines == 1 else [1, 2]
        for direction in directions:
            km_lengths = self.lengths_in_direction(direction=direction)
            km_values = self.values_in_direction(direction=direction)
            km_lengths_type = self.lengths_type_in_direction(direction=direction)

            for i in range(len(km_lengths)):
                if km_lengths_type[i] == 'computed':
                    km_lengths[i] = (db_km_to_km(km_values[i + 1]) - db_km_to_km(km_values[i])) * 1000

            dir_key = 0 if direction in [0, 1] else 1
            self._km_lengths[dir_key] = km_lengths

    def compute_geometric_offset(self):
        """Computes the geometric offset (overlength, underlength) for each kilometrage segment based on official geometric lengths."""

        geometric_offset_m: list[float] = [0]
        # compute lengths for each direction
        if self.n_lines == 1:
            km_lines = self.lines[0]
            lengths = self.lengths_in_direction(direction=0)
            lengths_types = self.lengths_type_in_direction(direction=0)

            segment_lengths = [line.length for line in km_lines]

            for ol, sl, lt in zip(lengths[:-1], segment_lengths[:-1], lengths_types[:-1]):
                difference_m = sl - ol
                if abs(difference_m) > 3:
                    offset_m = difference_m

                else:
                    offset_m = 0

                # append current offset
                geometric_offset_m.append(offset_m)

            # transfer over-/underlength to following segments

            for i in range(len(geometric_offset_m) - 1):
                if lengths_types[i + 1] == 'computed' and any([lt == 'nominal' for lt in lengths_types]):
                    geometric_offset_m[i + 1] += geometric_offset_m[i]

                else:
                    geometric_offset_m[i + 1] = 0

            geometric_offset_list = [geometric_offset_m]

        elif self.n_lines == 2:
            geometric_offset_list = []
            for direction in [1, 2]:
                geometric_offset_m: list[float] = [0]

                km_lines = self.lines[direction - 1]
                lengths = self.lengths_in_direction(direction=direction)
                lengths_types = self.lengths_type_in_direction(direction=direction)
                segment_lengths = [line.length for line in km_lines]

                for ol, sl, lt in zip(lengths[:-1], segment_lengths[:-1], lengths_types[:-1]):
                    # if lt == 'nominal':
                    difference_m = sl - ol
                    if abs(difference_m) > 3:
                        offset_m = difference_m

                    else:
                        offset_m = 0

                    # append current offset
                    geometric_offset_m.append(offset_m)

                # transfer over-/underlength to following segments
                for i in range(len(geometric_offset_m) - 1):
                    if lengths_types[i + 1] == 'computed' and any([lt == 'nominal' for lt in lengths_types]):
                        geometric_offset_m[i + 1] += geometric_offset_m[i]

                    else:
                        geometric_offset_m[i + 1] = 0

                geometric_offset_list.append(geometric_offset_m)

        else:
            raise NotImplementedError(f'self.n_km_lines = {self.n_lines}. Possible values should only be 1 or 2.')

        # set attribute
        self._offset_m = geometric_offset_list

    def correct_point_positions(self):
        """Corrects points positions by nominal segment lengths."""
        directions = [0] if self._n_km_lines == 1 else [1, 2]
        direction_key = 0
        for direction in directions:
            if len(directions) == 2:
                direction_key = direction - 1
            km_points = self.points_in_direction(direction=direction)
            km_lines = self.lines[direction_key]
            if len(km_points) - len(km_lines) > 1:
                km_points = km_points[: 1 + len(km_lines) - len(km_points)]

            # if difference between nominal geometric length and geometric length aligns for two neigbouring segments
            # move km point accordingly
            for i in range(1, len(km_points) - 1):
                # get values
                km_points = self.points_in_direction(direction=direction)
                km_lengths = self.lengths_in_direction(direction=direction)
                km_lines = self.lines[direction_key]
                km_segment_lengths = [line.length for line in km_lines]
                km_lengths_types = self.lengths_type_in_direction(direction=direction)

                if abs(km_lengths[i - 1]) < 1e-6 or abs(km_lengths[i]) < 1e-6:
                    # skip km jumps
                    continue

                diff_1 = km_lengths[i - 1] - km_segment_lengths[i - 1]
                diff_2 = km_lengths[i] - km_segment_lengths[i]

                if (
                    diff_1 * diff_2 < 0 and min([abs(diff_1), abs(diff_2)]) > 1.5
                ):  # errors must have opposite sign and must be greater than threshold
                    if (
                        km_lengths_types[i - 1] == km_lengths_types[i] == 'nominal'
                    ):  # or km_lengths_types[i-1] == km_lengths_types[i] == 'computed':
                        if abs(diff_1) > abs(diff_2):
                            if diff_2 < 0:
                                new_km_point = km_lines[i].interpolate(-diff_2)
                                move_right = True
                            else:
                                new_km_point = km_lines[i - 1].interpolate(km_segment_lengths[i - 1] - diff_2)
                                move_right = False
                        else:
                            # abs(diff_1) < abs(diff_2)
                            if diff_1 > 0:
                                new_km_point = km_lines[i].interpolate(diff_1)
                                move_right = True
                            else:
                                new_km_point = km_lines[i - 1].interpolate(km_lengths[i - 1])
                                move_right = False

                        if move_right == True:
                            new_line_1, new_line_2 = split_line_at_point(km_lines[i], new_km_point)
                            new_km_line_1 = LineString(list(km_lines[i - 1].coords) + list(new_line_1.coords))
                            new_km_line_2 = LineString(new_line_2.coords)

                        else:  # move left
                            new_line_1, new_line_2 = split_line_at_point(km_lines[i - 1], new_km_point)
                            new_km_line_1 = LineString(new_line_1.coords)
                            new_km_line_2 = LineString(list(new_line_2.coords) + list(km_lines[i].coords))

                        # remove original line
                        rem = km_lines.pop(i)
                        rem = km_lines.pop(i - 1)

                        # add splitted km lines to existing km lines
                        km_lines.insert(i - 1, new_km_line_1)
                        km_lines.insert(i, new_km_line_2)

                        km_points[i] = new_km_point

                self._km_points[direction_key] = km_points
                self._lines[direction_key] = km_lines

    def km(self, point: Point, direction: int = 0, return_type: Literal['db', 'float'] = 'float') -> Union[float, str]:
        """Returns the kilometrage value for a given point and direction.

        The computation of the kilometrage value is based on the geometry of the kilometrage lines as well as the kilometrage points and values of the Kilometrage instance.

        Parameter
        ---------
        point: Point
            The UTM coordinates (horizontal, vertical) for which kilometrage will be computed. Point will be projected on kilometrage line without consideration of the points distance. Must be passed as shapely Point instance.
        direction:
            The direction for which the kilometer is computed.
        return_type: Literal['db', 'float']
            Controls the return type of the function. If set to 'db' returns the kilometer as string in db-format (e.g. '3.6 + 53'). If set to 'float', returns kilometer as float.

        Returns
        -------
        km: float | str
            The computed kilometrage value. The type of returned variable depends on parameter, see 'return_type'.
        """
        # number of kilometrage lines
        n_lines = self.n_lines
        # error message
        direction_error_str = f'Invalid value for direciont: {direction}. There exist two kilometrage lines, one for each direction. Set direction=1 or direction=2.'

        # verify input direction and get kilometrage lines and values if legit direction
        if n_lines == 1:
            if direction != 0:
                # direction doesn't matter
                logger.debug(
                    f'Received direction={direction}. Ignoring direction as there exists only on kilometrage line.'
                )

            km_lines = self.lines[0]
            km_values = self.values_in_direction(direction=0)

        elif n_lines == 2:
            # two directions
            if direction == 0:
                raise ValueError(direction_error_str)

            elif direction == 1 or direction == 2:
                km_lines = self.lines[direction - 1]
                km_values = self.values_in_direction(direction=direction)

            else:
                raise ValueError(direction_error_str)

        else:
            raise NotImplementedError(f'self.n_km_lines = {self.n_lines}. Possible values should only be 1 or 2.')

        # get km_line segment closest to point
        distances = [point.distance(km_line_seg) for km_line_seg in km_lines]
        min_index = np.argmin(distances)
        km_segment = km_lines[min_index]

        # kilometer value at start of kilometrage segment
        km_segment_start = db_km_to_km(km_values[min_index])
        km_segment_end = db_km_to_km(km_values[min_index + 1])

        # coordinates of segment line
        # km_points = [Point(coord) for coord in km_segment.coords]

        # project point on km segment
        point_on_kilometrage = nearest_points(km_segment, point)[0]

        # if only km information from ISR (and not from GEO-STRECKE dataset)
        if self._enhance_kilometrage == False:
            km = km_segment_start + km_segment.project(point_on_kilometrage) / 1000
            if return_type == 'float':
                return round(km, 4)
            elif return_type == 'db':
                return km_to_db_km(km)

        else:  # complex computation of kilometrage
            # get kilometrage
            km_percentage = km_segment.project(point_on_kilometrage, normalized=True)

            # always one km line (min_index) less than km values
            if min_index > len(km_values) - 2:
                nominal_length_m = (db_km_to_km(km_values[-1]) - db_km_to_km(km_values[min_index])) * 1000
            else:
                nominal_length_m = (db_km_to_km(km_values[min_index + 1]) - db_km_to_km(km_values[min_index])) * 1000

            # precompute km line error (difference between geometric length of km line(s) and nominal geometric length)
            #            key = 0 if direction < 2 else 1
            #            km_length_km = np.sum(self.length_m[key]) / 1000

            # current and next kilometrage value (always at start of segment)
            curr_km_value = km_values[min_index]
            next_km_value = km_values[min_index + 1]

            km_length_type = self.lengths_type_in_direction(direction=direction)[min_index]
            offset_m_list = self.offset_in_direction(direction=direction)

            # distance based on km values at start and end of segment
            nominal_segment_length_km = db_km_to_km(next_km_value) - db_km_to_km(curr_km_value)

            # nominal geometric length of segment
            nominal_geometric_length_m = self.lengths_in_direction(direction=direction)[min_index]
            nominal_length_m = round(1000 * nominal_segment_length_km)

            # compute difference between the geometric length of kilometrage line and the nominal geometric length of line (from db-geo-strecken dataset)
            segment_error_m = km_segment.length - nominal_geometric_length_m
            official_diff = db_km_to_km(km_values[-1]) - db_km_to_km(km_values[0])

            km_points_ = self.points_in_direction(direction=direction)
            if min_index < len(km_points_) - 1 and km_points_[min_index + 1].distance(point_on_kilometrage) < 3:
                # if km is almost at end of segment, set km value to end of segment
                km = db_km_to_km(km_values[min_index + 1])

            elif nominal_geometric_length_m < 1e-6:
                # km jump: every km value inside the jump is set to km value after km jump
                # note: segment should be very short (~ 1m)
                if min_index < len(km_lines) - 1:
                    km_segment_end = db_km_to_km(km_values[min_index + 1])
                    km = km_segment_end
                else:
                    km_segment_start = db_km_to_km(km_values[min_index])
                    km = km_segment_start
                # km_db = km_to_db_km(km)

            elif abs(segment_error_m) < 1:
                # difference between nominal geometric length and geometric length is small: scale to official length
                distance_from_start_km = km_percentage * (nominal_geometric_length_m / 1000)
                km = km_segment_start + distance_from_start_km

            else:
                # difference between offical length and geometric length is not small and positive: overlength
                # -> treat as overlength after offical length is reached
                # difference between offical length and geometric length is not small and negative: missing length
                # -> treat as km jump at end of segment

                # km line error of current kilometrage segment
                segment_error_m = km_segment.length - nominal_geometric_length_m

                if segment_error_m < 0:  # no km info from geo strecken
                    # segment error negative: missing length and no km info
                    # missing length at start: offset
                    # missing length at end: no offset
                    if (
                        self._offset_from_start_m != 0 and min_index == 0
                    ):  # offset from start is only considered for first segment
                        distance_from_start_km = (
                            km_percentage * (km_segment.length / 1000) + self._offset_from_start_m / 1000
                        )
                    elif self._has_km_info == False:
                        distance_from_start_km = km_percentage * (nominal_geometric_length_m / 1000)
                    elif km_length_type == 'computed':  # has_km_info is True
                        distance_from_start_km = km_percentage * (nominal_geometric_length_m / 1000)
                    else:
                        distance_from_start_km = km_percentage * (km_segment.length / 1000)

                elif segment_error_m > 0:
                    if self._offset_from_start_m != 0 and min_index == 0:  # final
                        distance_from_start_km = (
                            km_percentage * (km_segment.length / 1000) + self._offset_from_start_m / 1000
                        )
                    elif self._has_km_info == False:
                        # treat error as continously increasing with track length -> substract percentage of error
                        distance_from_start_km = km_percentage * (km_segment.length / 1000) - km_percentage * (
                            segment_error_m / 1000
                        )
                    elif km_length_type == 'computed':  # has_km_info is True
                        distance_from_start_km = km_percentage * (nominal_geometric_length_m / 1000)
                    else:
                        distance_from_start_km = km_percentage * (km_segment.length / 1000)
                else:
                    # distance_from_start_m = km_percentage * (km_segment.length / 1000)
                    raise NotImplementedError('Can never be accessed.')

                km = km_segment_start + distance_from_start_km

            offset_m = offset_m_list[min_index]
            km += offset_m / 1000

            # special formatting when km value (float) exceeds value at segment end
            if km > db_km_to_km(next_km_value) or only_km_db(km_to_db_km(km)) > only_km_db(next_km_value):
                # if km is greater than last km value of segment treat as overlength
                # overlength in db format is shown as '14,9 + 52 | +1000'
                curr_km, curr_meter = curr_km_value.split('+')

                if db_km_to_km(curr_km_value) >= db_km_to_km(next_km_value):
                    km_db = f'{curr_km} +{curr_meter} | +{round(1000*(km - db_km_to_km(next_km_value)) + nominal_length_m,1)}'
                else:
                    # meter_added = round(float(curr_meter) + nominal_length_m)
                    # if nominal_length_m < 0: nominal_length_m = 0
                    overlength_m = round(1000 * (km - db_km_to_km(next_km_value)))
                    temp_km = km - overlength_m / 1000
                    km_at_overlength_start = km_to_db_km(temp_km)
                    km_db = f'{km_at_overlength_start} | +{round(overlength_m, 1)}'

                # get kilometer and meter values seperately
                def to_km(db_string):
                    return float(db_string.split(' | ')[0].split('+')[0].replace(',', '.').strip())

                def to_m(db_string):
                    return float(db_string.split(' | ')[0].split('+')[1].replace(',', '.').strip())

                next_only_km = to_km(next_km_value)
                curr_only_km = to_km(km_db)
                curr_only_m = to_m(km_db)

                # current km greater than next km
                if next_only_km < curr_only_km:
                    # compute difference and overlength
                    diff_only_km = curr_only_km - next_only_km
                    new_only_km = next_only_km
                    new_only_m = round(curr_only_m + diff_only_km * 1000, 1)

                    if '|' in km_db:
                        overlength_str = km_db.split(' | ')[1]
                        if (
                            new_only_km == next_only_km
                            and (float(overlength_str.replace('+', '')) + new_only_m) / 1000 < diff_only_km
                        ):
                            km_db = f'{new_only_km} +{float(overlength_str.replace("+","")) + new_only_m}'
                        else:
                            km_db = f'{new_only_km} +{new_only_m} | {overlength_str}'
                    else:
                        km_db = f'{new_only_km} +{new_only_m}'

            elif km < db_km_to_km(curr_km_value):
                diff_m = round(km - db_km_to_km(curr_km_value), 3) * 1000
                km_db = f'{curr_km_value} | +{diff_m}'

            else:
                km_db = km_to_db_km(km)

            # return type
            if return_type == 'db':
                return km_db
            elif return_type == 'float':
                return km
            else:
                raise ValueError(f'Unkown return_type: {return_type}')

    def integrate_kilometrage_points(
        self,
        values_list: Tuple[str, list[Point], Union[Literal['before', 'after'], None], float],
        direction: int,
        boundary_kms: Tuple[str, str],
        last_val: bool = False,
        first_val: bool = False,
    ):
        """Integrates official kilometrage point given by parameter 'values_list'. Must only be used by TrackSegment instances passing kilometrage information from data set db-geo-strecken, as it is a very specialized function. To simply set kilometrage points, use Kilometrage.add_km_point.

        The general idea is to split the kilometrage line into multiple segments, where one segment always runs from one km value (point) to the next km value (point).

        Parameters
        ----------
        values_list: Tuple[str, list[Point], Union[Literal['before', 'after'], None], float])
            - values_list[0]: str
                The kilometrage value in DB format as string.
            - values_list[1]: list[Point]
                The geometric point of the kilomatrage value. If this list contains more than one point, that means km value is outside the geometry of the track, so geometry of km_line will be expanded using those points.
            - value_list[2]: Union[Literal['before', 'after'], None]
                If values_list[1] has more than one point, this parameter indicates in which direction km line will be expanded
            - value_list[3]: float
                The official length in meter until the next kilometrage value.
        direction: int
            The direction for which kilomerage points will be added.
        """

        # extract values
        km_str = values_list[0]
        point_list = values_list[1]
        merge = values_list[2]
        nominal_geometric_length = values_list[3]

        # get km lines for direction
        km_lines = self.line(direction=direction)

        # if no expansions of km line (one point)
        if isinstance(merge, type(None)) or merge == 'end_point':
            assert len(point_list) == 1, f'Wrong number of points in list {len(point_list)} (== 1)'

            # nearest line to km point
            point = point_list[0]
            distances = [point.distance(line) for line in km_lines]
            min_index = np.argmin(distances)
            km_line = km_lines[min_index]

            # km values
            km_values = self.values_in_direction(direction=direction)
            km_points = self.points_in_direction(direction=direction)

            # get projected distances along kilometrage
            point_running_distance = km_line.project(point)
            km_points_running_distances = km_line.project(km_points)

            # dont add point if it doesnt fit with the logical order of already existing km points
            if not any(
                [
                    point_running_distance < km_point_rd
                    and db_km_to_km(km_str) > db_km_to_km(km_val)
                    and km_line.distance(km_point) < 10
                    for (km_point_rd, km_val, km_point) in zip(km_points_running_distances, km_values, km_points)
                ]
            ):
                # project km point on line
                point_on_km_line = nearest_points(point, km_line)[1]

                # set point
                self.add_km_point(
                    point=point_on_km_line, value=km_str, length=nominal_geometric_length, direction=direction
                )

                # check if point is at boundary of km line
                is_boundary_point = (point_on_km_line.distance(Point(km_line.coords[0])) < 1e-4) or (
                    point_on_km_line.distance(Point(km_line.coords[-1])) < 1e-4
                )

                # get projected distances
                p0_projected = km_line.project(point_list[0], normalized=True)
                p0_kmline = nearest_points(km_line, point_list[0])[0]

                # no boundary point -> splitting line possible
                if is_boundary_point == False:
                    # split line at point
                    km_line_1, km_line_2 = split_line_at_point(line=km_line, point=point_on_km_line)

                    # km values
                    km_values = self.values_in_direction(direction=direction)

                    # check if value is op from
                    if km_str.replace(',', '.').replace(' ', '') == boundary_kms[0].replace(',', '.').replace(' ', ''):
                        # if op from is no boundary point means it does not lie at start of km line
                        # therefore we need to compute a new value for the start of the km line
                        # based on its geometry and then set the computed value

                        # set point to start of km line
                        start_point = Point(km_lines[0].coords[0])
                        # index of op from
                        from_km_index = km_values.index(km_str)

                        # compute
                        km = (
                            db_km_to_km(km_str)
                            - km_line_1.length / 1000
                            - np.sum([line.length for line in km_lines[:from_km_index]]) / 1000
                        )
                        km_db = km_to_db_km(km)

                        # check if value or point already exists
                        km_value_exists = any([abs(km - db_km_to_km(km_)) * 1000 < 1 for km_ in km_values])
                        km_points = self.points_in_direction(direction=direction)
                        km_point_exists = any([start_point.distance(km_point) < 1e-4 for km_point in km_points])

                        # only add point if km value does not
                        # only split km line if km value does not exist but the respective point already exists
                        if km_value_exists == False and km_point_exists == False:
                            # remove original line
                            rem = km_lines.pop(min_index)
                            # add splitted km lines to existing km lines
                            km_lines.insert(min_index, km_line_1)
                            km_lines.insert(min_index + 1, km_line_2)
                            self.add_km_point(
                                point=start_point, value=km_db, length=km_line_1.length, direction=direction
                            )
                        elif km_value_exists == False and km_point_exists == True:
                            # remove original line
                            rem = km_lines.pop(min_index)
                            # add splitted km lines to existing km lines
                            km_lines.insert(min_index, km_line_1)
                            km_lines.insert(min_index + 1, km_line_2)

                    # check if value is op to
                    elif km_str.replace(',', '.').replace(' ', '') == boundary_kms[1].replace(',', '.').replace(
                        ' ', ''
                    ):
                        # if op to is no boundary point means it does not lie at end of km line
                        # therefore we need to compute a new value for the end of the km line
                        # based on its geometry and then set the computed value

                        # set end point
                        end_point = Point(km_lines[-1].coords[-1])

                        # compute km value
                        km = db_km_to_km(km_str) + km_line_2.length / 1000
                        km_db = km_to_db_km(km)

                        # check if km value or point already exists
                        km_value_exists = any([abs(km - db_km_to_km(km_)) * 1000 < 1 for km_ in km_values])
                        km_points = self.points_in_direction(direction=direction)
                        km_point_exists = any([end_point.distance(km_point) < 1e-4 for km_point in km_points])

                        # only add if value and point dont exist
                        if km_value_exists == False and km_point_exists == False:
                            # remove original line
                            rem = km_lines.pop(min_index)
                            # add splitted km lines to existing km lines
                            km_lines.insert(min_index, km_line_1)
                            km_lines.insert(min_index + 1, km_line_2)
                            self.add_km_point(
                                point=end_point, value=km_db, length=km_line_2.length, direction=direction
                            )
                        elif km_value_exists == False and km_point_exists == True:
                            # remove original line
                            rem = km_lines.pop(min_index)
                            # add splitted km lines to existing km lines
                            km_lines.insert(min_index, km_line_1)
                            km_lines.insert(min_index + 1, km_line_2)

                    else:
                        # remove original line
                        rem = km_lines.pop(min_index)
                        # add splitted km lines to existing km lines
                        km_lines.insert(min_index, km_line_1)
                        km_lines.insert(min_index + 1, km_line_2)
                        # can this be deleted ? Should never be entered
                        if (
                            first_val == True
                            and len(km_lines) == 2
                            and len(km_values) == 1
                            and (
                                km_str.replace(',', '.').replace(' ', '')
                                == boundary_kms[0].replace(',', '.').replace(' ', '')
                            )
                        ):
                            km_db = km_to_db_km(db_km_to_km(km_str) - km_lines[0].length / 1000)
                            self.add_km_point(
                                point=Point(km_lines[0].coords[0]),
                                value=km_db,
                                length=km_lines[0].length,
                                direction=direction,
                            )

                # get km values
                km_values = self.values_in_direction(direction=direction)

                # correction if something went wrong and one km_value was not set
                # check if a km point exists at the start and end of kilometrage
                # and if not, compute the km and it with the point
                if len(km_values) == len(km_lines) and last_val == True:
                    km_points = self.points_in_direction(direction=direction)
                    if not km_lines[0].project(km_points[0]) < 1e-3:
                        km_0 = km_to_db_km(db_km_to_km(km_values[0]) - km_lines[0].length / 1000)
                        self.add_km_point(
                            point=Point(km_lines[0].coords[0]),
                            value=km_0,
                            length=km_lines[0].length,
                            direction=direction,
                        )
                    elif not km_lines[-1].project(km_points[-1]) < 1e-3:
                        km_end = km_to_db_km(db_km_to_km(km_values[-1]) + km_lines[-1].length / 1000)
                        self.add_km_point(
                            point=Point(km_lines[-1].coords[-1]),
                            value=km_end,
                            length=km_lines[-1].length,
                            direction=direction,
                        )

                # set new km lines
                self._set_km_lines_for_direction(km_lines=km_lines, direction=direction)

        # else (serveral points)
        else:
            assert (merge == 'before') or (merge == 'after'), f'Wrong value for merge: {merge}'

            # nearest line to points
            distances = [np.mean(line.distance(point_list)) for line in km_lines]
            min_index = np.argmin(distances)
            km_line = km_lines[min_index]

            # compute projected distances along km line of point
            p0_projected = km_line.project(point_list[0], normalized=True)
            p0_kmline = nearest_points(km_line, point_list[0])[0]

            # checks if the merge flag may be erronous by verifying if the point already lies on the km line (instead of being some distance away from it)
            if (
                len(point_list) == 1
                and ((p0_projected > 1e-4) and (p0_projected) < 1 - 1e-4)
                and p0_kmline.distance(point_list[0]) < 1e-3
            ):
                # wrong merge (point is already on line, no need to merge)
                split_point = point_list[0]
                km_line_1, km_line_2 = split_line_at_point(line=km_line, point=split_point)

                # remove original line
                rem = km_lines.pop(min_index)

                # add splitted km lines to existing km lines
                km_lines.insert(min_index, km_line_1)
                km_lines.insert(min_index + 1, km_line_2)

                # set new km lines and add point
                self._set_km_lines_for_direction(km_lines=km_lines, direction=direction)
                self.add_km_point(point=split_point, value=km_str, length=km_line_2.length, direction=direction)

                # add value at end of rail (bigger than km_to)
                km_end_str = km_to_db_km(db_km_to_km(km_str) + km_line_2.length / 1000)

                self.add_km_point(point=Point(km_line_2.coords[-1]), value=km_end_str, length=0, direction=direction)

                if merge == 'before' and first_val == True and Point(km_lines[0].coords[0]).distance(split_point) > 0:
                    km_values = self.values_in_direction(direction=direction)
                    prev_km_val = km_to_db_km(db_km_to_km(km_values[0]) - km_lines[0].length / 1000)
                    self.add_km_point(
                        point=Point(km_line.coords[0]), value=prev_km_val, length=km_line.length, direction=direction
                    )

            # add points to existing km line according to value_list[2] (merge: before, after, None) (raise error if None)
            elif merge == 'before':
                # get km values and points
                km_values = self.values_in_direction(direction=direction)
                km_points = self.points_in_direction(direction=direction)
                # next km value that is greater than given kilometer
                next_km_val = [km_val for km_val in km_values if db_km_to_km(km_val) > db_km_to_km(km_str)]

                if len(next_km_val) == 0:
                    # no next km because it is the first point added
                    # have to use pre values (are set beforehand in TrackSegment.integrate_kilometrage_points)
                    km_values, km_points = self._pre_values()
                    next_km_val = [
                        km_val
                        for km_val in km_values
                        if (db_km_to_km(km_val) > db_km_to_km(km_str) or only_km_db(km_val) > only_km_db(km_str))
                        and not (only_km_db(km_val) < only_km_db(km_str))
                    ]

                if len(next_km_val) > 0:
                    # merge
                    index = km_lines.index(km_line)
                    rem = km_lines.pop(index)
                    km_line = LineString(point_list + list(km_line.coords))
                    km_lines.insert(index, km_line)

                    # get next km point
                    index = km_values.index(next_km_val[0])
                    next_km_point = km_points[index]

                    # project next km point on km line if it is not alredy on the line
                    if next_km_point.distance(km_line) > 1e-6:
                        next_km_point = nearest_points(km_line, next_km_point)[0]

                    # check if next point is at the end of km line -> split not possible
                    distance_percent = km_line.project(next_km_point, normalized=True)
                    if not ((distance_percent == 1)):
                        # split
                        km_line_1, km_line_2 = split_line_at_point(line=km_line, point=next_km_point)

                        # remove original line
                        rem = km_lines.pop(min_index)

                        # add splitted km lines to existing km lines
                        km_lines.insert(min_index, km_line_1)
                        km_lines.insert(min_index + 1, km_line_2)

                    # first point
                    point = point_list[0]
                    self._set_km_lines_for_direction(km_lines=km_lines, direction=direction)
                    self.add_km_point(point=point, value=km_str, length=nominal_geometric_length, direction=direction)

            else:
                # merge after
                km_line = LineString(list(km_line.coords) + point_list)

                # set split point
                split_km_point = point_list[0]

                # verify if boundary
                is_boundary_point = (split_km_point.distance(Point(km_line.coords[0])) < 1e-4) or (
                    split_km_point.distance(Point(km_line.coords[-1])) < 1e-4
                )
                if is_boundary_point == False:
                    # split at next km point
                    km_line_1, km_line_2 = split_line_at_point(km_line, split_km_point)

                    # remove original line
                    rem = km_lines.pop(min_index)

                    # add splitted km lines to existing km lines
                    km_lines.insert(min_index, km_line_1)
                    km_lines.insert(min_index + 1, km_line_2)
                    # first point
                    point = point_list[0]
                    # set
                    self._set_km_lines_for_direction(km_lines=km_lines, direction=direction)
                    self.add_km_point(point=point, value=km_str, length=nominal_geometric_length, direction=direction)

                else:
                    km_lines[-1] = km_line
                    self._set_km_lines_for_direction(km_lines=km_lines, direction=direction)
                    self.add_km_point(
                        point=point_list[-1], value=km_str, length=nominal_geometric_length, direction=direction
                    )

        self._has_km_info = True
