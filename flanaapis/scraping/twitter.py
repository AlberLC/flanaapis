import os
import re
from typing import Iterable

import aiohttp
import flanautils
from flanautils import Media, MediaType, OrderedSet, Source, return_if_first_empty

from flanaapis.exceptions import ResponseError, TwitterMediaNotFoundError

TWITTER_ENDPOINT_V1 = 'https://api.twitter.com/1.1/statuses/lookup.json'
TWITTER_ENDPOINT_V2 = 'https://api.twitter.com/2/tweets'
BEARER_TOKEN = os.environ['TWITTER_BEARER_TOKEN']
HEADERS = {'Authorization': f'Bearer {BEARER_TOKEN}'}


@return_if_first_empty(OrderedSet)
def find_tweet_ids(text: str | list[str]) -> OrderedSet[str]:
    if isinstance(text, list):
        text = ''.join(text)
    return OrderedSet(re.findall(r'atus/(\d+)', text))


async def get_tweets_data(url: str, params: dict) -> dict:
    data = await flanautils.get_request(url, params, headers=HEADERS)
    try:
        return data['data']
    except (TypeError, KeyError):
        return data


@return_if_first_empty([])
async def get_referenced_tweets(tweet_ids: Iterable[str]) -> list[str]:
    try:
        tweets_data = await get_tweets_data(TWITTER_ENDPOINT_V2, params={'ids': ','.join(tweet_ids), 'expansions': 'attachments.media_keys', 'media.fields': 'media_key', 'tweet.fields': 'entities'})
    except ResponseError:
        return []

    referenced_tweets = []
    for tweet in tweets_data:
        try:
            urls = tweet['entities']['urls']
        except (KeyError, TypeError):
            continue

        for url in urls:
            try:
                referenced_tweets.append(url['expanded_url'])
            except KeyError:
                continue

    return referenced_tweets


def get_all_medias_from_tweet(tweet_medias_data: dict) -> OrderedSet[Media]:
    tweet_medias = OrderedSet()
    for tweet_media_data in tweet_medias_data:
        if tweet_media_data['type'] == 'photo':
            tweet_medias.add(Media(tweet_media_data['media_url_https'], MediaType.IMAGE, Source.TWITTER))
            continue

        try:
            variants = tweet_media_data['video_info']['variants']
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

        tweet_medias.add(Media(max_bitrate_url, MediaType.VIDEO if tweet_media_data['type'] == 'video' else MediaType.GIF, Source.TWITTER))

    return tweet_medias


async def get_medias(text: str) -> OrderedSet[Media]:
    medias: OrderedSet[Media] = OrderedSet()

    tweet_ids = find_tweet_ids(text)
    while referenced_tweet_ids := find_tweet_ids(await get_referenced_tweets(tweet_ids)) - tweet_ids:
        tweet_ids |= referenced_tweet_ids
    if not tweet_ids:
        return medias

    try:
        tweets_data = await get_tweets_data(TWITTER_ENDPOINT_V1, params={'id': ','.join(tweet_ids), 'tweet_mode': 'extended'})
    except aiohttp.ClientError:
        tweets_data = []

    for tweet_data in tweets_data:
        try:
            medias_data = tweet_data['extended_entities']['media']
        except KeyError:
            pass
        else:
            medias |= get_all_medias_from_tweet(medias_data)

    if not medias:
        raise TwitterMediaNotFoundError()

    return medias
