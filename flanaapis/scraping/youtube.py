import asyncio
import concurrent.futures
import pathlib
import re
import subprocess
import uuid
from typing import Iterable

import pytube
import pytube.exceptions
from flanautils import Media, MediaType, OrderedSet, Source

from flanaapis.exceptions import YouTubeMediaNotFoundError

YOUTUBE_BASE_URL = 'https://www.youtube.com/watch?v='


def find_youtube_ids(text: str) -> OrderedSet[str]:
    # https://www.youtube.com/watch?v=xTYy_CaN0Us
    # https://youtu.be/hrTKAuD-ulc
    # https://youtube.com/shorts/L0cK0VPC3jQ?feature=share
    return OrderedSet(re.findall(r'(?:tube\.com/(?:watch\?v=|shorts/)|tu\.be/)([\w-]+)', text))


def make_youtube_urls(ids: Iterable[str]) -> list[str]:
    return [f'{YOUTUBE_BASE_URL}{id}' for id in ids]


async def get_medias(youtube_ids: Iterable[str], timeout_for_media: int | float = None) -> OrderedSet[Media]:
    youtube_ids = OrderedSet(youtube_ids)

    medias: OrderedSet[Media] = OrderedSet()

    if not (youtube_urls := make_youtube_urls(youtube_ids)):
        return medias

    with concurrent.futures.ProcessPoolExecutor(max_workers=3) as pool:
        for youtube_url in youtube_urls:
            try:
                bytes_ = await asyncio.wait_for(asyncio.get_running_loop().run_in_executor(pool, video_bytes, youtube_url), timeout_for_media)
            except (asyncio.TimeoutError, pytube.exceptions.LiveStreamError):
                pass
            else:
                medias.add(Media(bytes_, MediaType.VIDEO, Source.YOUTUBE))

    if not medias:
        raise YouTubeMediaNotFoundError

    return medias


def video_bytes(url: str) -> bytes:
    yt = pytube.YouTube(url)

    video_stream = yt.streams.filter(type='video').order_by('bitrate').order_by('resolution').desc().first()
    audio_mp3_stream = yt.streams.filter(type='audio', subtype='mp3').order_by('bitrate').desc().first()
    audio_mp4_stream = yt.streams.filter(type='audio', subtype='mp4').order_by('bitrate').desc().first()
    audio_stream = audio_mp3_stream if getattr(audio_mp3_stream, 'bitrate', 0) >= getattr(audio_mp4_stream, 'bitrate', 0) else audio_mp4_stream

    video_file_name = f'{id(video_stream)}.{video_stream.subtype}'
    audio_file_name = f'{id(audio_stream)}.{audio_stream.subtype}'
    output_file_name = f'{str(uuid.uuid1())}.mp4'

    video_stream.download(filename=video_file_name)
    audio_stream.download(filename=audio_file_name)

    subprocess.run(['ffmpeg', '-y', '-i', video_file_name, '-i', audio_file_name, '-c', 'copy', output_file_name], stderr=subprocess.DEVNULL)

    with open(output_file_name, 'rb') as file:
        video_bytes_ = file.read()

    pathlib.Path(video_file_name).unlink(missing_ok=True)
    pathlib.Path(audio_file_name).unlink(missing_ok=True)
    pathlib.Path(output_file_name).unlink(missing_ok=True)

    return video_bytes_
