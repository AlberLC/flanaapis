import os
import unittest

import flanautils
from flanautils import MediaType, Source

from flanaapis import InstagramMediaNotFoundError
from flanaapis.scraping import instagram

os.environ |= flanautils.find_environment_variables('../.env')


class TestInstagramScraper(unittest.IsolatedAsyncioTestCase):
    async def _test_one_media(self, url: str, type_: MediaType, source: Source = Source.INSTAGRAM):
        medias = await instagram.get_medias(instagram.find_ids(url))
        media = medias[0]

        self.assertEqual(1, len(medias))
        self.assertIsNotNone(media.url)
        self.assertEqual(type_, media.type_)
        self.assertEqual(source, media.source)

    async def _test_image_album(self, url: str, n_medias: int):
        medias = await instagram.get_medias(instagram.find_ids(url))

        self.assertEqual(n_medias, len(medias))
        for i in range(n_medias):
            self.assertIsNotNone(medias[i].url)
            self.assertEqual(MediaType.IMAGE, medias[i].type_)
            self.assertEqual(Source.INSTAGRAM, medias[i].source)

    async def test_empty(self):
        with self.assertRaises(InstagramMediaNotFoundError):
            await instagram.get_medias(instagram.find_ids('https://www.instagram.com/p/CRjFIK6F9PU/'))  # empty

    async def test_one_media(self):
        # with self.subTest('image_1'):
        #     await self._test_one_media('https://www.instagram.com/p/CRluCdOBmNY/', MediaType.IMAGE)  # phoenix valorant
        # with self.subTest('image_2'):
        #     await self._test_one_media('https://www.instagram.com/p/CRg1KACFvsE/', MediaType.IMAGE)  # meme skins valorant money
        with self.subTest('image_3'):
            await self._test_one_media('https://www.instagram.com/p/CRUWyBvM4qq/', MediaType.IMAGE)  # latina girl with braids

        # with self.subTest('video_1'):
        #     await self._test_one_media('https://www.instagram.com/p/CRgotu_I4tt/', MediaType.VIDEO)  # valorant video dance
        with self.subTest('video_2'):
            await self._test_one_media('https://www.instagram.com/p/CZQAs7cINzZ/', MediaType.VIDEO)  # girl video party
        with self.subTest('video_3'):
            await self._test_one_media('https://www.instagram.com/reel/CqWosLCD46Y/', MediaType.VIDEO)  # the pope
        # with self.subTest('video_without_sound'):
        #     await self._test_one_media('https://www.instagram.com/p/CRgiVOEIjZ-/', MediaType.VIDEO)  # sage video without sound
        with self.subTest('long_video_1'):
            await self._test_one_media('https://www.instagram.com/p/CZcTl1BBKA0/?hl=es', MediaType.VIDEO)  # long video skater girl
        with self.subTest('long_video_2'):
            await self._test_one_media('https://www.instagram.com/tv/CbLGc7vlCY_/?utm_medium=share_sheet', MediaType.VIDEO)  # long video cateto bocadillo

    async def test_image_album(self):
        with self.subTest('image_album_1'):
            await self._test_image_album('https://www.instagram.com/p/CqJT0UyOxTE/', 2)  # 2 images of the little mermaid
        with self.subTest('image_album_2'):
            await self._test_image_album('https://www.instagram.com/p/CqVqOe-t_Rr/', 8)  # 8 images of beach stones
        with self.subTest('image_album_3'):
            await self._test_image_album('https://www.instagram.com/p/CqN3q1bLezt/', 9)  # 9 images of psychology things

    # async def test_video_album(self):
    #     medias = await instagram.get_medias(instagram.find_ids('https://www.instagram.com/p/CRjl72oFdmV/'))  # 2 valorant skins videos
    #
    #     n_medias = 2
    #     self.assertEqual(n_medias, len(medias))
    #     for i in range(n_medias):
    #         self.assertIsNotNone(medias[i].url)
    #         self.assertEqual(MediaType.VIDEO, medias[i].type_)
    #         self.assertEqual(Source.INSTAGRAM, medias[i].source)

    async def test_images_and_videos_1(self):
        medias = await instagram.get_medias(instagram.find_ids('https://www.instagram.com/p/CSE1EpAn7NT/'))  # 4 images and 1 video of a girl

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

    async def test_images_and_videos_2(self):
        medias = await instagram.get_medias(instagram.find_ids('https://www.instagram.com/p/CqVNTa0MkMk/?igshid=MDJmNzVkMjY%3D'))  # 3 images and 2 videos of the basque parliament

        self.assertEqual(5, len(medias))
        self.assertIsNotNone(medias[0].url)
        self.assertEqual(MediaType.IMAGE, medias[0].type_)
        self.assertEqual(Source.INSTAGRAM, medias[0].source)
        self.assertIsNotNone(medias[1].url)
        self.assertEqual(MediaType.VIDEO, medias[1].type_)
        self.assertEqual(Source.INSTAGRAM, medias[1].source)
        self.assertIsNotNone(medias[2].url)
        self.assertEqual(MediaType.VIDEO, medias[2].type_)
        self.assertEqual(Source.INSTAGRAM, medias[2].source)
        self.assertIsNotNone(medias[3].url)
        self.assertEqual(MediaType.IMAGE, medias[3].type_)
        self.assertEqual(Source.INSTAGRAM, medias[3].source)
        self.assertIsNotNone(medias[4].url)
        self.assertEqual(MediaType.IMAGE, medias[4].type_)
        self.assertEqual(Source.INSTAGRAM, medias[4].source)

    # async def test_images_and_videos_3(self):
    #     medias = await instagram.get_medias(instagram.find_ids('https://www.instagram.com/p/CqJU-GGqfUk/'))  # 1 image and 3 video of frank cuesta
    #
    #     self.assertEqual(4, len(medias))
    #     self.assertIsNotNone(medias[0].url)
    #     self.assertEqual(MediaType.IMAGE, medias[0].type_)
    #     self.assertEqual(Source.INSTAGRAM, medias[0].source)
    #     self.assertIsNotNone(medias[1].url)
    #     self.assertEqual(MediaType.VIDEO, medias[1].type_)
    #     self.assertEqual(Source.INSTAGRAM, medias[1].source)
    #     self.assertIsNotNone(medias[2].url)
    #     self.assertEqual(MediaType.VIDEO, medias[2].type_)
    #     self.assertEqual(Source.INSTAGRAM, medias[2].source)
    #     self.assertIsNotNone(medias[3].url)
    #     self.assertEqual(MediaType.VIDEO, medias[3].type_)
    #     self.assertEqual(Source.INSTAGRAM, medias[3].source)

    async def test_images_and_videos_4(self):
        medias = await instagram.get_medias(instagram.find_ids('https://www.instagram.com/p/CucbR2wIekU/?igshid=MTIzZWMxMTBkOA%3D%3D'))  # 5 images and 1 video of aitana

        self.assertEqual(6, len(medias))
        self.assertIsNotNone(medias[0].url)
        self.assertEqual(MediaType.IMAGE, medias[0].type_)
        self.assertEqual(Source.INSTAGRAM, medias[0].source)
        self.assertIsNotNone(medias[1].url)
        self.assertEqual(MediaType.VIDEO, medias[1].type_)
        self.assertEqual(Source.INSTAGRAM, medias[1].source)
        self.assertIsNotNone(medias[2].url)
        self.assertEqual(MediaType.IMAGE, medias[2].type_)
        self.assertEqual(Source.INSTAGRAM, medias[2].source)
        self.assertIsNotNone(medias[3].url)
        self.assertEqual(MediaType.IMAGE, medias[3].type_)
        self.assertEqual(Source.INSTAGRAM, medias[3].source)
        self.assertIsNotNone(medias[4].url)
        self.assertEqual(MediaType.IMAGE, medias[4].type_)
        self.assertEqual(Source.INSTAGRAM, medias[4].source)
        self.assertIsNotNone(medias[5].url)
        self.assertEqual(MediaType.IMAGE, medias[5].type_)
        self.assertEqual(Source.INSTAGRAM, medias[5].source)
