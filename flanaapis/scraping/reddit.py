import html
import pathlib
import re
from collections.abc import Iterable

import aiohttp
import flanautils
import yt_dlp
from flanautils import Media, MediaType, OrderedSet, Source

from flanaapis.exceptions import RedditMediaNotFoundError, ResponseError
from flanaapis.scraping import functions, yt_dlp_wrapper

BASE_URL = 'https://www.reddit.com/'
CONTENT_PATH = 'comments/'


def find_ids(text: str) -> OrderedSet[str]:
    return OrderedSet(re.findall('ddit.*ments/(\w+)/', text))


async def get_medias(
    ids: Iterable[str],
    audio_only=False,
    preferred_video_codec: str = None,
    preferred_extension: str = None,
    timeout_for_media: int | float = None
) -> OrderedSet[Media]:
    medias: OrderedSet[Media] = OrderedSet()

    if not (urls := make_urls(OrderedSet(ids))):
        return medias

    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                data = await flanautils.get_request(url, session=session)
                medias |= await get_medias_from_data(
                    data,
                    audio_only,
                    preferred_video_codec,
                    preferred_extension,
                    timeout_for_media
                )
            except ResponseError:
                pass

    if not medias:
        raise RedditMediaNotFoundError

    if audio_only:
        medias = await functions.filter_audios(medias)

    return medias


async def get_medias_from_data(
    data: list[dict],
    audio_only=False,
    preferred_video_codec: str = None,
    preferred_extension: str = None,
    timeout: int | float = None
) -> OrderedSet[Media]:
    medias = OrderedSet()

    data = data[0]['data']['children'][0]['data']

    # image
    if data.get('post_hint') == 'image':
        extension = pathlib.Path(data['url']).suffix.strip('.')
        medias.add(Media(html.unescape(data['url']), MediaType.IMAGE, extension, Source.REDDIT))

    # images / gifs
    if data.get('media_metadata'):
        if data.get('gallery_data'):
            media_ids = (media_data['media_id'] for media_data in data['gallery_data']['items'])
        else:
            media_ids = data['media_metadata'].keys()
        for media_id in media_ids:
            media_data = data['media_metadata'][media_id]
            if (url := yt_dlp.utils.traverse_obj(media_data, ('s', 'u'))) and isinstance(url, str):
                medias.add(Media(html.unescape(url), MediaType.IMAGE, 'jpg', Source.REDDIT))
            elif url := yt_dlp.utils.traverse_obj(media_data, ('s', 'gif')):
                medias.add(Media(html.unescape(url), MediaType.GIF, 'gif', Source.REDDIT))
            elif url := yt_dlp.utils.traverse_obj(media_data, ('s', 'mp4')):
                medias.add(Media(html.unescape(url), MediaType.VIDEO, 'mp4', Source.REDDIT))

    internal_hosted_video_urls = OrderedSet()
    internal_hosted_video_urls.add(yt_dlp.utils.traverse_obj(data, ('media', 'reddit_video', 'fallback_url')))
    internal_hosted_video_urls.add(yt_dlp.utils.traverse_obj(data, ('secure_media', 'reddit_video', 'fallback_url')))
    internal_hosted_video_urls -= None
    if internal_hosted_video_urls:
        # internal hosted videos
        for internal_hosted_video_url in internal_hosted_video_urls:
            video_url = html.unescape(internal_hosted_video_url)
            audio_url = re.sub('_\d+\.mp4', '_audio.mp4', video_url)
            video_bytes = await flanautils.get_request(video_url)
            try:
                audio_bytes = await flanautils.get_request(audio_url)
            except ResponseError:
                bytes_ = video_bytes
            else:
                bytes_ = await flanautils.merge(video_bytes, audio_bytes)
            medias.add(Media(bytes_, MediaType.VIDEO, source=Source.REDDIT))
    else:
        # external media
        if any((data.get('media'), data.get('secure_media'), data.get('media_embed'), data.get('secure_media_embed'))):
            medias.add(
                await yt_dlp_wrapper.get_media(
                    html.unescape(data['url']),
                    audio_only,
                    preferred_video_codec,
                    preferred_extension,
                    timeout
                )
            )

    return medias


def make_urls(ids: Iterable[str]) -> list[str]:
    return [f'{BASE_URL}{CONTENT_PATH}{id}.json' for id in ids]
