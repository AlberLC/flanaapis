__all__ = ['clear_past_precipitation_probability', 'get_day_weathers_by_place']

import datetime
from typing import overload

import flanautils

from flanaapis.geolocation import functions
from flanaapis.geolocation.models import Place
from flanaapis.weather import google, open_weather_map, visual_crossing
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
async def get_day_weathers_by_place(place_query: str, ratios: list[float] = None) -> tuple[InstantWeather, list[DayWeather]]:
    pass


@overload
async def get_day_weathers_by_place(latitude: float, longitude: float, ratios: list[float] = None) -> tuple[InstantWeather, list[DayWeather]]:
    pass


async def get_day_weathers_by_place(latitude: float | str, longitude: float = None, ratios: list[float] = None) -> tuple[InstantWeather, list[DayWeather]]:
    def get_timezone(current_weather, days_weathers) -> datetime.timezone | None:
        try:
            return current_weather.date_time.tzinfo
        except AttributeError:
            try:
                return days_weathers[0].timezone
            except (IndexError, TypeError):
                return None

    latitude, longitude = await functions.ensure_coordinates(latitude, longitude)

    open_current_weather, open_day_weathers = await open_weather_map.get_day_weathers_by_place(latitude, longitude)
    vc_current_weather, vc_day_weathers = await visual_crossing.get_day_weathers_by_place(latitude, longitude)
    timezone = get_timezone(open_current_weather, open_day_weathers) or get_timezone(vc_current_weather, vc_day_weathers)
    google_current_weather, google_day_weathers = await google.get_day_weathers_by_place(latitude, longitude, timezone)

    all_day_weathers = [day_weathers for day_weathers in (open_day_weathers, vc_day_weathers, google_day_weathers) if day_weathers]

    final_day_weathers = []
    if len(all_day_weathers) == 1:
        final_day_weathers = all_day_weathers[0]
    else:
        first_date = sorted(day_weathers[0].date for day_weathers in all_day_weathers)[0]
        last_date = sorted(day_weathers[-1].date for day_weathers in all_day_weathers)[-1]
        date = first_date
        while date <= last_date:
            all_day_weather = [day_weather for day_weathers in all_day_weathers if (day_weather := flanautils.find(day_weathers, condition=lambda day_weather: day_weather.date == date))]
            if len(all_day_weather) == 1:
                final_day_weathers.append(all_day_weather[0])
            else:
                final_day_weathers.append(DayWeather.mean(all_day_weather, ratios))
            date = date + datetime.timedelta(days=1)

    return InstantWeather.mean((open_current_weather, vc_current_weather, google_current_weather), ratios), final_day_weathers
