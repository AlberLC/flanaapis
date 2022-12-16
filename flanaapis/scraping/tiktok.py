import re
from typing import Iterable

import flanautils
from flanautils import Media, MediaType, OrderedSet, Source

from flanaapis.scraping import constants, functions


def find_download_urls(text: str) -> list[str]:
    partial_download_urls = re.findall(r'web\.tiktok\.com.+=&vr=', text)
    return [f'https://v16-{partial_download_url}' for partial_download_url in partial_download_urls]


async def find_ids(text: str) -> OrderedSet[str]:
    mobile_ids = re.findall(r'vm\.tiktok\.com/(\w+)', text)
    mobile_tiktok_urls = [f'https://vm.tiktok.com/{mobile_id}/' for mobile_id in mobile_ids]
    tiktok_urls = [str((await flanautils.get_request(mobile_tiktok_url, headers={'User-Agent': constants.USER_AGENT}, return_response=True)).url) for mobile_tiktok_url in mobile_tiktok_urls]
    text = f"{text}{''.join(tiktok_urls)}"

    return OrderedSet(re.findall(r'tok.*v(?:ideo)?/(\d+)', text))


async def get_download_url_medias(download_urls: Iterable[str] = (), audio_only=False) -> OrderedSet[Media]:
    medias: OrderedSet[Media] = OrderedSet()

    if not download_urls:
        return medias

    for download_url in OrderedSet(download_urls):
        medias.add(Media(download_url, MediaType.VIDEO, 'mp4', Source.TIKTOK))

    if audio_only:
        medias = await functions.filter_audios(medias)

    return medias
