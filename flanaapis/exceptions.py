from flanautils.exceptions import NotFoundError, ResponseError


class InstagramLoginError(ResponseError):
    pass


class MediaNotFoundError(NotFoundError):
    source: str


class PlaceNotFoundError(NotFoundError):
    pass


class InstagramMediaNotFoundError(MediaNotFoundError):
    source = 'Instagram'


class TikTokMediaNotFoundError(MediaNotFoundError):
    source = 'TikTok'


class TwitterMediaNotFoundError(MediaNotFoundError):
    source = 'Twitter'


class YouTubeMediaNotFoundError(MediaNotFoundError):
    source = 'YouTube'
