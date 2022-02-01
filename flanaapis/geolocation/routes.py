from fastapi import APIRouter
from pydantic import BaseModel

from flanaapis.geolocation import functions, open_street_map

router = APIRouter()


class PlaceOutput(BaseModel):
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


@router.get("/place", response_model=PlaceOutput, response_model_exclude_defaults=True, response_model_exclude_unset=True)
async def find_place(query: str, near_to_latitude: float = None, near_to_longitude: float = None, fast: bool = False):
    match near_to_latitude, near_to_longitude:
        case [float(), _] | [_, float()]:
            return (await open_street_map.find_place(query, near_to_latitude, near_to_longitude)).to_dict()
        case _ if fast:
            return (await open_street_map.find_place(query, near_to_latitude, near_to_longitude)).to_dict()
        case _:
            return (await functions.find_place(query)).to_dict()


# noinspection PyUnusedLocal
@router.get("/places", response_model=list[PlaceOutput], response_model_exclude_defaults=True, response_model_exclude_unset=True)
async def find_places(query: str, fast: bool = False):
    return [place.to_dict() for place in await open_street_map.find_places(query)]


@router.get("/timezone")
async def find_places(query: str, fast: bool = False):
    return await functions.find_timezone(query, fast) or {}
