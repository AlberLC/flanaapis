import os

import flanautils
from flanautils import Media, MediaType, Source

os.environ |= flanautils.find_environment_variables('../.env')

import unittest

from scraping import instagram


class TestInstagramScraper(unittest.IsolatedAsyncioTestCase):
    async def _test_one_media(self, url: str, type_: MediaType):
        medias = await instagram.get_medias(url)
        media = medias[0]

        self.assertEqual(1, len(medias))
        self.assertIsNotNone(media.url)
        self.assertEqual(type_, media.type_)
        self.assertEqual(Source.INSTAGRAM, media.source)

    async def test_empty(self):
        medias = await instagram.get_medias('https://www.instagram.com/p/CRjFIK6F9PU/')
        media = medias[0]

        self.assertEqual(Media(type_=MediaType.ERROR, source=Source.INSTAGRAM), media)

    async def test_one_media(self):
        with self.subTest('image_1'):
            await self._test_one_media('https://www.instagram.com/p/CRluCdOBmNY/', MediaType.IMAGE)
        with self.subTest('image_2'):
            await self._test_one_media('https://www.instagram.com/p/CRg1KACFvsE/', MediaType.IMAGE)
        with self.subTest('image_3'):
            await self._test_one_media('https://www.instagram.com/p/CRUWyBvM4qq/', MediaType.IMAGE)

        with self.subTest('image_1'):
            await self._test_one_media('https://www.instagram.com/p/CRluCdOBmNY/', MediaType.IMAGE)
        with self.subTest('image_2'):
            await self._test_one_media('https://www.instagram.com/p/CRg1KACFvsE/', MediaType.IMAGE)
        with self.subTest('image_3'):
            await self._test_one_media('https://www.instagram.com/p/CRUWyBvM4qq/', MediaType.IMAGE)

        with self.subTest('video_1'):
            await self._test_one_media('https://www.instagram.com/p/CRgotu_I4tt/', MediaType.VIDEO)
        with self.subTest('video_2'):
            await self._test_one_media('https://www.instagram.com/p/CZQAs7cINzZ/', MediaType.VIDEO)
        with self.subTest('video_without_sound'):
            await self._test_one_media('https://www.instagram.com/p/CRgiVOEIjZ-/', MediaType.VIDEO)

    async def test_video_album(self):
        medias = await instagram.get_medias('https://www.instagram.com/p/CRjl72oFdmV/')

        self.assertEqual(2, len(medias))
        self.assertIsNotNone(medias[0].url)
        self.assertEqual(MediaType.VIDEO, medias[0].type_)
        self.assertEqual(Source.INSTAGRAM, medias[0].source)
        self.assertIsNotNone(medias[1].url)
        self.assertEqual(MediaType.VIDEO, medias[1].type_)
        self.assertEqual(Source.INSTAGRAM, medias[1].source)

    async def test_images_and_videos(self):
        medias = await instagram.get_medias('https://www.instagram.com/p/CSE1EpAn7NT/')

        self.assertEqual(5, len(medias))
        self.assertIsNotNone(medias[0].url)
        self.assertEqual(MediaType.IMAGE, medias[0].type_)
        self.assertEqual(Source.INSTAGRAM, medias[0].source)
        self.assertIsNotNone(medias[1].url)
        self.assertEqual(MediaType.IMAGE, medias[1].type_)
        self.assertEqual(Source.INSTAGRAM, medias[1].source)
        self.assertIsNotNone(medias[2].url)
        self.assertEqual(MediaType.IMAGE, medias[2].type_)
        self.assertEqual(Source.INSTAGRAM, medias[2].source)
        self.assertIsNotNone(medias[3].url)
        self.assertEqual(MediaType.IMAGE, medias[3].type_)
        self.assertEqual(Source.INSTAGRAM, medias[3].source)
        self.assertIsNotNone(medias[4].url)
        self.assertEqual(MediaType.VIDEO, medias[4].type_)
        self.assertEqual(Source.INSTAGRAM, medias[4].source)
