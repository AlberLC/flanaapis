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
            pass
        else:
            filtered_medias.add(Media(bytes_, MediaType.AUDIO, 'mp3'))

    return filtered_medias
