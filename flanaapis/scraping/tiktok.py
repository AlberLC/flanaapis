import asyncio
import concurrent.futures
import re
from typing import Iterable

import flanautils
from TikTokApi import TikTokApi
from flanautils import Media, MediaType, OrderedSet, Source

from flanaapis.exceptions import TikTokMediaNotFoundError
from flanaapis.scraping import constans


def find_download_urls(text: str) -> list[str]:
    partial_download_urls = re.findall(r'web\.tiktok\.com.+=&vr=', text)
    return [f'https://v16-{partial_download_url}' for partial_download_url in partial_download_urls]


async def find_tiktok_ids(text: str) -> OrderedSet[str]:
    mobile_ids = re.findall(r'vm\.tiktok\.com/(\w+)', text)
    mobile_tiktok_urls = [f'https://vm.tiktok.com/{mobile_id}/' for mobile_id in mobile_ids]
    tiktok_urls = [str((await flanautils.get_request(mobile_tiktok_url, headers={'User-Agent': constans.USER_AGENT}, return_response=True)).url) for mobile_tiktok_url in mobile_tiktok_urls]
    text = f"{text}{''.join(tiktok_urls)}"

    return OrderedSet(re.findall(r'v(?:ideo)?/(\d+)', text))


def get_media_dict_by_id(tiktok_id: str) -> dict:
    api: TikTokApi = TikTokApi.get_instance()

    tiktok_data = api.get_tiktok_by_id(tiktok_id)
    video_data = tiktok_data['itemInfo']['itemStruct']['video']
    song_data = tiktok_data['itemInfo']['itemStruct']['music']
    try:
        download_url = video_data['playAddr']
    except KeyError:
        download_url = video_data['downloadAddr']

    song_info = Media(
        song_data['playUrl'],
        MediaType.AUDIO,
        Source.TIKTOK,
        song_data['title'],
        song_data['authorName'],
        song_data['album']
    ) if song_data else None

    return Media(download_url, MediaType.VIDEO, Source.TIKTOK, song_info=song_info).to_dict()


async def get_medias(tiktok_ids: Iterable[str], download_urls: Iterable[str] = ()) -> OrderedSet[Media]:
    tiktok_ids = OrderedSet(tiktok_ids)

    medias: OrderedSet[Media] = OrderedSet()

    if not tiktok_ids and not download_urls:
        return medias

    with concurrent.futures.ProcessPoolExecutor(max_workers=3) as pool:
        for tiktok_id in tiktok_ids:
            result_dict = await asyncio.get_running_loop().run_in_executor(pool, get_media_dict_by_id, tiktok_id)
            medias.add(Media.from_dict(result_dict, lazy=False))

    for download_url in download_urls:
        medias.add(Media(download_url, MediaType.VIDEO, Source.TIKTOK))

    if not medias:
        raise TikTokMediaNotFoundError

    return medias
