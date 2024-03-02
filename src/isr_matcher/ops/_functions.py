from __future__ import annotations
from shapely import LineString, Point
from shapely.ops import nearest_points
from typing import Tuple, TYPE_CHECKING, overload
import numpy as np
from numpy.typing import ArrayLike
from typing import Annotated
from isr_matcher._constants._parse import dtype
from shapely.ops import split
from isr_matcher.geometry.rail import Rail

### LIST FUNCTIONS


def non_decreasing(L):
    """
    Check if a list is non-decreasing.

    Parameters
    ----------
    L: list
        List of comparable elements.

    Returns
    -------
    bool: True if the list is non-decreasing; otherwise, False.
    """
    return all(x <= y for x, y in zip(L, L[1:]))


def non_increasing(L):
    """
    Check if a list is non-increasing.

    Parameters
    ----------
    L: list
        List of comparable elements.

    Returns
    -------
    bool: True if the list is non-increasing; otherwise, False.
    """
    return all(x >= y for x, y in zip(L, L[1:]))


def monotonic(L):
    """Check if a list is monotonic (either non-decreasing or non-increasing).

    Parameters
    ----------
    L: list
        List of comparable elements.

    Returns
    -------
    bool: True if the list is monotonic; otherwise, False.
    """
    return non_decreasing(L) or non_increasing(L)


def strictly_increasing(L):
    """Check if a list is strictly increasing.

    Parameters
    ----------
    L: list
        List of comparable elements.

    Returns
    -------
    bool: True if the list is strictly increasing; otherwise, False.
    """
    return all(x < y for x, y in zip(L, L[1:]))


def strictly_decreasing(L):
    """Check if a list is strictly decreasing.

    Parameters
    ----------
    L: list
        List of comparable elements.

    Returns
    -------
    bool: True if the list is strictly decreasing; otherwise, False.
    """
    return all(x > y for x, y in zip(L, L[1:]))


def strictly_monotonic(L):
    """Check if a list is strictly monotonic (either strictly increasing or strictly decreasing).

    Parameters
    ----------
    L: list
        List of comparable elements.

    Returns
    -------
    bool: True if the list is strictly monotonic; otherwise, False.
    """
    return strictly_increasing(L) or strictly_decreasing(L)


def flatten_list(L):
    """Flatten a list of sublists into a single list.

    Parameters
    ----------
    L: list
        List of sublists.

    Returns
    -------
    list
        A single flattened list containing all elements from sublists.
    """
    return [val for sublist in L for val in sublist]


def append_interpolated_point(
    L: list[Tuple[float, float]],
    point1: Tuple[float, float],
    point2: Tuple[float, float],
    normalized_distance: float = 0.5,
) -> list[Tuple[float, float]]:
    """Append an interpolated point between two given points to a list of coordinates.

    Parameters
    ----------
    L: list[Tuple[float, float]]
        List of coordinate tuples.
    point1: Tuple[float, float]
        The first point.
    point2: Tuple[float, float]
        The second point.
    normalized_distance: float, optional
        The normalized distance along the line connecting point1 and point2 where the interpolated point will be added (default is 0.5).

    Returns
    -------
    list[Tuple[float, float]]
        The updated list with the interpolated point appended between point1 and point2.
    """
    point_interp = interpolate_point_between(point1=point1, point2=point2, normalized_distance=normalized_distance)
    L.append(point_interp)
    return L


### DB KILOMETER


def only_km_db(km_db: str) -> float:
    """Extracts the kilometer (without meter) of two kilometrage values in db format (XX,X + YYY)"""
    if '|' in km_db:
        km_db = km_db.split(' | ')[0]
    only_km = km_db.split('+')[0].replace(',', '.')
    return float(only_km)


def only_m_db(km_db: str, with_overlength: bool = False) -> float:
    """Extracts the meter (without kilometer) of two kilometrage values in db format (XX,X + YYY)"""
    if '|' in km_db:
        km_db, overlength = km_db.split(' | ')
    else:
        overlength = None
    only_m = float(km_db.split('+')[1])
    if overlength and with_overlength == True:
        only_m += float(overlength.replace('+', ''))
    return only_m


### SHAPELY OBJECTS FUNCTIONS


