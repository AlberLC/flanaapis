import html
import os
import re
from typing import Iterable

import flanautils
import playwright
import playwright.async_api
from flanautils import Media, MediaType, OrderedSet, Source

from flanaapis.exceptions import InstagramMediaNotFoundError
from flanaapis.scraping import constants

INSTAGRAM_BASE_URL = 'https://www.instagram.com/'
INSTAGRAM_LOGIN_URL = INSTAGRAM_BASE_URL + 'accounts/login/ajax/'
INSTAGRAM_CONTENT_PATH = 'p/'

cookies = None


def find_instagram_ids(text: str) -> OrderedSet[str]:
    return OrderedSet(re.findall(r'gram\.com/.+?/(.{11})', text))


def find_media_mark(text: str) -> str:
    try:
        return re.findall(r'[\w.]+\.(?:jpg|webp|mp4)\?', text)[0]
    except IndexError:
        return ''


def find_media_urls(text: str) -> list[str]:
    return re.findall(r'https(?:(?!https).)*?sid=\w{6}', text)


def get_content_media(media_urls: list[str]) -> OrderedSet[Media]:
    last_url = ''
    final_urls = OrderedSet()
    thumbnail_urls = OrderedSet()
    for media_url in media_urls:
        if not re.findall(r'e0&cb.*cache', media_url) and '.mp4?efg' not in media_url:
            last_url = ''
            continue

        if '.mp4?' in media_url and 'jpg' in last_url:
            thumbnail_urls.add(last_url)
        final_urls.add(media_url)

        last_url = media_url

    final_urls -= thumbnail_urls

    content_medias = OrderedSet()
    for final_url in final_urls:
        if '.mp4?' in final_url:
            media_type = MediaType.VIDEO
            extension = 'mp4'
        else:
            media_type = MediaType.IMAGE
            extension = 'jpg'
        content_medias.add(Media(final_url, media_type, extension, Source.INSTAGRAM))
    return content_medias


async def get_medias(instagram_ids: Iterable[str], audio_only=False) -> OrderedSet[Media]:
    global cookies

    instagram_ids = OrderedSet(instagram_ids)

    medias: OrderedSet[Media] = OrderedSet()

    if not (instagram_urls := make_instagram_urls(instagram_ids)):
        return medias

    async with playwright.async_api.async_playwright() as p:
        async with await p.chromium.launch() as browser:
            context = await browser.new_context(user_agent=constants.USER_AGENT_2, locale='es-ES')
            page: playwright.async_api.Page = await context.new_page()

            if cookies:
                # noinspection PyTypeChecker
                await context.add_cookies(cookies)
            else:
                await login(page)
                cookies = await context.cookies()

            for instagram_url in instagram_urls:
                await page.goto(instagram_url)
                await page.wait_for_load_state('networkidle')
                button = page.locator('button[aria-label=Siguiente]')
                while await button.count():
                    await button.click()
                await page.wait_for_load_state('networkidle')
                html_content = html.unescape(await page.content())

                new_medias = get_content_media(find_media_urls(html_content))
                for media in new_medias:
                    response = await context.request.fetch(media.url)
                    media.bytes_ = await response.body()
                medias |= new_medias

    if not medias:
        raise InstagramMediaNotFoundError

    if audio_only:
        for media in medias:
            if not media.content:
                continue

            media.url = None
            media.bytes_ = await flanautils.to_mp3(media.bytes_ or await flanautils.get_request(media.url))
            media.type_ = MediaType.AUDIO
            media.extension = 'mp3'

    return medias


async def login(page: playwright.async_api.Page):
    await page.goto(INSTAGRAM_BASE_URL)
    button = page.locator("'Permitir cookies necesarias y opcionales'")
    if await button.count():
        await button.click()
    await page.fill('input[name=username]', os.environ['INSTAGRAM_USERNAME'])
    await page.fill('input[name=password]', os.environ['INSTAGRAM_PASSWORD'])
    await page.click("'Entrar'")
    await page.wait_for_load_state('networkidle')
    button = page.locator("'Guardar información'")
    if await button.count():
        await button.click()
    await page.wait_for_load_state('networkidle')
    button = page.locator("'Ahora no'")
    if await button.count():
        await button.click()


def make_instagram_urls(ids: Iterable[str]) -> list[str]:
    return [f'{INSTAGRAM_BASE_URL}{INSTAGRAM_CONTENT_PATH}{id}' for id in ids]
