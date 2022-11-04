import random
import re
from typing import Iterable

import aiohttp
import flanautils
from flanautils import Media, MediaType, OrderedSet, Source

from flanaapis.exceptions import InstagramMediaNotFoundError, ResponseError
from flanaapis.scraping import constants, functions

INSTAGRAM_BASE_URL = 'https://www.instagram.com/'
INSTAGRAM_LOGIN_URL = INSTAGRAM_BASE_URL + 'accounts/login/ajax/'
INSTAGRAM_CONTENT_PATH = 'p/'


def find_instagram_ids(text: str) -> OrderedSet[str]:
    return OrderedSet(re.findall(r'gram\.com/.+?/(.{11})', text))


def find_media_urls(text: str) -> list[str]:
    return re.findall(r'https(?:(?!https).)*?sid=\w{6}', text)


def get_content_media(media_urls: list[str]) -> OrderedSet[Media]:
    last_url = ''
    final_urls = OrderedSet()
    thumbnail_urls = OrderedSet()
    for media_url in media_urls:
        if (
                r'\/' in media_url
                or
                not re.findall(r'\.(?:jpg|webp)\?stp=dst-jpg_e[13]5&.+cache', media_url)
                and
                not re.findall('e0&cb.*cache', media_url)
                and
                not re.findall('jpg.*[ps]1080', media_url)
                and
                '.mp4?efg' not in media_url
                and
                '.mp4?_nc_ht=' not in media_url
        ):
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
    medias: OrderedSet[Media] = OrderedSet()

    if not (instagram_urls := make_instagram_urls(OrderedSet(instagram_ids))):
        return medias

    async with aiohttp.ClientSession() as session:
        headers = {"User-Agent": f"user-agent: {random.choice(constants.GOOGLE_BOT_USER_AGENTS)}"}
        for instagram_url in instagram_urls:
            try:
                html = await flanautils.get_request(instagram_url, headers=headers, session=session)
                new_medias = get_content_media(find_media_urls(html))
                for media in new_medias:
                    media.bytes_ = await flanautils.get_request(media.url, headers=headers, session=session)
                medias |= new_medias
            except ResponseError:
                pass

    if not medias:
        raise InstagramMediaNotFoundError

    if audio_only:
        medias = await functions.filter_audios(medias)

    return medias


def make_instagram_urls(ids: Iterable[str]) -> list[str]:
    return [f'{INSTAGRAM_BASE_URL}{INSTAGRAM_CONTENT_PATH}{id}' for id in ids]
