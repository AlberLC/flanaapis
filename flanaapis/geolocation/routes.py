from fastapi import APIRouter

from flanaapis.geolocation import functions, open_street_map

router = APIRouter()


@router.get("/place")
async def find_place(name: str, near_to_latitude: float = None, near_to_longitude: float = None):
    match near_to_latitude, near_to_longitude:
        case [float(), _] | [_, float()]:
            return (await open_street_map.find_place(name, near_to_latitude, near_to_longitude)).to_dict()
        case _:
            return (await functions.find_place(name)).to_dict()


@router.get("/places")
async def find_places(name: str):
    return [place.to_dict() for place in await open_street_map.find_places(name)]
