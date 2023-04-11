import asyncio
import html as html_module
import random
import re
from typing import Iterable

import aiohttp
import flanautils
import playwright.async_api
from flanautils import Media, MediaType, OrderedSet, ResponseError, Source

from flanaapis.exceptions import InstagramMediaNotFoundError
from flanaapis.scraping import constants, functions


def filter_media_urls(media_urls: list[str]) -> OrderedSet[Media]:
    if not media_urls:
        return OrderedSet()

    sid = None
    last_url = ''
    selected_urls = {}
    thumbnail_urls = set()

    for media_url in media_urls:
        if (
                not re.findall('(?:-15/.*=dst-jpg_e\d{2}|mp4).*sid=\w+$', media_url)
                or
                sid
                and
                sid != get_media_url_sid(media_url)
        ):
            last_url = ''
            continue

        if not sid:
            sid = get_media_url_sid(media_url)

        selected_urls[get_media_url_id(media_url)] = media_url
        if 'jpg' in media_url and 'mp4' in last_url:
            thumbnail_urls.add(media_url)

        last_url = media_url

    final_urls = OrderedSet(selected_urls.values()) - thumbnail_urls

    content_medias = OrderedSet()
    for final_url in final_urls:
        if 'jpg' in final_url:
            media_type = MediaType.IMAGE
            extension = 'jpg'
        else:
            media_type = MediaType.VIDEO
            extension = 'mp4'
        content_medias.add(Media(final_url, media_type, extension, Source.INSTAGRAM))

    return content_medias


def filter_media_urls_v2(media_urls: list[str]) -> OrderedSet[Media]:
    last_url = ''
    last_video_url = ''
    last_video_id = ''
    final_urls = OrderedSet()
    thumbnail_urls = OrderedSet()
    for media_url in media_urls:
        if (
                not re.findall('-15/.*=dst-jpg', media_url)
                and
                'mp4' not in media_url
        ):
            last_url = ''
            continue

        if 'jpg' in media_url:
            if 'mp4' in last_url:
                thumbnail_urls.add(media_url)
        else:
            video_id = get_media_url_id(media_url)
            if video_id == last_video_id:
                final_urls -= last_video_url
            last_video_url = media_url
            last_video_id = video_id
        final_urls.add(media_url)

        last_url = media_url

    final_urls -= thumbnail_urls

    content_medias = OrderedSet()
    for final_url in final_urls:
        if 'jpg' in final_url:
            media_type = MediaType.IMAGE
            extension = 'jpg'
        else:
            media_type = MediaType.VIDEO
            extension = 'mp4'
        content_medias.add(Media(final_url, media_type, extension, Source.INSTAGRAM))

    return content_medias


def find_ids(text: str) -> OrderedSet[str]:
    return OrderedSet(re.findall('gram\.com(?!/stories).+?/(.{11})', text))


def find_media_urls(text: str) -> list[str]:
    return re.findall('https(?:(?!http|\"|\.insta).)*=[0-9a-fA-F]+', text)


async def get_html(url: str) -> str:
    async with playwright.async_api.async_playwright() as playwright_:
        async with await playwright_.chromium.launch() as browser:
            context: playwright.async_api.BrowserContext = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.49 Safari/537.36',
                screen={
                    'width': 1920,
                    'height': 1080
                },
                viewport={
                    'width': 1280,
                    'height': 720
                },
                device_scale_factor=1,
                is_mobile=False,
                has_touch=False,
                default_browser_type='chromium',
                locale='es-ES'
            )
            context.set_default_timeout(3000)

            page = await context.new_page()
            await page.goto(url, timeout=30000)

            try:
                await page.click("'Permitir solo cookies necesarias'")
            except playwright.async_api.Error:
                pass
            await page.wait_for_load_state('networkidle')

            try:
                button = await page.wait_for_selector("button[aria-label='Siguiente']")
                while True:
                    await button.click()
                    await asyncio.sleep(0.2)
            except playwright.async_api.Error:
                pass

            return html_module.unescape(await page.content()).replace('\\', '')


def get_media_url_id(media_url_: str) -> str:
    return re.findall('/((?:(?!/).)*)\.(?:jpg|webp|mp4)', media_url_)[0]


def get_media_url_sid(media_url_: str) -> str | None:
    try:
        return re.findall('sid=(\w+)', media_url_)[0]
    except IndexError:
        pass


async def get_medias(ids: Iterable[str], audio_only=False) -> OrderedSet[Media]:
    medias: OrderedSet[Media] = OrderedSet()

    if not (urls := make_urls(OrderedSet(ids))):
        return medias

    for url in urls:
        medias |= filter_media_urls(find_media_urls(await get_html(url)))

    if not medias:
        raise InstagramMediaNotFoundError

    if audio_only:
        medias = await functions.filter_audios(medias)

    return medias


async def get_medias_v2(ids: Iterable[str], audio_only=False) -> OrderedSet[Media]:
    medias: OrderedSet[Media] = OrderedSet()

    if not (urls := make_urls(OrderedSet(ids))):
        return medias

    async with aiohttp.ClientSession() as session:
        headers = {"User-Agent": f"user-agent: {random.choice(constants.GOOGLE_BOT_USER_AGENTS)}"}
        for url in urls:
            try:
                html = await flanautils.get_request(url, headers=headers, session=session)
                medias |= filter_media_urls_v2(find_media_urls(html))
            except ResponseError:
                pass

    if not medias:
        raise InstagramMediaNotFoundError

    if audio_only:
        medias = await functions.filter_audios(medias)

    return medias


def make_urls(ids: Iterable[str]) -> list[str]:
    return [f'{constants.INSTAGRAM_BASE_URL}{constants.INSTAGRAM_CONTENT_PATH}{id}' for id in ids]
