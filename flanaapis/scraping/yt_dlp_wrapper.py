import asyncio
import pathlib
import uuid
from collections.abc import Iterable

import flanautils
import yt_dlp
from flanautils import Media, MediaType, Source

from flanaapis.scraping import constants


def run_youtube_dl(options: dict, url: str):
    with flanautils.suppress_stderr(), yt_dlp.YoutubeDL(options) as ydl:
        try:
            filtered_info = {}
            for k, v in ydl.extract_info(url).items():
                if k in ('album', 'artist', 'extractor_key', 'preview', 'title', 'track'):
                    filtered_info[k] = v
                elif k == 'requested_downloads':
                    filtered_info['final_extension'] = v[0].get('ext')
                    filtered_info['output_file_name'] = v[0].get('_filename')
            return filtered_info
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
    url = await flanautils.resolve_real_url(url)

    output_file_stem = str(uuid.uuid1())

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

    try:
        media_info = await flanautils.run_process_async(run_youtube_dl, options, url, timeout=timeout)
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

    output_file_path = next(flanautils.find_paths_by_stem(output_file_stem, lazy=True))
    bytes_ = output_file_path.read_bytes()

    if (
            not (extension := output_file_path.suffix.strip('.'))
            and
            not (extension := media_info.get('final_extension'))
            and
            (output_file_name := media_info.get('output_file_name'))
    ):
        extension = pathlib.Path(output_file_name).suffix.strip('.')

    extractor_key = media_info.get('extractor_key', '')
    if 'generic' == extractor_key.lower():
        bytes_format = await flanautils.get_format(bytes_)
        if any(format_ in bytes_format for format_ in ('jfif', 'jpeg', 'jpg', 'png', 'tiff')):
            type_ = MediaType.IMAGE
        elif 'gif' in bytes_format:
            type_ = MediaType.GIF
        elif any(format_ in bytes_format for format_ in ('avchd', 'avi', 'flv', 'mkv', 'mov', 'mp4', 'webm', 'wmv')):
            type_ = MediaType.VIDEO
        elif any(format_ in bytes_format for format_ in ('aac', 'flac', 'm4a', 'mp3', 'wav')):
            type_ = MediaType.AUDIO
        else:
            type_ = None

        if domains := flanautils.find_url_domains(url):
            source = domains[0]
        else:
            source = None
    else:
        if audio_only:
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
        title = title[:constants.YT_DLP_WRAPPER_TITLE_MAX_LENGTH]
        try:
            bytes_ = await flanautils.edit_metadata(output_file_path, {'title': title}, overwrite=False)
        except FileNotFoundError:
            pass

    output_file_path.unlink(missing_ok=True)

    if media_info.get('preview'):
        song_info = Media(
            media_info.get('preview'),
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
) -> list[Media]:
    return [media for url in urls if (media := await get_media(
        url,
        preferred_video_codec,
        preferred_extension,
        force,
        audio_only,
        timeout_for_media
    ))]
