from typing import Iterator, overload

import flanautils

from flanaapis.geolocation.models import Place


@overload
async def find_place(place_name: str, near_to_place: Place = None) -> Place | None:
    pass


@overload
async def find_place(place_name: str, near_to_latitude: float = None, near_to_longitude: float = None) -> Place | None:
    pass


async def find_place(place_name: str, near_to_latitude: float = None, near_to_longitude: float = None) -> Place | None:
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
        for place in await find_places(place_name):
            if (distance := place.distance_to(center_place)) < shortest_distance:
                shortest_distance = distance
                nearest_place = place

        if nearest_place:
            return nearest_place
    else:
        return next(await find_places(place_name), None)


async def find_places(place_name: str) -> Iterator[Place]:
    places_data: list[dict] = await flanautils.get_request(f'https://nominatim.openstreetmap.org/search.php',
                                                           {'q': place_name,
                                                            'format': 'jsonv2',
                                                            'accept-language': 'es-ES,es,en'}
                                                           )
    return (Place(place_data['display_name'], place_data['lat'], place_data['lon']) for place_data in places_data)
