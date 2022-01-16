from __future__ import annotations  # todo0 remove in 3.11

from enum import Enum

from fastapi import APIRouter
from pydantic import BaseModel

from flanaapis.scraping import instagram, tiktok, twitter

router = APIRouter(prefix='/medias')


class Input(BaseModel):
    text: str


class Media(BaseModel):
    url: str = None
    type: str = None
    source: str = None
    title: str = None
    author: str = None
    album: str = None
    song_info: Media = None


@router.post('/', response_model=list[Media], response_model_exclude_defaults=True, response_model_exclude_unset=True)
async def get_medias(input_: Input):
    medias_data = []

    for media in (*await instagram.get_medias(input_.text), *await tiktok.get_medias(input_.text), *await twitter.get_medias(input_.text)):
        response_media_vars = {}

        media_vars = media.to_dict(pickle_types=())
        for k, v in media_vars.items():
            if k == 'type_':
                k = 'type'
            if isinstance(v, Enum):
                v = v.name.lower()
            response_media_vars[k] = v

        medias_data.append(response_media_vars)

    return medias_data