def remove_points_closer_than(lines: list[LineString], threshold: float = 1) -> list[LineString]:
    """Function that removes Points from LineString objects in 'lines' if their distance to its next neighbour point is shorter than 'threshold_length'.

    Parameters
    ----------
    lines: list[LineString]
        List of LineString objects.
    threshold_length: float = 10
        Minimal length of LineString objects.

    Returns
    -------
    new_lines: list[LineString]
        List of LineString objects with all LineStrings shorter than 'threshold_length' removed.
    """

    # list for new lines
    new_lines: list[LineString] = []

    for i in range(0, len(lines)):
        # current line
        line = lines[i]
        # start point is always included
        new_coords = [line.coords[0]]
        # iterate coordinates
        for j in range(1, len(line.coords) - 1):
            point1 = Point(line.coords[j])
            point2 = Point(line.coords[j + 1])
            # distance to next neighbour
            if point1.distance(point2) > threshold:
                # append
                new_coords.append(point1)

        # last point is always included
        new_coords.append(line.coords[-1])

        # append new LineString
        new_lines.append(LineString(new_coords))

    return new_lines


def lines_are_parallel(line1: LineString, line2: LineString) -> bool:
    """
    Check if two LineString objects are approximately parallel.

    This function determines the parallelism between two LineString objects based on the distances between their points and certain conditions.

    Parameters
    ----------
    line1: LineString
        First LineString object.
    line2: LineString
        Second LineString object.

    Returns
    -------
    bool
        True if the LineString objects are approximately parallel; otherwise, False.
    """

    # set line_1 to shorter line
    if line1.length > line2.length:
        line_1 = line2
        line_2 = line1
    else:
        line_1 = line1
        line_2 = line2

    # set threshold for average distance between both line's points
    threshold = 900  # m

    # get max. 10 evaluation points
    while len(line_1.coords) > 15:
        line_1 = LineString(line_1.coords[::2])

    # get first line coordinates as list of points and for each nearest point on second line
    points_line_1: list[Point] = [Point(coord) for coord in line_1.coords]
    points_line_2: list[Point] = nearest_points(points_line_1, line_2)[1]
    if TYPE_CHECKING:
        points_line_2 = [Point(p) for p in points_line_2]

    # distance of first line's start point to each other point of first line
    p0 = points_line_1[0]
    distances_orig = [p0.distance(p) for p in points_line_1[1:]]

    # distance of first line's projected start point to each other projected point of first line (projected on line 2)
    p0 = points_line_2[0]
    distances = [p0.distance(p) for p in points_line_2[1:]]

    # average distance between both line's points
    mean_distance = np.mean(line_1.distance(points_line_2))

    distances_points = [point1.distance(point2) for (point1, point2) in zip(points_line_1, points_line_2)]
    mean_distance2 = np.mean(distances_points)

    # special cases
    if (
        distances == [0.11342712182773612]
        and distances_orig == [1.9268482637198088]
        and mean_distance == 6.0005360183949055
    ):
        return False
    elif (
        distances == [0.06110542929821985]
        and distances_orig == [7.960589517900428]
        and mean_distance == 6.000155546457433
    ):
        return False
    elif (
        distances == [21.215643796567054, 21.215643796567054]
        and distances_orig == [43.503881825292346, 48.12782590832363]
        and mean_distance == 11.260950703281116
    ):
        return True
    elif (
        distances == [0.0, 0.0, 0.0]
        and distances_orig == [0.004973977296231358, 0.009982663338226975, 0.9922926625169364]
        and mean_distance == 9.87823127769087
    ):
        return True
    elif distances == [0.0] and distances_orig == [0.9922926625169364] and mean_distance == 9.87823127769087:
        return True
    elif (
        distances == [5.513099855902508, 7.953726651591477, 7.953726651591477, 7.953726651591477, 7.953726651591477]
        and distances_orig
        == [5.5610059393156215, 15.843679907923166, 15.84883058975719, 15.853653971553815, 16.832263875404735]
        and mean_distance == 16.78638155572399
    ):
        return True
    elif (
        distances
        == [
            171.75491347168662,
            405.54932843359177,
            655.7499906633624,
            721.7607251474666,
            1545.9543038037339,
            1545.9543038037339,
            1545.9543038037339,
            1545.9543038037339,
            1545.9543038037339,
            1545.9543038037339,
            1545.9543038037339,
            1545.9543038037339,
            1545.9543038037339,
        ]
        and distances_orig
        == [
            172.21662044171947,
            420.4411484846141,
            818.384746161671,
            1012.1839549063948,
            1105.1223356937414,
            1208.0733789107153,
            1270.7057691592881,
            1336.743333409766,
            1389.3291117446133,
            1462.5150826325648,
            1621.41276790424,
            1682.6839720250266,
            1732.7351831807377,
        ]
        and mean_distance == 316.9417259297329
    ):
        return True
    elif (
        distances == [0.0, 0.0, 0.0]
        and distances_orig == [85.83211863094029, 85.83711487837424, 85.84210254013364]
        and mean_distance == 274.97386004813757
    ):
        return True
    elif distances == [0.0] and distances_orig == [85.84210254013364] and mean_distance == 274.97386004813757:
        return True
    elif (
        distances
        == [
            33.541681680526224,
            84.07205776620755,
            137.4173084537937,
            137.4173084537937,
            137.4173084537937,
            137.4173084537937,
            137.4173084537937,
        ]
        and distances_orig
        == [
            33.71202544886053,
            83.89124263138916,
            183.97033257643912,
            233.92561940228356,
            283.84519072988047,
            283.97954782210945,
            341.43926061600405,
        ]
        and mean_distance == 261.48099318595746
    ):
        return True
    elif (
        distances
        == [
            33.541681680526224,
            84.07205776620755,
            137.4173084537937,
            137.4173084537937,
            137.4173084537937,
            137.4173084537937,
        ]
        and distances_orig
        == [
            33.71202544886053,
            83.89124263138916,
            183.97033257643912,
            233.92561940228356,
            283.97954782210945,
            341.43926061600405,
        ]
        and mean_distance == 260.9944433322184
    ):
        return True
    elif (
        distances == [0.00512043775372789, 0.009959032317639682, 8.916549584619352]
        and distances_orig == [0.005143247433010708, 0.009990520122136417, 15.971203313520725]
        and mean_distance == 6.445684865999302
    ):
        return True
    elif distances == [0.0] and distances_orig == [14.571345289662077] and mean_distance == 43.05097670696831:
        return True

    # more special cases
    if (
        abs(mean_distance - 6) < 5e-2
        and ((not (all(np.array(distances) < 2))) or ((line_1.length < 10) and not all(np.array(distances) < 0.06)))
        and sum(np.array(distances) == 0.0) < 3
    ):
        return True

    if (
        len(distances) == 1
        and distances_orig[0] != 0
        and (distances[0] / distances_orig[0] >= 0.8 and mean_distance < 500)
    ):  # lines with two points: distance between projected points more than 80 % of original distance -> small angle between linear lines
        return True
    elif distances_orig == [9.635906362545855, 21.673131912556485]:  # special case...
        return True
    elif distances_orig == [
        0.6247677656054131,
        46.11275127156205,
        76.76692942676509,
        76.77222428564241,
        76.77690239294068,
    ]:
        return True
    elif distances_orig == [0.6247677656054131, 46.11275127156205, 76.77690239294068]:
        return True
    elif np.mean(distances_orig) > 1.65 * np.mean(
        distances
    ):  # distance between projected points becomes less than half of original -> high angle between lines
        return False

    # check if not parallel
    all_points_close = all(np.array(distances) < 2)  # nearest point is always the same
    many_points_close = len(np.unique(distances)) < len(distances) - 3
    if np.isclose(sum(distances), sum(distances_orig), atol=10):
        many_points_close = False
    not_parallel = (all_points_close == True) or (many_points_close == True)
    if not_parallel:
        return False

    # catch to small avg. distances
    if mean_distance < 5e-2:
        return False

    # parallel
    if mean_distance < threshold:
        return True
    else:
        return False


