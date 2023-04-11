import re
import urllib.parse
from typing import AsyncIterable

import playwright
from playwright.async_api import async_playwright

from flanaapis.geolocation.models import Place
from playwright.async_api import async_playwright


async def find_place(place_query: str) -> Place | None:
    async with async_playwright() as p:
        async with await p.chromium.launch() as browser:
            try:
                page: playwright.async_api.Page = await browser.new_page()
                await page.goto(f"https://www.google.es/maps/search/{'+'.join(place_query.split())}")
                if await (button := page.locator("'Acepto'")).count() or await (button := page.locator("'Aceptar todo'")).count():
                    await button.first.click()
                while '@' not in page.url:
                    await page.wait_for_event('framenavigated')

                await page.wait_for_load_state('domcontentloaded')
                if await page.query_selector("'Google Maps no encuentra'"):
                    return
            except playwright.async_api.TimeoutError:
                return

            try:
                place_name, latitude, longitude = re.findall(r'(?:place|search)/\d*(.+)/@([\d.-]+),([\d.-]+)', page.url)[0]
            except IndexError:
                return

            place_name = urllib.parse.unquote(place_name.replace('+', ' ').strip())

            return Place(place_name, latitude, longitude)


async def find_place_showing_progress(place_query: str) -> AsyncIterable[str | Place | None]:
    yield 'Abriendo navegador...'
    async with async_playwright() as p:
        async with await p.chromium.launch() as browser:
            try:
                page: playwright.async_api.Page = await browser.new_page()
                yield 'Dirigiéndome a google.es/maps...'
                await page.goto(f"https://www.google.es/maps/search/{'+'.join(place_query.split())}")

                if await (button := page.locator("'Acepto'")).count() or await (button := page.locator("'Aceptar todo'")).count():
                    yield 'Aceptando consentimiento de privacidad...'
                    await button.first.click()

                yield 'Rebuscando coordenadas en la página...'
                while '@' not in page.url:
                    await page.wait_for_event('framenavigated')

                await page.wait_for_load_state('domcontentloaded')
                if await page.query_selector("'Google Maps no encuentra'"):
                    yield
                    return
            except playwright.async_api.TimeoutError:
                yield
                return

            try:
                place_name, latitude, longitude = re.findall(r'(?:place|search)/\d*(.+)/@([\d.-]+),([\d.-]+)', page.url)[0]
            except IndexError:
                yield
                return

            place_name = urllib.parse.unquote(place_name.replace('+', ' ').strip())

            yield Place(place_name, latitude, longitude)
