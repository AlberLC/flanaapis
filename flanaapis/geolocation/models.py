from __future__ import annotations  # todo0 remove when it's by default

from flanautils import FlanaBase, OrderedSet


class Place(FlanaBase):
    """Simple class for manage Place data."""

    def __init__(
        self,
        name: str = None,
        latitude: float = None,
        longitude: float = None,
        country: str = None,
        country_code: str = None,
        state: str = None,
        state_district: str = None,
        province: str = None,
        county: str = None,
        city: str = None,
        town: str = None,
        borough: str = None,
        postcode: str = None,
        neighbourhood: str = None,
        road: str = None,
        number: str = None,
        amenity: str = None
    ):
        self._name = ', '.join(OrderedSet(name.split(', '))) if name else name
        self.latitude = float(latitude) if latitude else latitude
        self.longitude = float(longitude) if longitude else longitude
        self.country = country
        self.country_code = country_code
        self.state = state
        self.state_district = state_district
        self.province = province
        self.county = county
        self.city = city
        self.town = town
        self.borough = borough
        self.postcode = postcode
        self.neighbourhood = neighbourhood
        self.road = road
        self.number = number
        self.amenity = amenity

    def __str__(self):
        return self.name

    @property
    def name(self):
        address_parts = [address_part.strip() if len(address_part) <= 10 else f'{address_part[:10].strip()}...' for address_part in (self.town, self.city, self.county, self.state, self.country) if address_part]
        return ', '.join(address_parts) if address_parts else self._name

    def distance_to(self, place: Place) -> float:
        """Calculate the distance between two places."""

        return ((place.latitude - self.latitude) ** 2 + (place.longitude - self.longitude) ** 2) ** (1 / 2)