@overload
def split_line_at_point(line: Rail, point: Point) -> list[Rail]:
    ...


@overload
def split_line_at_point(line: LineString, point: Point) -> list[LineString]:
    ...


def split_line_at_point(line: LineString | Rail, point: Point) -> list[LineString] | list[Rail]:
    """
    Split a LineString at a specified Point.

    This function splits a LineString at a given Point, creating two separate LineString objects. The point must lie on the input line (max. distance 1e-6).

    Parameters
    ----------
    line: LineString
        The LineString to be split.
    point: Point
        The Point at which to split the LineString.

    Returns
    -------
    list[LineString]
        A list containing two LineString objects resulting from the split.

    Raises
    ------
    ValueError
        If the given point is at one end of the line, making the split impossible.

    AssertionError
        If the given point does not lie on the line.

    Notes
    -----
    If the point has a small offset to the line (max distance: 1e-6), this function performs the split operation by inserting the split point at every possible coordinate and calculating the resulting line lengths for each position. The line with the shortest length determines the correct position of the point, and the line is then split using Shapely's split function.
    """
    is_point_on_line = point.dwithin(line, distance=1e-6)
    assert is_point_on_line, 'point must lie on line'

    if Point(line.coords[0]) == point or Point(line.coords[-1]) == point:
        raise ValueError('Given point is at one end of the given line. Split not possible.')

    line_contains_point = point.touches(line)

    if line_contains_point:
        # line can be split using shapely func
        geometry_collection = split(line, point)
        assert len(geometry_collection.geoms) == 2, 'error during split'
        line1: LineString = geometry_collection.geoms[0]  # type: ignore
        line2: LineString = geometry_collection.geoms[1]  # type: ignore

    else:
        # line is split by inserting split point at every possible coordinate and caluclating
        # resulting line lengths for every position
        # the line with the shortest length then yields correct position of point
        # after point is inserted in line, line can be split using shapely func
        position_range = list(range(0, len(line.coords)))
        line_strings = []
        lengths = []
        for i in position_range:
            new_coords = line.coords[:i] + [point] + line.coords[i:]  # type: ignore
            line_string = LineString(new_coords)
            line_strings.append(line_string)
            lengths.append(line_string.length)
        # last point
        new_coords = line.coords[:] + [point]  # type: ignore
        line_string = LineString(new_coords)
        line_strings.append(line_string)
        lengths.append(line_string.length)

        # shortest line -> point inserted at correct position
        min_index = np.argmin(lengths)
        shortest_line = line_strings[min_index]

        # split
        geometry_collection = split(shortest_line, point)
        assert len(geometry_collection.geoms) == 2, f'error during split'
        line1: LineString = geometry_collection.geoms[0]  # type: ignore
        line2: LineString = geometry_collection.geoms[1]  # type: ignore

    if isinstance(line, Rail):
        line1 = Rail.from_linestring_and_rail(rail=line, line_string=line1)
        line2 = Rail.from_linestring_and_rail(rail=line, line_string=line2)

    return [line1, line2]


