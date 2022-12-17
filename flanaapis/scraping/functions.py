from typing import Iterable

import flanautils
from flanautils import Media, MediaType, OrderedSet


async def filter_audios(medias: Iterable[Media]) -> OrderedSet[Media]:
    filtered_medias = OrderedSet()

    for media in medias:
        if not media.content:
            continue

        if media.type_ is MediaType.VIDEO:
            try:
                bytes_ = await flanautils.to_mp3(media.bytes_ or await flanautils.get_request(media.url))
            except ValueError:
                continue
            else:
                extension = 'mp3'
        elif media.type_ is MediaType.AUDIO:
            bytes_ = media.bytes_
            extension = media.extension
        else:
            continue

        new_media = media.deep_copy()
        new_media.url = None
        new_media.bytes_ = bytes_
        new_media.type_ = MediaType.AUDIO
        new_media.extension = extension
        filtered_medias.add(new_media)

    return filtered_medias
