from typing import Iterable

import flanautils
from flanautils import Media, MediaType, OrderedSet


async def filter_audios(medias: Iterable[Media]) -> OrderedSet[Media]:
    filtered_medias = OrderedSet()

    for media in medias:
        if not media.content:
            continue
        try:
            bytes_ = await flanautils.to_mp3(media.bytes_ or await flanautils.get_request(media.url))
        except ValueError:
            continue

        new_media = media.deep_copy()
        new_media.url = None
        new_media.bytes_ = bytes_
        new_media.type_ = MediaType.AUDIO
        new_media.extension = 'mp3'
        filtered_medias.add(new_media)

    return filtered_medias