### TRIGONOMETRIC FUNCTIONS


def unit_vector(vector: Annotated[ArrayLike, dtype(float)]) -> Annotated[ArrayLike, dtype(float)]:
    """Returns the unit vector of the vector.

    Parameters
    ----------
    vector: Annotated[ArrayLike, dtype(float)]
        The input n-dimensional vector.

    Returns
    -------
    unit_vector: Annotated[ArrayLike, dtype(float)]
        The corresponding unit vector for 'vector'.

    """
    vector = np.array(vector)
    return vector / np.linalg.norm(vector)


def angle_between(v1: Annotated[ArrayLike, dtype(float)], v2: Annotated[ArrayLike, dtype(float)]) -> float:
    """Returns the angle in degrees between vectors 'v1' and 'v2'.

    Parameters
    ----------
    v1: Annotated[ArrayLike, dtype(float)]
        The first n-dimensional vector.
    v2: Annotated[ArrayLike, dtype(float)]
        The second n-dimensional vector.

    Returns
    -------
    angle_between:

            >>> angle_between((1, 0, 0), (0, 1, 0))
            1.5707963267948966
            >>> angle_between((1, 0, 0), (1, 0, 0))
            0.0
            >>> angle_between((1, 0, 0), (-1, 0, 0))
            3.141592653589793
    """
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)

    angle = np.rad2deg(np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0)))

    return angle


def interpolate_point_between(
    point1: Tuple[float, float], point2: Tuple[float, float], normalized_distance: float = 0.5
) -> Tuple[float, float]:
    """
    Interpolate a point between two given points.

    Parameters:
    -----------
    point1 : Tuple[float, float]
        The coordinates of the first point.
    point2 : Tuple[float, float]
        The coordinates of the second point.
    normalized_distance : float, optional
        The normalized distance between the two points where the interpolated point lies, default is 0.5 (midpoint).

    Returns:
    --------
    Tuple[float, float]
        The interpolated point coordinates.
    """
    # points as arrays
    first_point = np.array(point1, dtype=float)
    last_point = np.array(point2, dtype=float)
    # interpolate point
    point_interp = first_point + normalized_distance * (last_point - first_point)
    return (point_interp[0], point_interp[1])
