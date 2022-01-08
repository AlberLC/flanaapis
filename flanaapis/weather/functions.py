import datetime
from typing import overload

import flanautils

from flanaapis.geolocation import functions
from flanaapis.geolocation.models import Place
from flanaapis.weather import open_weather_map, visual_crossing
from flanaapis.weather.models import DayWeather, InstantWeather


def clear_past_precipitation_probability(day_weathers: list[DayWeather], timezone: datetime.timezone):
    for day_weather in day_weathers:
        for instant_weather in day_weather.instant_weathers:
            if instant_weather.date_time < datetime.datetime.now(timezone):
                instant_weather.precipitation_probability = None


@overload
async def get_day_weathers_by_place(place: Place, ratios: list[float] = None) -> tuple[InstantWeather, list[DayWeather]]:
    pass


@overload
async def get_day_weathers_by_place(place_name: str, ratios: list[float] = None) -> tuple[InstantWeather, list[DayWeather]]:
    pass


@overload
async def get_day_weathers_by_place(latitude: float, longitude: float, ratios: list[float] = None) -> tuple[InstantWeather, list[DayWeather]]:
    pass


async def get_day_weathers_by_place(latitude: float, longitude: float = None, ratios: list[float] = None) -> tuple[InstantWeather, list[DayWeather]]:
    latitude, longitude = await functions.parse_place_arguments(latitude, longitude)

    open_current_weather, open_day_weathers = await open_weather_map.get_day_weathers_by_place(latitude, longitude)
    vc_current_weather, vc_day_weathers = await visual_crossing.get_day_weathers_by_place(latitude, longitude)

    final_day_weathers = []
    if open_day_weathers:
        if vc_day_weathers:
            first_date = open_date if (open_date := open_day_weathers[0].date) < (vc_date := vc_day_weathers[0].date) else vc_date
            last_date = open_date if (open_date := open_day_weathers[-1].date) > (vc_date := vc_day_weathers[-1].date) else vc_date
            date = first_date
            while date <= last_date:
                open_day_weather = flanautils.find(open_day_weathers, condition=lambda day_weather: day_weather.date == date)
                vc_day_weather = flanautils.find(vc_day_weathers, condition=lambda day_weather: day_weather.date == date)
                if open_day_weather:
                    if vc_day_weather:
                        final_day_weathers.append(DayWeather.mean((open_day_weather, vc_day_weather), ratios))
                    else:
                        final_day_weathers.append(open_day_weather)
                else:
                    final_day_weathers.append(vc_day_weather)
                date = date + datetime.timedelta(days=1)
        else:
            final_day_weathers = open_day_weathers
    elif vc_day_weathers:
        final_day_weathers = vc_day_weathers

    return InstantWeather.mean((open_current_weather, vc_current_weather), ratios), final_day_weathers
