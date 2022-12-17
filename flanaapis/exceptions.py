from flanautils import NotFoundError, ResponseError


class InstagramLoginError(ResponseError):
    pass


class MediaNotFoundError(NotFoundError):
    source: str


class PlaceNotFoundError(NotFoundError):
    pass


class InstagramMediaNotFoundError(MediaNotFoundError):
    source = 'Instagram'


class RedditMediaNotFoundError(MediaNotFoundError):
    source = 'Reddit'


class TikTokMediaNotFoundError(MediaNotFoundError):
    source = 'TikTok'


class TwitterMediaNotFoundError(MediaNotFoundError):
    source = 'Twitter'


class YouTubeMediaNotFoundError(MediaNotFoundError):
    source = 'YouTube'
