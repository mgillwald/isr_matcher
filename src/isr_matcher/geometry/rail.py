from __future__ import annotations
from shapely import LineString, Point
from typing import Tuple, Annotated, TYPE_CHECKING
from isr_matcher.data_handlers.transformer import Transformer

# from numpy.typing import ArrayLike
# from pyrailmapping._constants._properties import ISR_PROPERTIES_TRACK_SEGMENTS
# from pyrailmapping._constants._parse import dtype
# import numpy as np

# false at run time (for type hint only)
# if TYPE_CHECKING:
#    from pyrailmapping.geometry.operational_point import OperationalPoint
#    from pyrailmapping.geometry.track_segment import TrackSegment


class Rail(LineString):
    """Represents a rail. Inherits from LineString so shapely functions can be used on instances directly.

    Attributes
    ----------
    _id_to_attrs : dict
        Dictionary mapping ID to attributes.
    __slots__ : tuple
        Slots for assigning __class__.
    """

    _id_to_attrs = {}
    __slots__ = (
        LineString.__slots__
    )  # slots must be the same for assigning __class__ - https://stackoverflow.com/a/52140968

    def __init__(
        self, coords: Tuple[float, float], lines_c: list, layout: dict, name: str, track: int, index: int | None = None
    ):
        """Initializes a Rail object.

        Parameters
        ----------
        coords : Tuple[float, float]
            Coordinates of the rail.
        lines_c : list
            List of lines.
        layout : dict
            Dictionary containing layout information.
        name : str
            Name of the rail.
        track : int
            Track number.
        index : int, optional
            Index of the rail, by default None
        """
        # get lines in direction from track segment
        lines = [LineString(coords) for coords in lines_c]
        lines_1 = [lines[i] for i in range(len(lines)) if i in layout['direction_1_rails']]
        lines_2 = [lines[i] for i in range(len(lines)) if i in layout['direction_2_rails']]

        # determine direction for rail
        line = LineString(coords)
        if line in lines_1 and line in lines_2:  # monorails (could be directed but treated as bi-directional)
            direction = 0
        elif line in lines_1:
            direction = 1
        elif line in lines_2:
            direction = 2
        else:  # sidings (could be directed but treated as bi-directional)
            direction = 0

        self._id_to_attrs[id(self)] = dict(
            lines=lines, layout=layout, name=name, direction=direction, track=track, index=index
        )

    def __new__(
        cls, coords: Tuple[float, float], lines_c: list, layout: dict, name: str, track: int, index: int | None = None
    ) -> Rail:
        """Creates a new instance of Rail.

        Parameters
        ----------
        coords : Tuple[float, float]
            Coordinates of the rail.
        lines_c : list
            List of lines.
        layout : dict
            Dictionary containing layout information.
        name : str
            Name of the rail.
        track : int
            Track number.
        index : int, optional
            Index of the rail, by default None

        Returns
        -------
        Rail
            A new instance of Rail.
        """
        line_string = super().__new__(cls, coords)
        line_string.__class__ = cls
        return line_string

    @property
    def index(self) -> int | None:
        """Returns index."""
        return self._id_to_attrs[id(self)]['index']

    @index.setter
    def index(self, value: int | None):
        """Sets index of rail."""
        self._id_to_attrs[id(self)]['index'] = value

    @property
    def direction(self) -> int:
        """Returns direction of rail."""
        return self._id_to_attrs[id(self)]['direction']

    @direction.setter
    def direction(self, value: int):
        """Sets direction for rail."""
        self._id_to_attrs[id(self)]['direction'] = value

    @property
    def track(self) -> str:
        """Returns track number the rail belongs to."""
        return self._id_to_attrs[id(self)]['track']

    @track.setter
    def track(self, value: int):
        """Sets the track number."""
        self._id_to_attrs[id(self)]['track'] = value

    @property
    def track_segment_name(self) -> str:
        """Returns name of track segment the rail belongs to."""
        return self._id_to_attrs[id(self)]['name']

    @track_segment_name.setter
    def track_segment_name(self, value: str):
        """Sets the track segment name."""
        self._id_to_attrs[id(self)]['name'] = value

    @property
    def layout(self) -> dict:
        """Returns layout of the track segmetn the rail belongs to."""
        return self._id_to_attrs[id(self)]['layout']

    @layout.setter
    def layout(self, value: dict):
        """Sets the track segment layout."""
        self._id_to_attrs[id(self)]['layout'] = value

    @property
    def lines(self) -> list[LineString]:
        """Returns the all rails of the track segment the line belongs to."""
        return self._id_to_attrs[id(self)]['lines']

    @lines.setter
    def lines(self, value: list):
        """Sets the track segment line coordinates."""
        self._id_to_attrs[id(self)]['lines'] = value

    @property
    def coords_wgs(self) -> list[Point]:
        transformer = Transformer(source_cs='epsg:31467', target_cs='epsg:4326')
        points_wgs = []
        for coord_utm in self.coords[:]:
            coord_wgs = transformer.transform('source_to_target', Point([coord_utm[1], coord_utm[0]]))
            points_wgs.append(Point(coord_wgs))
        return points_wgs

    @classmethod
    def from_linestring_and_rail(cls, rail: Rail, line_string: LineString) -> Rail:
        """Creates a new rail instance with coordinates from 'line_string' and all other attributes copied from 'rail'.

        Parameters
        ----------
        other: Rail
            An instance of class Rail whose attributes will be copied to self.
        """
        new_rail = cls(
            coords=line_string.coords,  # type: ignore
            lines_c=rail.lines,
            layout=rail.layout,
            name=rail.track_segment_name,
            track=int(rail.track),
            index=rail.index,
        )

        new_rail.direction = rail.direction

        return new_rail

    # Pickling support
    def __reduce__(self):
        return (
            self.__class__,
            (
                tuple(self.coords),
                [line.coords for line in self.lines],
                self._id_to_attrs[id(self)]['layout'],
                self._id_to_attrs[id(self)]['name'],
                self._id_to_attrs[id(self)]['track'],
                self._id_to_attrs[id(self)]['index'],
            ),
        )
