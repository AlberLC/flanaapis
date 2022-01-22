import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
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


def find_instagram_ids(text: str) -> OrderedSet[str]:
    return OrderedSet(re.findall(r'/(?:p|reel|tv)/(.{11})', text))


def make_instagram_urls(codes: Iterable[str]) -> list[str]:
    return [f'{INSTAGRAM_BASE_URL}{INSTAGRAM_CONTENT_PATH}{code}' for code in codes]


def find_media_urls(text: str) -> list[str]:
    return re.findall(r'https.*?sid=\w{6}', text)


def find_media_mark(text: str) -> str:
    try:
        return re.findall(r'\w+\.(?:jpg|mp4)\?', text)[0]
    except IndexError:
        return ''


def find_media_size(text: str) -> float:
    try:
        return float(re.findall(r'/[sp](\d+)x\d+/', text)[0])
    except IndexError:
        return float('inf')


def select_content_urls(media_urls: list[str]) -> OrderedSet[Media]:
    @dataclass(unsafe_hash=True)
    class CandidateUrl:
        position: int = field(compare=False, hash=False)
        url: str
        size: float = field(default=float('inf'), compare=False, hash=False)

    video_urls = defaultdict(OrderedSet)
    image_urls = defaultdict(OrderedSet)
    ignored_image_marks = []

    media_position = 0
    last_was_video = False
    for media_url in reversed(media_urls):
        if (
                re.findall(r'-19/s\d+x\d+', media_url)
                or
                '-19/' in media_url
                or
                '/sh' in media_url
                or
                'mp4?_nc_ht' in media_url
                or
                '&oh=00_AT_' in media_url
                or
                'scontent-mad1-1.' not in media_url
                or
                not re.findall(r'-\d{2}(/\w{3})?(/[sp]\d+x\d+)?/\w+\.(jpg|mp4)\?', media_url)
        ):
            continue

        if '.mp4' in media_url:
            if last_was_video:
                continue

            media_mark = find_media_mark(media_url)
            video_urls[media_mark].add(CandidateUrl(media_position, media_url, find_media_size(media_url)))
            media_position += 1
            last_was_video = True
        elif '.jpg' in media_url:
            media_mark = find_media_mark(media_url)

            if last_was_video:
                ignored_image_marks.append(media_mark)
            last_was_video = False

            if media_mark not in ignored_image_marks:
                image_urls[media_mark].add(CandidateUrl(media_position, media_url, find_media_size(media_url)))
                media_position += 1

    best_candidate_urls: list[CandidateUrl] = []
    for image_mark, image_urls_ in image_urls.items():
        best_candidate_urls.append(sorted(image_urls_, key=lambda u: u.size, reverse=True)[0])
    for video_mark, video_urls_ in video_urls.items():
        best_candidate_urls.append(video_urls_[0])

    content_medias = OrderedSet()
    for best_candidate_url in sorted(best_candidate_urls, key=lambda u: u.position):
        url = best_candidate_url.url
        content_medias.add(Media(url, MediaType.IMAGE if '.jpg' in url else MediaType.VIDEO, Source.INSTAGRAM))

    content_medias.reverse()  # because was reversed in the for
    return content_medias


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
