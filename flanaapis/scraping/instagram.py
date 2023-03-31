import random
import re
from typing import Iterable

import aiohttp
import flanautils
from flanautils import Media, MediaType, OrderedSet, ResponseError, Source

from flanaapis.exceptions import InstagramMediaNotFoundError
from flanaapis.scraping import constants, functions


def find_ids(text: str) -> OrderedSet[str]:
    return OrderedSet(re.findall(r'gram\.com/.+?/(.{11})', text))


def find_media_urls(text: str) -> list[str]:
    return re.findall(r'https(?:(?!http|\"|\.insta).)*=[0-9a-fA-F]+', text)


async def get_medias(ids: Iterable[str], audio_only=False) -> OrderedSet[Media]:
    medias: OrderedSet[Media] = OrderedSet()

    if not (urls := make_urls(OrderedSet(ids))):
        return medias

    async with aiohttp.ClientSession() as session:
        headers = {"User-Agent": f"user-agent: {random.choice(constants.GOOGLE_BOT_USER_AGENTS)}"}
        for url in urls:
            try:
                html = await flanautils.get_request(url, headers=headers, session=session)
                new_medias = get_post_medias(find_media_urls(html))
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


def get_post_medias(media_urls: list[str]) -> OrderedSet[Media]:
    def get_video_id(media_url_: str) -> str:
        return re.findall('/((?:(?!/).)*)\.mp4', media_url_)[0]

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
            video_id = get_video_id(media_url)
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


def make_urls(ids: Iterable[str]) -> list[str]:
    return [f'{constants.INSTAGRAM_BASE_URL}{constants.INSTAGRAM_CONTENT_PATH}{id}' for id in ids]
