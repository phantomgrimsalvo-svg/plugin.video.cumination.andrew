# -*- coding: utf-8 -*-
"""Tests for Cumination (Andrew) logo padding + fanart framing (no Kodi)."""
from __future__ import absolute_import

import os
import shutil
import tempfile
import unittest

from PIL import Image

from resources.lib import andrew_art as art


class _FakeListItem(object):
    def __init__(self):
        self.art = {}
        self.props = {}

    def setArt(self, mapping):
        self.art = dict(mapping)

    def setProperty(self, key, value):
        self.props[key] = value


def _save_rgb(path, size, color, band=None):
    im = Image.new('RGB', size, color)
    if band:
        bx, by, bw, bh, bcolor = band
        draw = Image.new('RGB', (bw, bh), bcolor)
        im.paste(draw, (bx, by))
    im.save(path)
    im.close()
    return path


class FramingTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='cumi-art-')
        self.cache = os.path.join(self.tmpdir, 'cache')
        self.framed = os.path.join(self.tmpdir, 'framed')
        os.makedirs(self.cache)
        os.makedirs(self.framed)
        self.settings = art.default_settings()
        self.settings['cache_dir'] = self.cache
        self.settings['framed_dir'] = self.framed
        self.settings['addon_fanart'] = os.path.join(self.tmpdir, 'fanart.jpg')
        _save_rgb(self.settings['addon_fanart'], (1280, 720), (10, 10, 10))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_logo_padding_keeps_full_wordmark_on_poster_and_square(self):
        # Ultra-wide wordmark: red bar across a 800x80 canvas (10:1).
        logo = os.path.join(self.tmpdir, 'sitelogo.png')
        im = Image.new('RGB', (800, 80), (0, 0, 0))
        im.paste(Image.new('RGB', (780, 50), (220, 20, 20)), (10, 15))
        im.save(logo)
        im.close()

        square, poster = art.framed_logo_paths(logo, self.settings)
        self.assertTrue(square and os.path.isfile(square))
        self.assertTrue(poster and os.path.isfile(poster))

        poster_im = Image.open(poster)
        self.assertEqual(poster_im.size, (art.POSTER_W, art.POSTER_H))
        # Full wordmark is a contiguous red run; scale-crop of this 2:3 poster
        # must still include red (the name), not only black bars.
        extrema = poster_im.convert('RGB').getextrema()
        self.assertGreater(extrema[0][1], 100)
        # Horizontal extent of red pixels should be most of the poster width
        # (logo is fitted to ~80% of width) — not a thin center crop leftover.
        px = poster_im.convert('RGB').load()
        red_cols = [
            x for x in range(poster_im.size[0])
            if any(px[x, y][0] > 150 for y in range(0, poster_im.size[1], 8))
        ]
        self.assertGreater(len(red_cols), int(art.POSTER_W * 0.55))
        poster_im.close()

        sq = Image.open(square)
        self.assertEqual(sq.size, (art.SQUARE_W, art.SQUARE_H))
        sq.close()

        built, props = art.build_art(logo, is_folder=True, settings=self.settings)
        self.assertEqual(props.get('Andrew.ArtType'), 'logo')
        self.assertEqual(built['clearlogo'], logo)
        self.assertEqual(built['banner'], logo)
        self.assertEqual(built['landscape'], logo)
        self.assertEqual(built['poster'], poster)
        self.assertEqual(built['thumb'], square)
        self.assertEqual(props.get('Andrew.LogoSafe'), 'true')

    def test_pillarbox_mode_a_no_face_crop(self):
        portrait = os.path.join(self.tmpdir, 'actress.jpg')
        # Magenta "face" strip at the very top; body is teal.
        im = Image.new('RGB', (400, 800), (0, 128, 128))
        im.paste(Image.new('RGB', (400, 80), (255, 0, 255)), (0, 0))
        im.save(portrait, 'JPEG', quality=95)
        im.close()

        settings = dict(self.settings)
        settings['posterfanart'] = True
        settings['portrait_fanart_extras'] = True
        settings['portrait_fanart_mode'] = art.MODE_PILLARBOX
        built, props = art.build_art(portrait, is_folder=False, settings=settings)
        self.assertEqual(props.get('Andrew.FanartMode'), art.MODE_PILLARBOX)
        self.assertEqual(props.get('Andrew.FanartFramed'), 'true')
        fanart = Image.open(built['fanart'])
        self.assertEqual(fanart.size, (art.FANART_W, art.FANART_H))
        # Side bars are black.
        left = fanart.getpixel((2, art.FANART_H // 2))
        self.assertLess(sum(left), 40)
        # The magenta face band is still present (not cropped off).
        rgb = fanart.convert('RGB')
        magenta = 0
        for y in range(0, rgb.size[1], 4):
            for x in range(0, rgb.size[0], 4):
                p = rgb.getpixel((x, y))
                if p[0] > 200 and p[2] > 200 and p[1] < 80:
                    magenta += 1
        rgb.close()
        self.assertGreater(magenta, 200)
        fanart.close()

    def test_topfill_mode_b_keeps_top_face(self):
        portrait = os.path.join(self.tmpdir, 'face.jpg')
        im = Image.new('RGB', (400, 900), (0, 0, 40))
        im.paste(Image.new('RGB', (400, 120), (255, 255, 0)), (0, 0))  # face / top
        im.paste(Image.new('RGB', (400, 120), (0, 255, 0)), (0, 780))  # feet / bottom
        im.save(portrait, 'JPEG', quality=95)
        im.close()

        settings = dict(self.settings)
        settings['posterfanart'] = True
        settings['portrait_fanart_extras'] = True
        settings['portrait_fanart_mode'] = art.MODE_TOPFILL
        built, props = art.build_art(portrait, is_folder=False, settings=settings)
        self.assertEqual(props.get('Andrew.FanartAlignY'), 'top')
        fanart = Image.open(built['fanart'])
        top_px = fanart.getpixel((art.FANART_W // 2, 8))
        self.assertGreater(top_px[0] + top_px[1], 300)  # yellow face
        # Bottom of the 16:9 crop should NOT be the green feet (those are below).
        bot_px = fanart.getpixel((art.FANART_W // 2, art.FANART_H - 8))
        self.assertLess(bot_px[1], 200)
        fanart.close()

    def test_pan_mode_c_frames_run_top_to_bottom(self):
        portrait = os.path.join(self.tmpdir, 'pan.jpg')
        im = Image.new('RGB', (400, 1000), (20, 20, 20))
        im.paste(Image.new('RGB', (400, 100), (255, 0, 0)), (0, 0))
        im.paste(Image.new('RGB', (400, 100), (0, 0, 255)), (0, 900))
        im.save(portrait, 'JPEG', quality=95)
        im.close()

        settings = dict(self.settings)
        settings['posterfanart'] = True
        settings['portrait_fanart_extras'] = True
        settings['portrait_fanart_mode'] = art.MODE_PAN
        built, props = art.build_art(portrait, is_folder=False, settings=settings)
        self.assertEqual(props.get('Andrew.FanartMode'), art.MODE_PAN)
        frames = props.get('Andrew.FanartPanFrames', '').split('|')
        self.assertGreaterEqual(len(frames), 3)
        first = Image.open(frames[0])
        last = Image.open(frames[-1])
        first_top = first.getpixel((art.FANART_W // 2, 8))
        last_bot = last.getpixel((art.FANART_W // 2, art.FANART_H - 8))
        self.assertGreater(first_top[0], 180)  # red at start
        self.assertGreater(last_bot[2], 180)  # blue at end
        first.close()
        last.close()
        self.assertTrue(built['fanart'].endswith('.jpg') or os.path.isfile(built['fanart']))

    def test_listitem_wrapper_sets_fanart_image_property(self):
        logo = os.path.join(self.tmpdir, 'x.png')
        _save_rgb(logo, (400, 60), (255, 128, 0))
        liz = _FakeListItem()
        settings = dict(self.settings)
        settings['posterfanart'] = False
        art.apply_to_listitem(liz, logo, is_folder=True, settings=settings)
        self.assertIn('Fanart_Image', liz.props)
        self.assertEqual(liz.props.get('Andrew.ArtType'), 'logo')
        self.assertEqual(liz.art.get('clearlogo'), logo)

    def test_landscape_letterbox_optional(self):
        wide = os.path.join(self.tmpdir, 'land.jpg')
        _save_rgb(wide, (1600, 600), (50, 50, 200))
        settings = dict(self.settings)
        settings['posterfanart'] = True
        settings['portrait_fanart_extras'] = True
        settings['landscape_fanart_mode'] = art.MODE_LETTERBOX
        built, props = art.build_art(wide, is_folder=False, settings=settings)
        self.assertEqual(props.get('Andrew.ArtAspect'), 'landscape')
        fanart = Image.open(built['fanart'])
        self.assertEqual(fanart.size, (art.FANART_W, art.FANART_H))
        fanart.close()


if __name__ == '__main__':
    unittest.main()
