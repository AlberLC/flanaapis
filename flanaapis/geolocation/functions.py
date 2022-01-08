from typing import AsyncIterator

from flanaapis.exceptions import PlaceNotFoundError
from flanaapis.geolocation import google_maps, open_street_map
from flanaapis.geolocation.models import Place


async def find_place(place_name: str) -> Place | None:
    return await google_maps.find_place(place_name) or await open_street_map.find_place(place_name)


async def find_place_showing_progress(place_name: str) -> AsyncIterator[str | Place | None]:
    async for result in google_maps.find_place_showing_progress(place_name):
        if result is None:
            break
        yield result
    else:
        return

    yield 'Google maps no ha encontrado nada. Buscando en openstreetmap.org...'
    yield await open_street_map.find_place(place_name)


async def parse_place_arguments(latitude: float, longitude: float = None) -> tuple[float, float]:
    match latitude, longitude:
        case Place() as place, _:
            latitude = place.latitude
            longitude = place.longitude
        case str(place_name), _ if place := await find_place(place_name):
            latitude = place.latitude
            longitude = place.longitude
        case str(), _:
            raise PlaceNotFoundError

    return latitude, longitude
