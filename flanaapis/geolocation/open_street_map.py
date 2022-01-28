from typing import overload

import flanautils

from flanaapis.geolocation.models import Place


@overload
async def find_place(place_query: str, near_to_place: Place = None) -> Place | None:
    pass


@overload
async def find_place(place_query: str, near_to_latitude: float = None, near_to_longitude: float = None) -> Place | None:
    pass


async def find_place(place_query: str, near_to_latitude: float = None, near_to_longitude: float = None) -> Place | None:
    match near_to_latitude, near_to_longitude:
        case Place() as center_place, _:
            pass
        case int() | float(), int() | float():
            center_place = Place('', near_to_latitude, near_to_longitude)
        case _:
            center_place = None

    if center_place:
        nearest_place = None
        shortest_distance = float('inf')
        for place in await find_places(place_query):
            if (distance := place.distance_to(center_place)) < shortest_distance:
                shortest_distance = distance
                nearest_place = place

        if nearest_place:
            return nearest_place
    else:
        return next(iter(await find_places(place_query)), None)


async def find_places(place_query: str) -> list[Place]:
    places_data: list[dict] = await flanautils.get_request(f'https://nominatim.openstreetmap.org/search',
                                                           {'q': place_query,
                                                            'format': 'jsonv2',
                                                            'accept-language': 'es-ES,es,en',
                                                            'addressdetails': True})

    places = []
    for place_data in places_data:
        place = Place(place_data.get('display_name'), place_data.get('lat'), place_data.get('lon'))

        if 'address' in place_data:
            place.country = place_data['address'].get('country')
            place.country_code = place_data['address'].get('country_code')
            place.state = place_data['address'].get('state')
            place.state_district = place_data['address'].get('state_district')
            place.county = place_data['address'].get('county')
            place.city = place_data['address'].get('city')
            place.borough = place_data['address'].get('borough')
            place.postcode = place_data['address'].get('postcode')
            place.neighbourhood = place_data['address'].get('neighbourhood')
            place.road = place_data['address'].get('road')
            place.number = place_data['address'].get('house_number')
            place.amenity = place_data['address'].get('amenity')

        places.append(place)

    return places
