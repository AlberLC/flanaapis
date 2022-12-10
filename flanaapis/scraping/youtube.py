import asyncio
import multiprocessing
import pathlib
import re
import subprocess
import uuid
from typing import Iterable

import flanautils
import pytube
import pytube.exceptions
from flanautils import Media, MediaType, OrderedSet, Source

from flanaapis.exceptions import YouTubeMediaNotFoundError

YOUTUBE_BASE_URL = 'https://www.youtube.com/watch?v='


def download_multiprocess(stream, file_name):
    stream.download(filename=file_name)


def find_youtube_ids(text: str) -> OrderedSet[str]:
    # https://www.youtube.com/watch?v=xTYy_CaN0Us
    # https://youtu.be/hrTKAuD-ulc
    # https://youtube.com/shorts/L0cK0VPC3jQ?feature=share
    # https://www.youtube.com/embed/yntdjlWyH9Y?feature=oembed&enablejsapi=1%5C
    return OrderedSet(re.findall(r'(?:tube\.com/(?:watch\?v=|shorts/|embed/)|tu\.be/)([\w-]+)', text))


def make_youtube_urls(ids: Iterable[str]) -> list[str]:
    return [f'{YOUTUBE_BASE_URL}{id}' for id in ids]


async def get_media(url: str, audio_only=False, timeout: int | float = None) -> Media:
    async def run_process(process_: multiprocessing.Process):
        process_.start()
        while process_.is_alive():
            await asyncio.sleep(1)

    async def wait_for_process(process_: multiprocessing.Process):
        try:
            await asyncio.wait_for(run_process(process_), timeout)
        except asyncio.TimeoutError:
            process_.terminate()
            raise

    yt = pytube.YouTube(url)
    audio_stream = yt.streams.filter(type='audio', subtype='mp4').order_by('bitrate').desc().first()
    audio_file_name = f'{id(audio_stream)}.{audio_stream.subtype}'
    await wait_for_process(multiprocessing.Process(target=download_multiprocess, args=(audio_stream, audio_file_name)))

    if audio_only:
        with open(audio_file_name, 'rb') as file:
            bytes_ = file.read()
        pathlib.Path(audio_file_name).unlink(missing_ok=True)
        return Media(
            await flanautils.edit_metadata(await flanautils.to_mp3(bytes_), {'title': audio_stream.title}, overwrite=False),
            MediaType.AUDIO,
            'mp3',
            Source.YOUTUBE,
            title=audio_stream.title
        )

    video_stream = yt.streams.filter(type='video').order_by('bitrate').order_by('resolution').desc().first()
    video_file_name = f'{id(video_stream)}.{video_stream.subtype}'
    output_file_name = f'{str(uuid.uuid1())}.mp4'
    await wait_for_process(multiprocessing.Process(target=download_multiprocess, args=(video_stream, video_file_name)))

    args = ['ffmpeg', '-y', '-i', video_file_name, '-i', audio_file_name]
    if re.findall(r'av01\.0\.\d\dM\.0\d', video_stream.video_codec):
        args.extend(['-c:v', 'libx264', '-preset', 'veryfast', '-b:v', str(video_stream.bitrate), '-r', str(video_stream.fps), '-c:a', 'copy', output_file_name])
    else:
        args.extend(['-c', 'copy', output_file_name])
    process = await asyncio.create_subprocess_exec(*args, stderr=subprocess.DEVNULL)
    await process.wait()

    with open(output_file_name, 'rb') as file:
        video_bytes_ = file.read()

    pathlib.Path(audio_file_name).unlink(missing_ok=True)
    pathlib.Path(video_file_name).unlink(missing_ok=True)
    pathlib.Path(output_file_name).unlink(missing_ok=True)

    return Media(video_bytes_, MediaType.VIDEO, 'mp4', Source.YOUTUBE)


async def get_medias(youtube_ids: Iterable[str], audio_only=False, timeout_for_media: int | float = None) -> OrderedSet[Media]:
    youtube_ids = OrderedSet(youtube_ids)

    medias: OrderedSet[Media] = OrderedSet()

    if not (youtube_urls := make_youtube_urls(youtube_ids)):
        return medias

    for youtube_url in youtube_urls:
        try:
            medias.add(await get_media(youtube_url, audio_only, timeout_for_media))
        except (asyncio.TimeoutError, pytube.exceptions.LiveStreamError):
            pass

    if not medias:
        raise YouTubeMediaNotFoundError

    return medias
