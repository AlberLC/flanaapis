from __future__ import annotations  # todo0 remove in 3.11

from dataclasses import dataclass

import flanautils
from flanautils.models.bases import FlanaBase


@dataclass(unsafe_hash=True)
class Place(FlanaBase):
    """Simple class for manage Place data."""

    name: str = None
    latitude: float = None
    longitude: float = None
    country: str = None
    country_code: str = None
    state: str = None
    state_district: str = None
    county: str = None
    city: str = None
    borough: str = None
    postcode: str = None
    neighbourhood: str = None
    road: str = None
    number: str = None
    amenity: str = None

    def __post_init__(self):
        if self.name:
            self.name = ', '.join(flanautils.data_structures.ordered_set.OrderedSet(self.name.split(', ')))
        if self.latitude:
            self.latitude = float(self.latitude)
        if self.longitude:
            self.longitude = float(self.longitude)

    def __str__(self):
        address_parts = [address_part for address_part in (self.city, self.state_district, self.state, self.country) if address_part]
        return ', '.join(address_parts) if address_parts else self.name

    def distance_to(self, place: Place) -> float:
        """Calculate the distance between two places."""

        return ((place.latitude - self.latitude) ** 2 + (place.longitude - self.longitude) ** 2) ** (1 / 2)
