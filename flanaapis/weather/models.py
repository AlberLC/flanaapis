from __future__ import annotations  # todo0 remove in 3.11

import datetime
from dataclasses import dataclass, field
from enum import auto
from typing import Any, Iterable, Sequence

from flanautils import FlanaBase, FlanaEnum, MeanBase


class DayPhases(FlanaEnum):
    NIGHT = 2
    MORN = 9
    DAY = 14
    EVE = 19


class PrecipitationType(FlanaEnum):
    FREEZINGRAIN = auto()
    ICE = auto()
    RAIN = auto()
    SNOW = auto()


@dataclass(unsafe_hash=True)
class Precipitation(FlanaBase):
    type_: PrecipitationType
    start_date: datetime.datetime
    end_date: datetime.datetime
    volume: float


@dataclass(unsafe_hash=True)
class InstantWeather(MeanBase, FlanaBase):
    date_time: datetime.datetime = None
    clouds: float = field(default=None, metadata={'unit': '%'})
    description: str = None
    dew_point: float = field(default=None, metadata={'unit': 'ºC'})
    humidity: float = field(default=None, metadata={'unit': '%'})
    icon: Any = None
    precipitation_probability: float = field(default=None, metadata={'unit': '%'})
    pressure: float = field(default=None, metadata={'unit': 'hPa'})
    rain_volume: float = field(default=None, metadata={'unit': 'mm'})
    snow_volume: float = field(default=None, metadata={'unit': 'mm'})
    temperature: float = field(default=None, metadata={'unit': 'ºC'})
    temperature_feel: float = field(default=None, metadata={'unit': 'ºC'})
    uvi: float = None
    visibility: float = field(default=None, metadata={'unit': 'km'})
    wind_degrees: float = None
    wind_gust: float = field(default=None, metadata={'unit': 'km/h'})
    wind_speed: float = field(default=None, metadata={'unit': 'km/h'})

    def _dict_repr(self) -> Any:
        self_vars = super()._dict_repr()
        for k, v in self_vars.items():
            if isinstance(v, datetime.datetime):
                self_vars[k] = v.timestamp()
            elif isinstance(v, datetime.timezone):
                self_vars[k] = str(v)

        return self_vars

    @classmethod
    def mean(
        cls,
        objects: Sequence,
        ratios: list[float] = None,
        attribute_names: Iterable[str] = ('clouds', 'dew_point', 'humidity', 'precipitation_probability', 'pressure', 'rain_volume', 'snow_volume', 'temperature', 'temperature_feel', 'uvi', 'visibility', 'wind_degrees', 'wind_gust', 'wind_speed')
    ) -> InstantWeather:
        if not objects:
            return InstantWeather()

        # noinspection PyTypeChecker
        instant_weather: InstantWeather = super().mean(objects, ratios, attribute_names)
        for object_ in objects:
            if object_:
                instant_weather.date_time = object_.date_time

        return instant_weather

    def merge(self, other: InstantWeather, left_priority=True) -> InstantWeather:
        for k, v in vars(self).items():
            if v is None or not left_priority:
                setattr(self, k, getattr(other, k, None))
        return self


