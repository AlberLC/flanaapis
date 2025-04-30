import asyncio
import pathlib
import uuid
from collections.abc import Iterable
from typing import Any

import aiohttp.client_exceptions
import flanautils
import yt_dlp
from flanautils import Media, MediaType, OrderedSet, Source

from flanaapis.scraping import constants


async def _get_media_info(
    url: str,
    output_file_stem: str,
    preferred_video_codec: str = None,
    preferred_extension: str = None,
    force=False,
    audio_only=False,
    timeout: int | float = None
) -> dict[str, str] | None:
    try:
        url = await flanautils.resolve_real_url(url)
    except (aiohttp.client_exceptions.ClientConnectorError, aiohttp.client_exceptions.InvalidURL):
        return

    options = _get_options(output_file_stem, preferred_video_codec, preferred_extension, force, audio_only)

    try:
        media_info = await flanautils.run_process(_run_youtube_dl, options, url, timeout=timeout)
    except asyncio.TimeoutError:
        media_info = None

    if not media_info:
        for path in flanautils.find_paths_by_stem(output_file_stem):
            while True:
                try:
                    path.unlink()
                except PermissionError:
                    await asyncio.sleep(1)
                else:
                    break

        return

    return media_info


def _get_options(
    output_file_stem: str,
    preferred_video_codec: str = None,
    preferred_extension: str = None,
    force=False,
    audio_only=False
) -> dict[str, Any]:
    options = {
        "outtmpl": f'{output_file_stem}.%(ext)s',
        'logtostderr': True,
        'noplaylist': True,
        'extract_flat': 'in_playlist'
    }
    if not force:
        options['allowed_extractors'] = ['default', '-generic']
    if audio_only:
        options['format'] = 'mp3/bestaudio/best'
        options['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
    if preferred_video_codec:
        options['format_sort'] = {'+vcodec': preferred_video_codec}
    if preferred_extension:
        options['format_sort'] = options.get('format_sort', {}) | {'ext': preferred_extension}

    return options


def _run_youtube_dl(options: dict, url: str) -> dict[str, str] | None:
    with flanautils.suppress_stderr(), yt_dlp.YoutubeDL(options) as ydl:
        try:
            return {
                k: v for k, v in ydl.extract_info(url).items()
                if k in {'album', 'artist', 'extractor_key', 'preview', 'title', 'track'}
            }
        except yt_dlp.utils.DownloadError:
            pass


async def get_media(
    url: str,
    preferred_video_codec: str = None,
    preferred_extension: str = None,
    force=False,
    audio_only=False,
    timeout: int | float = None
) -> Media | None:
    output_file_stem = str(uuid.uuid1())
    if not (
        media_info := await _get_media_info(url, output_file_stem, preferred_video_codec, preferred_extension, force, audio_only, timeout)
    ):
        return

    try:
        output_file_path = next(flanautils.find_paths_by_stem(output_file_stem, lazy=True))
    except StopIteration:
        return

    if (
        not (extension := output_file_path.suffix.strip('.'))
        and
        not (extension := media_info.get('final_extension'))
        and
        (output_file_name := media_info.get('output_file_name'))
    ):
        extension = pathlib.Path(output_file_name).suffix.strip('.')

    extractor_key = media_info.get('extractor_key', '')
    image_formats = ('jfif', 'jpeg', 'jpg', 'png', 'tiff')
    video_formats = ('avchd', 'avi', 'flv', 'mkv', 'mov', 'mp4', 'webm', 'wmv')
    audio_formats = ('aac', 'flac', 'm4a', 'mp3', 'wav')
    if 'generic' == extractor_key.lower():
        format_ = await flanautils.get_format(output_file_path)
        if any(image_format in format_ for image_format in image_formats):
            type_ = MediaType.IMAGE
        elif 'gif' in format_:
            type_ = MediaType.GIF
        elif any(video_format in format_ for video_format in video_formats):
            type_ = MediaType.VIDEO
        elif any(audio_format in format_ for audio_format in audio_formats):
            type_ = MediaType.AUDIO
        else:
            type_ = None

        if domains := flanautils.find_url_domains(url):
            source = domains[0]
        else:
            source = None
    else:
        if audio_only or extension in audio_formats:
            type_ = MediaType.AUDIO
        elif extension == 'gif':
            type_ = MediaType.GIF
        else:
            type_ = MediaType.VIDEO

        try:
            source = Source[extractor_key.upper()]
        except (AttributeError, KeyError):
            source = extractor_key

    if title := media_info.get('title'):
        title = title[:constants.YT_DLP_WRAPPER_TITLE_MAX_LENGTH].strip()
        bytes_ = await flanautils.edit_metadata(output_file_path, {'title': title}, overwrite=False)
    else:
        bytes_ = output_file_path.read_bytes()

    output_file_path.unlink(missing_ok=True)

    if preview := media_info.get('preview'):
        song_info = Media(
            preview,
            MediaType.AUDIO,
            'mp3',
            Source.TIKTOK,
            media_info.get('track'),
            media_info.get('artist'),
            media_info.get('album')
        )
    else:
        song_info = None

    return Media(bytes_, type_, extension, source, title, song_info=song_info)


async def get_medias(
    urls: Iterable[str],
    preferred_video_codec: str = None,
    preferred_extension: str = None,
    force=False,
    audio_only=False,
    timeout_for_media: int | float = None
) -> OrderedSet[Media]:
    return OrderedSet([media for url in urls if (media := await get_media(
        url,
        preferred_video_codec,
        preferred_extension,
        force,
        audio_only,
        timeout_for_media
    ))])
