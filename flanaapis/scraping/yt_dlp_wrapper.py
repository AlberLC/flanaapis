import asyncio
import pathlib
import uuid
from collections.abc import Iterable

import flanautils
import yt_dlp
from flanautils import Media, MediaType, Source

TITLE_MAX_LENGTH = 20


def run_youtube_dl(options: dict, url: str):
    with flanautils.suppress_stderr():
        ydl = yt_dlp.YoutubeDL(options)
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
    audio_only=False,
    preferred_video_codec: str = None,
    preferred_extension: str = None,
    timeout: int | float = None
) -> Media | None:
    output_file_stem = str(uuid.uuid1())

    options = {
        "outtmpl": f'{output_file_stem}.%(ext)s',
        'logtostderr': True,
        'noplaylist': True,
        'extract_flat': 'in_playlist'
    }
    if audio_only:
        options |= {
            'format': 'mp3/bestaudio/best',
            'postprocessors': [{  # Extract audio using ffmpeg
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }]
        }
    if preferred_video_codec:
        options |= {'format_sort': {'+vcodec': preferred_video_codec}}
    if preferred_extension:
        options |= {'format_sort': options.get('format_sort', {}) | {'ext': preferred_extension}}

    try:
        media_info = await flanautils.run_process_async(run_youtube_dl, options, url, timeout=timeout)
    except asyncio.TimeoutError:
        media_info = None

    if not media_info:
        for path in pathlib.Path().iterdir():
            if path.stem == output_file_stem:
                path.unlink()
                break
        return

    if (
            not (extension := media_info.get('extension'))
            and
            (output_file_name := media_info.get('output_file_name'))
    ):
        extension = pathlib.Path(output_file_name).suffix.strip('.')
    output_file_name = f'{output_file_stem}.{extension}' if extension else output_file_stem
    output_file_path = pathlib.Path(output_file_name)
    bytes_ = output_file_path.read_bytes()

    if title := media_info.get('title'):
        title = title[:TITLE_MAX_LENGTH]
        try:
            bytes_ = await flanautils.edit_metadata(output_file_path, {'title': title}, overwrite=False)
        except ValueError:
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

    source = media_info.get('extractor_key', '')
    try:
        source = Source[source.upper()]
    except (AttributeError, KeyError):
        pass

    return Media(
        bytes_,
        MediaType.AUDIO if audio_only else MediaType.VIDEO,
        extension,
        source=source,
        title=title,
        song_info=song_info
    )


async def get_medias(
    urls: Iterable[str],
    audio_only=False,
    preferred_video_codec: str = None,
    preferred_extension: str = None,
    timeout: int | float = None
) -> list[Media]:
    return [media for url in urls if (media := await get_media(url, audio_only, preferred_video_codec, preferred_extension, timeout))]
