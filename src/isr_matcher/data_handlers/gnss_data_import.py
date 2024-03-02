from pathlib import Path
from typing import Literal, Union, Tuple
import numpy as np
import pandas as pd
from isr_matcher.geometry.gnss_series import GNSSSeries
from datetime import datetime


class GNSSDataImport:

    """
    Class that manages the import of GPS data.

    Attributes
    ----------
    TODO

    """

    def __init__(self):
        self.column_names_obligatory = [['time_utc', 'time_s'], 'latitude', 'longitude']
        self.column_names_optional = ['altitude_m', 'velocity_ms', 'acceleration_ms2']

    def read_csv(
        self,
        csv_path: Path | str,
        column_name_dict: dict | None,
        delimiter: str = ',',
        decimal: str = '.',
        na_values: list[str] | None = None,
        skiprows: int = 0,
    ):
        """
        "time_utc": "time_utc",
        "time_s": "measured_time_1_in_s",
        "latitude": "latitude",
        "longitude": "longitude",
        "altitude_m": None,
        "velocity_ms": "speed_ms",
        "acceleration_ms2": None,
        """

        # assert input
        if not isinstance(column_name_dict, type(None)):
            if column_name_dict['time_s'] and column_name_dict['time_utc']:
                # both times
                parse_dates = [column_name_dict['time_utc']]

            elif column_name_dict['time_s']:
                # no utc time
                parse_dates = False

            elif column_name_dict['time_utc']:
                # compute time in seconds
                parse_dates = [column_name_dict['time_utc']]
                time_s = None
            else:
                raise ValueError(
                    "Both 'time_utc' and 'time_s' in column_name_dict are None. At least one must be specified: The csv file must contain at least one time column. Please set the corresponding column name in column_name_dict."
                )
        else:
            parse_dates = ['time_utc']

        try:
            # read
            df = pd.read_csv(
                csv_path,
                delimiter=delimiter,
                decimal=decimal,
                parse_dates=parse_dates,
                na_values=na_values,
                skiprows=skiprows,
            )

        except:
            # read
            df = pd.read_csv(
                csv_path,
                delimiter=delimiter,
                decimal=decimal,
                parse_dates=False,
                na_values=na_values,
                skiprows=skiprows,
            )

        for column in self.column_names_obligatory:
            if isinstance(column, list):
                assert (
                    column[0] in df.columns or column[1] in df.columns
                ), 'One time column is missing in csv file or has wrong name. Please check the file or the column_name_dict parameter.'
            else:
                assert (
                    column in df.columns
                ), f'Column {column} is missing in csv file or incorrectly mapped with parameter column_name_dict.'

        if not isinstance(column_name_dict, type(None)):
            # parse
            column_names_dict = {
                val: key for (key, val) in zip(column_name_dict.keys(), column_name_dict.values()) if val
            }
            column_names = [val for val in column_name_dict.values() if val]
            column_names_dict = {
                val: key for (key, val) in zip(column_name_dict.keys(), column_name_dict.values()) if val
            }

            # rename to standardized column names
            df = df[column_names]
            df = df.rename(columns=column_names_dict)

        # average over identical positions
        aggregate = []
        for column in df.columns:
            aggregate.append((column, np.mean))
        df = df.groupby(['latitude', 'longitude'], sort=False).agg('mean').reset_index()

        # extract values
        time_utc = df['time_utc'].to_numpy() if 'time_utc' in df.columns else None
        time_s = df['time_s'].to_numpy() if 'time_s' in df.columns else None
        altitude_m = df['altitude_m'].to_numpy() if 'altitude_m' in df.columns else None
        velocity_ms = df['velocity_ms'].to_numpy() if 'velocity_ms' in df.columns else None
        acceleration_ms2 = df['acceleration_ms2'].to_numpy() if 'acceleration_ms2' in df.columns else None

        # return instance
        return GNSSSeries(
            time_utc=time_utc,
            time_s=time_s,
            latitude=df['latitude'].to_numpy(),
            longitude=df['longitude'].to_numpy(),
            altitude_m=altitude_m,
            velocity_ms=velocity_ms,
            acceleration_ms2=acceleration_ms2,
        )
