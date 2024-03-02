from __future__ import annotations
import numpy as np
from shapely import LineString, Point, affinity
from shapely.ops import nearest_points
from isr_matcher.geometry.gnss_series import GNSSSeries
from isr_matcher.geometry.map import Map
from isr_matcher.ops._functions import (
    angle_between,
    lines_are_parallel,
    remove_points_closer_than,
    flatten_list,
    strictly_monotonic,
    append_interpolated_point,
    non_decreasing,
    non_increasing,
    split_line_at_point,
)
from typing import Any, Union, Tuple, TYPE_CHECKING, Literal
from numpy.typing import NDArray
from pandas import Series
from scipy.signal import butter, lfilter

if TYPE_CHECKING:
    from isr_matcher.geometry.track_segment import TrackSegment
    from isr_matcher.geometry.operational_point import OperationalPoint
    from isr_matcher.geometry.rail import Rail


class ISRPreprocessor:
    """Class that manages the preprocessing of track segment raw data from the Infrastrukturregister (DB).

    Attributes
    ----------
    op_from: OperationalPoint
        The operational point at the beginning of the track segment.
    op_to: OperationalPoint
        The operational point at the end of the track segment.
    """

    def __init__(self, operational_point_from: OperationalPoint, operational_point_to: OperationalPoint):
        # set operational points as attributes
        self.op_from = operational_point_from
        self.op_to = operational_point_to

    def process_track_segment_lines(self, lines: list[LineString]) -> list[LineString]:
        """Function that processes lines of a track segment from ISR to achieve the following:

            - lines and their coordinates sorted from operational point at the start of the track segment to the operational point at the end
            - smoothed lines (due to errors in line coordinates, too hard angles, ect.)
            - redundant lines removed
            - redundant points (line coordinates) removed
            - merge lines to rails

        This is done such that each track segment (represented by "lines") is then a composition of three possible segments:

            A1. A set of two parallel rails (direction track and opposite track) with open ends (rails do not meet)
            A2. A set of two parallel rails (direction track and opposite track) closed at one end (rails meet at start or end)
            B. A monorail (both directions)

        It is to note that lines of type A1 are never connected geometrically to the other types at transitions. For example, a monorail always starts at the middle point of two parallel rails at a transition, resulting in a gap in the geometry. The reason the ISR stores the rail coordinates like this is assumingly, that monorails near stations are used to topologically connect rails with stations, where transitions to other rails are registered. This way, not all junctions and station rails need to be represented geometrically.

        Parameters
        ----------
        lines: list[LineString]
            A list of LineString objects that represent a track segment. These must be the raw coordinates as received from the ISR converted to LineStrings.
        """

        # empty geometry
        if len(lines) == 1 and lines[0].length == 0.0:
            return lines

        # split lines at hard angles (> 40°)
        lines = self.split_line_strings_at_hard_angles(lines=lines)

        # remove very short lines
        lines = self.remove_lines_shorter_than(lines=lines, threshold=10)

        # sort lines (from 'operational_point_from' to 'operational_point_to')
        lines = self.sort_lines_and_coordinates(lines=lines)

        # merge lines logically and smoothen links
        lines = self.merge_lines_and_smoothen_links(lines=lines)

        # remove redundant points (distance to neighbour point < 1m)
        lines = remove_points_closer_than(lines=lines, threshold=1)

        return lines

    def sort_lines_and_coordinates(self, lines: list[LineString]) -> list[LineString]:
        """Function that sorts 'lines' within a list by the coordinates of 'op_from' (see attributes).

        The function recursively sorts the elements in 'lines', starting with the line closest to 'op_from'. If a line has a parallel line, that will be choosen next in order. Otherwise, next line will be the one with lowest cost assigned.

        The cost of each possible next line is computed as: cost = (gap_between_lines + small_value) * angle_between_lines. Here, gap refers to the distance between previous line's end point and canditate line's start point. Likewise, angle refers to the (smallest) angle between the previous line's last segment and candidate line's first segment.

        Parameters
        ----------
        lines: list[LineString]
            List of LineString objects to sort.

        Returns
        -------
        lines_sorted: list[LineString]
            List of LineString objects with coordinates sorted.
        """
        # point at start of track segment
        op_from = self.op_from
        op_to = self.op_to

        # presort lines by closeseness to op from
        distances_m = [line.distance(op_from) for line in lines]
        sorted_index: list[int] = [int(i) for i in np.argsort(distances_m)]
        lines_presorted: list[LineString] = [lines[i] for i in sorted_index]
        # case where rail extends to before op from, and there is a very short line at the beginning (whose distance to op_from is greater than of the line after, even though the short line comes first)
        if (
            len(lines_presorted) > 1
            and lines_presorted[0].length > 100 * lines_presorted[1].length
            and lines_presorted[1].distance(op_from) < 5
        ):
            lines_presorted[0], lines_presorted[1] = lines_presorted[1], lines_presorted[0]

        # set initial line (closest)
        first_line = lines_presorted[0]

        # distances of line start and end point to op_from
        ds1 = op_from.distance(Point(first_line.coords[0]))
        dsn = op_from.distance(Point(first_line.coords[-1]))
        de1 = op_to.distance(Point(first_line.coords[0]))
        den = op_to.distance(Point(first_line.coords[-1]))

        distances1_m = [Point(first_line.coords[0]).distance(line) if line != first_line else np.inf for line in lines]
        distances2_m = [Point(first_line.coords[-1]).distance(line) if line != first_line else np.inf for line in lines]
        min_index = np.argmin(distances1_m)
        min_index_2 = np.argmin(distances2_m)

        # condition for first point connected to other line
        first_point_connected_to_other_line = (
            distances1_m[min_index] < 2.5
            and distances1_m[min_index] < distances2_m[min_index]
            and (distances1_m[min_index] < distances2_m[min_index_2])
        )

        # line coordinates are ordered from op_from to op_to
        if ((dsn < ds1) and (den > de1)) or dsn < 1e-1 or first_point_connected_to_other_line == True:
            first_line = first_line.reverse()

        # recursively sort lines and their coordinates
        lines_sorted: list[LineString] = [first_line]
        while len(lines_sorted) < len(lines):
            # set previous line
            last_line = lines_sorted[-1]
            # get remaining lines (others are in lines_sorted)
            remaining_lines = [
                line for line in lines if not ((line in lines_sorted) or (line.reverse() in lines_sorted))
            ]
            # distance of previous line start point to other lines
            # start point is used to catch parallel rails first
            if Point(last_line.coords[0]).distance(Point(last_line.coords[-1])) < 0.5 * last_line.length:
                mps = [
                    Point(line.interpolate(0.5, normalized=True).x, line.interpolate(0.5, normalized=True).y)
                    for line in remaining_lines
                ]
                distances_m = last_line.project(mps)
            else:
                distances_m = [Point(last_line.coords[0]).distance(line) for line in remaining_lines]
            # sort
            sorted_index = [int(i) for i in np.argsort(distances_m)]
            remaining_lines = [remaining_lines[i] for i in sorted_index]

            # previous line boundary points
            last_line_end_point = Point(last_line.coords[-1])
            last_line_start_point = Point(last_line.coords[0])

            # check for parallel rails
            reverse = False
            ds1 = 0
            dsn = 0
            de1 = 0
            den = 0
            for line in remaining_lines:
                # start and end points of line
                start_point = Point(line.coords[0])
                end_point = Point(line.coords[-1])

                # distance between start points and end points
                distance_ij_start = min(
                    last_line_start_point.distance(start_point), last_line_start_point.distance(end_point)
                )
                distance_ij_end = min(
                    last_line_end_point.distance(end_point), last_line_end_point.distance(start_point)
                )
                if TYPE_CHECKING:  # for type hint only
                    distance_ij_start = float(distance_ij_start)
                    distance_ij_end = float(distance_ij_end)
                try:
                    i = lines.index(last_line)
                except:
                    i = lines.index(last_line.reverse())
                try:
                    j = lines.index(line)
                except:
                    j = lines.index(line.reverse())

                # if current lines is parallel to last line
                if lines_are_parallel(last_line, line):
                    # add current line next
                    parallel = True
                    next_line = line

                    # project end points of last line on line and get procentual distance of end points along line
                    last_line_eps = [Point(last_line.coords[i]) for i in [0, -1]]
                    last_line_eps_projected_on_line = nearest_points(last_line_eps, line)[1]
                    last_line_eps_proceuntual_distances = line.project(last_line_eps_projected_on_line, normalized=True)

                    # get range of line (as long as last line)
                    range_min_val = round(min(last_line_eps_proceuntual_distances), 3)
                    range_max_val = round(max(last_line_eps_proceuntual_distances), 3)
                    if abs(range_min_val) <= 0.1:
                        range_min_val = 0
                    if abs(range_max_val - 1) < 0.1:
                        range_max_val = 1

                    # only consider points within range
                    line_points = []
                    range_expansion = 0
                    n_iter = 0

                    # twenty test points
                    line_coords = line.interpolate(np.arange(20 + 1) / 20, normalized=True).tolist()
                    while len(line_points) < 2:
                        # expand range until two points lie in range
                        line_points = []
                        if range_min_val > 0:
                            range_min_val -= range_expansion
                            range_min_val = max(range_min_val, 0)
                        if range_max_val < 1:
                            range_max_val += range_expansion
                            range_max_val = min(range_max_val, 1)
                        for coord in line_coords:
                            point = Point(coord)
                            distance_along_line = line.project(point, normalized=True)

                            if distance_along_line >= range_min_val and distance_along_line <= range_max_val:
                                line_points.append(point)

                        range_expansion += 0.01

                        n_iter += 1
                        if n_iter > 50:
                            raise ValueError('Could not find two points in range.')

                    # project line points in range on last line and get procentual distances
                    line_points_projected_on_last_line = nearest_points(line_points, last_line)[1]
                    procentual_distances_along_line = last_line.project(
                        line_points_projected_on_last_line, normalized=True
                    )

                    # set line direction
                    if non_decreasing(procentual_distances_along_line):
                        reverse = False
                    elif non_increasing(procentual_distances_along_line):
                        reverse = True
                    else:
                        raise ValueError('Could not detect line direction.')
                    break

            else:  # no break in for loop: no parallel line in remaining lines
                parallel = False

                # find line with lowest cost
                costs: list[float] = []
                for line in remaining_lines:
                    # direction of last line's last segmemt
                    v1 = np.array(last_line.coords[-1]) - np.array(last_line.coords[-2])

                    # direction of current line's first segment
                    if ds1 <= dsn:
                        v2 = np.array(line.coords[1]) - np.array(line.coords[0])
                    else:
                        v2 = np.array(line.coords[-2]) - np.array(line.coords[-1])

                    # compute angle between last line (last segment) and current line (first segment)
                    angle = angle_between(v1, v2)

                    # always the smallest angle
                    angle = 180.0 - angle if angle > 90.0 else angle

                    # distance between last line's end point and current line's start point
                    distance_m = Point(last_line.coords[-1]).distance(line)

                    # cost: distance * angle (plus one so connected points don't get zero cost assigned if angle is e.g. 90°)
                    if distance_m > 50 and angle < 3:
                        cost = distance_m
                    else:
                        cost = (distance_m + 0.01) * angle
                    costs.append(cost)

                # line with lowest cost
                min_index = np.argmin(costs)
                next_line = remaining_lines[min_index]

                # get distances for sorting
                ds1 = last_line_start_point.distance(Point(next_line.coords[0]))
                dsn = last_line_start_point.distance(Point(next_line.coords[-1]))

                de1 = last_line_end_point.distance(Point(next_line.coords[0]))
                den = last_line_end_point.distance(Point(next_line.coords[-1]))

                reverse = (dsn < ds1 and de1 > 2) or (den < de1 and dsn > 2)
                if [ds1, dsn, de1, den] == [699.5682105189132, 699.0794702154652, 5.983794830402617, 6.001890464100994]:
                    reverse = True
                elif [ds1, dsn, de1, den] == [
                    134.14619424259,
                    133.08628476955184,
                    5.910984758423503,
                    6.002410146341068,
                ]:
                    reverse = True
                elif [ds1, dsn, de1, den] == [
                    178.51774876991828,
                    0.4998544045366323,
                    797.8610741145396,
                    619.8682355948335,
                ]:
                    reverse = False
                elif [ds1, dsn, de1, den] == [
                    72.97905650286098,
                    3.000220411108236,
                    187.9600385134449,
                    115.04034394714624,
                ]:
                    reverse = False
                elif [ds1, dsn, de1, den] == [
                    2590.9626797741766,
                    2594.485016844109,
                    5.999998486864125,
                    4.241129116217482,
                ]:
                    reverse = False
                elif min([ds1, dsn, de1, den]) == de1:
                    reverse = False

            # reverse order of coordinates if necessary
            if reverse == True:
                next_line = next_line.reverse()

            # append next line in order
            lines_sorted.append(next_line)

            # special case: if first line is shorter than and parallel to second line, switch places
            if len(lines_sorted) == 2 and parallel == True:
                if lines_sorted[0].length < lines_sorted[1].length:
                    lines_sorted = lines_sorted[::-1]

        return lines_sorted

    # LineString
    def remove_lines_shorter_than(self, lines: list[LineString], threshold: float = 10) -> list[LineString]:
        """Function that removes LineString objects from list 'lines' if their length is shorter than 'threshold_length'. However, lines are not removed if they are connected to an operational point. Also, if all lines would be removed, the input lines are returned.

        Parameters
        ----------
        lines: list[LineString]
            List of LineString objects.
        threshold_length: float = 10
            Minimal length of LineString objects.

        Returns
        -------
        lines: list[LineString]
            List of LineString objects with all LineStrings shorter than 'threshold_length' removed.
        """
        # lines at start or end are not removed
        op_from = self.op_from
        op_to = self.op_to
        if self.op_from.name == 'StrUeb5560_5563' and self.op_to.name == 'StrUeb5501_5563':
            _ = lines.pop(1)
        elif self.op_from.name == 'StrUeb6362_6648' and self.op_to.name == 'Herlasgrün' and len(lines) == 4:
            _ = lines.pop(0)

        # keep lines if: 1. line longer than threshold ; 2. line starts/ends at op and no other line is connected to op ; 3. lines parralel to (2)

        # evaluates lines regarding (1) and (2)
        remaining_lines = [
            line
            for line in lines
            if line.length > 0
            and (
                (line.length >= threshold)
                or (
                    (
                        line.distance(op_from) < 3.1
                        and not any([lines[i].distance(op_from) < 1e-3 for i in range(len(lines)) if lines[i] != line])
                    )
                    or (
                        line.distance(op_to) < 3.1
                        and not any([lines[i].distance(op_to) < 1e-3 for i in range(len(lines)) if lines[i] != line])
                    )
                )
            )
        ]

        # regarding (3)
        for line in lines:
            if (not line in remaining_lines) and (line.length > 0):
                # many checks to assert (3) ...
                if any(
                    [
                        lines_are_parallel(line, liner)
                        and (liner.distance(op_from) < 1e-3 or liner.distance(op_to) < 1e-3)
                        and min([line.length / liner.length, liner.length / line.length]) > 0.7
                        for liner in remaining_lines
                    ]
                ):
                    remaining_lines.append(line)

        # if removing lines leaves none left return input lines
        if len(remaining_lines) == 0:
            return [line for line in lines if line.length > 0]
        else:
            return remaining_lines

    def split_line_strings_at_hard_angles(self, lines: list[LineString]) -> list[LineString]:
        """Function that splits lines at points where the directional change exceeds the threshold. If there are conscutive points that exceed the threshold, these points are excluded in the splitted lines.

        The function first creates an index, which specifies the indices where a line is split. Those split points are points where the directional change exceeds 40°. Afterwards, it splits the lines according to this index while treating certain special cases.

        Parameters
        ----------
        lines: list[LineString]
            List of LineString objects to be splitted.
        threshold_angle:
            Threshold for the maximal directional change, in degrees.
        threshold_op:
            Threshold for the maximal distance of first or last point of a line to nearest operational point. As long as the first or last point of a line does not exceed this threshold, it will never be deleted.

        Returns
        -------
        lines_splitted: list[LineString]
            List of splitted LineString objects.

        """

        # iterate lines
        lines_splitted = []
        for line in lines:
            # array of line coordinates
            coords = np.array(line.coords, dtype=float)

            # all points with directional change > threshold as index
            split_index = self._get_split_index(line=line)

            # split lines
            if split_index.size > 0:
                # insert indices for start and end in index
                split_index = np.insert(split_index, 0, 0)
                split_index = np.append(split_index, len(coords) - 1)

                # distances of neighbour indices
                diff_index = np.diff(split_index)

                # split lines according to index
                for i, diff in zip(range(len(split_index) - 1), diff_index):
                    # special case: line split at every point
                    if len(line.coords) == len(split_index):
                        new_line = LineString(coords[split_index[i] : split_index[i + 1] + 1])
                        lines_splitted.append(new_line)

                    # skip points where next neighbouring point also exceeds threshold for angle (except first and last coordinate of line)
                    # these points are ecxluded in the resulting splitted lines
                    elif diff > 1 or (split_index[i] == 0 or split_index[i] == len(coords) - 2):
                        # special case: angle threshold exceed at second and third point
                        # --> splitting would result in the first line having only one point (not possible)
                        # --> therefore, we keep the line from point 1 to point 3 but split it into two lines (angles will be smoothed when joining lines again)
                        if split_index[i] == 0 and split_index[i + 1] == 2:
                            new_line_1 = LineString(coords[0:2])
                            new_line_2 = LineString(coords[1:3])
                            lines_splitted.append(new_line_1)
                            lines_splitted.append(new_line_2)

                        # special case: angle threshold exceed at second-last and third-last point
                        # --> splitting would result in the last line having only one point (not possible)
                        # --> therefore, we keep the line from point n-3 to point n-2 but split it into two lines (angles will be smoothed when joining lines again)
                        elif (split_index[i] == len(coords) - 3 and split_index[i + 1] == len(coords) - 1) and len(
                            coords
                        ) > 4:
                            new_line_1 = LineString(coords[len(coords) - 2 : len(coords)])
                            new_line_2 = LineString(coords[len(coords) - 3 : len(coords) - 1])
                            lines_splitted.append(new_line_2)
                            lines_splitted.append(new_line_1)

                        # general: line splitted according to split_index
                        else:
                            new_line = LineString(coords[split_index[i] : split_index[i + 1] + 1])
                            lines_splitted.append(new_line)

            else:
                # original line
                lines_splitted.append(line)

        return lines_splitted

    def _get_split_index(self, line: LineString) -> NDArray[Any]:
        """Function that computes an index for 'line' specifying points where the directional change exceeds 'threshold_angle'. This index can then be used to split lines.

        Each element of 'split_index' specifies a point, where the directional change exceeds 'threshold_angle'. As directional change can not be computed for the first and last point of a line, the following method is applied. If the first / last angle (second / second-last point) exceeds the threshold, we delete the first / last point, except if it is a start / end point of the overall track segment, which is checked by comparing distance to 'threshold_op'.

        Parameters
        ----------
        lines: list[LineString]
            List of LineString objects to be splitted.

        Returns
        -------
        split_index: NDArray[Any]
            Index representing the split points of the given line.
        """
        # set thresholds
        threshold_angle: float = 40.0  # threshold for the maximal directional change, in degrees.

        # array of line coordinates
        coords = np.array(line.coords, dtype=float)

        # find all points with directional change >= threshold_angle
        # store those points in list split_index
        split_index = []
        for i in range(1, len(coords) - 1):
            # compute angle
            v1 = coords[i] - coords[i - 1]
            v2 = coords[i + 1] - coords[i]
            alpha = angle_between(v1, v2)

            # compare angle to threshold
            if alpha >= threshold_angle:
                split_index.append(i)

        # index as array
        return np.array(split_index, dtype=int)

    @staticmethod
    def merge_lines_and_smoothen_links(
        lines: list[LineString], merge_index: Union[list[list[int]], None] = None, merge_km_line: bool = False
    ) -> list[LineString]:
        """
        Merges LineString objects and smoothes links between them if necessary.

        This method merges LineString objects according to the specified merge groups. If no merge groups are provided, it computes them automatically. It also smoothes the links between merged LineString objects when necessary by connecting segments using spline interpolation.

        Parameters
        ----------
        lines: list[LineString]
            A list of LineString objects to be merged and smoothed.
        merge_index: Union[list[list[int]], None], optional
            A list of indices specifying the merge groups. If not provided, the function computes merge groups automatically. Default is None.
        merge_km_line: bool
            A boolean indicating whether to merge Kilometer lines. Default is False.

        Returns
        -------
        merged_lines: list[LineString]
            A list of merged LineString objects.

        Raises
        ------
        ValueError: If there is more than one gap in line groups.
        """

        # merge index given
        if merge_index:
            # main merge group has more than one element
            if len(merge_index[0]) > 1:
                # handle if path has gaps
                threshold = 500
                path = merge_index[0]
                index_exceeded = [
                    i for i in range(len(path) - 1) if lines[path[i]].distance(lines[path[i + 1]]) > threshold
                ]

                if len(index_exceeded) == 0:
                    # no gap
                    merge_groups_index = merge_index
                elif len(index_exceeded) == 1:
                    # split merge group at gap
                    k = index_exceeded[0]
                    merge_groups_index = [path[: k + 1], path[k + 1 :]]
                else:
                    raise ValueError('More than one gap in line group')

            else:  # single line in merge group
                merge_groups_index = merge_index

        else:
            # compute index of merge groups
            merge_groups_index = ISRPreprocessor._get_merge_index(lines=lines, merge_km_line=merge_km_line)

        # merge lines
        merged_lines = []
        for n, group_index in enumerate(merge_groups_index):
            # if current merge_group contains only one line, and this line is in another merge_group -> skip line
            merge_groups_flat = flatten_list(merge_groups_index[:n] + merge_groups_index[n + 1 :])
            if (len(group_index) == 1) and (group_index[0] in merge_groups_flat):
                continue

            # if current merge_group contains only one line, and this line is in no other merge_group -> keep line
            elif len(group_index) == 1:
                merged_lines.append(lines[group_index[0]])

            # else -> merge lines in current merge group and keep merged line
            else:
                # coords of first line in merge group
                coords: list[Tuple[float, float]] = list(lines[group_index[0]].coords[:])

                # iterate over current merge_group
                for i in group_index[1:]:
                    # extract two points from each line for fitting a cubic spline at the link of both lines
                    spline_points_1, spline_points_2, cutoff = ISRPreprocessor._get_spline_points(
                        lines=lines,
                        coords_first_line=coords,
                        indice_second_line=i,
                        indice_group=group_index[0],
                    )

                    # no smoothing
                    if spline_points_1[1] == spline_points_2[0]:
                        # if second spline point of first line exactly equals first spline point of second line
                        # assumption: no smoothing required
                        # merge without smoothing
                        if TYPE_CHECKING:
                            assert isinstance(coords, list)
                        coords = coords[: -1 - cutoff] + lines[i].coords[cutoff:]  # type: ignore

                    # smoothing
                    else:
                        # fit spline on spline points and evaluate spline at interpolated points
                        intermediate_points = ISRPreprocessor._get_intermediate_points_from_spline(
                            spline_points_1=spline_points_1,
                            spline_points_2=spline_points_2,
                        )

                        # merge: first line until cutoff + two intermediate points from spline interpolation +  second line coordinates after cutoff
                        if cutoff > 0:
                            if cutoff >= len(coords):
                                coords = coords[:1]
                            else:
                                coords = coords[:-cutoff]

                            if cutoff >= len(lines[i].coords):
                                coords_second_line = list([lines[i].coords[-1]])  # type: ignore
                            else:
                                coords_second_line = list(lines[i].coords[cutoff:])

                        else:
                            coords_second_line = list(lines[i].coords[cutoff:])

                        # merge
                        coords_second_line: list[Tuple[float, float]]
                        coords += intermediate_points + coords_second_line

                # create LineString and append
                merged_line = LineString(coords)
                merged_lines.append(merged_line)

        return merged_lines

    @staticmethod
    def _get_merge_index(lines: list[LineString], merge_km_line: bool = False) -> list[list[int]]:
        """Recursive function that identifies connected LineString objects and returns them as merge groups.

        This function recursively identifies connected LineString objects based on various criteria, such as distance between endpoints, angle between lines, and orthogonal distance. It returns these connected lines as merge groups, where each group is represented as a list of line indices.

        The function uses thresholds for distance, angle, and orthogonal distance between lines to determine connections. It also handles specific cases, including circular tracks. Thresholds are emperically determined and do not work for all cases, wherefore some special scenarios are considered when merging kilometer line segments.

        Parameters
        ----------
        lines: list[LineString]
            List of LineString objects.
        merge_km_line: bool
            If true, considers some special cases unique to merging km line segments. TODO: Param + special case could be removed: compute middle line for parallel lines with uneven starting points (and not choose one line as km_line)

        Returns
        -------
        merge_groups_index: list[list[int]]
            List containing n sublists, where n is the number of elements in 'lines'. Each sublist is an index of connected lines.

        Note
        ----

            - Assumes list 'lines' is ordered ( lines: [LineString closest to self.operational_point_from, ..., LineString closest to self.operational_point_to] ).
            - Assumes coordinates of LineStrings in 'lines' to be sorted ( LineString.coords: [Point closest to self.operational_point_from, ..., Point closest to self.operational_point_to])

        """
        # set thresholds
        threshold_distance: float = 1500
        threshold_orth_distance: float = 2.5

        # get index of merge groups
        merge_groups_index = []
        for i in range(len(lines)):
            # no more mergable lines exist
            if len(merge_groups_index) == len(lines):
                break

            # current line
            line = lines[i]
            # initalize list with element 0
            distances = [0]
            # initialize with current line indice
            connected_lines_index = [i]

            if i in flatten_list(merge_groups_index):
                # if current line is already in another merge group, skip line
                continue
            # recursively find next connected lines
            while np.min(distances) <= threshold_distance:
                # compute distance of current lines end point to each other line's start point
                distances = []
                for j in range(len(lines)):
                    # skip identical line
                    if i != j:
                        # lines that are already in a merge group are skipped
                        if (j in flatten_list(merge_groups_index)) or (j in connected_lines_index):
                            continue

                        # parallel lines are never connected
                        if lines_are_parallel(lines[i], lines[j]):
                            continue

                        # converging ends are never connected
                        if (
                            sum(
                                [
                                    abs(Point(lines[i].coords[-1]).distance(Point(lines[k].coords[0])) - 3) < 1e-1
                                    for k in range(len(lines))
                                ]
                            )
                            == 2
                        ):
                            continue

                        # also skip lines with a connecting segment between them
                        for k in range(len(lines)):
                            if (k != i) and (k != j):
                                line_k_sp = Point(lines[k].coords[0])
                                line_k_ep = Point(lines[k].coords[-1])
                                line_i_ep = Point(lines[i].coords[-1])
                                line_j_sp = Point(lines[j].coords[0])
                                if line_i_ep.distance(line_k_sp) < 5 and line_k_ep.distance(line_j_sp) < 5:
                                    segment_between_ij = True
                                    break
                        else:
                            segment_between_ij = False

                        if segment_between_ij == True:
                            continue

                        # distance
                        distance = Point(line.coords[-1]).distance(Point(lines[j].coords[0]))
                        distances.append(distance)

                        # orthagonal distance
                        l1 = LineString(line.coords[-2:][::-1])
                        l2 = LineString(lines[j].coords[:2])
                        p = Point(l2.coords[0])
                        xfact, yfact = (1000, 1000)
                        if l1.length < 1:  # upscale for very short segments (< 1m)
                            xfact *= 100
                            yfact *= 100
                        l1 = affinity.scale(l1, xfact=xfact, yfact=yfact, origin=l1.coords[1])  # type: ignore
                        orthagonal_distance = p.distance(l1)

                        # angle
                        w1 = np.array(lines[j].coords[1]) - np.array(lines[j].coords[0])
                        w2 = np.array(line.coords[-2]) - np.array(line.coords[-1])
                        angle = angle_between(w1, w2)
                        angle = 180.0 - angle if angle > 90.0 else angle

                        # consider special case
                        parameter_array = np.array([distance, orthagonal_distance, angle])

                        SPECIAL_CASES = [
                            np.array(
                                [3.13907789400891, 2.986966115748664, 17.341841423788225]
                            ),  # track: 3522, segment: Oppenheim - Dienheim
                            np.array(
                                [200.04896971634594, 4.2217422807994405, 7.141904465487386]
                            ),  # track: 2550 Mönchengladbach-Lürrip - Korschenbroich
                            np.array(
                                [3.0003078548233333, 3.000262904038304, 0.3105360289441421]
                            ),  # 2291 Essen-Steele - Essen-Eiberg
                            np.array(
                                [400.00374750717583, 4.319764001762686, 0.6170319605716941]
                            ),  # 4600 Wannweil - Kirchentellinsfurt
                            np.array(
                                [28.995907871753765, 3.091205076120937, 12.940236046495727]
                            ),  # 2650 Dortmund-Scharnhorst - Dortmund-Kurl
                            np.array(
                                [0.0, 1.530119148726014e-07, 58.57849854565285]
                            ),  # 2611 Hochneukirch - Rheydt-Odenkirchen
                            np.array(
                                [365.1244147279689, 3.3160250748159603, 0.705237953418731]
                            ),  # 5904 Lauf (links Pegnitz) - Ottensoos
                            np.array(
                                [4.16353128e03, 2.41078546e-02, 3.38548118e-01]
                            ),  # 5919 Massetal - Ilmenau-Wolfsberg
                            np.array([400.28831103, 3.553157, 0.51088207]),  # 5830 Sünching - Mangolding
                            np.array([95.66818572, 6.70897181, 7.21241728]),  # 5919 Massetal - Ilmenau-Wolfsberg
                        ]
                        SPECIAL_CASES_CONT = [
                            np.array(
                                [99.05695181040886, 1.0486660460614903, 4.725762965042378]
                            ),  # 5850 Nürnberg-Dutzendteich - Nürnberg Hbf
                            np.array(
                                [200.13773177, 1.77580676, 1.40672978]
                            ),  # 2550 Mönchengladbach-Lürrip - Korschenbroich
                            np.array([187.96003851, 72.97905643, 1.68067838]),
                        ]
                        if merge_km_line == True:
                            SPECIAL_CASES.append(
                                np.array([2.9997919, 2.99979164, 0.02105202])
                            )  # 3730 Diez Ost - Staffel
                            SPECIAL_CASES.append(
                                np.array([3.0002536800846458, 2.9998203249460644, 0.9749016242332118])
                            )  # 3230 Saarbrücken Hbf - StrUeb_3230_3238
                            SPECIAL_CASES.append(
                                np.array([3.0001197726537336, 2.984426608948086, 5.898632811689708])
                            )  # 2631 Daufenbach - Kordel
                            SPECIAL_CASES.append(
                                np.array([3.000178842353281, 3.000178698081252, 4.640941010748776])
                            )  # 1760 Himmighausen - Langeland
                            SPECIAL_CASES.append(
                                np.array([131.2911133272276, 75.17012977755833, 5.38096315592594])
                            )  #  2273 Maria-Veen - Coesfeld (Westf)
                            SPECIAL_CASES.append(
                                np.array([3.00030467, 3.00030429, 4.75361045e-06])
                            )  # 3230 StrUeb2330_2505 - Rheinhausen
                            SPECIAL_CASES.append(np.array([3.0001541, 2.99368664, 4.92999098]))
                            SPECIAL_CASES.append(np.array([3.00556078, 3.00556059, 1.00313426e-3]))

                        # special case where lines should not be merged (e.g large gap between rails due to a section running through another country)
                        if any(
                            [
                                all(np.isclose(parameter_array, special_case, atol=1e-5))
                                for special_case in SPECIAL_CASES_CONT
                            ]
                        ):
                            continue

                        # check if special cases for merging apply
                        if any(
                            [
                                all(np.isclose(parameter_array, special_case, atol=1e-5))
                                for special_case in SPECIAL_CASES
                            ]
                        ):
                            special_case = True
                        else:
                            special_case = False

                        # check connected lines
                        threshold_angle = 30
                        i_end_connections = [
                            Point(lines[i].coords[-1]).distance(Point(lines[k].coords[-1])) < 1e-2
                            if (i != k)
                            else False
                            for k in range(len(lines))
                        ]
                        j_start_connections = [
                            Point(lines[j].coords[0]).distance(Point(lines[k].coords[0])) < 1e-2 if (j != k) else False
                            for k in range(len(lines))
                        ]

                        # angle at i_end connection
                        vi1 = np.array(lines[i].coords[-2]) - np.array(lines[i].coords[-1])
                        k = [k for k in range(len(lines)) if i_end_connections[k] == True]
                        if len(k) == 1:
                            vi2 = np.array(lines[k[0]].coords[-2]) - np.array(lines[k[0]].coords[-1])
                            angle_i_v1_v2 = angle_between(vi1, vi2)
                        else:
                            angle_i_v1_v2 = 0

                        # angle at j_start connection
                        vj1 = np.array(lines[j].coords[1]) - np.array(lines[j].coords[0])
                        k = [k for k in range(len(lines)) if j_start_connections[k] == True]
                        if len(k) == 1:
                            vj2 = np.array(lines[k[0]].coords[1]) - np.array(lines[k[0]].coords[0])
                            angle_j_v1_v2 = angle_between(vj1, vj2)
                        else:
                            angle_j_v1_v2 = 0

                        # do not merge lines with too large angle even when they are connected (e.g. circular tracks)
                        if sum(j_start_connections) == 1 and angle_j_v1_v2 < 15 and special_case == False:
                            continue

                        elif sum(i_end_connections) == 1 and angle_i_v1_v2 < 15 and special_case == False:
                            continue

                        # if large angle, only merge if line end points are extremely close
                        # reason: there are sometimes line end points with large angle between them but
                        #         that are extremely close. We want to merge only those, otherwise if
                        #         the angle is to large we do not want to merge and skip those lines here.
                        #         The large angle itself is unproblematic as it will be handled by smoothing.
                        if (distance == 0 or distance > 3) and (angle > threshold_angle) and special_case == False:
                            continue
                        # second condition for connection
                        elif (
                            distance <= threshold_distance and orthagonal_distance <= threshold_orth_distance
                        ) or special_case == True:
                            # append line index to merge group
                            connected_lines_index.append(j)
                            break

                    # set distance to inf for identical line
                    else:
                        distances.append(np.inf)

                else:
                    # if no connected lines are found exit while loop
                    break

                # set current line to last connected line
                i = j
                line = lines[i]

            # append current merge group
            merge_groups_index.append(connected_lines_index)

        return merge_groups_index

    @staticmethod
    def _get_spline_points(
        lines: list[LineString],
        coords_first_line: list[Tuple[float, float]],
        indice_second_line: int,
        indice_group: int,
    ) -> Tuple[list[Tuple[float, float]], list[Tuple[float, float]], int]:
        """Extracts key points from two lines for fitting a cubic spline that connects them.

        This function is intended to be used within the 'merge_lines_and_smoothen_links' method and is responsible for extracting two key points from each of the two lines. These key points are then used to fit a cubic spline that creates a smooth link between the lines.

        The function removes or adjusts points from both lines to create space between their ends for smoother spline connections. It ensures that the spline points are monotone and meets specified criteria for angles and length differences.

        Parameters
        ----------
        lines: list[LineString]
            List of LineString objects.
        coords_first_line: list[Tuple[float, float]]
            Coordinates of the first line. (Last point already omitted)
        indice_second_line: int
            Position of second line in 'lines'.
        indice_group: int
            Position of first line in 'lines'. Used to extract the last point of first line if interpolation is necessary as last point is omitted in coords_first_line)

        Returns
        -------
        spline_points_1: list[Tuple[float, float]]
            The first two key points for spline fitting (from the first line).
        spline_points_2: list[Tuple[float, float]]
            The second two key points for spline fitting (from the second line).
        cutoff: int
            The number of points that are cut off from each line's end to ensure monotone spline points.
        """

        # initalize
        spline_points_1: list[Tuple[float, float]] = []
        spline_points_2: list[Tuple[float, float]] = []
        not_monotone = True
        i = 0

        # while coordinates are not monotone, reduce/increase indice by 1
        while not_monotone == True:
            # spline_points_2 initially represents second and third point from second line
            coords_second_line = [(float(p[0]), float(p[1])) for p in lines[indice_second_line].coords]
            spline_points_2 = coords_second_line[0 + i : 2 + i]

            # spline_points_1 initially represents third-last and second-last point from first line
            if i == 0:
                spline_points_1 = list(coords_first_line[-2:])
            elif i == 1:
                mp1: Point = LineString(coords_first_line[-2:]).interpolate(0.5, normalized=True)
                spline_points_1 = list(coords_first_line[-2:-1]) + [(mp1.x, mp1.y)]
                mp2: Point = LineString(coords_second_line[:2]).interpolate(0.5, normalized=True)
                spline_points_2 = list(coords_second_line[0:1]) + [(mp2.x, mp2.y)]

            else:
                spline_points_1 = list(coords_first_line[-2 - i : -i])

            # if no spline points, we use first line coordinate for first point and gradually move second point closer from line end to line start along line.
            if len(spline_points_1) == 0:
                spline_points_1 = list(coords_first_line[:1])
                p2 = coords_first_line[1]
                distance = 4 / (i - len(coords_first_line) + 5)
                spline_points_1 = append_interpolated_point(
                    L=spline_points_1, point1=spline_points_1[0], point2=(p2[0], p2[1]), normalized_distance=distance
                )

            # if spline_points_1 has only one point, it is the first coordinate of line 1
            # we interpolate halfway between first and second coordinate for the second
            # coordinate of spline_points_1
            elif len(spline_points_1) == 1:
                p2 = lines[indice_group].coords[1]
                spline_points_1 = append_interpolated_point(
                    L=spline_points_1, point1=spline_points_1[0], point2=(p2[0], p2[1])
                )

            # if no spline points, we use first line coordinate for first point and gradually move second point closer from line end to line start along line.
            if len(spline_points_2) == 0:
                spline_points_2 = coords_second_line[-1:]
                p2 = coords_second_line[-2]
                distance = 4 / (i - len(coords_second_line) + 5)
                spline_points_2 = append_interpolated_point(
                    L=spline_points_2, point1=spline_points_2[0], point2=(p2[0], p2[1]), normalized_distance=distance
                )
                spline_points_2 = spline_points_2[::-1]  # reverse

            # if spline_points_2 has only one point, it is the last coordinate of line 1
            # we interpolate halfway between last and second-last coordinate for the second
            # coordinate of spline_points_2
            elif len(spline_points_2) == 1:
                p2 = coords_second_line[-2]
                spline_points_2 = append_interpolated_point(
                    L=spline_points_2, point1=spline_points_2[0], point2=(p2[0], p2[1])
                )
                spline_points_2 = spline_points_2[::-1]  # reverse

            # same middle point
            if spline_points_1[1] == spline_points_2[0]:
                return spline_points_1, spline_points_2, i

            # x and y coordinates
            x = [spline_points_1[0][0], spline_points_1[1][0], spline_points_2[0][0], spline_points_2[1][0]]
            y = [spline_points_1[0][1], spline_points_1[1][1], spline_points_2[0][1], spline_points_2[1][1]]

            # angle
            v_sp_1 = np.array([spline_points_1[1][0], spline_points_1[1][1]]) - np.array(
                [spline_points_1[0][0], spline_points_1[0][1]]
            )
            v_sp_2 = np.array([spline_points_2[0][0], spline_points_2[0][1]]) - np.array(
                [spline_points_1[1][0], spline_points_1[1][1]]
            )
            angle = angle_between(v_sp_1, v_sp_2)

            # length diff
            l1 = LineString(spline_points_1).length
            l2 = LineString(spline_points_2).length
            ratio = l1 / l2 if l1 < l2 else l2 / l1
            check_length_diff = ratio > 0.01 or ((l1 < 1) or (l2 < 1))

            # check if one variable is strictly monotone, verify angle and length difference
            if (strictly_monotonic(x) or strictly_monotonic(y)) and angle <= 40 and check_length_diff == True:
                not_monotone = False
                break

            # iterations
            i += 1
            if i > 100:
                raise ValueError('spline points can not be found')

        return spline_points_1, spline_points_2, i

    @staticmethod
    def _get_intermediate_points_from_spline(
        spline_points_1: list[Tuple[float, float]], spline_points_2: list[Tuple[float, float]]
    ) -> list[Tuple[float, float]]:
        """Fits a cubic spline through 4 points specified by 'spline_points_1' and 'spline_points_2' and evaluates the spline at two interpolated coordinates between them, returning the two new points.

        This function is designed to fit a cubic spline through the four given points and then calculate two new points along the spline between 'spline_points_1' and 'spline_points_2'. These new points help create a smoother transition between the LineString objects connected by the spline.

        The function uses cubic spline interpolation to create the smooth transition and ensures that the calculated points are arranged correctly based on the provided points and any variable switches that may be necessary for interpolation.

        Parameters
        ----------
        spline_points_1: list[Tuple[float, float]]
            First two points for spline fitting.
        spline_points_2: list[Tuple[float, float]]
            Second two points for spline fitting.

        Returns
        -------
        intermediate_points: list[Tuple[float,float]]
            Two points on the spline between 'spline_points_1' and 'spline_points_2'.
        """
        from scipy.interpolate import CubicSpline

        # check size of input lists
        assert_msg = 'Lists spline_points_1 and spline_points_2 must each have size 2.'
        assert len(spline_points_1) == 2 and len(spline_points_2) == 2, assert_msg

        # flags
        reversed = False
        switched_vars = False

        # x and y coordinates at the four points
        x = [spline_points_1[0][0], spline_points_1[1][0], spline_points_2[0][0], spline_points_2[1][0]]
        y = [spline_points_1[0][1], spline_points_1[1][1], spline_points_2[0][1], spline_points_2[1][1]]

        # x must be strictly monotonic in order to use CubicSpline interpolation
        # if x is not monotonic, check if y is monotonic and if yes, switch variables
        # if neither x or y are monotonic, smoothing / spline interpolation cannot be used
        if not strictly_monotonic(x):
            if strictly_monotonic(y):
                z = y
                y = x
                x = z
                switched_vars = True
            else:
                raise ValueError('x or y not monotonic')

        # if x is decreasing, reverse to make x increasing (needed for CubicSpline)
        if x[2] - x[1] < 0:
            x = x[::-1]
            y = y[::-1]
            reversed = True

        # fit spline on 4 points
        # general case: second-last and third-last point of first line + second and third point of second line
        # first line has 2 points: first point of first line + point halfway along first line + second and third point of second line
        # second line has 2 points: second-last and third-last point of first line + point halfway along second line + second point of second line
        spline = CubicSpline(x=x, y=y)

        # create spline evaluation points
        # we evaluate the spline at two new locations between last point of fist line and first point of second line
        # both points are evenly spaced along the vector pointing from last point of first line to first point of second line
        v1 = np.array(spline_points_1[-1])
        v2 = np.array(spline_points_2[0])
        intermediate_point_1 = v1 + (1 / 3) * (v2 - v1)
        intermediate_point_2 = v2 + (1 / 3) * (v1 - v2)

        # k determines if we take x or y value from points, which depends on if the variables have been switched
        if switched_vars:
            k = 1
        else:
            k = 0

        # if order of variables was reversed, ...
        if reversed:
            x_new = [intermediate_point_2[k], intermediate_point_1[k]]
        else:
            x_new = [intermediate_point_1[k], intermediate_point_2[k]]

        # evaluate spline at new locations
        y_new = spline(x_new)

        # if variabels have been switched, ...
        if switched_vars:
            intermediate_points = [(y, x) for x, y in zip(x_new, y_new)]
        else:
            intermediate_points = [(x, y) for x, y in zip(x_new, y_new)]

        # if order of variables was reversed, ...
        if reversed:
            intermediate_points = intermediate_points[::-1]

        return intermediate_points


