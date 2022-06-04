import html
import re
from typing import Iterable

import playwright
import playwright.async_api
from flanautils import Media, MediaType, OrderedSet, Source

from flanaapis.exceptions import InstagramMediaNotFoundError
from flanaapis.scraping import constans

INSTAGRAM_BASE_URL = 'https://www.instagram.com/'
INSTAGRAM_LOGIN_URL = INSTAGRAM_BASE_URL + 'accounts/login/ajax/'
INSTAGRAM_CONTENT_PATH = 'p/'

cookies = None


def find_instagram_ids(text: str) -> OrderedSet[str]:
    return OrderedSet(re.findall(r'/(?:p|reel|tv)/(.{11})', text))


def find_media_mark(text: str) -> str:
    try:
        return re.findall(r'[\w.]+\.(?:jpg|webp|mp4)\?', text)[0]
    except IndexError:
        return ''


def find_media_urls(text: str) -> list[str]:
    return re.findall(r'https(?:(?!https).)*?sid=\w{6}', text)


async def get_medias(text: str) -> OrderedSet[Media]:
    global cookies

    medias: OrderedSet[Media] = OrderedSet()

    if not (instagram_urls := make_instagram_urls(find_instagram_ids(text))):
        return medias

    async with playwright.async_api.async_playwright() as p:
        async with await p.chromium.launch() as browser:
            context = await browser.new_context(user_agent=constans.USER_AGENT_2, locale='es-ES')
            page: playwright.async_api.Page = await context.new_page()

            if cookies:
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
                medias |= select_content_urls(find_media_urls(html_content))

    if not medias:
        raise InstagramMediaNotFoundError

    return medias


async def login(page: playwright.async_api.Page):
    await page.goto('https://www.instagram.com/')
    button = page.locator("'Permitir cookies necesarias y opcionales'")
    if await button.count():
        await button.click()
    await page.fill('input[name=username]', 'flanagan0125')
    await page.fill('input[name=password]', '0125210')
    await page.click("'Entrar'")
    await page.wait_for_load_state('networkidle')
    button = page.locator("'Guardar información'")
    if await button.count():
        await button.click()
    await page.wait_for_load_state('networkidle')
    button = page.locator("'Ahora no'")
    if await button.count():
        await button.click()


def make_instagram_urls(codes: Iterable[str]) -> list[str]:
    return [f'{INSTAGRAM_BASE_URL}{INSTAGRAM_CONTENT_PATH}{code}' for code in codes]


def select_content_urls(media_urls: list[str]) -> OrderedSet[Media]:
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

    return OrderedSet(Media(final_url, MediaType.VIDEO if '.mp4?' in final_url else MediaType.IMAGE, Source.INSTAGRAM) for final_url in final_urls)
