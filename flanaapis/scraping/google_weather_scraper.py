import json
import re

import requests
from bs4 import BeautifulSoup as bs

"""
Part of this code is based on Dniamir's work https://github.com/dniamir/GoogleWeather.
And another part was made possible because of Andrej Kesely answer on https://stackoverflow.com/.
"""

URL = "https://www.google.com/search?hl=es&lr=lang_es&ie=UTF-8&q=weather"
HEADER = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Language": "es-ES,es;q=0.5",
}


def mph_to_kmph(mph):
    # Converts Miles per Hour to Kilometers per Hour
    return round(mph * 1.6, 1)


def kmph_to_mph(kmph):
    # Converts Kilometers per Hour to Miles per Hour
    return round(kmph / 1.6, 1)


def f_to_c(f):
    # Converts Farenheit to Celsius
    return round((f - 32) * (5 / 9), 1)


def c_to_f(c):
    # Converts Celsius to Farenheit
    return round(c * (9 / 5) + 32, 1)


def _get_soup(header, url):
    """This functions simply gets the header and url, creates a session and
       generates the "soup" to pass to the other functions.

    Args:
        header (dict): The header parameters to be used in the session.
        url (string): The url address to create the session.

    Returns:
        bs4.BeautifulSoup: The BeautifoulSoup object.
    """

    # Try to read data from URL, if it fails, return None
    try:
        session = requests.Session()
        session.headers["User-Agent"] = header["User-Agent"]
        session.headers["Accept-Language"] = header["Language"]
        session.headers["Content-Language"] = header["Language"]
        html = session.get(url)
        return bs(html.text, "html.parser")
    except:
        print(f"ERROR: Unable to retrieve data from {url}")
        return None


def _get_weather_now(soup, output_units):
    """Gets the current weather conditions.

    Args:
        soup (bs4.BeautifulSoup): The BeautifoulSoup object.
        output_units (dict): A dictionary contatining "temp" key, which can be
                             "c" for Celsius or "f" for Farenheit and a "speed"
                             key, which can be "km/h" for Kilometers Per Hour
                             or "mph" for Miles Per Hour.

    Returns:
        dict: A dictionary containing the current "Temperature", "Datetime",
                "Weather Condition", "Precipitation Probability", "Humidity"
                and "Wind Speed".
    """

    # Create a dictionary to store the output data
    data = dict()

    # Get the region output from Google
    region = soup.find("div", attrs={"id": "wob_loc"}).text

    # Get Weather Data
    data["temp"] = float(soup.find("span", attrs={"id": "wob_tm"}).text)
    data["datetime"] = soup.find("div", attrs={"id": "wob_dts"}).text
    data["weather"] = soup.find("span", attrs={"id": "wob_dc"}).text
    data["precip_prob"] = float(
        soup.find("span", attrs={"id": "wob_pp"}).text.replace("%", "")
    )
    data["humidity"] = float(
        soup.find("span", attrs={"id": "wob_hm"}).text.replace("%", "")
    )
    data["wind"] = soup.find("span", attrs={"id": "wob_ws"}).text

    # Autodetect and convert "Temperature" and "Wind Speed" units
    if "km/h" in data["wind"]:
        data["wind"] = float(data["wind"].replace("km/h", ""))

        if output_units["speed"] == "mph":
            data["wind"] = kmph_to_mph(data["wind"])

        if output_units["temp"] == "f":
            data["temp"] = c_to_f(data["temp"])

        input_units = "metric"
    else:
        data["wind"] = float(data["wind"].replace("mph", ""))

        if output_units["speed"] == "kph":
            data["wind"] = mph_to_kmph(data["wind"])

        if output_units["temp"] == "c":
            data["temp"] = f_to_c(data["temp"])

        input_units = "imperial"

    return input_units, region, data


def _get_next_days(soup, input_units, output_units):
    """Gets a summary of the next 8 days (including today).

    Args:
        soup (bs4.BeautifulSoup): The BeautifoulSoup object.
        input_units (string): The autodetected input units, they can be either
                              "metric" or "imperial".
        output_units (dict): A dictionary contatining "temp" key, which can be
                             "c" for Celsius or "f" for Farenheit and a "speed"
                             key, which can be "km/h" for Kilometers Per Hour
                             or "mph" for Miles Per Hour.

    Returns:
        list: A list of the next 8 days (including today) containing "Weather
              Condition", "Day Name", "Minimum Temperature" and "Maximum
              Temperature" for each day.
    """
    # Create a list to store the output data
    data = list()

    # Extract data from soup
    days = soup.find("div", attrs={"id": "wob_dp"})

    # Iterate over every single day
    for day in days.findAll("div", attrs={"class": "wob_df"}):
        day_name = day.find("div").attrs["aria-label"]
        weather = day.find("img").attrs["alt"]
        temp = day.findAll("span", {"class": "wob_t"})

        # Get the right data for the chosen output units
        if input_units == "metric":
            if output_units["temp"] == "c":
                max_temp = float(temp[0].text)
                min_temp = float(temp[2].text)
            else:
                max_temp = float(temp[1].text)
                min_temp = float(temp[3].text)
        else:
            if output_units["temp"] == "c":
                max_temp = float(temp[1].text)
                min_temp = float(temp[3].text)
            else:
                max_temp = float(temp[0].text)
                min_temp = float(temp[2].text)

        # Append the values to the output list
        data.append(
            {
                "day": day_name,
                "weather": weather,
                "max_temp": max_temp,
                "min_temp": min_temp,
            }
        )

    return data


