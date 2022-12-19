import re
from typing import Iterable

import flanautils
from flanautils import Media, MediaType, OrderedSet, Source

from flanaapis.exceptions import TikTokMediaNotFoundError
from flanaapis.scraping import constants, functions, yt_dlp_wrapper


async def _find_ids(text: str, pattern: str) -> OrderedSet[str]:
    return OrderedSet(re.findall(pattern, text), re.findall(pattern, ''.join(await get_desktop_urls(text))))


def find_download_urls(text: str) -> list[str]:
    partial_download_urls = re.findall(r'web\.tiktok\.com.+=&vr=', text)
    return [f'https://v16-{partial_download_url}' for partial_download_url in partial_download_urls]


async def find_ids(text: str) -> OrderedSet[str]:
    return await _find_ids(text, 'tok.*[tv](?:ideo)?/(\d+)')


async def find_users_and_ids(text: str) -> OrderedSet[str]:
    return await _find_ids(text, 'tok\.com/(.*/\d+)')


async def get_desktop_urls(text: str) -> OrderedSet[str]:
    mobile_ids = re.findall(r'vm\.tiktok\.com/(\w+)', text)
    mobile_urls = [f'https://vm.tiktok.com/{mobile_id}/' for mobile_id in mobile_ids]
    'https://www.tiktok.com/t/ZTRVN7RgG/'
    t_ids = re.findall(r'tok.*t/(\w+)', text)
    t_urls = [f'{constants.TIKTOK_BASE_URL}t/{t_id}' for t_id in t_ids]
    return OrderedSet([str((await flanautils.get_request(mobile_url, headers={'User-Agent': constants.USER_AGENT}, return_response=True)).url) for mobile_url in mobile_urls + t_urls])


async def get_medias(
    users_and_ids: Iterable[str] = (),
    download_urls: Iterable[str] = (),
    audio_only=False,
    preferred_video_codec: str = None,
    preferred_extension: str = None,
    force_gif_download=False,
    timeout_for_media: int | float = None
) -> OrderedSet[Media]:
    medias: OrderedSet[Media] = OrderedSet()

    urls = make_urls(OrderedSet(users_and_ids))
    download_urls = OrderedSet(download_urls)

    if not urls and not download_urls:
        return medias

    for url in urls:
        if media := await yt_dlp_wrapper.get_media(url, preferred_video_codec, preferred_extension, audio_only, force_gif_download, timeout_for_media):
            medias.add(media)

    for download_url in OrderedSet(download_urls):
        medias.add(Media(download_url, MediaType.VIDEO, 'mp4', Source.TIKTOK))

    if not medias:
        raise TikTokMediaNotFoundError

    if audio_only:
        medias = await functions.filter_audios(medias)

    return medias


def make_urls(users_and_ids: Iterable[str]) -> list[str]:
    return [f'{constants.TIKTOK_BASE_URL}{user_and_id}' for user_and_id in users_and_ids]
