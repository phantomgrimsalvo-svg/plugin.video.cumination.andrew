# -*- coding: utf-8 -*-
"""Tests for precache depth caps, queue persist, and image URL guards (no Kodi)."""
from __future__ import absolute_import

import os
import tempfile
import unittest

from resources.lib import andrew_art as art
from resources.lib import precache_lib as pc


class DepthAndFollowTests(unittest.TestCase):
    def test_clamp_depth(self):
        self.assertEqual(pc.clamp_depth(0), 1)
        self.assertEqual(pc.clamp_depth(1), 1)
        self.assertEqual(pc.clamp_depth(3), 3)
        self.assertEqual(pc.clamp_depth(9), pc.MAX_DEPTH)
        self.assertEqual(pc.clamp_depth('nope'), pc.DEFAULT_DEPTH)
        self.assertEqual(pc.MAX_DEPTH, 4)

    def test_never_follow_playback_or_search(self):
        self.assertEqual(pc.listing_kind('pornhub.Playvid', 'Clip'), 'skip')
        self.assertEqual(pc.listing_kind('xvideos.Playvid', 'x'), 'skip')
        self.assertEqual(pc.listing_kind('main.PlayStream', 'x'), 'skip')
        self.assertEqual(pc.listing_kind('pornhub.Search', 'Search'), 'skip')
        self.assertEqual(pc.listing_kind('pornhub.ContextQuality', 'Quality'), 'skip')
        self.assertFalse(pc.should_follow_dir('pornhub.Playvid', 'Clip', 1, 3, True))
        self.assertFalse(pc.should_follow_dir('pornhub.Search', 'Search', 1, 3, True))

    def test_follow_categories_until_depth_cap(self):
        self.assertTrue(pc.should_follow_dir('pornhub.Categories', 'Categories', 1, 2, True))
        self.assertFalse(pc.should_follow_dir('pornhub.Categories', 'Categories', 2, 2, True))
        self.assertTrue(pc.should_follow_dir('pornhub.List', 'Amateur', 2, 3, True))
        self.assertFalse(pc.should_follow_dir('pornhub.List', 'Amateur', 3, 3, True))
        self.assertFalse(pc.should_follow_dir('pornhub.List', 'Amateur', 1, 3, False))

    def test_next_page_is_not_followed(self):
        self.assertEqual(pc.listing_kind('pornhub.List', 'Next Page...'), 'next')
        self.assertFalse(pc.should_follow_dir('pornhub.List', '[COLOR hotpink]Next Page[/COLOR]', 1, 3, True))


class ImageUrlTests(unittest.TestCase):
    def test_reject_videos_accept_thumbs(self):
        self.assertTrue(pc.looks_like_video_url('https://cdn.example/video.mp4'))
        self.assertTrue(pc.looks_like_video_url('https://cdn.example/master.m3u8?token=1'))
        self.assertFalse(pc.looks_like_image_url('https://cdn.example/video.mp4'))
        self.assertTrue(pc.looks_like_image_url('https://cdn.example/thumb.jpg'))
        self.assertTrue(pc.looks_like_image_url('https://cdn.example/i/abc123'))
        self.assertFalse(pc.looks_like_image_url('/local/logo.png'))
        self.assertFalse(pc.looks_like_image_url('special://home/thumb.png'))

    def test_image_urls_from_listing_entry(self):
        urls = pc.image_urls_from_entry({
            'iconimage': 'https://cdn.example/t.jpg|Referer=https://x/',
            'fanart': 'https://cdn.example/f.png',
            'url': 'https://site.example/video.mp4',
            'mode': 'pornhub.Playvid',
        })
        self.assertEqual(urls, ['https://cdn.example/t.jpg', 'https://cdn.example/f.png'])
        self.assertEqual(pc.image_urls_from_entry({
            'iconimage': 'https://cdn.example/clip.mp4',
        }), [])


