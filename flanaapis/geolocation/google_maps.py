import re
import urllib.parse
from typing import AsyncIterable

import playwright
from playwright.async_api import async_playwright

from flanaapis.geolocation.models import Place


async def find_place(place_name: str) -> Place | None:
    async with async_playwright() as p:
        async with await p.chromium.launch() as browser:
            try:
                page: playwright.async_api.Page = await browser.new_page()
                await page.goto(f"https://www.google.es/maps/search/{'+'.join(place_name.split())}")
                await page.click("'Acepto'")
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


async def find_place_showing_progress(place_name: str) -> AsyncIterable[str | Place | None]:
    yield 'Abriendo navegador...'
    async with async_playwright() as p:
        async with await p.chromium.launch() as browser:
            try:
                page: playwright.async_api.Page = await browser.new_page()
                yield 'Dirigiendome a google.es/maps...'
                await page.goto(f"https://www.google.es/maps/search/{'+'.join(place_name.split())}")
                yield 'Aceptando consentimiento de privacidad...'
                await page.click("'Acepto'")
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
