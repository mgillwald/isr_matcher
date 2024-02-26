from __future__ import annotations
from shapely import Point
from typing import Literal, Tuple, Union, TypeVar
from isr_matcher.data_handlers.transformer import Transformer
from shapely.geometry.base import BaseGeometry

# Type T: only instances of class BaseGeometry or subclasses (Point, Linestring, etc.)
T = TypeVar("T", bound="BaseGeometry")


class OperationalPoint(Point):
    _id_to_attrs = {}
    __slots__ = Point.__slots__  # slots must be the same for assigning __class__ - https://stackoverflow.com/a/52140968

    def __init__(self, coords_epsg31467: Tuple[float, float], properties: dict, properties_info: dict):
        self._id_to_attrs[id(self)] = dict(properties=properties, properties_info=properties_info)

    def __new__(cls, coords_epsg31467: Tuple[float, float], properties: dict, properties_info: dict):
        point = super().__new__(cls, coords_epsg31467)
        point.__class__ = cls

        return point

    # getters
    @property
    def element_type(self) -> str:
        return 'OperationalPoint'

    @property
    def ID(self) -> int:
        # ID of operational point in ISR
        return self._id_to_attrs[id(self)]['properties']['ID']

    @property
    def name(self) -> str:
        # name of operational point
        return self._id_to_attrs[id(self)]['properties']['BST_STELLE_NAME']

    @property
    def rl100(self) -> str:
        # abbreviation in terms of Richtlinie 100 (DB)
        if self._id_to_attrs[id(self)]['properties']['BST_STELLENART'] == 'Stub':
            return self._id_to_attrs[id(self)]['properties']['REF_RL100'] + ' (ref)'
        else:
            return self._id_to_attrs[id(self)]['properties']['BST_RL100']

    @property
    def point_type(self) -> str:
        # type of operational point
        return self._id_to_attrs[id(self)]['properties']['BST_STELLENART']

    @property
    def track_list(self) -> list[int]:
        # tracks associated with operational point
        if self._id_to_attrs[id(self)]['properties']['BST_STELLENART'] == 'Stub':
            return [
                self._id_to_attrs[id(self)]['properties']['STRECKE1'],
                self._id_to_attrs[id(self)]['properties']['STRECKE2'],
            ]
        else:
            return [self._id_to_attrs[id(self)]['properties']['STRNR']]

    @property
    def km(self) -> Union[float, None]:
        # kilometrage at operational point
        if self._id_to_attrs[id(self)]['properties']['BST_STELLENART'] == 'Stub':
            # track junctions do not have explicit km info
            return None
        else:
            # km belongs to track number
            return self._id_to_attrs[id(self)]['properties']['LAGE_KM_V']

    @property
    def coords_wgs84(self) -> Tuple[float, float]:
        # coordinates in reference system epsg:4326 / wgs84
        if self._id_to_attrs[id(self)]['properties']['BST_STELLENART'] == 'Stub':
            transformer = Transformer(source_cs='epsg:31467', target_cs='epsg:4326')
            point_epsg4326 = transformer.transform('source_to_target', Point([self.y, self.x]))
            return [point_epsg4326.x, point_epsg4326.y]
        else:
            lon_lat = self._id_to_attrs[id(self)]['properties']['ALG_GEO_LAGE']
            return [lon_lat[1], lon_lat[0]]

    @property
    def properties(self) -> dict:
        return self._id_to_attrs[id(self)]['properties']

    @property
    def properties_info(self) -> dict:
        return self._id_to_attrs[id(self)]['properties_info']

    # Pickling support
    def __reduce__(self):
        return (
            self.__class__,
            (
                tuple(self.coords),
                self._id_to_attrs[id(self)]['properties'],
                self._id_to_attrs[id(self)]['properties_info'],
            ),
        )