class QueuePersistTests(unittest.TestCase):
    def test_visit_key_and_enqueue_dedupe(self):
        job = pc.new_job([{
            'site': 'pornhub', 'mode': 'pornhub.Main', 'url': 'https://www.pornhub.com/',
        }], depth=2, max_items=10, max_bytes=0)
        self.assertEqual(job['status'], 'running')
        self.assertEqual(len(job['queue']), 1)
        child = {
            'site': 'pornhub', 'mode': 'pornhub.Categories',
            'url': 'https://www.pornhub.com/categories', 'depth': 2,
        }
        self.assertTrue(pc.enqueue_child(job, child))
        self.assertFalse(pc.enqueue_child(job, child))
        first = pc.pop_next(job)
        pc.mark_visited(job, first)
        self.assertIn(pc.visit_key('pornhub', 'pornhub.Main', 'https://www.pornhub.com/'), job['visited'])
        pc.maybe_complete_site(job, 'pornhub')
        self.assertNotIn('pornhub', job['done_sites'])
        pc.pop_next(job)
        pc.maybe_complete_site(job, 'pornhub')
        self.assertIn('pornhub', job['done_sites'])

    def test_caps_and_status(self):
        job = pc.new_job([], depth=2, max_items=5, max_bytes=100)
        job['stats']['images'] = 5
        self.assertEqual(pc.cap_reached(job['stats'], 5, 100), 'max_items')
        job['stats']['images'] = 1
        job['stats']['bytes'] = 100
        self.assertEqual(pc.cap_reached(job['stats'], 5, 100), 'max_bytes')
        self.assertIsNone(pc.cap_reached(job['stats'], 0, 0))
        job['status'] = 'complete'
        job['finished'] = 1700000000
        job['stats']['images'] = 12
        job['stats']['bytes'] = 2048
        text = pc.format_status(job)
        self.assertIn('Last precache', text)
        self.assertIn('12 images', text)

    def test_json_roundtrip_survives_restart(self):
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        try:
            job = pc.new_job([
                {'site': 'txxx', 'mode': 'txxx.Main', 'url': 'https://txxx.com/'},
                {'site': 'pornhub', 'mode': 'pornhub.Main', 'url': 'https://www.pornhub.com/'},
            ], depth=3, max_items=100, max_bytes=50 * 1024 * 1024)
            pc.pop_next(job)
            job['stats']['images'] = 4
            job['stats']['bytes'] = 12345
            pc.save_job(path, job)
            loaded = pc.load_job(path)
            self.assertEqual(loaded['status'], 'running')
            self.assertEqual(loaded['depth'], 3)
            self.assertEqual(len(loaded['queue']), 1)
            self.assertEqual(loaded['queue'][0]['site'], 'pornhub')
            self.assertEqual(loaded['stats']['images'], 4)
        finally:
            os.remove(path)

    def test_cache_path_helper_and_prefer_cached(self):
        tmp = tempfile.mkdtemp(prefix='cumi-pc-')
        settings = art.default_settings()
        settings['cache_dir'] = tmp
        url = 'https://cdn.example/thumbs/a.jpg'
        path = art.src_cache_path_for_url(url, settings)
        self.assertTrue(path.startswith(os.path.join(tmp, 'src')))
        self.assertEqual(art.resolve_cached_image(url, settings), url)
        os.makedirs(os.path.dirname(path))
        with open(path, 'wb') as fh:
            fh.write(b'x' * 64)
        self.assertEqual(art.resolve_cached_image(url, settings), path)
        self.assertEqual(art.resolve_cached_image(url + '|Referer=https://x/', settings), path)
        art_dict, _props = art.build_art(url, is_folder=False, settings=settings)
        self.assertEqual(art_dict['thumb'], path)

    def test_expected_disk_note(self):
        note = pc.expected_disk_note(2500, 400, 2, 8)
        self.assertIn('8 site', note)
        self.assertIn('depth 2', note)
        self.assertIn('never videos', note)


if __name__ == '__main__':
    unittest.main()
