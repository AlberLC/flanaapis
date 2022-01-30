import os
import re
from typing import Iterable

import aiohttp
import flanautils
from flanautils import Media, MediaType, OrderedSet, Source

from flanaapis.exceptions import InstagramLoginError, InstagramMediaNotFoundError, ResponseError

INSTAGRAM_BASE_URL = 'https://www.instagram.com/'
INSTAGRAM_LOGIN_URL = INSTAGRAM_BASE_URL + 'accounts/login/ajax/'
INSTAGRAM_USER_AGENT = 'Instagram 123.0.0.21.114 (iPhone; CPU iPhone OS 11_4 like Mac OS X; en_US; en-US; scale=2.00; 750x1334) AppleWebKit/605.1.15'
# INSTAGRAM_USER_AGENT_2 = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36'
INSTAGRAM_CONTENT_PATH = 'p/'

cookies = None


def find_instagram_ids(text: str) -> OrderedSet[str]:
    return OrderedSet(re.findall(r'/(?:p|reel|tv)/(.{11})', text))


def find_media_mark(text: str) -> str:
    try:
        return re.findall(r'[\w.]+\.(?:jpg|mp4)\?', text)[0]
    except IndexError:
        return ''


def find_media_size(text: str) -> float:
    try:
        return float(re.findall(r'/[sp](\d+)x\d+/', text)[0])
    except IndexError:
        return float('inf')


def find_media_urls(text: str) -> list[str]:
    return re.findall(r'https.*?sid=\w{6}', text)


async def get_medias(text: str) -> OrderedSet[Media]:
    medias: OrderedSet[Media] = OrderedSet()

    if not (instagram_urls := make_instagram_urls(find_instagram_ids(text))):
        return medias

    async with aiohttp.ClientSession() as session:
        if not cookies:
            await login(session)

        session._cookie_jar = cookies

        for instagram_url in instagram_urls:
            try:
                html = await flanautils.get_request(instagram_url, session=session)
            except ResponseError:
                medias.add(Media(type_=MediaType.ERROR, source=Source.INSTAGRAM))
            else:
                medias.update(select_content_urls(find_media_urls(html)))

    if not medias:
        raise InstagramMediaNotFoundError

    return medias


async def login(session: aiohttp.ClientSession):
    global cookies

    session.headers.update({'user-agent': INSTAGRAM_USER_AGENT})

    async with session.get(INSTAGRAM_BASE_URL) as cookie_response:
        session.headers.update({'x-csrftoken': cookie_response.cookies['csrftoken'].value})

    async with session.post(
            INSTAGRAM_LOGIN_URL,
            data={'username': os.environ['INSTAGRAM_USERNAME'],
                  'password': os.environ['INSTAGRAM_PASSWORD']}
    ) as login_response:
        try:
            data = await login_response.json()
        except aiohttp.ContentTypeError:
            raise InstagramLoginError(f'{login_response.status}: {login_response.reason}.')
        if not data.get('authenticated'):
            raise InstagramLoginError(f"{login_response.status}: {login_response.reason}. {data['message']}")

    cookies = session.cookie_jar


def make_instagram_urls(codes: Iterable[str]) -> list[str]:
    return [f'{INSTAGRAM_BASE_URL}{INSTAGRAM_CONTENT_PATH}{code}' for code in codes]


def select_content_urls(media_urls: list[str]) -> OrderedSet[Media]:
    was_last_image = False
    final_urls = []
    for media_url in media_urls:
        if not re.findall(r'e35/\d+', media_url) and '.mp4?efg' not in media_url:
            continue

        if '.jpg?' in media_url:
            was_last_image = True
            final_urls.append(media_url)
        elif was_last_image:
            was_last_image = False
            final_urls.pop()
            final_urls.append(media_url)

    return OrderedSet(Media(final_url, MediaType.IMAGE if '.jpg?' in final_url else MediaType.VIDEO, Source.INSTAGRAM) for final_url in final_urls)
