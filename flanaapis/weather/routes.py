from fastapi import APIRouter

from flanaapis.weather import functions

router = APIRouter()


@router.get("/weather")
async def weather(latitude: float, longitude: float):
    current_weather, day_weathers = await functions.get_day_weathers_by_place(latitude, longitude)

    for i, day_weather in enumerate(day_weathers):
        for j, instant_weather in enumerate(day_weather.instant_weathers):
            day_weather.instant_weathers[j] = instant_weather.to_dict()
        day_weathers[i] = day_weather.to_dict()

    return {
        'current_weather': current_weather.to_dict(),
        'day_weathers': day_weathers
    }