@dataclass(unsafe_hash=True)
class DayWeather(MeanBase, FlanaBase):
    date: datetime.date = None
    timezone: datetime.timezone = None
    sunrise: datetime.datetime = None
    sunset: datetime.datetime = None
    min_temperature: float = None
    max_temperature: float = None
    instant_weathers: list[InstantWeather] = field(default_factory=list)

    def _dict_repr(self) -> Any:
        self_vars = super()._dict_repr()
        for k, v in self_vars.items():
            if isinstance(v, datetime.date):
                self_vars[k] = datetime.datetime(v.year, v.month, v.day).timestamp()
            elif isinstance(v, datetime.timezone):
                self_vars[k] = str(v)

        return self_vars

    def distribute_precipitation_volume(self, precipitations: Iterable[Precipitation]):
        def distribute_precipitation_volume_(precipitation_type: PrecipitationType, precipitations_: Iterable[Precipitation]):
            grouped_precipitations: dict[int, list[Precipitation]] = {}
            for hours in range(1, 25):
                grouped_precipitations[hours] = [precipitation.copy() for precipitation in precipitations_ if (precipitation.end_date - precipitation.start_date).total_seconds() / 3600 == hours]

            hourly_precipitations: list[Precipitation] = grouped_precipitations[1]
            for hours in range(2, 25):
                for precipitation in grouped_precipitations[hours]:
                    start_hour = precipitation.start_date.hour
                    start_hours = list(range(start_hour, min(start_hour + hours, 24)))

                    for hourly_precipitation in hourly_precipitations:
                        if hourly_precipitation.start_date.hour in start_hours:
                            start_hours.remove(hourly_precipitation.start_date.hour)
                            precipitation.volume -= hourly_precipitation.volume
                    if start_hours:
                        hourly_volume = precipitation.volume / len(start_hours)
                    else:
                        continue
                    for start_hour in start_hours:
                        start_date = precipitation.start_date.replace(hour=start_hour)
                        hourly_precipitations.append(Precipitation(precipitation_type, start_date, start_date + datetime.timedelta(hours=1), hourly_volume))
            hourly_precipitations.sort(key=lambda precipitation: precipitation.start_date)

            attribute_name = f'{precipitation_type.name.lower()}_volume'
            for precipitation in hourly_precipitations:
                if not precipitation.volume:
                    return

                if not (instant_weather := next(iter(self.get_instant_weathers_by_hour(precipitation.start_date.hour)), None)):
                    instant_weather = InstantWeather(precipitation.start_date)
                    self.instant_weathers.append(instant_weather)
                setattr(instant_weather, attribute_name, precipitation.volume)

            self.instant_weathers.sort(key=lambda instant_weather_: instant_weather_.date_time)

        precipitations = [precipitation for precipitation in precipitations if precipitation.start_date.date() == self.date]
        temp_precipitations = []
        for precipitation in precipitations:
            next_day_first_hour_date_time = (precipitation.start_date + datetime.timedelta(days=1)).replace(hour=0)
            if next_day_first_hour_date_time < precipitation.end_date:
                precipitation_hours = (precipitation.end_date - precipitation.start_date).total_seconds() / 3600
                hours_until_next_day = (next_day_first_hour_date_time - precipitation.start_date).total_seconds() / 3600
                next_day_precipitation_hours = precipitation_hours - hours_until_next_day
                temp_precipitations.append(Precipitation(precipitation.type_, precipitation.start_date, next_day_first_hour_date_time, precipitation.volume / precipitation_hours * hours_until_next_day))
                temp_precipitations.append(Precipitation(precipitation.type_, next_day_first_hour_date_time, next_day_first_hour_date_time + datetime.timedelta(hours=next_day_precipitation_hours), precipitation.volume / precipitation_hours * next_day_precipitation_hours))
            else:
                temp_precipitations.append(precipitation)
        precipitations = temp_precipitations
        if rain := [precipitation for precipitation in precipitations if precipitation.type_ is PrecipitationType.RAIN]:
            distribute_precipitation_volume_(PrecipitationType.RAIN, rain)
        if snow := [precipitation for precipitation in precipitations if precipitation.type_ is PrecipitationType.SNOW]:
            distribute_precipitation_volume_(PrecipitationType.SNOW, snow)

    def fill_24h_instant_weathers(self):
        if not self.date:
            return

        for hour in range(24):
            if not self.get_instant_weathers_by_hour(hour):
                new_instant_weather = InstantWeather(datetime.datetime(self.date.year, self.date.month, self.date.day, hour, tzinfo=self.timezone))
                self.instant_weathers.insert(hour, new_instant_weather)

    def get_instant_weathers_by_hour(self, hour: int) -> list[InstantWeather]:
        return [instant_weather for instant_weather in self.instant_weathers if instant_weather.date_time and instant_weather.date_time.hour == hour]

    @classmethod
    def mean(
        cls,
        objects: Sequence,
        ratios: list[float] = None,
        attribute_names: Iterable[str] = ('sunrise', 'sunset', 'min_temperature', 'max_temperature')
    ) -> DayWeather:
        if not objects:
            return DayWeather()

        final_instant_weathers = []
        for hour in range(24):
            instant_weathers = [instant_weather for day_weather in objects if (instant_weather := next(iter(day_weather.get_instant_weathers_by_hour(hour)), None))]
            if instant_weathers:
                final_instant_weathers.append(InstantWeather.mean(instant_weathers, ratios))

        # noinspection PyTypeChecker
        day_weather: DayWeather = super().mean(objects, ratios, attribute_names)
        for object_ in objects:
            day_weather.date = object_.date
            day_weather.timezone = object_.timezone
            day_weather.instant_weathers = final_instant_weathers

        return day_weather

    def merge(self, other: DayWeather, left_priority=True) -> DayWeather:
        vars_copy = vars(self).copy()
        vars_copy.popitem()

        for k, v in vars_copy.items():
            if v in (None, []) or not left_priority:
                setattr(self, k, getattr(other, k, None))

        new_instant_weathers = []
        for hour in range(24):
            self_instant_weather = next(iter(self.get_instant_weathers_by_hour(hour)), None)
            other_instant_weather = next(iter(other.get_instant_weathers_by_hour(hour)), None)
            if self_instant_weather:
                if other_instant_weather:
                    new_instant_weathers.append(self_instant_weather.merge(other_instant_weather, left_priority))
                else:
                    new_instant_weathers.append(self_instant_weather)
            elif other_instant_weather:
                new_instant_weathers.append(other_instant_weather)
        self.instant_weathers = new_instant_weathers

        return self
