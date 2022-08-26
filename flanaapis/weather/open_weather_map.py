__all__ = [
    'add_daily_attributes_from_current_data_format',
    'create_instant_weather_by_data',
    'get_day_weathers_by_place',
    'get_hourly_precipitation',
    'get_hourly_precipitations',
    'get_weather_api_data'
]

import asyncio
import datetime
import os
from typing import Iterable, overload

import aiohttp
import flanautils

import flanaapis.geolocation.functions
import flanaapis.weather.functions
from flanaapis.exceptions import ResponseError
from flanaapis.geolocation.models import Place
from flanaapis.weather.models import DayPhases, DayWeather, InstantWeather, Precipitation, PrecipitationType

UNITS = 'metric'
LANGUAGE = 'es'
BASE_ENDPOINT = 'https://api.openweathermap.org/data/2.5'
PAST_ENDPOINT = f'{BASE_ENDPOINT}/onecall/timemachine'
NEAR_FUTURE_ENDPOINT = f'{BASE_ENDPOINT}/forecast'
PRESENT_FUTURE_ENDPOINT = f'{BASE_ENDPOINT}/onecall'
MAX_RETRIES_PAST_REQUEST = 5


def add_daily_attributes_from_current_data_format(day_weathers: Iterable[DayWeather], data: dict, timezone: datetime.timezone):
    date_time = datetime.datetime.fromtimestamp(data['current']['dt'], tz=timezone)
    day_weather = flanautils.find(day_weathers, condition=lambda day_weather_: day_weather_.date == date_time.date())
    try:
        day_weather.sunrise = datetime.datetime.fromtimestamp(data['current']['sunrise'], timezone)
        day_weather.sunset = datetime.datetime.fromtimestamp(data['current']['sunset'], timezone)
    except KeyError:
        pass


def create_instant_weather_by_data(data: dict, timezone: datetime.timezone) -> InstantWeather:
    def format_old_open_weather_map_api_data() -> dict:
        for k, v in data['main'].items():
            data[k] = v
        data['clouds'] = sum(data['clouds'].values())
        data['wind_deg'] = data.get('wind', {}).get('deg')
        data['wind_gust'] = data.get('wind', {}).get('gust')
        data['wind_speed'] = data.get('wind', {}).get('speed')

        return data

    if 'main' in data:
        data = format_old_open_weather_map_api_data()

    return InstantWeather(
        date_time=datetime.datetime.fromtimestamp(data['dt'], tz=timezone),
        clouds=data.get('clouds'),
        description=data.get('weather', ({},))[0].get('description'),
        dew_point=data.get('dew_point'),
        humidity=data.get('humidity'),
        icon=data.get('weather', ({},))[0].get('icon'),
        precipitation_probability=pop * 100 if (pop := data.get('pop')) else pop,  # p -> %
        pressure=data.get('pressure'),
        temperature=data.get('temp'),
        temperature_feel=data.get('feels_like'),
        uvi=data.get('uvi'),
        visibility=visibility / 1000 if (visibility := data.get('visibility')) else visibility,  # visibility m -> km
        wind_degrees=data.get('wind_deg'),
        wind_gust=data.get('wind_gust'),
        wind_speed=wind_speed * 3.6 if (wind_speed := data.get('wind_speed')) else wind_speed  # wind_speed m/s -> km/h
    )


@overload
async def get_day_weathers_by_place(place: Place) -> tuple[InstantWeather, list[DayWeather]]:
    pass


@overload
async def get_day_weathers_by_place(place_query: str) -> tuple[InstantWeather, list[DayWeather]]:
    pass


@overload
async def get_day_weathers_by_place(latitude: float, longitude: float) -> tuple[InstantWeather, list[DayWeather]]:
    pass


