import html
import pathlib
import re
from collections.abc import Iterable

import aiohttp
import flanautils
import yt_dlp
from flanautils import Media, MediaType, OrderedSet, Source

from flanaapis.exceptions import RedditMediaNotFoundError, ResponseError
from flanaapis.scraping import constants, functions, instagram, tiktok, twitter


def find_ids(text: str) -> OrderedSet[str]:
    return OrderedSet(re.findall(r'ddit.*ments/(\w+)/', text))


async def get_medias(
    ids: Iterable[str],
    preferred_video_codec: str = None,
    preferred_extension: str = None,
    force=False,
    audio_only=False,
    timeout_for_media: int | float = None
) -> OrderedSet[Media]:
    medias: OrderedSet[Media] = OrderedSet()

    if not (urls := make_urls(OrderedSet(ids))):
        return medias

    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                data = await flanautils.get_request(url, session=session)
            except ResponseError:
                continue

            data = data[0]['data']['children'][0]['data']
            medias |= await get_medias_from_data(
                data,
                preferred_video_codec,
                preferred_extension,
                force,
                audio_only,
                timeout_for_media
            )

    if not medias:
        raise RedditMediaNotFoundError

    if audio_only:
        medias = await functions.filter_audios(medias)

    return medias


async def get_medias_from_data(
    data: dict,
    preferred_video_codec: str = None,
    preferred_extension: str = None,
    force=False,
    audio_only=False,
    timeout: int | float = None
) -> OrderedSet[Media]:
    medias = OrderedSet()

    for crosspost_data in data.get('crosspost_parent_list', ()):
        medias |= await get_medias_from_data(crosspost_data)

    data['url'] = html.unescape(data['url'])

    # image
    if data.get('post_hint') == 'image':
        extension = pathlib.Path(data['url']).suffix.strip('.')
        medias.add(Media(data['url'], MediaType.IMAGE, extension, Source.REDDIT))

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

    # internal hosted videos
    internal_hosted_video_urls = OrderedSet()
    internal_hosted_video_urls.add(yt_dlp.utils.traverse_obj(data, ('media', 'reddit_video', 'fallback_url')))
    internal_hosted_video_urls.add(yt_dlp.utils.traverse_obj(data, ('secure_media', 'reddit_video', 'fallback_url')))
    internal_hosted_video_urls -= None
    if internal_hosted_video_urls:
        for internal_hosted_video_url in internal_hosted_video_urls:
            video_url = html.unescape(internal_hosted_video_url)
            audio_url = re.sub(r'_\d+\.mp4', '_audio.mp4', video_url)
            try:
                video_bytes = await flanautils.get_request(video_url)
            except ResponseError:
                continue
            try:
                audio_bytes = await flanautils.get_request(audio_url)
            except ResponseError:
                bytes_ = video_bytes
            else:
                bytes_ = await flanautils.merge(video_bytes, audio_bytes)
            medias.add(Media(bytes_, MediaType.VIDEO, source=Source.REDDIT))

    # external media
    if (
        not data.get('is_self')
        and
        data.get('post_hint') != 'image'
        and
        not data.get('is_gallery')
        and
        not internal_hosted_video_urls
        and
        data['url']
    ):
        if 'instagram' in data['url']:
            medias |= await instagram.get_medias(instagram.find_ids(data['url']))
        elif 'tiktok' in data['url']:
            medias |= await tiktok.get_medias(
                await tiktok.find_users_and_ids(data['url']),
                tiktok.find_download_urls(data['url']),
                preferred_video_codec,
                preferred_extension,
                force,
                audio_only,
                timeout
            )
        elif 'twitter' in data['url']:
            medias |= await twitter.get_medias(twitter.find_ids(data['url']))
        elif not data.get('is_reddit_media_domain'):
            medias.add(Media(data['url']))

    return medias


def make_urls(ids: Iterable[str]) -> list[str]:
    return [f'{constants.REDDIT_BASE_URL}{constants.REDDIT_CONTENT_PATH}{id}.json' for id in ids]
