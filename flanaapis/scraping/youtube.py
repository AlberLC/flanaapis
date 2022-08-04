import pathlib
import re
import subprocess
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
            medias.add(Media(video_bytes(youtube_url), MediaType.VIDEO, Source.YOUTUBE))
        except ValueError:
            medias.add(Media(type_=MediaType.ERROR, source=Source.YOUTUBE))

    return medias


def video_bytes(url: str) -> bytes:
    yt = pytube.YouTube(url)

    video_stream = yt.streams.filter(type='video').order_by('resolution').order_by('filesize').desc().first()
    audio_stream = yt.streams.filter(type='audio').order_by('bitrate').desc().first()

    video_file_name = f'video.{video_stream.subtype}'
    audio_file_name = f'audio.{audio_stream.subtype}'

    video_stream.download(filename=video_file_name)
    audio_stream.download(filename=audio_file_name)

    subprocess.run(f'ffmpeg -y -i {video_file_name} -i {audio_file_name} -c copy output.mp4', stderr=subprocess.DEVNULL)

    with open('output.mp4', 'rb') as file:
        video_bytes_ = file.read()

    pathlib.Path(video_file_name).unlink(missing_ok=True)
    pathlib.Path(audio_file_name).unlink(missing_ok=True)
    pathlib.Path('output.mp4').unlink(missing_ok=True)

    return video_bytes_
