import datetime
from typing import overload

import flanaapis.geolocation.functions
from flanaapis.scraping import google_weather_scraper
from flanaapis.weather.models import DayWeather, InstantWeather


def create_instant_weather_by_data(data: dict, timezone: datetime.timezone, days_offset=0) -> InstantWeather:
    now = datetime.datetime.now(timezone) + datetime.timedelta(days=days_offset)
    hour = datetime.datetime.strptime(data['datetime'].split()[-1], '%H:%M').hour

    return InstantWeather(
        date_time=datetime.datetime(now.year, now.month, now.day, hour, tzinfo=timezone),
        description=data.get('weather'),
        humidity=data.get('humidity'),
        precipitation_probability=data.get('precip_prob'),  # %
        temperature=data.get('temp'),
        temperature_feel=data.get('temp'),
        wind_speed=data.get('wind_speed') or data.get('wind')  # km/h
    )


@overload
async def get_day_weathers_by_place(place_query: str, timezone: datetime.timezone = None) -> tuple[InstantWeather, list[DayWeather]]:
    pass


@overload
async def get_day_weathers_by_place(latitude: float, longitude: float, timezone: datetime.timezone = None) -> tuple[InstantWeather, list[DayWeather]]:
    pass


async def get_day_weathers_by_place(latitude: float | str, longitude: float = None, timezone: datetime.timezone = None) -> tuple[InstantWeather | None, list[DayWeather] | None]:
    latitude, longitude = await flanaapis.geolocation.functions.ensure_coordinates(latitude, longitude)
    place = await flanaapis.geolocation.open_street_map.find_place(f'{latitude}, {longitude}')

    # noinspection PyBroadException
    try:
        api_weather_data = google_weather_scraper.get_forecast(str(place))
    except Exception:
        return None, None

    if not timezone:
        if api_timezone_data := await flanaapis.geolocation.functions.find_timezone(latitude, longitude):
            timezone = datetime.timezone(datetime.timedelta(seconds=api_timezone_data['gmtOffset']))
        else:
            timezone = datetime.timezone(datetime.timedelta())

    current_weather = create_instant_weather_by_data(api_weather_data['weather_now'], timezone)
    current_weather.date_time = datetime.datetime.now(timezone)

    day_weathers = []

    last_day_name = ''
    days_offset = -1
    day_weather = None
    for hour_data in api_weather_data['hourly_forecast']:
        if last_day_name != (day_name := hour_data['datetime'].split()[0]):
            last_day_name = day_name
            days_offset += 1
            try:
                day_data = api_weather_data['next_days'][days_offset]
            except IndexError:
                day_data = {}
            day_weathers.append(
                day_weather := DayWeather(
                    date=datetime.datetime.now(timezone).date() + datetime.timedelta(days=days_offset),
                    timezone=timezone,
                    min_temperature=day_data.get('min_temp'),
                    max_temperature=day_data.get('max_temp')
                )
            )

        day_weather.instant_weathers.append(create_instant_weather_by_data(hour_data, timezone, days_offset))

    return current_weather, day_weathers
