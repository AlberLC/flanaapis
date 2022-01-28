import os
from typing import AsyncIterator, overload

import flanautils

from flanaapis.exceptions import PlaceNotFoundError
from flanaapis.geolocation import google_maps, open_street_map
from flanaapis.geolocation.models import Place

TIMEZONE_API_KEY = os.environ['TIMEZONEDB_API_KEY']
TIMEZONE_BASE_ENDPOINT = 'https://api.timezonedb.com/v2.1/get-time-zone'


@overload
async def ensure_coordinates(place_query: str, fast: bool = False) -> tuple[float, float]:
    pass


@overload
async def ensure_coordinates(latitude: float, longitude: float = None, fast: bool = False) -> tuple[float, float]:
    pass


async def ensure_coordinates(latitude: float | str, longitude: float = None, fast: bool = False) -> tuple[float, float]:
    match latitude, longitude:
        case Place() as place, _:
            latitude = place.latitude
            longitude = place.longitude
        case str(), _ if coordinates := flanautils.find_coordinates(latitude):
            latitude, longitude = coordinates
        case str(place_query), _ if place := await find_place(place_query, fast):
            latitude = place.latitude
            longitude = place.longitude
        case str(), _:
            raise PlaceNotFoundError

    return latitude, longitude


@overload
async def get_timezone_data(place_query: str, fast: bool = False) -> dict | None:
    pass


@overload
async def get_timezone_data(latitude: float, longitude: float = None, fast: bool = False) -> dict | None:
    pass


async def get_timezone_data(latitude: float | str, longitude: float = None, fast: bool = False) -> dict | None:
    latitude, longitude = await ensure_coordinates(latitude, longitude, fast)
    parameters = {
        'key': TIMEZONE_API_KEY,
        'format': 'json',
        'by': 'position',
        'lat': latitude,
        'lng': longitude
    }
    timezone_data = await flanautils.get_request(TIMEZONE_BASE_ENDPOINT, params=parameters)

    if timezone_data['status'] == 'OK':
        return timezone_data


async def find_place(place_query: str, fast: bool = False) -> Place | None:
    if not fast and (partial_place := await google_maps.find_place(place_query)):
        return await open_street_map.find_place(f'{partial_place.latitude}, {partial_place.longitude}')
    else:
        return await open_street_map.find_place(place_query)


async def find_place_showing_progress(place_query: str) -> AsyncIterator[str | Place | None]:
    async for result in google_maps.find_place_showing_progress(place_query):
        if result is None:
            break
        yield result
    else:
        return

    yield 'Google maps no ha encontrado nada. Buscando en openstreetmap.org...'
    yield await open_street_map.find_place(place_query)
