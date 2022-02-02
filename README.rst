FlanaApis
=========

|license| |project_version| |python_version|

Set of functions that can be used as an imported library or as an api rest running the main.py. There is currently an instance of the api running at https://flanaserver.ddns.net/flanaapis.

|

Installation
------------

Python 3.10 or higher is required.

.. code-block::

    pip install flanaapis

|

Features
--------

1) Geolocation
~~~~~~~~~~~~~~

1.1) Find a place on earth
..........................

- Library functions:
    - :code:`flanaapis.geolocation.functions.find_place(...)`
- Api endpoints:
    - https://flanaserver.ddns.net/flanaapis/place?query=malaga
    - https://flanaserver.ddns.net/flanaapis/place?query=36.796171,-4.4779943

1.2) Find places on earth
.........................

- Library functions:
    - :code:`flanaapis.geolocation.functions.find_places(...)`
- Api endpoints:
    - https://flanaserver.ddns.net/flanaapis/places?query=malaga
    - https://flanaserver.ddns.net/flanaapis/places?query=36.796171,-4.4779943

1.3) Find timezone
..................

- Library functions:
    - :code:`flanaapis.geolocation.functions.find_timezone(...)`

- Api endpoints:
    - https://flanaserver.ddns.net/flanaapis/timezone?query=malaga
    - https://flanaserver.ddns.net/flanaapis/timezone?query=36.796171,-4.4779943

All geolocation functions and endpoints have a parameter :code:`fast: bool`. If :code:`fast=true` (false by default) google maps won't be used. It will directly use the https://nominatim.openstreetmap.org api but it's somewhat less precise.

|

2) Scraping
~~~~~~~~~~~

2.1) Twitter
............

It use Twitter api, doesn't really scrape.

- Library functions:
    - :code:`flanaapis.scraping.twitter.get_medias(...)`
- Api endpoints:
    - POST https://flanaserver.ddns.net/flanaapis/medias with parameters {"text": "any link/s"}.

2.2) Instagram
..............

- Library functions:
    - :code:`flanaapis.scraping.instagram.get_medias(...)`
- Api endpoints:
    - POST https://flanaserver.ddns.net/flanaapis/medias with parameters {"text": "any link/s"}.

2.3) TikTok
...........

- Library functions:
    - :code:`flanaapis.scraping.tiktok.get_medias(...)`

- Api endpoints:
    - POST https://flanaserver.ddns.net/flanaapis/medias with parameters {"text": "any link/s"}.

2.4) Google weather
...................

Based on `github.com/lfhohmann/google-weather-scraper`_.

- Library functions:
    - :code:`flanaapis.scraping.google_weather_scraper.get_forecast(...)`

- Api endpoints:
    - see `3) Weather`_

|

3) Weather
~~~~~~~~~~

Gets the mean of the data from several sources:

1. `openweathermap.org`_
2. `visualcrossing.com`_
3. `google.com/search?q=weather`_

- Library functions:
    - :code:`flanaapis.functions.weather.get_day_weathers_by_place(...)`

- Api endpoints:
    - https://flanaserver.ddns.net/flanaapis/weather?latitude=36.796171&longitude=-4.4779943


.. |license| image:: https://img.shields.io/github/license/AlberLC/flanaapis?style=flat
    :target: https://github.com/AlberLC/flanaapis/blob/main/LICENSE
    :alt: License

.. |project_version| image:: https://img.shields.io/pypi/v/flanaapis
    :target: https://pypi.org/project/flanaapis/
    :alt: PyPI

.. |python_version| image:: https://img.shields.io/pypi/pyversions/flanaapis
    :target: https://www.python.org/downloads/
    :alt: PyPI - Python Version

.. _github.com/lfhohmann/google-weather-scraper: https://github.com/lfhohmann/google-weather-scraper
.. _openweathermap.org: https://openweathermap.org/
.. _visualcrossing.com: https://www.visualcrossing.com/
.. _google.com/search?q=weather: https://www.google.com/search?q=weather