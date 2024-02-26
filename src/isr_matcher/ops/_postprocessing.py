import numpy as np
from isr_matcher.geometry.map import Map
from isr_matcher.geometry.rail import Rail
from isr_matcher.geometry.track_segment import TrackSegment
from shapely.geometry import Point, LineString
import numpy as np
from isr_matcher.ops._functions import angle_between, split_line_at_point
from isr_matcher._constants._parse import db_km_to_km
from isr_matcher.data_handlers.transformer import Transformer
from shapely.ops import nearest_points
from typing import Tuple, Literal
from itertools import groupby
from isr_matcher.geometry.gnss_series import GNSSSeries
import warnings
import bisect
import folium
import pandas as pd
from pathlib import Path
from scipy.interpolate import splprep, splev
from itertools import cycle


class MMPostprocessor:
    def __init__(self, map_: Map):
        self._map = map_

    @property
    def map(self) -> Map:
        return self._map

    def concatenate_rails(
        self, S: list[int], start_point: Point, end_point: Point, resolution_m: float = 5, interpol: bool = False
    ) -> LineString:
        """"""

        path_by_index: list[int] = np.array(S)[np.concatenate(([True], np.diff(S) != 0))].tolist()
        path_by_rails: list[Rail] = [self.map['rails'][s] for s in path_by_index]

        # concatenate rails
        path = path_by_rails[0]
        for i in range(1, len(path_by_rails)):
            import matplotlib.pyplot as plt

            f, ax = plt.subplots(1, 1)
            ax.plot(*path.xy, color='k', alpha=0.3)
            ax.plot(*path_by_rails[i].xy, color='g')
            if i < len(path_by_rails) - 1:
                ax.plot(*path_by_rails[i + 1].xy, color='b')

            # clip next rail (if transition at middle of rail, remove part of rail before transition point)
            if (
                path_by_rails[i].track_segment_name
                in 'Ludwigshafen (Rhein) Hbf, W 14 - Ludwigshafen (Rhein) Mitte 3401'
                and path_by_rails[i - 1].track_segment_name
                in 'Ludwigshafen (Rhein) Überleitung Süd - Ludwigshafen (Rhein) Mitte 3522'
            ):
                continue
            no_split = False
            split_point = nearest_points(path_by_rails[i], Point(path.coords[-1]))[0]
            split_postion = path_by_rails[i].project(split_point, normalized=True)

            ax.scatter(split_point.x, split_point.y, color='r')
            ax.scatter(Point(path_by_rails[i - 1].coords[-1]).x, Point(path_by_rails[i - 1].coords[-1]).y, color='k')
            ax.scatter(Point(path.coords[-1]).x, Point(path.coords[-1]).y, color='orange')

            plt.show()
            if split_postion > 0 and split_postion < 1:
                pre_split_point = nearest_points(path_by_rails[i], Point(path.coords[-2]))[0]
                distance = path_by_rails[i].project(split_point) - path_by_rails[i].project(pre_split_point)

                normal_distance = split_point.distance(path_by_rails[i - 1])
                if distance > 0:
                    new_split_point = path_by_rails[i].interpolate(
                        path_by_rails[i].project(split_point) + normal_distance * 6
                    )
                elif distance < 0:
                    new_split_point = path_by_rails[i].interpolate(
                        path_by_rails[i].project(split_point) - normal_distance * 6
                    )
                else:
                    segment = path_by_rails[i]
                    no_split = True
                if no_split == False:
                    segment1, segment2 = split_line_at_point(path_by_rails[i], new_split_point)

                    if distance > 0:
                        segment = segment2
                    else:
                        segment = segment1

            else:
                segment = path_by_rails[i]
            path = MMPostprocessor.join(path, segment)

        # clip path (if path starts/ends at middle of rail, remove part of rail after/before)
        start_point_on_path = nearest_points(path, start_point)[0]
        try:
            path = split_line_at_point(path, start_point_on_path)[1]
        except ValueError:
            pass
        end_point_on_path = nearest_points(path, end_point)[0]
        try:
            path = split_line_at_point(path, end_point_on_path)[0]
        except ValueError:
            pass

        ### smooth path (spline interpolation)
        try:
            # remove hard turns from path
            index = []
            for i in range(1, len(path.coords) - 1):
                v1 = np.array(path.coords[i]) - np.array(path.coords[i - 1])
                v2 = np.array(path.coords[i + 1]) - np.array(path.coords[i])
                a = angle_between(v1, v2)
                if abs(a) > 60:
                    index.append(i)
            x = np.array([c[0] for c in path.coords])
            y = np.array([c[1] for c in path.coords])
            x = np.delete(x, index)
            y = np.delete(y, index)
            path = LineString(np.column_stack([x, y]))

            # generate spline points by interpolating along path (1 point per 50 meter)
            # if spline points are too densely sampled from path, the spline will follow
            # the linear path, which makes spline interpolation redundant
            L = path.length
            interpol_points = path.interpolate(np.linspace(0, 1, int(L / 50)), normalized=True)
            x = np.array([c.x for c in interpol_points])
            y = np.array([c.y for c in interpol_points])

            # create spline
            points = np.column_stack((y, x))
            tck, u = splprep(points.T, s=0)

            # evaluate spline (1 point per 'resoltion_m' meter)
            y, x = splev(np.linspace(0, 1, int(L / resolution_m)), tck)
            path = LineString(np.column_stack([x, y]))

        except:
            pass

        return path

    @staticmethod
    def join(line: LineString | Rail, other: LineString | Rail) -> LineString:
        """Implements concatenation of rails into one path by connecting them by spline interpolation.

        Parameters
        ----------
        line: LineString | Rail
            An instance
        other: Rail
            Another instance of class Rail.

        Note
        ----


        """

        line1 = line
        line2 = other

        # ensure line coordinates are ordered in same direction
        d1s2s, d1s2n = Point(line1.coords[0]).distance([Point(line2.coords[0]), Point(line2.coords[-1])])
        d1n2s, d1n2n = Point(line1.coords[-1]).distance([Point(line2.coords[0]), Point(line2.coords[-1])])
        d_min = np.min([d1s2s, d1s2n, d1n2s, d1n2n])

        if d_min == d1s2s:  # line1 reversed, line2 normal
            line1 = line1.reverse()
        elif d_min == d1s2n:  # line1 reversed, line2 reversed
            line1 = line1.reverse()
            line2 = line2.reverse()
        elif d_min == d1n2s:  # line1 normal, line2 normal
            pass
        else:  # line1 normal, line2 reversed
            line2 = line2.reverse()

        # if lines are connected already, skip connecting
        d = Point(line1.coords[-1]).distance(Point(line2.coords[0]))
        if d < 1e-6:
            return LineString(list(line1.coords) + list(line2.coords[1:]))

        else:
            return LineString(list(line1.coords) + list(line2.coords))

        # connect lines
        s_length = 30  # length to cut off from end of first line
        if line1.length - s_length > 0:
            split_point = line1.interpolate(distance=line1.length - s_length)  # compute split point
            split_line_1, split_line_2 = split_line_at_point(
                line=line1, point=split_point
            )  # split first line (cut off end of line)
            result_line = LineString(list(split_line_1.coords) + list(line2.coords))  # connect lines
        else:
            result_line = LineString(
                line1.coords[:1] + list(line2.coords)
            )  # connect first point of first line with second line

        # iterate over resulting line to assert no hard angles
        result_line_coords = result_line.coords[:1]
        angles = []
        for i in range(1, len(result_line.coords) - 1):
            v1 = np.array(result_line.coords[i]) - np.array(result_line.coords[i - 1])
            v2 = np.array(result_line.coords[i + 1]) - np.array(result_line.coords[i])
            angle = angle_between(v1, v2)

            if angle < 30:
                angles.append(angle)
                result_line_coords.append(result_line.coords[i])

        result_line_coords.append(result_line.coords[-1])
        result_line = LineString(result_line_coords)

        # f, ax = plt.subplots(1, 1)
        # ax.plot(*line1.xy)
        # ax.plot(*line2.xy)
        # ax.plot(*result_line.xy)
        # plt.show()

        return result_line

    def compute_position_parameter(self, path: LineString, rail_sequence: list[Rail], gnss_coords: list[Point]):
        """
        Fucntion to compute positional parameters in track space (track_nr, dircetion, kilometrage and projected gnss coordinates).

        Parameters
        ----------
        path: LineString
            LineString representing the continous path of vehicle.
        rail_sequence: list[Rail]
            List of rails. Each entry is the assigned rail for corresponding GNSS measurment.
        gnss_coords: list[Point]
            The GNSS measurements in UTM coordinate system (EPSG:31467).

        Note
        ----
        The lists 'rail_sequence' and 'gnss_coords' must be of equal length. Each rail corresponds to exactly one measurement, therefore Rails can be repeated. Same for 'track_segment_sequence'.

        """

        # compute kilometrage and projections on path
        matched_points_utm = []
        matched_points_wgs = []
        kms_db = []
        kms = []
        kms_running = [0.0]
        directions = []
        rails = []
        gnss_error_m = []
        inclines = []
        for i, (opt_rail, point) in enumerate(zip(rail_sequence, gnss_coords)):
            # projection on path
            matched_point_utm = nearest_points(path, point)[0]
            matched_points_utm.append(matched_point_utm)

            # gnss error
            error_m = point.distance(matched_point_utm)
            gnss_error_m.append(error_m)

            # projection of matched point (utm to wgs)
            transformer = Transformer(source_cs='epsg:31467', target_cs='epsg:4326')
            matched_point_wgs = transformer.transform(
                'source_to_target', Point([matched_point_utm.y, matched_point_utm.x])
            )
            matched_points_wgs.append(matched_point_wgs)

            # compute parameters
            for j, track_segment in enumerate(self.map['track_segments']):
                # find matching track segment for rail
                if (int(opt_rail.track) == int(track_segment.track_nr)) and (
                    opt_rail.track_segment_name == track_segment.name
                ):
                    # get km
                    if track_segment.kilometrage.n_lines == 2 and opt_rail.direction == 0:
                        if len(directions) > 0 and not np.isnan(directions[-1]):
                            direction = directions[-1]
                        else:
                            direction = 1
                    else:
                        direction = opt_rail.direction
                    km_db = track_segment.km(point=matched_point_utm, direction=direction, return_type='db')
                    km = db_km_to_km(km_db)
                    kms_db.append(km_db)
                    kms.append(km)

                    # get rail types
                    match opt_rail.direction:
                        case 0:
                            rail_type = 'eingleisig'
                        case 1:
                            rail_type = 'Richtungsgleis'
                        case 2:
                            rail_type = 'Gegengleis'
                        case _:
                            raise ValueError('Unknown rail direction.')
                    rails.append(rail_type)

                    # running km: distances are computed based on path geometry, not by kilometrage values
                    if i > 0:
                        # running km
                        km_running = (
                            abs(path.project(matched_points_utm[i]) - path.project(matched_points_utm[i - 1])) / 1000
                        )
                        # if km_running > 2:
                        #    import matplotlib.pyplot as plt
                        #    f, ax = plt.subplots(1, 1)
                        #    ax.plot(*path.xy, color='k')
                        #    ax.scatter(matched_points_utm[i-1].x, matched_points_utm[i-1].y)
                        #    ax.scatter(matched_points_utm[i].x, matched_points_utm[i].y)
                        #    plt.show()
                        kms_running.append(kms_running[-1] + km_running)

                        # the rest just to get the direction...
                        # same track segment as for last gnss point / last km
                        if rail_sequence[i] == rail_sequence[i - 1]:
                            # running distance
                            distance_since_last_point_km = (
                                opt_rail.project(gnss_coords[i]) - opt_rail.project(gnss_coords[i - 1])
                            ) / 1000  # abs(track_segment.km(point=gnss_coords[i], direction=int(direction), return_type='float') - track_segment.km(point=gnss_coords[i-1], direction=int(direction), return_type='float'))
                            # abs_distance_since_last_point_km = abs(distance_since_last_point_km)

                            # direction
                            if distance_since_last_point_km > 0:
                                direction = 1
                            elif distance_since_last_point_km < 0:
                                direction = 2
                            else:
                                direction = directions[-1]  # use last direction

                        # rail changed since last gnss point / last km
                        else:
                            # distance from last point to current rail end (rail end can also be start of rail)
                            distance_rail_start, distance_rail_end = gnss_coords[i - 1].distance(
                                [Point(opt_rail.coords[0]), Point(opt_rail.coords[-1])]
                            )
                            if distance_rail_start < distance_rail_end:
                                # ride on rail started at beginning of rail
                                rail_end = Point(opt_rail.coords[0])
                                distance_2 = (opt_rail.project(gnss_coords[i]) - opt_rail.project(rail_end)) / 1000

                            else:
                                # ride on rail started at end of rail
                                rail_end = Point(opt_rail.coords[-1])
                                distance_2 = -(opt_rail.project(rail_end) - opt_rail.project(gnss_coords[i])) / 1000

                            # direction: (we use moving direction on current rail and ignore direction on last rail)
                            if distance_2 > 0:
                                direction = 1
                            elif distance_2 < 0:
                                direction = 2
                            else:
                                direction = directions[-1]  # use last direction

                    else:
                        # set initial direction to nan because it can not be determined
                        # will be set to the next direction later
                        direction = np.nan

                    # get incline
                    incline = track_segment.incline(km=km, direction=opt_rail.direction)
                    inclines.append(incline)

                    # skip to next measurement
                    directions.append(direction)
                    break

            else:
                raise ValueError('No matching track segment found.')

        # replace nan values by next neighbor value
        directions = [
            directions[i] if np.isnan(directions[i]) == False else directions[i + 1]
            for i in range(len(directions))[::-1]
        ][::-1]

        position_parameter_dict = {
            'track_numbers': [int(rail.track) for rail in rail_sequence],
            'rail_types': rails,
            'directions': directions,
            'kms': kms,
            'kms_db': kms_db,
            'kms_running': kms_running,
            'matched_coordinates_utm': matched_points_utm,
            'matched_coordinates_wgs': matched_points_wgs,
            'gnss_error_m': gnss_error_m,
            'inclines': inclines,
        }

        return position_parameter_dict

    def compute_track_segment_sequence(self, rail_sequence: list[Rail]) -> Tuple[list[TrackSegment], list[int]]:
        """Computes the track segment sequence given a sequence of rails."""

        # lists
        track_segment_sequence = []
        track_segment_indices = []
        for i, rail in enumerate(rail_sequence):
            # find rail in track segments
            for track_segment in self.map['track_segments']:
                # set skip bool
                skip = False
                # skip if previous rail is the same as current rail
                if (i == 0) or (rail_sequence[i - 1].track_segment_name != rail_sequence[i].track_segment_name):
                    if (int(rail.track) == int(track_segment.track_nr)) and (
                        rail.track_segment_name == track_segment.name
                    ):
                        # append track segment to list
                        track_segment_sequence.append(track_segment)
                        track_segment_indices.append(i)
                        break

                else:
                    skip = True

            else:
                if skip == False:
                    raise ValueError('Could not match rail with track segment')

        return track_segment_sequence, track_segment_indices

    def compute_incline_profile(
        self,
        path: LineString,
        gnss_coords_utm: list[Point],
        track_segment_sequence: list[TrackSegment],
        track_segment_indices: list[int],
        rail_sequence: list[Rail],
        position_dict: dict,
    ):
        """TODO"""

        # inclines at kilometrage values

        inclines_list = []
        kms_inclines_list = []
        track_segment_names_list = []
        track_segment_indices_new = track_segment_indices + [len(rail_sequence) - 1]
        for n, (i1, i2) in enumerate(zip(track_segment_indices_new[:-1], track_segment_indices_new[1:])):
            # i1:i2 -> rails belonging to a single track segment, i1: first occurence of a rail belonging track segment, i2-1: last occurence of a rail belonging track segment

            # it is possible that the train changes movement direction while driving on the track segment
            # if moving dircetion = 2 (in direction of decreasing kilometrage), inclines must be negated and reversed.
            # therefore, we have to check if train changes direction while on the track segment and if so,
            # split the ride into trips where each trips has a single direction
            moving_directions = position_dict['directions']
            trips = [list(g) for k, g in groupby(moving_directions[i1:i2])]

            # kms / inclines per trip
            # transition between trips is instaneous (last km_val+incline of last trip jumps to first km_val/incline of next trip)
            trips_kms = []
            trips_inclines = []
            track_segment_names = []
            for t in range(len(trips)):
                # trip indices
                ti = sum([len(trips[k]) for k in range(0, t)])
                ti1 = i1 + ti
                ti2 = ti1 + len(trips[t])

                match moving_directions[ti1]:
                    case 1:
                        index1, index2 = 0, -1
                    case 2:
                        index1, index2 = -1, 0
                    case _:
                        raise ValueError('Unkown direction')

                # first and last rail of trip
                rail_0 = rail_sequence[ti1]
                rail_n = rail_sequence[ti2 - 1]

                if track_segment_sequence[n].kilometrage.n_lines == 2 and rail_0.direction == 0:
                    if rail_sequence[ti1 - 1].direction > 0:
                        rail0_direction = rail_sequence[ti1 - 1].direction
                    elif rail_sequence[ti2].direction > 0:
                        rail0_direction = rail_sequence[ti2].direction
                    else:
                        rail0_direction = 1
                else:
                    rail0_direction = rail_0.direction
                if track_segment_sequence[n].kilometrage.n_lines == 2 and rail_n.direction == 0:
                    if rail_sequence[ti1 - 1].direction > 0:
                        railn_direction = rail_sequence[ti1 - 1].direction
                    elif rail_sequence[ti2].direction > 0:
                        railn_direction = rail_sequence[ti2].direction
                    else:
                        railn_direction = 1
                else:
                    railn_direction = rail_n.direction

                # compute km from and km to
                if n > 0 and t == 0:
                    km_from = track_segment_sequence[n].km(point=Point(rail_0.coords[index1]), direction=rail0_direction)  # type: ignore
                elif n == 0:
                    km_from = track_segment_sequence[n].km(point=gnss_coords_utm[ti1], direction=rail0_direction)  # type: ignore
                else:
                    km_from = track_segment_sequence[n].km(point=gnss_coords_utm[ti1 - 1], direction=rail0_direction)  # type: ignore
                if n < len(track_segment_indices) - 2 and t == len(trips) - 1:
                    km_to = track_segment_sequence[n].km(point=Point(rail_n.coords[index2]), direction=railn_direction)  # type: ignore
                else:
                    km_to = track_segment_sequence[n].km(point=gnss_coords_utm[ti2 - 1], direction=railn_direction)  # type: ignore

                # compute inlcine profile

                if abs(km_from - km_to) < 1e-3:
                    if len(track_segment_sequence[n].lines_1) == 1:
                        km_from = track_segment_sequence[n].km_from
                        km_to = track_segment_sequence[n].km_to

                kms_inclines, inclines = track_segment_sequence[n].incline_profile(km_from=km_from, km_to=km_to)

                trips_kms += kms_inclines
                trips_inclines += inclines
                track_segment_names += len(kms_inclines) * [track_segment_sequence[n].name]

            kms_inclines_list.append(trips_kms)
            inclines_list.append(trips_inclines)
            track_segment_names_list.append(track_segment_names)

        # inclines at running km (transform kilometrage kms to running kms)
        running_kms_list = []
        for n, (kms_inclines, inclines) in enumerate(zip(kms_inclines_list, inclines_list)):
            # remove duplicates
            diff = np.diff(kms_inclines)
            index_double = np.arange(len(kms_inclines))[np.append(diff, 1) == 0]
            kms_inclines = np.delete(kms_inclines, index_double)
            inclines = np.delete(inclines, index_double)

            # moving direction
            if kms_inclines[1] - kms_inclines[0] > 0:
                direction = 1
            elif kms_inclines[1] - kms_inclines[0] < 0:
                direction = 2
            else:
                raise ValueError('Could not determine direction.')

            # transform kilometrage to points
            km_points = [track_segment_sequence[n].point(km=km_, direction=direction) for km_ in kms_inclines]

            # project points on path which yields running distances (based on path lentgth)
            if n == 0:
                running_kms = [0.0]
                distance_since_km = 0.0
            else:
                distance_since_km = abs(path.project(km_points[0]) - path.project(last_km_point)) / 1000
                running_kms = [running_kms_list[-1][-1] + distance_since_km]

            distances_along_path = path.project(km_points)
            for d1, d2 in zip(distances_along_path[1:], distances_along_path[:-1]):
                d = abs(d1 - d2) / 1000
                running_kms.append(running_kms[-1] + d)

            running_kms = np.round(running_kms, 3)
            running_kms_list.append(running_kms)

            last_km_point = km_points[-1]

        # if inclines are missing for a segment, check if
        # last available incline and next available incline are the same.
        # If yes, set nan values to the same value.
        inclines = np.concatenate((inclines_list))
        index = np.where(np.isnan(inclines))[0]
        if len(index) > 0:
            split_indices = np.where(np.diff(index) > 1)[0] + 1
            if len(split_indices) > 0:
                index_list = np.split(index, split_indices)
            else:
                index_list = [index]
            for index in index_list:
                if index[0] > 0:
                    inc1 = inclines[index[0] - 1]
                else:
                    inc1 = None
                if index[-1] < len(inclines) - 1:
                    inc2 = inclines[index[-1] + 1]
                else:
                    inc2 = None
                if inc1 == inc2:
                    inclines[index] = inc1

        # incline profile
        incline_profile = {
            'kms': np.concatenate((running_kms_list)).tolist(),
            'inclines': inclines.tolist(),
            'track_segment_names': np.concatenate((track_segment_names_list)).tolist(),
        }

        return incline_profile

    @staticmethod
    def split_into_subgroups_by_nan(
        kms: list[float], inclines: list[float], track_segment_names: list[str]
    ) -> Tuple[list[list[float]], list[list[float]], list[list[str]]]:
        """Splits kilometer values and inclines from incline profile into subgroups based on nan-values in inclines."""

        kms_splitted = []
        inc_splitted = []
        tsn_splitted = []
        sub_list_kms = []
        sub_list_inc = []
        sub_list_tsn = []
        for i in range(0, len(kms)):
            if i == 0:
                sub_list_kms.append(kms[i])
                sub_list_inc.append(inclines[i])
                sub_list_tsn.append(track_segment_names[i])

            elif (not np.isnan(inclines[i - 1])) and np.isnan(inclines[i]):  # break
                sub_list_kms.append(kms[i])
                sub_list_inc.append(inclines[i])
                sub_list_tsn.append(track_segment_names[i])
                kms_splitted.append(sub_list_kms)
                inc_splitted.append(sub_list_inc)
                tsn_splitted.append(sub_list_tsn)
                sub_list_kms = []
                sub_list_inc = []
                sub_list_tsn = []

            elif (np.isnan(inclines[i - 1])) and not np.isnan(inclines[i]):  # break
                kms_splitted.append(sub_list_kms)
                inc_splitted.append(sub_list_inc)
                tsn_splitted.append(sub_list_tsn)
                sub_list_kms = []
                sub_list_inc = []
                sub_list_tsn = []
                sub_list_kms.append(kms[i])
                sub_list_inc.append(inclines[i])
                sub_list_tsn.append(track_segment_names[i])

            else:
                sub_list_kms.append(kms[i])
                sub_list_inc.append(inclines[i])
                sub_list_tsn.append(track_segment_names[i])

            if i == len(kms) - 1:
                kms_splitted.append(sub_list_kms)
                inc_splitted.append(sub_list_inc)
                tsn_splitted.append(sub_list_tsn)

        return kms_splitted, inc_splitted, tsn_splitted

    def compute_height_profile(self, incline_profile: dict, track_segment_sequence: list[TrackSegment]) -> dict:
        """TODO"""

        kms = incline_profile['kms']
        inclines = incline_profile['inclines']
        track_segment_names = incline_profile['track_segment_names']

        # split incline profile into groups by nan values
        kms_groups, inc_groups, tsn_groups = self.split_into_subgroups_by_nan(
            kms=kms, inclines=inclines, track_segment_names=track_segment_names
        )

        # compute incline profile for each group
        height_groups = []
        searched = []
        for n, (km_group, inc_group, tsn_group) in enumerate(zip(kms_groups, inc_groups, tsn_groups)):
            # if nan group, append and continue to next group
            if np.isnan(inc_group[0]):
                height_groups.append(inc_group)
                continue

            # relative height profile
            h = [0.0]
            for i in range(1, len(km_group)):
                height_gain = (km_group[i] - km_group[i - 1]) * inc_group[i - 1]
                total_height = h[-1] + height_gain
                h.append(total_height)
            h = np.array(h)

            # find track segments for km group
            track_segment_list: list[TrackSegment] = []
            for track_segment in track_segment_sequence:
                if track_segment in track_segment_list:
                    continue

                for track_segment_name in tsn_group:
                    if track_segment.name == track_segment_name:
                        track_segment_list.append(track_segment)

            # absolute height profile
            max_height_from_incline = np.max(h)
            max_height_at_km = km_group[np.argmax(h)]
            max_height_from_isr = -1.0

            warning = False
            if n == 0:
                track_segment_list = track_segment_list[1:]
            if n == len(kms_groups) - 1:
                track_segment_list = track_segment_list[:-1]
            for track_seg in track_segment_list:
                if track_seg in searched:
                    continue
                inf_max_height = track_seg.properties['INF_HOECHSTHOEHE']
                if isinstance(inf_max_height, float):
                    if inf_max_height > max_height_from_isr:
                        max_height_from_isr = inf_max_height
                    searched.append(track_seg.name)
                else:
                    warning = True
            if max_height_from_isr == -1.0:
                max_height_from_isr = 0
                warnings.warn(
                    message='Max height information is missing completely in ISR. Height profile is (or parts of it are) affected by a constant offset.'
                )
            elif warning == True:
                warnings.warn(
                    message='Max height information partly missing in ISR. Height profile (or parts of it) may be affected by a constant offset.'
                )

            diff = max_height_from_isr - max_height_from_incline
            h_isr = h + diff

            height_groups.append(h_isr)

        # interpolate nan values for height profile
        # derive values for nan inclines from interpolated height profile
        height_groups: list[list[float]]
        kms_groups: list[list[float]]
        for i, (h_group, km_group, inc_group) in enumerate(zip(height_groups, kms_groups, inc_groups)):
            if i == 0:
                continue
            if i == len(height_groups) - 1:
                continue

            # interpolate
            if np.isnan(h_group[0]):
                h_1 = height_groups[i - 1][-1]
                h_2 = height_groups[i + 1][0]
                km_1 = kms_groups[i - 1][-1]
                km_2 = kms_groups[i + 1][0]

                h_diff = h_2 - h_1
                km_diff = km_2 - km_1
                m = h_diff / (km_diff)

                new_height_group = [h_1 + m * (km - km_1) for km in km_group]
                height_groups[i] = new_height_group

                inc_groups[i] = len(inc_groups[i]) * [m]
                inc_groups[i - 1][-1] = m

        # height and incline profile
        height_and_incline_profiles = {
            'inclines': np.concatenate((inc_groups)),
            'height': np.concatenate((height_groups)),
            'kms': incline_profile['kms'],
        }

        return height_and_incline_profiles

    def velocity_from_gnss(
        self, kms_running: list[float], gnss: GNSSSeries, incline_profile: dict, correct_velocity: bool = True
    ) -> list[float]:
        """TODO"""

        inclines = incline_profile['inclines']
        kms = incline_profile['kms']

        # velocity_over_path
        dt_avg = np.mean(np.diff(gnss.time_s))
        velocity_over_path_kmh = []
        S = kms_running * 1000  # positions in meter
        for i in range(0, len(gnss)):
            if i == 0:
                # Use forward differences for first point
                ds = S[i + 1] - S[i]
                dt = gnss.time_s[i + 1] - gnss.time_s[i]
            elif i == len(S) - 1:
                # Use backward differences for last point
                ds = S[i] - S[i - 1]
                dt = gnss.time_s[i] - gnss.time_s[i - 1]
            else:
                # Use central differences for intermediate points
                ds = S[i + 1] - S[i - 1]
                dt = gnss.time_s[i + 1] - gnss.time_s[i - 1]

            if 2 * dt < dt_avg:  # dt can't be much smaller than average dt
                dt = dt_avg

            if correct_velocity == True:
                # get incline
                next_smaller_idx = bisect.bisect(kms, kms_running[i])
                incline = inclines[next_smaller_idx - 1]

                # correct velocity with incline angle
                alpha = np.arctan(incline / 1000)
                v = 3.6 * ds / dt / np.cos(alpha)  # km / h

            else:
                v = 3.6 * ds / dt

            velocity_over_path_kmh.append(v)

        # moving average with window length 5
        # first and last values are unfiltered
        velocity_filtered_kmh = pd.Series(velocity_over_path_kmh).rolling(5, center=True).mean().tolist()
        velocity_filtered_kmh[0] = velocity_over_path_kmh[0]
        velocity_filtered_kmh[1] = np.mean(velocity_over_path_kmh[:3])
        velocity_filtered_kmh[-2] = np.mean(velocity_over_path_kmh[-3:])
        velocity_filtered_kmh[-1] = velocity_over_path_kmh[-1]

        return velocity_filtered_kmh

    def acceleration_from_gnss_and_velocity(self, gnss: GNSSSeries, velocity_ms: list[float]) -> list[float]:
        """TODO"""

        # acceleration_over_path
        dt_avg = np.mean(np.diff(gnss.time_s))
        acceleration_over_path_ms2 = []
        for i in range(0, len(gnss)):
            if i == 0:
                # Use forward differences for first point
                dv = velocity_ms[i + 1] - velocity_ms[i]
                dt = gnss.time_s[i + 1] - gnss.time_s[i]
            elif i == len(velocity_ms) - 1:
                # Use backward differences for last point
                dv = velocity_ms[i] - velocity_ms[i - 1]
                dt = gnss.time_s[i] - gnss.time_s[i - 1]
            else:
                # Use central differences for intermediate points
                dv = velocity_ms[i + 1] - velocity_ms[i - 1]
                dt = gnss.time_s[i + 1] - gnss.time_s[i - 1]

            if 2 * dt < dt_avg:  # dt can't be much smaller than average dt
                dt = dt_avg

            acceleration_over_path_ms2.append(dv / dt)

        return acceleration_over_path_ms2

    @staticmethod
    def add_gps_series_to_map(m: folium.Map, gps: np.ndarray, df: pd.DataFrame):
        """TODO"""

        # coordinate sequence
        coordinate_sequence = [(p[0], p[1]) for p in gps]

        # extract datetime column
        datetime = df['time'].to_numpy()

        # popup for PolyLine
        # length_km = df['km_running'].to_list()[-1]                      # length of measurement ride in km
        # csv_index_start = df_subset.iloc[0].name + self.skiprows + 1     # first row index of subset in original csv file
        # csv_index_end = df_subset.iloc[-1].name + self.skiprows + 1      # last row index of subset in original csv file

        series = pd.Series(
            data=[
                f'{datetime[-1]} - {datetime[0]}',
                f'{(datetime[-1] - datetime[0]).item() / 6e10}',
                f'{len(coordinate_sequence)}',
                #           f'{csv_index_start} - {csv_index_end}',
                #            f'{length_km:.3f}',
            ],
            index=['Time', 'Duration [min]', 'Coordinates'],
            name=f'GNSS Messdaten',
        )
        df_line = series.to_frame()
        html_string = df_line.to_html(classes="table table-striped table-hover table-condensed table-responsive")
        popup = folium.Popup(html_string, max_width=500)

        scatter_group = folium.FeatureGroup(f"GNSS Messdaten").add_to(m)

        # add PolyLine
        folium.PolyLine(
            locations=coordinate_sequence,
            popup=popup,
            tooltip=f'GNSS Messdaten',
            color='black',
            weight=4,
            opacity=0.7,
            smooth_factor=0,
        ).add_to(scatter_group)

        cluster_list: list[pd.DataFrame] = []  # list for collecting rows with same location (lat, lon)
        for i, coord in enumerate(coordinate_sequence):
            # get measurement values for data point as table (will be shown as popup when clicking a point)
            row_df = df.iloc[i].to_frame(name=f'Point {df.iloc[i].name + 1}').iloc[:-5]

            if (i < len(coordinate_sequence) - 1) and (coord == coordinate_sequence[i + 1]):
                # append row
                cluster_list.append(row_df)

            else:
                row_df = pd.concat(objs=cluster_list + [row_df], axis=1)

                # popup showing data frame
                html_string = row_df.to_html(classes="table table-striped table-hover table-condensed table-responsive")
                popup = folium.Popup(html_string, max_width='600')

                # tooltip
                if len(cluster_list) > 0:
                    tooltip = f'GNSS Messdaten<br>{i+1} - {i+1+len(cluster_list)} / {len(coordinate_sequence)}'
                else:
                    tooltip = f'GNSS Messdaten<br>{i+1} / {len(coordinate_sequence)}'

                # plot measurement points as circles
                folium.Circle(
                    location=(coord[0], coord[1]),
                    radius=1,
                    color='black',
                    fill_color='lightgray',
                    opacity=0.8,
                    popup=popup,
                    tooltip=tooltip,
                ).add_to(scatter_group)

                cluster_list = []

    @staticmethod
    def add_result_to_map(
        m: folium.Map,
        df: pd.DataFrame | None,
        route,
        kms,
        gps_routed,
        distance_routed_m,
        path,
        time=None,
        name=None,
        return_map=False,
    ):
        """"""
        # coordinate sequence
        coordinate_sequence = [(p[0], p[1]) for p in gps_routed]

        if not isinstance(df, type(None)):
            # extract datetime column
            datetime = df['time'].to_numpy()

            # popup for PolyLine
            length_km = df['km_running'].to_list()[-1]  # length of measurement ride in km
        else:
            datetime = time

            length_km = kms[-1] - kms[0]

        if name:
            scatter_group = folium.FeatureGroup(name).add_to(m)
            color = 'green'
        else:
            scatter_group = folium.FeatureGroup(f"Ergebnis (Map Matching)").add_to(m)
            color = 'blue'
            name = 'Ergebnis (Map Matching)'

        series = pd.Series(
            data=[
                f'{datetime[-1]} - {datetime[0]}',
                f'{(datetime[-1] - datetime[0]).item() / 6e10}',
                f'{len(coordinate_sequence)}',
                #            f'{csv_index_start} - {csv_index_end}',
                f'{length_km:.3f}',
                f'{np.unique(route)}',
                f'{kms[0]} ({route[0]})',
                f'{kms[-1]} ({route[-1]})',
            ],
            index=[
                'Time',
                'Duration [min]',
                'Coordinates',
                'Ride Distance [km]',
                'Track(s)',
                'From [km (track)]',
                'To [km (track)]',
            ],
            name=name,
        )
        df_line = series.to_frame()
        html_string = df_line.to_html(classes="table table-striped table-hover table-condensed table-responsive")
        popup = folium.Popup(html_string, max_width=500)

        line_tooltip_string = (
            f'{name}<br>Track(s): {np.unique(route)}<br>From: {kms[0]} km ({route[0]}) To: {kms[-1]} km ({route[-1]})'
        )

        # add mapped measurements as line to map
        coordinate_sequence = [(p[0], p[1]) for p in gps_routed]
        path_sequence = [(p[0], p[1]) for p in path]
        folium.PolyLine(
            path_sequence,
            popup=popup,
            tooltip=line_tooltip_string,
            color=color,
            weight=3,
            opacity=0.8,
            smooth_factor=0,
        ).add_to(scatter_group)

        # plot mapped points as circles
        cluster_list: list[pd.DataFrame] = []  # list for collecting rows with same location (lat, lon)
        for i, coord in enumerate(coordinate_sequence):
            # get measurement values for data point as data frame (will be shown as popup when clicking a point)
            if not isinstance(df, type(None)):
                row_df = df.iloc[i].to_frame(name=f'Point {df.iloc[i].name + 1}')

                if (i < len(coordinate_sequence) - 1) and (coord == coordinate_sequence[i + 1]):
                    # append row
                    cluster_list.append(row_df)

                else:
                    row_df = pd.concat(objs=cluster_list + [row_df], axis=1)

                    # popup showing data frame
                    html_string = row_df.to_html(
                        classes="table table-striped table-hover table-condensed table-responsive"
                    )
                    popup = folium.Popup(html_string, max_width='600')

                    # tooltip
                    if len(cluster_list) > 0:
                        tooltip = (
                            f'Ergebnis (Map Matching)<br>{i+1} - {i+1+len(cluster_list)} / {len(coordinate_sequence)}'
                        )
                    else:
                        tooltip = f'Ergebnis (Map Matching)<br>{i+1} / {len(coordinate_sequence)}'

                    folium.Circle(
                        location=(coord[0], coord[1]),
                        radius=1,
                        color='black',
                        fill_color=color,
                        opacity=0.8,
                        popup=popup,
                        tooltip=tooltip,
                    ).add_to(scatter_group)

                    cluster_list = []
            else:
                # tooltip
                if len(cluster_list) > 0:
                    tooltip = f'{name}<br>{i+1} - {i+1+len(cluster_list)} / {len(coordinate_sequence)}'
                else:
                    tooltip = f'{name}<br>{i+1} / {len(coordinate_sequence)}'

                folium.Circle(
                    location=(coord[0], coord[1]),
                    radius=1,
                    color='black',
                    fill_color=color,
                    opacity=0.8,
                    #    popup=popup,
                    tooltip=tooltip,
                ).add_to(scatter_group)

        if return_map:
            return m

    @staticmethod
    def map_matching_results_to_map(
        df: pd.DataFrame, export_path: Path, df_path: pd.DataFrame, map_: Map | None = None, return_map: bool = False
    ) -> None | folium.Map:
        """TODO"""

        # create map
        m = folium.Map(
            location=(df['lat_measured'].iloc[0], df['lon_measured'].iloc[0]),
            control_scale=True,
            tiles=None,
            zoom_start=12,
        )

        # add background layer
        folium.TileLayer(tiles='OpenStreetMap', name='OpenStreetMap Background', overlay=True).add_to(m)

        if not isinstance(map_, type(None)):
            m = MMPostprocessor.add_isr_lines_to_map(m=m, isr_map=map_, return_map=True)

        # create gps array
        latitude, longitude = df['lat_measured'].to_numpy(), df['lon_measured'].to_numpy()
        gps_array = np.column_stack((latitude, longitude))
        df_gps = df[['time', 'time_from_start_s', 'lat_measured', 'lon_measured']]

        # add measurements to map
        MMPostprocessor.add_gps_series_to_map(m, gps_array, df_gps)

        # add matched results to map
        latitude, longitude = df_path['lat_wgs84'].to_numpy(), df_path['lon_wgs84'].to_numpy()
        path = np.column_stack((latitude, longitude))
        latitude, longitude = df['lat_wgs84'].to_numpy(), df['lon_wgs84'].to_numpy()
        gps_array = np.column_stack((latitude, longitude))
        MMPostprocessor.add_result_to_map(
            m, df, df['track_number'].to_numpy(), df['km_db'].to_numpy(), gps_array, df['gnss_error_m'].to_numpy(), path
        )

        if return_map:
            return m
        else:
            # save map
            folium.LayerControl().add_to(m)
            m.save(export_path / f'map.html')

    @staticmethod
    def add_isr_lines_to_map(m: folium.Map, isr_map: Map, return_map: bool = False):
        colors = [
            'red',
            #           'blue',
            'orange',
            #            'beige',
            'purple',
            'green',
            'darkred',
            #            'darkblue',
            #            'pink',
            'lightred',
            'lightblue',
            'darkgreen',
            'lightgreen',
            'cadetblue',
            'darkpurple',
            #            'lightgray',
            #            'gray',
            #            'black'
        ]
        color_cycle = cycle(colors)

        # sort rails by track number
        rails = isr_map['rails']
        tracks = [int(rail.track) for rail in rails]
        index = np.argsort(tracks).tolist()
        rails: list[Rail] = [rails[i] for i in index]  # type: ignore

        # add rails to map in groups based on track number
        for i, rail in enumerate(rails):
            if i == 0 or rails[i - 1].track != rails[i].track:
                scatter_group = folium.FeatureGroup(f'Strecke {str(rail.track)} (ISR)').add_to(m)
                color = next(color_cycle)

            coordinate_sequence = [(p.x, p.y) for p in rail.coords_wgs]
            folium.PolyLine(
                coordinate_sequence,
                popup=f'Strecke {rail.track}',
                tooltip=f'Strecke {rail.track}',
                color=color,
                weight=12,
                opacity=0.6,
                smooth_factor=0,
            ).add_to(scatter_group)

        # add betriebsstellen to map
        scatter_group_bs = folium.FeatureGroup('Betriebsstellen (ISR)').add_to(m)

        for bs in isr_map['operational_points']:
            folium.Circle(
                location=(bs.coords_wgs84[0], bs.coords_wgs84[1]),
                radius=8,
                color='green',
                fill_color='green',
                opacity=1,
                popup=f'{bs.name}',
                tooltip=f'{bs.name}',
            ).add_to(scatter_group_bs)

        if return_map == True:
            return m
