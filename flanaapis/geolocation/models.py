from __future__ import annotations  # todo0 remove in 3.11

from dataclasses import dataclass

import flanautils
from flanautils.models.bases import FlanaBase


@dataclass(unsafe_hash=True)
class Place(FlanaBase):
    """Simple class for manage Place data."""

    name: str
    latitude: float
    longitude: float

    def __init__(self, name: str, latitude: float, longitude: float):
        self.name = ', '.join(flanautils.data_structures.ordered_set.OrderedSet(name.split(', ')))
        self.latitude = float(latitude)
        self.longitude = float(longitude)

    def distance_to(self, place: Place) -> float:
        """Calculate the distance between two places."""

        return ((place.latitude - self.latitude) ** 2 + (place.longitude - self.longitude) ** 2) ** (1 / 2)