async def get_day_weathers_by_place(latitude: float | str, longitude: float = None) -> tuple[InstantWeather, list[DayWeather]]:
    latitude, longitude = await flanaapis.geolocation.functions.ensure_coordinates(latitude, longitude)

    day_weathers = []

    past_days_data, present_future_data, near_future_data, timezone = await get_weather_api_data(latitude, longitude)
    current_weather = create_instant_weather_by_data(present_future_data['current'], timezone)
    precipitations: list[Precipitation] = []

    # ----- hourly data -----
    hourly_data = [hour_data for past_day_data in past_days_data for hour_data in past_day_data['hourly']][:-1]
    hourly_data += present_future_data['hourly']
    hourly_data += near_future_data['list']

    for hour_data in hourly_data:
        hour_dt = datetime.datetime.fromtimestamp(hour_data['dt'], tz=timezone)
        day_weather = flanautils.find(day_weathers, condition=lambda day_weather_: day_weather_.date == hour_dt.date())
        if not day_weather or hour_dt.date() != day_weather.date:
            day_weathers.append(day_weather := DayWeather(hour_dt.date(), timezone))

        if hourly_precipitations := get_hourly_precipitations(hour_dt, hour_data):
            precipitations.extend(hourly_precipitations)

        temp_day_weather = DayWeather()
        temp_day_weather.instant_weathers.append(create_instant_weather_by_data(hour_data, timezone))
        day_weather.merge(temp_day_weather)

    # ----- daily data -----
    for past_day_data in past_days_data:
        add_daily_attributes_from_current_data_format(day_weathers, past_day_data, timezone)

    add_daily_attributes_from_current_data_format(day_weathers, present_future_data, timezone)

    for future_day_data in present_future_data['daily']:
        day_dt = datetime.datetime.fromtimestamp(future_day_data['dt'], tz=timezone).replace(hour=0)
        day_weather = flanautils.find(day_weathers, condition=lambda day_weather_: day_weather_.date == day_dt.date())
        if not day_weather:
            day_weather = DayWeather(day_dt.date(), timezone)
            day_weathers.append(day_weather)

        day_weather.sunrise = datetime.datetime.fromtimestamp(future_day_data['sunrise'], timezone)
        day_weather.sunset = datetime.datetime.fromtimestamp(future_day_data['sunset'], timezone)
        day_weather.min_temperature = future_day_data['temp']['min']
        day_weather.max_temperature = future_day_data['temp']['max']
        if daily_rain := future_day_data.get('rain') or 0:
            precipitations.append(Precipitation(PrecipitationType.RAIN, day_dt, day_dt + datetime.timedelta(days=1), daily_rain))
        if daily_snow := future_day_data.get('snow') or 0:
            precipitations.append(Precipitation(PrecipitationType.SNOW, day_dt, day_dt + datetime.timedelta(days=1), daily_snow))

        temp_day_weather = DayWeather()
        # noinspection PyTypeChecker
        for phase_name, hour in DayPhases.items:
            phase_name = phase_name.lower()
            hour_dt = day_dt.replace(hour=hour)

            future_day_data_copy = future_day_data.copy()
            future_day_data_copy['dt'] = int(hour_dt.timestamp())
            future_day_data_copy['temp'] = future_day_data['temp'][phase_name]
            future_day_data_copy['feels_like'] = future_day_data['feels_like'][phase_name]
            if phase_name != 'day':
                future_day_data_copy['uvi'] = 0
            temp_day_weather.instant_weathers.append(create_instant_weather_by_data(future_day_data_copy, timezone))
            day_weather.merge(temp_day_weather)

    for day_weather in day_weathers:
        day_weather.distribute_precipitation_volume(precipitations)

    flanaapis.weather.functions.clear_past_precipitation_probability(day_weathers, timezone)

    return current_weather, day_weathers


def get_hourly_precipitation(date: datetime.datetime, data: dict, precipitation_type: PrecipitationType, last_hours: int) -> Precipitation:
    try:
        return Precipitation(precipitation_type, date - datetime.timedelta(hours=last_hours), date, data[precipitation_type.name.lower()][f'{last_hours}h'])
    except KeyError:
        pass


def get_hourly_precipitations(date: datetime.datetime, data: dict) -> list[Precipitation]:
    rain_last_hour = get_hourly_precipitation(date, data, PrecipitationType.RAIN, last_hours=1)
    rain_last_3_hours = get_hourly_precipitation(date, data, PrecipitationType.RAIN, last_hours=3)
    snow_last_hour = get_hourly_precipitation(date, data, PrecipitationType.SNOW, last_hours=1)
    snow_last_3_hours = get_hourly_precipitation(date, data, PrecipitationType.SNOW, last_hours=3)

    return [precipitation for precipitation in (rain_last_hour, rain_last_3_hours, snow_last_hour, snow_last_3_hours) if precipitation]


async def get_weather_api_data(latitude: float, longitude: float) -> tuple[list[dict], dict, dict, datetime.timezone]:
    parameters = {
        'lat': latitude,
        'lon': longitude,
        'units': UNITS,
        'lang': LANGUAGE,
        'appid': os.environ['OPEN_WEATHER_MAP_API_KEY']
    }

    async with aiohttp.ClientSession() as session:
        past_days_data = []
        for days_to_the_past in reversed(range(6)):
            dt_query_param = datetime.datetime.now() - datetime.timedelta(days=days_to_the_past)
            for _ in range(MAX_RETRIES_PAST_REQUEST):
                try:
                    past_days_data.append(await flanautils.get_request(PAST_ENDPOINT, parameters | {'dt': int(dt_query_param.timestamp())}, session=session))
                    break
                except ResponseError:
                    await asyncio.sleep(1)

        present_future_data: dict = await flanautils.get_request(PRESENT_FUTURE_ENDPOINT, parameters, session=session)
        near_future_data: dict = await flanautils.get_request(NEAR_FUTURE_ENDPOINT, parameters, session=session)
        timezone = datetime.timezone(datetime.timedelta(seconds=present_future_data['timezone_offset']))

    return past_days_data, present_future_data, near_future_data, timezone
