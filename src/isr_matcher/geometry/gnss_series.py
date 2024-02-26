from __future__ import annotations
from pathlib import Path
from typing import Literal, Union, Tuple, TYPE_CHECKING
from numpy.typing import ArrayLike
import numpy as np
from shapely import Point, LineString
from isr_matcher.data_handlers.transformer import Transformer
from isr_matcher.ops._functions import angle_between
from isr_matcher._constants._parse import FLOAT_TYPES
import datetime


class GNSSSeries:

    """
    Container class for GPS series.

    Attributes
    ----------
    line_wgs: LineString
        Shapely LineString of measurements in WGS84 reference system (EPSG:4326). Axes: longitude, latitude.
    line_utm: LineString
        Shapely LineString of measurements in UTM reference system (EPSG:31467). Axes: x, y.
    time: np.ndarray
        Array of datetimes.
    time_s: np.ndarray
        Array of relative times from first time stamp, in seconds.
    latitude: np.ndarray
        Array of latitude coordinates (WGS84 / EPSG:4326).
    longitude: np.ndarray
        Array of longitude coordinates (WGS84 / EPSG:4326).
    x: np.ndarray
        Array of horizontal coordinates (UTM / EPSG:31467).
    y: np.ndarray
        Array of vertical coordinates (UTM / EPSG:31467).
    altitude_m: np.ndarray | None
        Array of altitudes in m, if available. Else, None.
    veolicty_ms: np.ndarray | None
        Array of velocities in m/s, if available. Else, None.
    acceleration_ms2: np.ndarray | None
        Array of acceleartions in m/s^2, if available. Else, None.
    """

    def __init__(
        self,
        time_utc: list[datetime.datetime] | np.ndarray | None,
        time_s: list[float] | np.ndarray | None,  # in seconds!
        latitude: list[float] | np.ndarray,  # in WGS84!
        longitude: list[float] | np.ndarray,  # in WGS84!
        altitude_m: list[float] | np.ndarray | None = None,
        velocity_ms: list[float] | np.ndarray | None = None,
        acceleration_ms2: list[float] | np.ndarray | None = None,
    ):
        # check_input
        self._check_input(time_utc, time_s, latitude, longitude, altitude_m, velocity_ms, acceleration_ms2)

        # project from wgs84 to utm
        transformer = Transformer(source_cs='epsg:4326', target_cs='epsg:31467')  # set up Transformer
        gnss_np = np.column_stack(tup=(latitude, longitude))  # gnss array (lat, lon)
        gnss_line_string_wgs_latlon = LineString(gnss_np)  # linestring
        gnss_line_string_utm_yx = transformer.transform(  # transform
            projection='source_to_target', object=gnss_line_string_wgs_latlon
        )
        gnss_line_string_utm_xy = LineString(  # invert axes
            [(y, x) for (x, y) in zip(gnss_line_string_utm_yx.xy[0], gnss_line_string_utm_yx.xy[1])]
        )

        # time in seconds
        if not self.notnone(time_s):
            time_s = np.array([(t - time_utc[0]) / np.timedelta64(1, 's') for t in time_utc])  # type: ignore
            if any(np.diff(time_s) == 0):
                idx = np.where(np.diff(time_s) == 0)[0]
                for i in idx:
                    # mean time diff
                    time_diff = np.median(np.diff(time_s))

                    # i and i+1 same time
                    time_s[i + 1 :] = time_s[i + 1 :] + time_diff

        if not self.notnone(time_utc):
            time_utc = np.ones(len(time_s)) * np.nan

        # set attributes
        self._line_wgs = LineString(np.column_stack(tup=(longitude, latitude)))
        self._line_utm = gnss_line_string_utm_xy
        self._time = time_utc
        self._time_s = time_s
        self._latitude = np.array(latitude)
        self._longitude = np.array(longitude)
        self._x = np.array(gnss_line_string_utm_xy.xy[0])
        self._y = np.array(gnss_line_string_utm_xy.xy[1])
        self._altitude_m = np.array(altitude_m) if not isinstance(altitude_m, type(None)) else None
        self._velocity_ms = np.array(velocity_ms) if not isinstance(velocity_ms, type(None)) else None
        self._acceleration_ms2 = np.array(acceleration_ms2) if not isinstance(acceleration_ms2, type(None)) else None
        self._sigma = None
        self._error = None

    # getter methods
    @property
    def line_wgs(self) -> LineString:
        """Returns a LineString of WGS84 coordinates. Axes: (longitude, latitude).

        Returns
        -------
        line_wgs: LineString
            LineString of WGS84 coordinates. Axes: (longitude, latitude).
        """
        return self._line_wgs

    @property
    def line_utm(self) -> LineString:
        """Returns a LineString of UTM (EPSG:31467) coordinates. Axes: (horizontal, vertical).

        Returns
        -------
        line_utm: LineString
            LineString of UTM (EPSG:31467) coordinates. Axes: (horizontal, vertical).
        """
        return self._line_utm

    @property
    def coords_wgs(self) -> list[Point]:
        """Returns a list of GNSS coordinates as Points (WGS84). Axes: (longitude, latitude).

        Returns
        -------
        coords_wgs: LineString
            List of WGS84 coordinates. Axes: (longitude, latitude).
        """
        return [Point(coord) for coord in self.line_wgs.coords]

    @property
    def coords_utm(self) -> list[Point]:
        """Returns a list of GNSS coordinates as Points (UTM: EPSG:31467). Axes: (horizontal, vertical).

        Returns
        -------
        coords_utm: LineString
            List of UTM coordinates (EPSG:31467). Axes: (horizontal, vertical).
        """
        return [Point(coord) for coord in self.line_utm.coords]

    @property
    def time(self) -> np.ndarray:
        """Returns an array of time stamps in datetime format.

        Returns
        -------
        time: np.ndarray
            Array of time stamps in datetime format.
        """
        return self._time

    @property
    def time_s(self) -> np.ndarray:
        """Returns an array of relative time differences from first time stamp, in seconds.

        Returns
        -------
        time_s: np.ndarray
            Array of relative time differences from first time stamp, in seconds.
        """
        return self._time_s

    @property
    def longitude(self) -> np.ndarray:
        """Returns an array of longitudes (WGS84).

        Returns
        -------
        longitude: np.ndarray
            Array of longitudes (WGS84).
        """
        return self._longitude

    @property
    def latitude(self) -> np.ndarray:
        """Returns an array of latitudes

        Returns
        -------
        latitude: np.ndarray
            Array of latitude (WGS84).
        """
        return self._latitude

    @property
    def x(self) -> np.ndarray:
        """Returns an array of hoizontal UTM coordinates (EPSG:31467).

        Returns
        -------
        x: np.ndarray
            Array of hoizontal UTM coordinates (EPSG:31467).
        """
        return self._x  # type: ignore

    @property
    def y(self) -> np.ndarray:
        """Returns an array of vertical UTM coordinates (EPSG:31467).

        Returns
        -------
        y: np.ndarray
            Array of vertical UTM coordinates (EPSG:31467).
        """
        return self._y  # type: ignore

    @property
    def altitude_m(self) -> np.ndarray | None:
        """Returns an array of altitudes in m, if available. Else returns None.

        Returns
        -------
        altitude_m: np.ndarray
            Array of altitudes in m, if available. Else None.
        """
        return self._altitude_m

    @property
    def velocity_ms(self) -> np.ndarray | None:
        """Returns an array of velocities in m/s, if available. Else returns None.

        Returns
        -------
        velocity_ms: np.ndarray
            Array of velocities in m/s, if available. Else None.
        """
        return self._velocity_ms

    @property
    def acceleration_ms2(self) -> np.ndarray | None:
        """Returns an array of accelerations in m/s^2, if available. Else returns None.

        Returns
        -------
        acceleration_ms2: np.ndarray
            Array of accelerations in m/s^2, if available. Else None.
        """
        return self._acceleration_ms2

    @property
    def sigma(self) -> float | None:
        """Returns sigma (Estimate of GNSS noise standard deviation), if available. Else returns None.

        Returns
        -------
        sigma: float | None
            Estimate of GNSS noise standard deviation. If not set, returns None.
        """
        return self._sigma

    @sigma.setter
    def sigma(self, value: float):
        """Set sigma (Estimate of GNSS noise standard deviation)."""
        self._sigma = value

    @property
    def error(self) -> float | None:
        """Returns gnss error (Estimate of GNSS error at each time step), if available. Else returns None.

        Returns
        -------
        error: float | None
            Estimate of GNSS error at each time step. If not set, returns None.
        """
        return self._sigma

    @error.setter
    def error(self, value: np.ndarray):
        """Set error (Estimate of GNSS error at each time step)."""
        self._error = value

    def __len__(self):
        """Method for calling len() on instances."""
        return len(self.x)

    def __getitem__(self, key):
        """Enables selecting subset of GNSSSeries by slice indexing"""
        if isinstance(key, slice):
            # Get the start, stop, and step from the slice
            start, stop, step = key.indices(len(self))
            # check for None attributes
            if not isinstance(self.altitude_m, type(None)):
                sliced_altitude_m = self.altitude_m[start:stop:step]
            else:
                sliced_altitude_m = None
            if not isinstance(self.velocity_ms, type(None)):
                sliced_velocity_ms = self.velocity_ms[start:stop:step]
            else:
                sliced_velocity_ms = None
            if not isinstance(self.acceleration_ms2, type(None)):
                sliced_acceleration_ms2 = self.acceleration_ms2[start:stop:step]
            else:
                sliced_acceleration_ms2 = None

            return GNSSSeries(
                time=self.time[start:stop:step],
                latitude=self.latitude[start:stop:step],
                longitude=self.longitude[start:stop:step],
                altitude_m=sliced_altitude_m,
                velocity_ms=sliced_velocity_ms,
                acceleration_ms2=sliced_acceleration_ms2,
            )
        else:  # single indexing not supported
            raise TypeError("Invalid argument type.")

    def prune(self, r: float, index: list | None = None):
        """Prunes noisy measurments within r of previous measurement. If index is given, prune by index."""
        temp = False
        if isinstance(index, type(None)):
            delete_index = []
            temp_delete_index = []
            last_point = Point(self.x[0], self.y[0])
            angle = 0.0
            for i in range(len(self) - 1):
                # distance between neighbor points
                next_point = Point(self.x[i + 1], self.y[i + 1])
                distance = last_point.distance(next_point)

                # angle
                if last_point != Point(self.x[0], self.y[0]):
                    p0 = np.array([second_last_point.x, second_last_point.y])
                    p1 = np.array([last_point.x, last_point.y])
                    p2 = np.array([next_point.x, next_point.y])
                    angle = angle_between(v1=p1 - p0, v2=p2 - p1)

                # compare with standard deviation and angle threshold
                if distance < r:
                    delete_index.append(i + 1)
                elif angle > 100:
                    temp_delete_index.append(i + 1)
                    temp = True
                else:
                    second_last_point = last_point
                    last_point = next_point

                if len(temp_delete_index) > 10 and np.all(np.diff(temp_delete_index) == 0):
                    temp_delete_index = []
                    second_last_point = last_point
                    last_point = next_point
                    temp = False
                elif len(temp_delete_index) > 10:
                    delete_index = np.unique(delete_index + temp_delete_index).tolist()
                    temp_delete_index = []
                    second_last_point = last_point
                    last_point = next_point
                    temp = False

        else:
            delete_index = index

        # prune noisy measurements
        if temp == True:
            delete_index = np.unique(delete_index + temp_delete_index).tolist()
        self._time = np.delete(self._time, delete_index)
        self._time_s = np.delete(self._time_s, delete_index)
        self._latitude = np.delete(self._latitude, delete_index)
        self._longitude = np.delete(self._longitude, delete_index)
        self._x = np.delete(self._x, delete_index)
        self._y = np.delete(self._y, delete_index)
        self._velocity_ms = (
            np.delete(self._velocity_ms, delete_index) if not isinstance(self._velocity_ms, type(None)) else None
        )
        self._altitude_m = (
            np.delete(self._altitude_m, delete_index) if not isinstance(self._altitude_m, type(None)) else None
        )
        self._acceleration_ms2 = (
            np.delete(self._acceleration_ms2, delete_index)
            if not isinstance(self._acceleration_ms2, type(None))
            else None
        )
        self._line_wgs = LineString(np.column_stack(tup=(self._longitude, self._latitude)))
        self._line_utm = LineString(np.column_stack(tup=(self._x, self._y)))

    @staticmethod
    def average_by_index(array, index):
        """Replaces consecutive values of an array given by index with their average."""
        return np.array([np.mean(array[idx].astype(float)) for idx in index], dtype=array.dtype)

    def average_low_velocity(self, threshold: float = 3.0):
        """Averages sequences in time series where velocity is smaller than 'threshold', in meter per second."""

        assert not isinstance(self.velocity_ms, type(None)), 'velocity_ms is None'

        # find consecutive sequences where all values are smaller than threshold
        mask = self.velocity_ms < threshold
        split_indices = np.where(~mask)[0]

        # split the array indices
        sequences_index = np.split(np.arange(len(self.velocity_ms)), split_indices)
        sequences_index = [arr for arr in sequences_index if len(arr) > 0]

        # average sequences for all parameters
        self._time = self.average_by_index(
            self._time, sequences_index
        )  # np.array([self._time[idx][0] for idx in sequences_index])
        self._time_s = self.average_by_index(self._time_s, sequences_index)
        self._latitude = self.average_by_index(self._latitude, sequences_index)
        self._longitude = self.average_by_index(self._longitude, sequences_index)
        self._x = self.average_by_index(self._x, sequences_index)
        self._y = self.average_by_index(self._y, sequences_index)
        self._velocity_ms = (
            self.average_by_index(self._velocity_ms, sequences_index)
            if not isinstance(self._velocity_ms, type(None))
            else None
        )
        self._altitude_m = (
            self.average_by_index(self._altitude_m, sequences_index)
            if not isinstance(self._altitude_m, type(None))
            else None
        )
        self._acceleration_ms2 = (
            self.average_by_index(self._acceleration_ms2, sequences_index)
            if not isinstance(self._acceleration_ms2, type(None))
            else None
        )
        self._line_wgs = LineString(np.column_stack(tup=(self._longitude, self._latitude)))
        self._line_utm = LineString(np.column_stack(tup=(self._x, self._y)))

    def boundary_string(self, r: float = 100.0) -> str:
        """Computes a boundary with radius 'r' around the gnss series and returns a string of WGS84 coordinates which can be used as input when querying with filter 'BOUNDARY' (see RailDataImport).

        Parameters
        ----------
        r: float
            The radius of the boundary, in meter. Default: 100.

        Returns
        -------
        coord_string: str
            String of WGS84 coordinates representing the boundary.
        """

        buffer = self.line_utm.buffer(r)  # compute buffer
        x, y = buffer.exterior.xy  # get coordinate arrays
        coord_string = ''.join([f'{x} {y} ' for x, y in zip(x, y)])  # create string
        return coord_string

    def notnone(self, value) -> bool:
        if not isinstance(value, type(None)):
            return True
        else:
            return False

    def _check_input(
        self,
        time_utc: list[datetime.datetime] | np.ndarray | None,
        time_s: list[float] | np.ndarray | None,
        latitude: list[float] | np.ndarray,  # in WGS84!
        longitude: list[float] | np.ndarray,  # in WGS84!
        altitude_m: list[float] | np.ndarray | None = None,
        velocity_ms: list[float] | np.ndarray | None = None,
        acceleration_ms2: list[float] | np.ndarray | None = None,
    ):
        if self.notnone(time_utc) and self.notnone(time_s):
            time = time_utc
        elif self.notnone(time_utc):
            time = time_utc
        elif self.notnone(time_s):
            time = time_s
        else:
            raise ValueError("Either 'time_utc' or 'time_s' must be given. Both are None")

        if len(time) == 0:
            raise ValueError("Input list with zero length.")

        # check input length
        arrays_equal_length = len(time) == len(latitude) == len(longitude)
        if not isinstance(altitude_m, type(None)):
            arrays_equal_length = arrays_equal_length and (len(time) == len(altitude_m))
        if not isinstance(velocity_ms, type(None)):
            arrays_equal_length = arrays_equal_length and (len(time) == len(velocity_ms))
        if not isinstance(acceleration_ms2, type(None)):
            arrays_equal_length = arrays_equal_length and (len(time) == len(acceleration_ms2))
        if not arrays_equal_length:
            raise ValueError(f"All input parameters must have the same length.")

        # check time
        if not isinstance(time, (list, np.ndarray)):
            raise TypeError(
                f"Parameter 'time' must be of type <list> or <numpy.ndarray>. Passed type was {type(time)}."
            )

        else:
            if not all([isinstance(val, np.datetime64) or isinstance(val, float) for val in time]):
                raise TypeError(
                    "All elements in 'time_utc' must be of type <numpy.datetime64>, all elements in 'time_s' must be of type float."
                )

        # check latitude
        if not isinstance(latitude, (list, np.ndarray)):
            raise TypeError(
                f"Parameter 'latitude' must be of type <list> or <numpy.ndarray>. Passed type was {type(latitude)}."
            )

        else:
            if not all([isinstance(val, FLOAT_TYPES) for val in latitude]):  # type: ignore
                raise TypeError("All elements in 'latitude' must be of type <float>.")

        # check longitude
        if not isinstance(longitude, (list, np.ndarray)):
            raise TypeError(
                f"Parameter 'longitude' must be of type <list> or <numpy.ndarray>. Passed type was {type(longitude)}."
            )

        else:
            if not all([isinstance(val, FLOAT_TYPES) for val in longitude]):  # type: ignore
                raise TypeError("All elements in 'longitude' must be of type <float>.")

        # check altitude
        if not isinstance(altitude_m, type(None)):
            if not isinstance(altitude_m, (list, np.ndarray)):
                raise TypeError(
                    f"Parameter 'altitude' must be of type <list> or <numpy.ndarray>. Passed type was {type(altitude_m)}."
                )

            else:
                if not all([isinstance(val, FLOAT_TYPES) for val in altitude_m]):  # type: ignore
                    raise TypeError("All elements in 'altitude' must be of type <float>.")

        # check velocity_ms
        if not isinstance(velocity_ms, type(None)):
            if not isinstance(velocity_ms, (list, np.ndarray)):
                raise TypeError(
                    f"Parameter 'velocity_ms' must be of type <list> or <numpy.ndarray>. Passed type was {type(velocity_ms)}."
                )

            else:
                if not all([isinstance(val, FLOAT_TYPES) for val in velocity_ms]):  # type: ignore
                    raise TypeError("All elements in 'velocity_ms' must be of type <float>.")

        # check acceleration_ms2
        if not isinstance(acceleration_ms2, type(None)):
            if not isinstance(acceleration_ms2, (list, np.ndarray)):
                raise TypeError(
                    f"Parameter 'acceleration_ms2' must be of type <list> or <numpy.ndarray>. Passed type was {type(acceleration_ms2)}."
                )

            else:
                if not all([isinstance(val, FLOAT_TYPES) for val in acceleration_ms2]):  # type: ignore
                    raise TypeError("All elements in 'acceleration_ms2' must be of type <float>.")
