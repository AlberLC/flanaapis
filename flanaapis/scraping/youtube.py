import asyncio
import pathlib
import re
import subprocess
import uuid
from typing import Iterable

import pytube
from flanautils import Media, MediaType, OrderedSet, Source

YOUTUBE_BASE_URL = 'https://www.youtube.com/watch?v='


def find_youtube_ids(text: str) -> OrderedSet[str]:
    return OrderedSet(re.findall(r'(?:v=|shorts/)(\w+)', text))


def make_youtube_urls(ids: Iterable[str]) -> list[str]:
    return [f'{YOUTUBE_BASE_URL}{id}' for id in ids]


async def get_medias(text: str) -> OrderedSet[Media]:
    medias: OrderedSet[Media] = OrderedSet()

    if not (youtube_urls := make_youtube_urls(find_youtube_ids(text))):
        return medias

    for youtube_url in youtube_urls:
        try:
            medias.add(Media(await video_bytes(youtube_url), MediaType.VIDEO, Source.YOUTUBE))
        except ValueError:
            medias.add(Media(type_=MediaType.ERROR, source=Source.YOUTUBE))

    return medias


async def video_bytes(url: str) -> bytes:
    yt = pytube.YouTube(url)

    video_stream = yt.streams.filter(type='video').order_by('resolution').order_by('filesize').desc().first()
    audio_mp3_stream = yt.streams.filter(type='audio', subtype='mp3').order_by('bitrate').desc().first()
    audio_mp4_stream = yt.streams.filter(type='audio', subtype='mp4').order_by('bitrate').desc().first()
    audio_stream = audio_mp3_stream if getattr(audio_mp3_stream, 'bitrate', 0) >= getattr(audio_mp4_stream, 'bitrate', 0) else audio_mp4_stream

    video_file_name = f'{id(video_stream)}.{video_stream.subtype}'
    audio_file_name = f'{id(audio_stream)}.{audio_stream.subtype}'
    output_file_name = f'{str(uuid.uuid1())}.mp4'

    video_stream.download(filename=video_file_name)
    audio_stream.download(filename=audio_file_name)

    process = await asyncio.create_subprocess_exec('ffmpeg', '-y', '-i', video_file_name, '-i', audio_file_name, '-c', 'copy', output_file_name, stderr=subprocess.DEVNULL)
    await process.wait()

    with open(output_file_name, 'rb') as file:
        video_bytes_ = file.read()

    pathlib.Path(video_file_name).unlink(missing_ok=True)
    pathlib.Path(audio_file_name).unlink(missing_ok=True)
    pathlib.Path(output_file_name).unlink(missing_ok=True)

    return video_bytes_
