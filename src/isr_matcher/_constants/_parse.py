# Script that contains functions for converting strings from json response (see utils._ISR_PROPERTIES).

from typing import Any, Tuple, Union, overload
import numpy as np
from dataclasses import dataclass
from isr_matcher._constants._filters import ISR_EXCEPTIONAL_STATION_NAMES

# data classes used for type hints


@dataclass
class dtype:
    dtype: Any


# tuple collection of integer and float types

INT_TYPES = (int, np.integer, np.int16, np.int32, np.int64)
FLOAT_TYPES = (int, np.integer, np.int16, np.int32, np.int64, float, np.float16, np.float32, np.float64)


# conversion functions


def identity(obj: Any) -> Any:
    """Returns the input."""
    return obj


def str_to_int(string: str) -> int:
    """Converts input string to integer."""
    return int(string)


@overload
def str_to_float(string: str) -> float:
    ...


@overload
def str_to_float(string: None) -> None:
    ...


def str_to_float(string: Union[str, None]) -> Union[float, None]:
    # TODO: refactor this function
    """Converts input string from ISR properties to float."""
    try:
        to_replace = ['Bremsweg', 'A', 'm', '(ET 420)']
        for replace in to_replace:
            string = string.replace(replace, '')
        return float(string.strip().replace(',', '.').replace(' ', ''))
    except:
        return string


def incline_to_array(string: str) -> np.ndarray:
    """Converts string with inclination profile to numpy array."""
    # TODO
    return string


def db_km_to_km(string: str) -> float:
    """Converts string with kilometrage from db format to km."""
    if '|' in string:
        string, overlength = string.split(' | ')
        overlength = float(overlength.replace('+', ''))
    else:
        overlength = 0
    km, m = string.split('+')
    if overlength:
        m = float(m)
        m += overlength
    return float(km.replace(',', '.')) + float(m) / 1000.0


def km_to_db_km(value: float) -> str:
    """Converts kilometer values to db format."""
    km = round(int(value * 10) / 10, 1)
    m = round(int(value * 10000) / 10000 - km, 3) * 1000
    return f'{km}'.replace('.', ',') + f' + {int(m)}'


def db_km_alt_to_km(number: int | str) -> float:
    """Converts string with kilometrage from alternative db format to km."""
    if isinstance(number, str):
        number = int(number)
    km = round((number - 1e8) / 1e5, 1)
    m = round(number - 1e8 - km * 1e5)
    return km + m / 1000


def str_to_lat_lon(string: str) -> Tuple[float, float]:
    """Converts string to latitude and longitude coordinate."""
    if 'auf Anfrage' in string:
        return (-1.0, -1.0)
    elif '+,' in string:
        return (-1.0, -1.0)
    else:
        lat_string, lon_string = string.replace('+', '').split(',')
    return (float(lat_string), float(lon_string))


def extract_station_names(
    track_name_string: str, split_only: bool = False, is_op_name: bool = False
) -> Tuple[str, str] | str:
    """TODO"""

    exceptional_names = ISR_EXCEPTIONAL_STATION_NAMES

    exceptional_name_list = [name for name in exceptional_names if name in track_name_string]

    if split_only:
        if len(exceptional_name_list) > 0:
            d = {}
            for i, exceptional_name in enumerate(exceptional_name_list):
                d[str((i + 1) * 10000)] = exceptional_name
                track_name_string = track_name_string.replace(exceptional_name, str((i + 1) * 10000))
            from_name, to_name = track_name_string.split(' - ')
            for i in range(len(exceptional_name_list)):
                from_name = from_name.replace(str((i + 1) * 10000), d[str((i + 1) * 10000)])
                to_name = to_name.replace(str((i + 1) * 10000), d[str((i + 1) * 10000)])
        else:
            from_name, to_name = track_name_string.split(' - ')

    else:
        if len(exceptional_name_list) > 0:
            for exceptional_name in exceptional_name_list:
                # 1
                if ' - ' in exceptional_name:
                    wild_card_name = exceptional_name.replace(' - ', '*').replace('-', '*')
                else:
                    wild_card_name = None

                # 2
                if '   ' in exceptional_name:
                    if wild_card_name:
                        name_split = wild_card_name.split('   ')
                    else:
                        name_split = exceptional_name.split('   ')
                    station_base_name = name_split[0]
                    additional_name = name_split[-1].strip()
                    wild_card_name = '*' + station_base_name + '*' + additional_name + '*'
                else:
                    wild_card_name = '*' + exceptional_name.replace('  ', ' ').replace(' ', '*') + '*'

                # 3
                if 'ß' in wild_card_name:
                    wild_card_name = wild_card_name.replace('ß', '*')

                track_name_string = track_name_string.replace(exceptional_name, wild_card_name)

                if is_op_name == True:
                    return track_name_string

        from_name, to_name = track_name_string.split(' - ')

    return from_name, to_name
