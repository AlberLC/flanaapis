from __future__ import annotations  # todo0 remove in 3.11

from enum import Enum

from fastapi import APIRouter
from flanautils import Media
from pydantic import BaseModel

from flanaapis.scraping import instagram, tiktok, twitter

router = APIRouter(prefix='/medias')


def media_to_dict(media: Media) -> dict:
    response_media_vars = {}

    media_vars = media.to_dict(pickle_types=())
    for k, v in media_vars.items():
        if k == 'type_':
            k = 'type'
        if isinstance(v, Enum):
            v = v.name.lower()
        elif isinstance(v, Media):
            v = media_to_dict(v)
        response_media_vars[k] = v

    return response_media_vars


class Input(BaseModel):
    text: str


class MediaOutput(BaseModel):
    url: str = None
    type: str = None
    source: str = None
    title: str = None
    author: str = None
    album: str = None
    song_info: MediaOutput = None


@router.post('/', response_model=list[MediaOutput], response_model_exclude_defaults=True, response_model_exclude_unset=True)
async def get_medias(input_: Input):
    return [media_to_dict(media) for media in (*await instagram.get_medias(input_.text), *await tiktok.get_medias(input_.text), *await twitter.get_medias(input_.text))]
