import os
import re
from typing import Iterable

import aiohttp
import flanautils
from flanautils import Media, MediaType, OrderedSet, ResponseError, Source, return_if_first_empty

from flanaapis.exceptions import TwitterMediaNotFoundError
from flanaapis.scraping import functions

ENDPOINT_V1 = 'https://api.twitter.com/1.1/statuses/lookup.json'
ENDPOINT_V2 = 'https://api.twitter.com/2/tweets'


@return_if_first_empty(OrderedSet)
def find_ids(text: str | list[str]) -> OrderedSet[str]:
    if isinstance(text, list):
        text = ''.join(text)
    return OrderedSet(re.findall(r'atus/(\d+)', text))


async def get_medias(ids: Iterable[str], audio_only=False) -> OrderedSet[Media]:
    ids = OrderedSet(ids)

    medias: OrderedSet[Media] = OrderedSet()

    while referenced_ids := find_ids(await get_referenced_tweet_urls(ids)) - ids:
        ids |= referenced_ids
    if not ids:
        return medias

    try:
        tweets_data = await get_tweet_data(ENDPOINT_V1, params={'id': ','.join(ids), 'tweet_mode': 'extended'})
    except aiohttp.ClientError:
        tweets_data = []

    for tweet_data in tweets_data:
        try:
            medias_data = tweet_data['extended_entities']['media']
        except KeyError:
            pass
        else:
            medias |= get_tweet_medias(medias_data)

    if not medias:
        raise TwitterMediaNotFoundError()

    if audio_only:
        medias = await functions.filter_audios(medias)

    return medias


@return_if_first_empty([])
async def get_referenced_tweet_urls(ids: Iterable[str]) -> list[str]:
    try:
        tweets_data = await get_tweet_data(ENDPOINT_V2, params={'ids': ','.join(ids), 'expansions': 'attachments.media_keys', 'media.fields': 'media_key', 'tweet.fields': 'entities'})
    except ResponseError:
        return []

    referenced_tweet_urls = []
    for tweet_data in tweets_data:
        try:
            urls = tweet_data['entities']['urls']
        except (KeyError, TypeError):
            continue

        for url in urls:
            try:
                referenced_tweet_urls.append(url['expanded_url'])
            except KeyError:
                continue

    return referenced_tweet_urls


async def get_tweet_data(url: str, params: dict) -> dict:
    data = await flanautils.get_request(url, params, headers={'Authorization': f"Bearer {os.environ['TWITTER_BEARER_TOKEN']}"})
    try:
        return data['data']
    except (TypeError, KeyError):
        return data


def get_tweet_medias(medias_data: dict) -> OrderedSet[Media]:
    medias = OrderedSet()
    for media_data in medias_data:
        if media_data['type'] == 'photo':
            medias.add(Media(media_data['media_url_https'], MediaType.IMAGE, 'jpg', Source.TWITTER))
            continue

        try:
            variants = media_data['video_info']['variants']
        except KeyError:
            continue

        max_bitrate = float('-inf')
        max_bitrate_url = ''
        for variant in variants:
            try:
                bitrate = variant['bitrate']
            except KeyError:
                continue

            if bitrate > max_bitrate:
                max_bitrate = bitrate
                max_bitrate_url = variant['url']

        if media_data['type'] == 'video':
            media_type = MediaType.VIDEO
            extension = 'mp4'
        else:
            media_type = MediaType.GIF
            extension = 'gif'
        medias.add(Media(max_bitrate_url, media_type, extension, Source.TWITTER))

    return medias
