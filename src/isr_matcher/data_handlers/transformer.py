import pyproj
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform
from typing import Literal, TypeVar

# Type T: only instances of class BaseGeometry or subclasses (Point, Linestring, etc.)
T = TypeVar("T", bound="BaseGeometry")


class Transformer:
    """TODO"""

    def __init__(self, source_cs: str, target_cs: str):
        """TODO"""
        # check if cs exist
        # TODO

        # store coordinate system names
        self._source = source_cs
        self._target = target_cs

        # define projection from source to target
        self._projection_from_source_to_target = pyproj.Transformer.from_proj(
            pyproj.Proj(source_cs), pyproj.Proj(target_cs)
        ).transform

        # define projection from target to source
        self._projection_from_target_to_source = pyproj.Transformer.from_proj(
            pyproj.Proj(target_cs), pyproj.Proj(source_cs)
        ).transform

    # define attributes as read-only
    @property
    def projection_from_source_to_target(self):
        return self._projection_from_source_to_target

    @property
    def projection_from_target_to_source(self):
        return self._projection_from_target_to_source

    @property
    def source(self):
        return self._source

    @property
    def target(self):
        return self._target

    def transform(self, projection: Literal["source_to_target", "target_to_source"], object: T) -> T:
        """Transforms a shapely.Geometry object from a source coordinate system to a target coordinate system.

        Parameters
        ----------
        projection: Literal["source_to_target", "target_to_source"]
            Defines whether to transform from source coordinate system to target coordinate system or the other way around.
        object: BaseGeometry
            The object to transform. The type of object must be a subclass of shapely.Geometry, e.g Point, LineString, MultiLineString, etc.

        Returns
        -------
        object: BaseGeometry
            A new instance of the same object class with transformed coordinates.

        Note
        ----
        Consider order of axes when transforming. For WGS84, axes order is (latitude, longitude).
        """

        # check type of object
        if not issubclass(type(object), BaseGeometry):
            raise ValueError(
                f"Unknown type of object: {type(object)}. Object must be a subclass of shapely.Geometry, e.g. Point, LineString, MulitLineString, etc."
            )

        if projection == "source_to_target":
            # project from source to target cs
            transformed_object = transform(self.projection_from_source_to_target, object)

        elif projection == "target_to_source":
            # project from target to source cs
            transformed_object = transform(self.projection_from_target_to_source, object)

        else:
            # raise error: unknown projection
            raise ValueError(
                f"Unkown projection: {projection}. Possible values are 'source_to_target' and 'target_to_source'."
            )

        return transformed_object
