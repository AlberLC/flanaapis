from __future__ import annotations  # todo0 remove when it's by default

import base64
from enum import Enum

from fastapi import APIRouter
from flanautils import Media
from pydantic import BaseModel

from flanaapis.scraping import instagram, tiktok, twitter, yt_dlp_wrapper

router = APIRouter(prefix='/medias')


def media_to_dict(media: Media) -> dict:
    response_media_vars = {}

    media_vars = media.to_dict()
    for k, v in media_vars.items():
        k = k.rstrip('_')

        match v:
            case bytes():
                v = base64.b64encode(v)
            case Enum():
                v = v.name.lower()
            case Media():
                v = media_to_dict(v)

        response_media_vars[k] = v

    return response_media_vars


class Input(BaseModel):
    text: str


class MediaOutput(BaseModel):
    url: str = None
    bytes: bytes = None
    type: str = None
    source: str = None
    title: str = None
    author: str = None
    album: str = None
    song_info: MediaOutput = None


@router.post('/', response_model=list[MediaOutput], response_model_exclude_defaults=True, response_model_exclude_unset=True)
async def get_medias(input_: Input):
    return [media_to_dict(media) for media in (
        *await twitter.get_medias(twitter.find_ids(input_.text)),
        *await instagram.get_medias(instagram.find_ids(input_.text)),
        *await tiktok.get_medias(await tiktok.find_ids(input_.text), tiktok.find_download_urls(input_.text)),
        *await yt_dlp_wrapper.get_medias(input_.text)
    )]
