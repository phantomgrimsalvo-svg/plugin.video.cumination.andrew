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
        self.assertEqual(built['poster'], poster)
        self.assertEqual(built['thumb'], square)
        self.assertEqual(props.get('Andrew.LogoSafe'), 'true')
        # Fanart/landscape are 16:9 letterboxed so Estuary Fanart view
        # does not cover-crop the wordmark.
        self.assertNotEqual(built['fanart'], logo)
        self.assertEqual(built['landscape'], built['fanart'])
        self.assertTrue(os.path.isfile(built['fanart']))

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

    def _nonblack_bbox(self, im, threshold=40):
        rgb = im.convert('RGB')
        px = rgb.load()
        w, h = rgb.size
        xs = []
        ys = []
        for y in range(h):
            for x in range(w):
                if sum(px[x, y]) > threshold:
                    xs.append(x)
                    ys.append(y)
        rgb.close()
        if not xs:
            return None
        return min(xs), min(ys), max(xs), max(ys)

    def test_small_portrait_pillarbox_fills_height_not_postage_stamp(self):
        # Live Cum Louder pornstars thumbs are ~233×261. thumbnail() left these
        # unscaled in the middle of 1280×720; Mode A must upscale to full height.
        portrait = os.path.join(self.tmpdir, 'small-pornstar.jpg')
        im = Image.new('RGB', (233, 261), (0, 160, 160))
        im.paste(Image.new('RGB', (233, 30), (255, 0, 255)), (0, 0))
        im.save(portrait, 'JPEG', quality=95)
        im.close()

        settings = dict(self.settings)
        settings['posterfanart'] = True
        settings['portrait_fanart_extras'] = True
        settings['portrait_fanart_mode'] = art.MODE_PILLARBOX
        settings['allow_remote_fetch'] = True
        built, props = art.build_art(portrait, is_folder=False, settings=settings)
        self.assertEqual(props.get('Andrew.FanartMode'), art.MODE_PILLARBOX)
        fanart = Image.open(built['fanart'])
        self.assertEqual(fanart.size, (art.FANART_W, art.FANART_H))

        bbox = self._nonblack_bbox(fanart)
        self.assertIsNotNone(bbox)
        left, top, right, bottom = bbox
        content_h = bottom - top + 1
        content_w = right - left + 1
        # Scaled height == 720: image fills height, top/bottom margins ~0.
        self.assertGreaterEqual(content_h, art.FANART_H - 4)
        self.assertLessEqual(top, 2)
        self.assertGreaterEqual(bottom, art.FANART_H - 3)
        # Classic pillarbox: black side bars, roughly equal, no 1:1 postage stamp.
        expected_w = int(round(233 * (float(art.FANART_H) / 261.0)))
        self.assertAlmostEqual(content_w, expected_w, delta=6)
        self.assertGreater(left, 80)
        self.assertGreater(art.FANART_W - 1 - right, 80)
        self.assertAlmostEqual(left, art.FANART_W - 1 - right, delta=8)
        left_px = fanart.getpixel((2, art.FANART_H // 2))
        right_px = fanart.getpixel((art.FANART_W - 3, art.FANART_H // 2))
        self.assertLess(sum(left_px), 40)
        self.assertLess(sum(right_px), 40)
        # Mid-column is content (teal), not a black hole around a tiny stamp.
        mid = fanart.getpixel((art.FANART_W // 2, art.FANART_H // 2))
        self.assertGreater(mid[1] + mid[2], 200)
        fanart.close()

    def test_small_portrait_cover_modes_fill_canvas(self):
        portrait = os.path.join(self.tmpdir, 'tiny-cover.jpg')
        im = Image.new('RGB', (233, 261), (200, 40, 40))
        im.save(portrait, 'JPEG', quality=95)
        im.close()
        src = Image.open(portrait)
        for fn in (art.cover_top_fanart, art.cover_center_fanart):
            framed = fn(src)
            self.assertEqual(framed.size, (art.FANART_W, art.FANART_H))
            # Cover must fill the canvas — no large black margins.
            bbox = self._nonblack_bbox(framed)
            self.assertIsNotNone(bbox)
            left, top, right, bottom = bbox
            self.assertLessEqual(left, 2)
            self.assertLessEqual(top, 2)
            self.assertGreaterEqual(right, art.FANART_W - 3)
            self.assertGreaterEqual(bottom, art.FANART_H - 3)
            framed.close()
        pan = art.pan_frame_fanart(src, 0.0)
        self.assertEqual(pan.size, (art.FANART_W, art.FANART_H))
        bbox = self._nonblack_bbox(pan)
        left, top, right, bottom = bbox
        self.assertLessEqual(left, 2)
        self.assertLessEqual(top, 2)
        self.assertGreaterEqual(right, art.FANART_W - 3)
        self.assertGreaterEqual(bottom, art.FANART_H - 3)
        pan.close()
        src.close()

    def test_folder_logo_fanart_is_letterboxed_16x9(self):
        logo = os.path.join(self.tmpdir, 'ah.png')
        im = Image.new('RGB', (800, 80), (0, 0, 0))
        im.paste(Image.new('RGB', (760, 48), (220, 20, 20)), (20, 16))
        im.save(logo)
        im.close()

        settings = dict(self.settings)
        settings['posterfanart'] = True
        built, props = art.build_art(logo, is_folder=True, settings=settings)
        self.assertEqual(props.get('Andrew.ArtType'), 'logo')
        self.assertEqual(built['clearlogo'], logo)
        self.assertEqual(built['thumb'].endswith('.png') or os.path.isfile(built['thumb']), True)
        self.assertNotEqual(built['fanart'], logo)
        fanart = Image.open(built['fanart'])
        self.assertEqual(fanart.size, (art.FANART_W, art.FANART_H))
        bbox = self._nonblack_bbox(fanart)
        self.assertIsNotNone(bbox)
        left, top, right, bottom = bbox
        # Full wordmark: spans most of the width, letterboxed top/bottom.
        self.assertGreater(right - left, int(art.FANART_W * 0.85))
        self.assertGreater(top, 200)
        self.assertLess(bottom, art.FANART_H - 200)
        top_bar = fanart.getpixel((art.FANART_W // 2, 4))
        self.assertLess(sum(top_bar), 40)
        fanart.close()
        # Padded square/poster still used for thumb/poster.
        thumb_im = Image.open(built['thumb'])
        poster_im = Image.open(built['poster'])
        self.assertEqual(thumb_im.size, (art.SQUARE_W, art.SQUARE_H))
        self.assertEqual(poster_im.size, (art.POSTER_W, art.POSTER_H))
        thumb_im.close()
        poster_im.close()

    def test_settings_from_addon_gates_remote_fetch(self):
        class FakeAddon(object):
            def __init__(self, data):
                self.data = data

            def getSetting(self, key):
                return self.data.get(key, '')

        data = {
            'posterfanart': 'true',
            'portrait_fanart_extras': 'true',
            'portrait_fanart_mode': '1',
            'landscape_fanart_mode': '0',
            'portrait_fanart_pan_duration': '24',
        }
        on = art.settings_from_addon(
            FakeAddon(data), 'cache', 'framed', 'fanart.jpg', images_dir='/images'
        )
        self.assertTrue(on['allow_remote_fetch'])
        self.assertEqual(on['remote_timeout'], 4)
        self.assertEqual(on['portrait_fanart_mode'], art.MODE_TOPFILL)
        self.assertEqual(on['images_dir'], '/images')

        data['portrait_fanart_extras'] = 'false'
        off = art.settings_from_addon(FakeAddon(data), 'cache', 'framed', 'fanart.jpg')
        self.assertFalse(off['allow_remote_fetch'])

        data['posterfanart'] = 'false'
        data['portrait_fanart_extras'] = 'true'
        off2 = art.settings_from_addon(FakeAddon(data), 'cache', 'framed', 'fanart.jpg')
        self.assertFalse(off2['allow_remote_fetch'])

    def test_modes_write_distinct_fanart_files_with_remote_fetch(self):
        portrait = os.path.join(self.tmpdir, 'tall.jpg')
        im = Image.new('RGB', (360, 900), (30, 30, 30))
        im.paste(Image.new('RGB', (360, 90), (255, 0, 0)), (0, 0))
        im.paste(Image.new('RGB', (360, 90), (0, 0, 255)), (0, 810))
        im.save(portrait, 'JPEG', quality=95)
        im.close()

        settings = dict(self.settings)
        settings['posterfanart'] = True
        settings['portrait_fanart_extras'] = True
        settings['allow_remote_fetch'] = True
        settings['cache_dir'] = self.cache

        fanarts = []
        for mode in (art.MODE_PILLARBOX, art.MODE_TOPFILL, art.MODE_PAN):
            settings['portrait_fanart_mode'] = mode
            built, props = art.build_art(portrait, is_folder=False, settings=settings)
            path = built['fanart']
            self.assertTrue(os.path.isfile(path), mode)
            self.assertNotEqual(path, portrait)
            self.assertEqual(props.get('Andrew.FanartFramed'), 'true')
            fanarts.append(os.path.realpath(path))
        self.assertEqual(len(set(fanarts)), 3)

    def test_https_cached_thumb_modes_are_distinct_files(self):
        portrait = os.path.join(self.tmpdir, 'remote-actress.jpg')
        im = Image.new('RGB', (400, 800), (20, 80, 80))
        im.paste(Image.new('RGB', (400, 80), (255, 0, 255)), (0, 0))
        im.save(portrait, 'JPEG', quality=95)
        im.close()

        url = 'https://cdn.example.test/thumbs/actress.jpg'
        dest = art._src_cache_path(url, self.settings)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy(portrait, dest)

        settings = dict(self.settings)
        settings['posterfanart'] = True
        settings['portrait_fanart_extras'] = True
        settings['allow_remote_fetch'] = True
        fanarts = []
        for mode in (art.MODE_PILLARBOX, art.MODE_TOPFILL, art.MODE_PAN):
            settings['portrait_fanart_mode'] = mode
            built, _props = art.build_art(url, is_folder=False, settings=settings)
            self.assertTrue(os.path.isfile(built['fanart']), mode)
            self.assertNotEqual(built['fanart'], url)
            fanarts.append(os.path.realpath(built['fanart']))
        self.assertEqual(len(set(fanarts)), 3)

        settings['allow_remote_fetch'] = False
        settings['portrait_fanart_mode'] = art.MODE_PILLARBOX
        os.remove(dest)
        for name in os.listdir(os.path.join(self.cache, 'fanart')):
            os.remove(os.path.join(self.cache, 'fanart', name))
        built, _props = art.build_art(url, is_folder=False, settings=settings)
        self.assertEqual(built['fanart'], url)

    def test_wide_logo_letterboxed_square_and_poster_aspects(self):
        logo = os.path.join(self.tmpdir, 'wordmark.png')
        im = Image.new('RGB', (900, 90), (0, 0, 0))
        im.paste(Image.new('RGB', (860, 50), (20, 180, 220)), (20, 20))
        im.save(logo)
        im.close()

        square, poster = art.framed_logo_paths(logo, self.settings)
        self.assertTrue(square and os.path.isfile(square))
        self.assertTrue(poster and os.path.isfile(poster))
        sq = Image.open(square)
        po = Image.open(poster)
        self.assertEqual(sq.size, (art.SQUARE_W, art.SQUARE_H))
        self.assertEqual(po.size, (art.POSTER_W, art.POSTER_H))
        self.assertAlmostEqual(sq.size[0] / float(sq.size[1]), 1.0, places=2)
        self.assertAlmostEqual(po.size[0] / float(po.size[1]), 2.0 / 3.0, delta=0.02)
        px = po.convert('RGB').load()
        cyan_cols = [
            x for x in range(po.size[0])
            if any(px[x, y][1] > 120 and px[x, y][2] > 150 for y in range(0, po.size[1], 8))
        ]
        self.assertGreater(len(cyan_cols), int(art.POSTER_W * 0.55))
        sq.close()
        po.close()

    def test_special_home_path_matches_shipped_framed_by_basename(self):
        images = os.path.join(self.tmpdir, 'images')
        os.makedirs(images)
        logo = os.path.join(images, 'sitetest.png')
        im = Image.new('RGB', (800, 80), (0, 0, 0))
        im.paste(Image.new('RGB', (780, 50), (220, 20, 20)), (10, 15))
        im.save(logo)
        im.close()
        framed = os.path.join(images, 'framed')
        written = art.generate_shipped_framed_logos(images, framed)
        self.assertGreaterEqual(written, 1)

        settings = dict(self.settings)
        settings['images_dir'] = images
        settings['framed_dir'] = framed
        src = 'special://home/addons/plugin.video.cumination.andrew/resources/images/sitetest.png'
        square, poster = art.framed_logo_paths(src, settings)
        self.assertTrue(square and square.endswith(os.path.join('square', 'sitetest.png')))
        self.assertTrue(poster and poster.endswith(os.path.join('poster', 'sitetest.png')))
        built, props = art.build_art(src, is_folder=True, settings=settings)
        self.assertEqual(props.get('Andrew.LogoSafe'), 'true')
        self.assertEqual(built['thumb'], square)
        self.assertEqual(built['clearlogo'], src)

    def test_remote_folder_logo_uses_src_cache_when_fetch_off_for_videos(self):
        logo = os.path.join(self.tmpdir, 'cdn-logo.png')
        im = Image.new('RGB', (640, 80), (0, 0, 0))
        im.paste(Image.new('RGB', (600, 40), (255, 200, 0)), (20, 20))
        im.save(logo)
        im.close()
        url = 'https://cdn.example.test/theme/logo.png'
        dest = art._src_cache_path(url, self.settings)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy(logo, dest)

        settings = dict(self.settings)
        settings['allow_remote_fetch'] = False
        square, poster = art.framed_logo_paths(url, settings)
        self.assertTrue(square and os.path.isfile(square))
        self.assertTrue(poster and os.path.isfile(poster))
        built, props = art.build_art(url, is_folder=True, settings=settings)
        self.assertEqual(props.get('Andrew.ArtType'), 'logo')
        self.assertEqual(built['thumb'], square)


if __name__ == '__main__':
    unittest.main()