def _get_wind(soup, output_units):
    """Wind Direction and Wind Bearing must be retrieved in a "special" manner,
       Google provides a 15 day forecast with 3 hour intervals containing Wind
       Speed, Wind Direction, Datetime and Wind Bearing. This function extracts
       this data.

    Args:
        soup (bs4.BeautifulSoup): The BeautifoulSoup object
        output_units (dict): A dictionary contatining "temp" key, which can be
                             "c" for Celsius or "f" for Farenheit and a "speed"
                             key, which can be "km/h" for Kilometers Per Hour
                             or "mph" for Miles Per Hour.

    Returns:
        list: A list containing one entry for every 3 hour period, each entry
              is another list, composed of wind speed, wind direction,
              datetime and wind bearing.
    """
    # Extracting the data from the "soup"
    wind = str(soup.find("div", attrs={"id": "wob_wg", "class": "wob_noe"}))
    data = re.findall(
        r'"(\d+ [\w\/]+) \w+ (\w+) (\w+-*\w*,* [0-9:]+\s*\w*)" class="wob_t" style="display:inline;text-align:right">\d+ [\w\/]+<\/span><span aria-label="\d+ [\w\/]+ \w+-*\w*,* [0-9:]+\s*\w*" class="wob_t" style="display:none;text-align:right">\d+ [\w\/]+<\/span><\/div><div style="[\w-]+:\d+"><\/div><img alt="\d+ [\w\/]+ \w+ \w+" aria-hidden="true" src="\/\/ssl.gstatic.com\/m\/images\/weather\/\w+.\w+" style="transform-origin:\d+% \d+%;transform:rotate\((\d+)\w+\)',
        wind,
    )

    # Extracting the input values units
    if "km/h" in data[0][0]:
        input_units = "metric"
    else:
        input_units = "imperial"

    # Iterating over data to post process it
    for idx, _ in enumerate(data):
        data[idx] = list(data[idx])

        # Removing the offset from Wind Bearing
        data[idx][3] = int(data[idx][3]) - 90

        # Extracting numerical values and converting units, if necessary
        if input_units == "metric":
            data[idx][0] = float(data[idx][0].replace("km/h", ""))

            if output_units["speed"] == "mph":
                data[idx][0] = kmph_to_mph(data[idx][0])

        else:
            data[idx][0] = float(data[idx][0].replace("mph", ""))

            if output_units["speed"] == "km/h":
                data[idx][0] = mph_to_kmph(data[idx][0])

    return data


def _get_hourly_forecast(header, url, output_units):
    """This functions extracts hourly forecast data for the next 15 days.

    Args:
        header (dict): The header parameters to be used in the session.
        url (string): The url address to create the session.
        output_units (dict): A dictionary contatining "temp" key, which can be
                            "c" for Celsius or "f" for Farenheit and a "speed"
                            key, which can be "km/h" for Kilometers Per Hour
                            or "mph" for Miles Per Hour.

    Returns:
        list: A list containing one dictionary for every 1 hour period. Each
              dictionary has "Datetime", "Humidity", "Precipitation Probability"
              "Temperature", "Weather Condition" and "Wind Speed".
    """
    # Build the header
    header = {"User-Agent": header["User-Agent"]}

    # Request and extract the data from the url
    text = requests.get(url, headers=header).text
    data_in = re.search(r"pmc='({.*?})'", text).group(1)
    data_in = json.loads(data_in.replace(r"\x22", '"').replace(r'\\"', r"\""))

    # Create a list to store the output data
    data_out = list()

    # Iterate over each entry
    for entry_in in data_in["wobnm"]["wobhl"]:

        # Create a dictionary to store the output entry
        entry_out = dict()

        # Pull data from the input entry into the output entry
        entry_out["datetime"] = entry_in["dts"]
        entry_out["weather"] = entry_in["c"]
        entry_out["humidity"] = float(entry_in["h"].replace("%", ""))
        entry_out["precip_prob"] = float(entry_in["p"].replace("%", ""))

        # Get the right data for the chosen output units
        if output_units["temp"] == "c":
            entry_out["temp"] = float(entry_in["tm"])
        else:
            entry_out["temp"] = float(entry_in["ttm"])

        if output_units["speed"] == "km/h":
            entry_out["wind_speed"] = float(entry_in["ws"].replace("km/h", ""))
        else:
            entry_out["wind_speed"] = float(entry_in["tws"].replace("mph", ""))

        # Append the output entry to the output list
        data_out.append(entry_out)

    return data_out


def get_forecast(region, output_units={"temp": "c", "speed": "km/h"}):
    """This is the wrapper that calls the other functions and joins the data into
       one output.

    Args:
        header (dict): The header parameters to be used in the session.
        url (string): The url address to create the session.
        region (string): The desired region to get the weather forecast.
        output_units (dict): A dictionary contatining "temp" key, which can be
                            "c" for Celsius or "f" for Farenheit and a "speed"
                            key, which can be "km/h" for Kilometers Per Hour
                            or "mph" for Miles Per Hour.

    Returns:
        dict: A dictionary containing all the data extracted by the other
              functions
    """
    # Build url and get the "soup" from it
    url = f"{URL}+{region.replace(' ', '+')}"
    soup = _get_soup(HEADER, url)

    # Create a dictionary to store the output data
    data = dict()

    # Check if we got a soup to work with
    if soup:
        input_units, data["region"], data["weather_now"] = _get_weather_now(
            soup, output_units
        )
        data["next_days"] = _get_next_days(soup, input_units, output_units)
        data["wind"] = _get_wind(soup, output_units)

    data["hourly_forecast"] = _get_hourly_forecast(HEADER, url, output_units)

    return data
