import pathlib
import uuid
from collections.abc import Iterable

import flanautils
from flanautils import Media, MediaType, Source
from yt_dlp import YoutubeDL, utils

TITLE_MAX_LENGTH = 20


def run_youtube_dl(options: dict, url: str):
    with flanautils.suppress_stderr():
        ydl = YoutubeDL(options)
        try:
            fields = ('album', 'artist', 'ext', 'preview', 'title', 'track')
            return {k: v for k, v in ydl.extract_info(url).items() if k in fields}
        except utils.DownloadError:
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

    media_info = await flanautils.run_process_async(run_youtube_dl, options, url, timeout=timeout)

    output_file_name = f'{output_file_stem}.{extension}' if (extension := media_info.get('ext')) else output_file_stem
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

    return Media(
        bytes_,
        MediaType.AUDIO if audio_only else MediaType.VIDEO,
        extension,
        source=media_info.get('extractor_key'),
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
    return [await get_media(url, audio_only, preferred_video_codec, preferred_extension, timeout) for url in urls]
