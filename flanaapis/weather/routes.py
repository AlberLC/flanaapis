from fastapi import APIRouter

from flanaapis.weather import functions

router = APIRouter()


@router.get("/weather", response_model=dict, response_model_exclude_defaults=True, response_model_exclude_unset=True)
async def weather(latitude: float, longitude: float):
    instant_weather, day_weathers = await functions.get_day_weathers_by_place(latitude, longitude)

    return {
        'current_weather': instant_weather.to_dict(),
        'day_weathers': [day_weather.to_dict() for day_weather in day_weathers]
    }