class MMPreprocessor:

    """
    Class that manages preprocessing of Map data and GNSS measurments for map matching. The following preprocessing steps are manages by this class:

        - GNSS noise estimation
        - Pruning of GNSS measurements based on GNSS noise
        - Identifying rails with double-direction and set direction attribute accordingly

    Attributes
    ----------
    map_data: list[OperationalPoint | TrackSegment]
        list of OperationalPoints and TrackSegments. Only TrackSegments are used for estimating the standard deviation.
    gnss: GNSSSeries
        Instance representing the GNSS measurements.
    r: float
        Serach radius for candidates. For each measurement, only rails within radius r are considered as potential matches.
    """

    def __init__(self, map_data: Map, gnss: GNSSSeries, r: float = 200.0):
        """
        Parameters
        ----------
        map_data: list[OperationalPoint | TrackSegment]
            list of OperationalPoints and TrackSegments. Only TrackSegments are used for estimating the standard deviation.
        gnss: GNSSSeries
            Instance representing the GNSS measurements.
        r: float
            Serach radius for candidates. For each measurement, only rails within radius r are considered as potential matches.
        """
        self._map = map_data
        self._gnss = gnss
        self._r = r

    @property
    def map(self) -> Map:
        """Returns the map."""
        return self._map

    @property
    def gnss(self) -> GNSSSeries:
        """Returns the gnss series."""
        return self._gnss

    @property
    def r(self) -> float:
        """Returns the search radius r."""
        return self._r

    def estimate_gnss_noise(self, method: Literal['std'] | Literal['mad']) -> float:
        """
        Estimates GNSS noise / error for each observation in 'self.gnss'.

        GNSS error is computed as error = sqrt( error_lateral**2 + error_forward**2 ), where lateral and along-track (forward) error are approximated.

        Lateral error is estimated by projecting observations onto their nearest rail. This underestimates the lateral error, as the nearest rail is not necessarily the correct rail.

        Forward error is estimated as the difference between the distance bewteen two observations along the track, and the distance based on velocity and time of both measurements. If the gnss series does not contain velocity measurements, the forward error is sampled from a set distribution.

        GNSS noise is estimated from total errors using either standard deviation (method='std') or median absolute deviation (method='mad'). Generally, the estimate using 'std' is higher, as 'mad' is more robust to outliers.

        Parameters
        ----------
        method: Literal['std'] | Literal['mad']
            The method to use for estimating the noise.

        Returns
        -------
        sigma: float
            Estimate of the GNSS noise.
        """

        # list of rails in vicinity of each observation
        candidates_list = [
            [rail for ts in self.map['track_segments'] for rail in ts.rails if Point(x, y).distance(rail) < self.r]
            for (x, y) in zip(self.gnss.x, self.gnss.y)
        ]

        # initialize
        velocity_ms = self.gnss.velocity_ms  # velocities
        time_s = self.gnss.time_s.astype(float)  # time from start, in seconds
        eta_list = []  # list of errors
        eta_with_nans = []  # used to interpolate error
        for t in range(1, len(self.gnss)):
            # measurement points i (t) and j (t-1)
            o_i = Point(self.gnss.x[t], self.gnss.y[t])
            o_j = Point(self.gnss.x[t - 1], self.gnss.y[t - 1])

            # distances of observations to all candidate rails
            distances_i = []
            distances_j = []
            for rail in candidates_list[t]:
                distance_i = o_i.distance(rail)
                distance_j = o_j.distance(rail)
                distances_i.append(distance_i)
                distances_j.append(distance_j)

            # compute error
            if len(distances_i) > 0 and len(distances_j) > 0:
                # lateral error (distance between observation and closest rail)
                eta_lat = min(distances_i)

                if not isinstance(velocity_ms, type(None)) and method == 'std':  # velocity information available
                    # find rails with minimum distance to observations
                    i = np.argmin(distances_i)
                    j = np.argmin(distances_j)

                    # only compute error if observations are closest to the same rail
                    if i == j:
                        # project o_i and o_j on rail and compute distance along rail
                        x_i = nearest_points(candidates_list[t][i], o_i)[0]
                        x_j = nearest_points(candidates_list[t][j], o_j)[0]
                        s_ij = abs(candidates_list[t][i].project(x_i) - candidates_list[t][i].project(x_j))

                        # compute s_tilde_ij: distance based on velocity v_i (t), v_j (t-1) and time delta_t
                        v = [velocity_ms[t - 1], velocity_ms[t]]
                        dt = time_s[t] - time_s[t - 1]
                        s_tilde_ij = np.trapz(v, dx=dt)

                        # compute forward error
                        eta_fwd = abs(s_ij - s_tilde_ij)

                    else:
                        if method == 'std':
                            eta_fwd = np.random.normal(loc=3.163, scale=2.32)
                        else:
                            eta_fwd = 0.0

                elif not (method == 'mad'):  # no velocity information available
                    # sample forward error
                    eta_fwd = np.random.normal(loc=3.163, scale=2.32)

                else:
                    eta_fwd = 0.0

                # total error
                eta = np.sqrt(eta_fwd**2 + eta_lat**2)
                eta_list.append(eta)
                eta_with_nans.append(eta)

        # store error array (interpolated)
        eta_interp = Series([0] + eta_with_nans).interpolate().to_numpy()
        self.gnss.error = eta_interp

        # estimate standard deviation
        match method:
            case 'std':
                sigma = float(np.std(eta_list, ddof=1))  # standard deviation
            case 'mad':
                sigma = 1.4826 * float(np.median(eta_list))  # MAD estimate of standard deviation
            case _:
                raise ValueError(f'Unknown method: {method}')  # raise error

        return sigma

    def prune(
        self,
        r: float | None = None,
        sigma_method: Literal['std'] | Literal['mad'] = 'std',
    ):
        """
        Prunes measurments within r of previous measurement.

        Parameters
        ----------
        r: float, optional
            Points within r of last included point of gnss series will be pruned. Optional, if not given sigma will be estimated from GNSS data.
        sigma_method: Literal['std'] | Literal['mad']
            The method to use for estimating GNSS noise. Only used if r is None.
        """

        # if no radius use 2 * sigma
        if not r:
            sigma = self.estimate_gnss_noise(method=sigma_method)  # estimate of gnss noise
            r = 2 * sigma

        # prune measurements based on r
        self.gnss.prune(r=r)  # TODO: option: average (speed) when pruning

    def average(self, threshold: float = 3.0):
        """
        Wrapper function. Average all parameters for sequences where velocity is smaller than 'threshold', in meter per second.

        Parameters
        ----------
        threshold: float
            The threshold, in meter per second.
        """

        self.gnss.average_low_velocity(threshold=threshold)

    def set_bidirectional_rails(self) -> Map:
        """
        Identifies bi-directional rails and sets their attribute 'direction' to 0.

        This method only considers directed rails, as monorails always are set to be bi-directional. Directed rails are set to bi-directional rails, if they belong to a rail sequence between type B transitions (eg. <==-=>).

        To identify bi-directional rail sequences, first type B transitions are identified by counting the number of points at rail ends, as type B transitions have 2 overlapping points due to rails joining at rail start/end. To identify rails between, for each bi-directional rail that end of the rail that is nor part of the type B transition, is added to list of points, thus creating a second start/end point for that rail. In a second iteration, those rails inbetween are then also identified.

        Note
        ----

        Transitions between rails:

            type A: =- | -=
            type B: <= | =>
            type C: -< | >-

        Returns
        -------
        map_data: list[TrackSegment | OperationalPoint]
            List of map elements with direction adjusted for bi-directional rails.
        """

        # collect start and end points of rails
        list_start_points = [Point(rail.coords[0]) for rail in self.map['rails']]
        list_end_points = [Point(rail.coords[-1]) for rail in self.map['rails']]

        # get direction for all rails as list
        list_rail_directions = [rail.direction for rail in self.map['rails']]

        # initalize list with new directions
        # set to reversed original list to enter loop
        list_rail_directions_new = list_rail_directions[::-1]

        # identify bidirectional rails based on number of points at rail start/end (see type B transitions)
        #   each time a bidirectional rail is identified, the rails other end point is added to list. This
        #   way, consecutive rails of the bidirectional rail will be set to bidirectional as well in the
        #   next iteration. Thus, max number of iterations is the maximum number of consecutive bi-
        #   directional rails in map plus one.
        rail_indices = []
        idx_rail = 0
        n_iter = 0
        while not all([d1 == d2 for (d1, d2) in zip(list_rail_directions, list_rail_directions_new)]):
            if n_iter > 0:
                list_rail_directions = list_rail_directions_new

            for rail in self.map['rails']:
                # skip rails whose direction already has been changed
                if idx_rail in rail_indices:
                    idx_rail += 1
                    continue

                # points at rail ends
                p0, pn = Point(rail.coords[0]), Point(rail.coords[-1])

                # number of coinceding points at rail start/end (with other rail's end points)
                #   here, coinceding means a distance of less than 1.5 m. This margin is used
                #   to catch small offsets, e.g. disconnected lines.
                d1 = p0.distance(list_start_points)
                d2 = pn.distance(list_end_points)
                idx1 = np.where(d1 < 1.5)[0]
                idx2 = np.where(d2 < 1.5)[0]
                count0 = len(idx1)
                countn = len(idx2)

                # change rail direction based on number of points
                if count0 > 1 or countn > 1:
                    if count0 > 1:
                        list_start_points.append(pn)  # add end point to list of start points
                    else:
                        list_end_points.append(p0)  # add start point to list of end points
                    rail.direction = 0  # set direction
                    rail_indices.append(idx_rail)  # add to index of rails whose direction has been changed
                idx_rail += 1  # increase counter

            # new directions
            list_rail_directions_new = [rail.direction for rail in self.map['rails']]
            n_iter += 1

        return self.map

    def split_rails_at_switch_zones(self) -> Map:
        """
        Splits rails at switch zones (switch zones are circular zones at rail end points where it is allowed to switch from one rail to another).

        Returns
        -------
        map_: Map
            The map with splitted rails.
        """
        # all rails in map
        rails = self.map['rails']

        # get all switch zones's center points (at rail ends)
        center_points = [Point(rail.coords[0]) for rail in rails] + [Point(rail.coords[-1]) for rail in rails]

        dr = 1.5  # radius of zone

        # for each switch zone's center points
        for center_point in center_points:
            # set up circular area (buffer)
            zone = center_point.buffer(dr)  # 5 m radius

            # identify rails which intersects circle boundary twice -> rails to split
            for rail in rails:
                # get intersection (no intersection -> Empty LineString, single intersection -> Point, multiple intersection -> LineString)
                intersection_geom = rail.intersection(zone)

                # split case 1: rail intersects zone twice
                if isinstance(intersection_geom, LineString) and len(intersection_geom.coords) > 1:
                    p_0 = Point(rail.coords[0])
                    p_n = Point(rail.coords[-1])
                    if p_0.distance(center_point) >= dr and p_n.distance(center_point) >= dr:
                        split = True
                    else:
                        split = False

                # split case 2: rail touches zone at boundary and rail end points are outside of zone
                elif isinstance(intersection_geom, Point) and (
                    intersection_geom.distance(center_point) >= dr and intersection_geom.distance(center_point) >= dr
                ):
                    split = True

                # else no split
                else:
                    split = False

                # split rail
                if split:
                    # get nearest point of rail to radius
                    split_point = nearest_points(rail, center_point)[0]

                    # split
                    rail_1, rail_2 = split_line_at_point(line=rail, point=split_point)

                    # replace rail in map by splitted rails
                    rail_index = self.map['rails'].index(rail)
                    self._map['rails'].pop(rail_index)
                    self._map['rails'].insert(rail_index, rail_1)
                    self._map['rails'].insert(rail_index + 1, rail_2)

        return self.map

    def index_rails(self) -> Map:
        """
        Assigns each rail an indice for identification during map matching.

        Returns
        -------
        map_: Map
            The map with indices assigned to rails.
        """
        # set indice for each rail
        for i, rail in enumerate(self.map['rails']):
            rail.index = i

        return self.map
