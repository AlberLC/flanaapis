import datetime
import os
from typing import overload

import flanautils

import flanaapis.geolocation.functions
import flanaapis.weather.functions
from flanaapis.exceptions import ResponseError
from flanaapis.geolocation.models import Place
from flanaapis.weather.models import DayWeather, InstantWeather, Precipitation, PrecipitationType

BASE_ENDPOINT = f'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline'


def create_instant_weather_by_data(data: dict, timezone: datetime.timezone) -> InstantWeather:
    return InstantWeather(
        date_time=datetime.datetime.fromtimestamp(data['datetimeEpoch'], timezone),
        clouds=data.get('cloudcover'),
        description=data.get('conditions'),
        dew_point=data.get('dew'),
        humidity=data.get('humidity'),
        icon=data.get('icon'),
        precipitation_probability=data.get('precipprob') or 0,  # %
        pressure=data.get('pressure'),
        temperature=data.get('temp'),
        temperature_feel=data.get('feelslike'),
        uvi=data.get('uvindex'),
        visibility=data.get('visibility'),  # km
        wind_degrees=data.get('winddir'),
        wind_gust=data.get('windgust'),
        wind_speed=data.get('windspeed')  # km/h
    )


async def get_weather_api_data(latitude: float, longitude: float) -> tuple[dict, datetime.timezone]:
    now = datetime.datetime.now()
    start_date = now - datetime.timedelta(days=5)
    end_date = now + datetime.timedelta(days=15)
    parameters = {
        'key': os.environ['VISUAL_CROSSING_API_KEY'],
        'unitGroup': 'metric',
        'lang': 'es'
    }

    api_data = await flanautils.get_request(f'{BASE_ENDPOINT}/{latitude},{longitude}/{int(start_date.timestamp())}/{int(end_date.timestamp())}', parameters)
    timezone = datetime.timezone(datetime.timedelta(hours=api_data['tzoffset']))

    return api_data, timezone


@overload
async def get_day_weathers_by_place(place: Place) -> tuple[InstantWeather, list[DayWeather]]:
    pass


@overload
async def get_day_weathers_by_place(place_name: str) -> tuple[InstantWeather, list[DayWeather]]:
    pass


@overload
async def get_day_weathers_by_place(latitude: float, longitude: float) -> tuple[InstantWeather, list[DayWeather]]:
    pass


async def get_day_weathers_by_place(latitude: float, longitude: float = None) -> tuple[InstantWeather | None, list[DayWeather] | None]:
    latitude, longitude = await flanaapis.geolocation.functions.parse_place_arguments(latitude, longitude)

    try:
        api_data, timezone = await get_weather_api_data(latitude, longitude)
    except ResponseError:
        return None, None

    current_weather = create_instant_weather_by_data(api_data['currentConditions'], timezone)

    day_weathers = []
    for day_data in api_data['days']:
        precipitations: list[Precipitation] = []
        day_date = datetime.datetime.fromtimestamp(day_data['datetimeEpoch'], timezone).replace(hour=0)
        day_weather = DayWeather(
            date=day_date.date(),
            timezone=timezone,
            sunrise=datetime.datetime.fromtimestamp(day_data['sunriseEpoch'], timezone),
            sunset=datetime.datetime.fromtimestamp(day_data['sunsetEpoch'], timezone),
            min_temperature=day_data['tempmin'],
            max_temperature=day_data['tempmax']
        )

        # Daily precipitation volumes
        if day_rain_volume := day_data.get('precip'):
            precipitations.append(Precipitation(PrecipitationType.RAIN, day_date, day_date + datetime.timedelta(days=1), day_rain_volume))
        if day_snow_volume := day_data.get('snow'):
            precipitations.append(Precipitation(PrecipitationType.SNOW, day_date, day_date + datetime.timedelta(days=1), day_snow_volume * 10))  # snow cm -> mm

        # Hourly precipitation volumes
        for hour_data in day_data.get('hours', ()):
            day_weather.instant_weathers.append(create_instant_weather_by_data(hour_data, timezone))
            hour_date = datetime.datetime.fromtimestamp(hour_data['datetimeEpoch'], timezone)
            if hour_rain_volume := hour_data.get('precip'):
                precipitations.append(Precipitation(PrecipitationType.RAIN, hour_date, hour_date + datetime.timedelta(hours=1), hour_rain_volume))
            if hour_snow_volume := hour_data.get('snow'):
                precipitations.append(Precipitation(PrecipitationType.SNOW, hour_date, hour_date + datetime.timedelta(hours=1), hour_snow_volume * 10))  # snow cm -> mm

        day_weather.distribute_precipitation_volume(precipitations)

        day_weathers.append(day_weather)

    flanaapis.weather.functions.clear_past_precipitation_probability(day_weathers, timezone)

    return current_weather, day_weathers
