from __future__ import annotations
from typing import TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from isr_matcher.geometry.track_segment import TrackSegment
    from isr_matcher.geometry.operational_point import OperationalPoint
    from isr_matcher.geometry.rail import Rail


# TypedDict
class Map(TypedDict):
    """TypedDict for type hinting"""

    track_segments: list[TrackSegment]  # list of all track segments in map
    operational_points: list[OperationalPoint]  # list of all operational points in map
    rails: list[Rail]  # list of all rails in map
    track_transitions: list[OperationalPoint]
