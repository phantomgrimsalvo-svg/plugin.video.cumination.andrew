# -*- coding: utf-8 -*-
"""Unit tests for aggregated global search helpers (no Kodi)."""
from __future__ import absolute_import

import os
import sqlite3
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from resources.lib.gsearch_lib import (  # noqa: E402
    clean_video_title, decorate_title, enrich_item, extract_search_url_from_source,
    is_search_mode, keyword_from_result_title, keyword_is_provided,
    normalize_plugin_queries, normalize_sort, parse_csv_names, parse_date, parse_rating,
    parse_views, relevance_score, site_allowed, sort_items, strip_colors, url_looks_complete,
)
from resources.lib.db_schema import migrate_custom_list_schema  # noqa: E402


class QueryAndSortTests(unittest.TestCase):
    def test_skin_aliases_map_to_main_modes(self):
        q = normalize_plugin_queries({'mode': 'skin_search', 'query': 'redhead'})
        self.assertEqual(q['mode'], 'main.skin_search')
        self.assertEqual(q['keyword'], 'redhead')

        q2 = normalize_plugin_queries({'mode': 'global_search', 'q': 'blonde'})
        self.assertEqual(q2['mode'], 'main.global_search')
        self.assertEqual(q2['keyword'], 'blonde')

        q3 = normalize_plugin_queries({'mode': 'search', 'keyword': 'fit'})
        self.assertEqual(q3['mode'], 'main.search')
        self.assertEqual(q3['keyword'], 'fit')

    def test_keyword_is_provided(self):
        self.assertFalse(keyword_is_provided(None))
        self.assertFalse(keyword_is_provided(''))
        self.assertFalse(keyword_is_provided('  '))
        self.assertTrue(keyword_is_provided('foo'))

    def test_normalize_sort(self):
        self.assertEqual(normalize_sort(None), 'relevance')
        self.assertEqual(normalize_sort('2'), 'views')
        self.assertEqual(normalize_sort('newness'), 'date')
        self.assertEqual(normalize_sort('top rated'), 'rating')

    def test_sort_unknowns_last(self):
        items = [
            {'name': 'old', 'date': 100, 'views': None, 'rating': 80, 'position': 0, 'relevance': 10},
            {'name': 'new', 'date': 200, 'views': 50, 'rating': None, 'position': 1, 'relevance': 5},
            {'name': 'none', 'date': None, 'views': None, 'rating': None, 'position': 2, 'relevance': 1},
        ]
        by_date = [i['name'] for i in sort_items(items, 'date')]
        self.assertEqual(by_date, ['new', 'old', 'none'])
        by_views = [i['name'] for i in sort_items(items, 'views')]
        self.assertEqual(by_views[0], 'new')
        self.assertEqual(by_views[-1], 'none')
        by_rating = [i['name'] for i in sort_items(items, 'rating')]
        self.assertEqual(by_rating[0], 'old')
        self.assertEqual(by_rating[-1], 'none')

    def test_relevance_prefers_exact_and_substring(self):
        self.assertGreater(relevance_score('redhead', 'redhead'), relevance_score('the redhead next door', 'redhead'))
        self.assertGreater(relevance_score('the redhead next door', 'redhead'), relevance_score('unrelated', 'redhead'))


class ParseMetaTests(unittest.TestCase):
    def test_parse_views(self):
        self.assertEqual(parse_views('1.2M views'), 1200000.0)
        self.assertEqual(parse_views('12K views'), 12000.0)
        self.assertEqual(parse_views('views: 1,234'), 1234.0)
        self.assertIsNone(parse_views('no numbers here'))

    def test_parse_rating(self):
        self.assertEqual(parse_rating('rated 89%'), 89.0)
        self.assertAlmostEqual(parse_rating('4.5/5 stars'), 90.0)
        self.assertIsNone(parse_rating('hello'))

    def test_parse_date_relative(self):
        now = 1_700_000_000
        ts = parse_date('uploaded 2 days ago', now=now)
        self.assertEqual(ts, now - 2 * 86400)
        self.assertIsNone(parse_date('mystery'))

    def test_enrich_and_decorate(self):
        item = enrich_item(
            {'name': 'Redhead amateur', 'desc': '2 days ago · 12K views · 90%', 'duration': '12:01', 'quality': '720p'},
            'redhead', 'PornHub', 3,
        )
        self.assertEqual(item['site_name'], 'PornHub')
        self.assertGreater(item['views'], 10000)
        self.assertGreater(item['rating'], 80)
        self.assertIsNotNone(item['date'])
        title = decorate_title('PornHub', '[COLOR hotpink]Clip[/COLOR]')
        self.assertEqual(title, '[PornHub] Clip')
        self.assertEqual(clean_video_title('[PornHub] Clip'), 'Clip')
        self.assertEqual(keyword_from_result_title('[COLOR orange][PornHub][/COLOR] Foo 12:01'), 'Foo')
        self.assertEqual(strip_colors('[COLOR hotpink]X[/COLOR]'), 'X')


class SiteFilterAndUrlTests(unittest.TestCase):
    def test_include_exclude(self):
        self.assertTrue(site_allowed('pornhub', include=None, exclude=['xvideos']))
        self.assertFalse(site_allowed('xvideos', include=None, exclude=['xvideos']))
        self.assertTrue(site_allowed('pornhub', include=['pornhub'], exclude=['pornhub']))
        self.assertFalse(site_allowed('xvideos', include=['pornhub'], exclude=None))
        self.assertEqual(parse_csv_names('PornHub, xVideos ; txxx'), ['pornhub', 'xvideos', 'txxx'])

    def test_search_mode_names(self):
        self.assertTrue(is_search_mode('pornhub.Search'))
        self.assertTrue(is_search_mode('xtheatre.XTSearch'))
        self.assertTrue(is_search_mode('porntrex.PTSearch'))
        self.assertFalse(is_search_mode('erome.Search_user'))
        self.assertFalse(is_search_mode('pornhub.List'))

    def test_extract_search_url_from_main_source(self):
        src = (
            "def Main():\n"
            "    site.add_dir('[COLOR hotpink]Search[/COLOR]', site.url + 'video/search?search=', 'Search', site.img_search)\n"
            "    List(site.url + 'video?o=cm')\n"
        )
        url, mode = extract_search_url_from_source(src, 'https://www.pornhub.com/')
        self.assertEqual(mode, 'Search')
        self.assertEqual(url, 'https://www.pornhub.com/video/search?search=')

        src2 = (
            "    site.add_dir('[COLOR hotpink]Search[/COLOR]', site.url + 'search/{0}/', 'Search', site.img_search)\n"
        )
        url2, mode2 = extract_search_url_from_source(src2, 'https://xxthots.com/')
        self.assertEqual(mode2, 'Search')
        self.assertIn('{0}', url2)
        self.assertTrue(url_looks_complete(url2))
        self.assertFalse(url_looks_complete('https://xvideos.com/?typef={cat}&k='))

        src3 = (
            "    site.add_dir('[COLOR hotpink]Search[/COLOR]', site.url + '?typef={}&k='.format(cat), 'Search', site.img_search)\n"
        )
        url3, mode3 = extract_search_url_from_source(src3, 'https://www.xvideos.com/')
        self.assertIsNone(url3)


class CustomListSchemaTests(unittest.TestCase):
    def test_migrate_adds_art_columns_without_dropping_rows(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        try:
            conn = sqlite3.connect(path)
            c = conn.cursor()
            c.execute('CREATE TABLE custom_lists (name)')
            c.execute('INSERT INTO custom_lists (name) VALUES (?)', ('My List',))
            conn.commit()
            migrate_custom_list_schema(c)
            conn.commit()
            c.execute('SELECT name, thumb, fanart, poster FROM custom_lists')
            row = c.fetchone()
            self.assertEqual(row[0], 'My List')
            self.assertTrue(all(v is None for v in row[1:]))
            c.execute('INSERT INTO custom_lists (name) VALUES (?)', ('Second',))
            c.execute('UPDATE custom_lists SET thumb = ?, fanart = ? WHERE name = ?',
                      ('http://example/t.png', '/tmp/fanart.jpg', 'Second'))
            conn.commit()
            c.execute('SELECT name FROM custom_lists ORDER BY rowid')
            names = [r[0] for r in c.fetchall()]
            self.assertEqual(names, ['My List', 'Second'])
            conn.close()
        finally:
            os.remove(path)

    def test_keywords_table_untouched_by_list_migration(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        try:
            conn = sqlite3.connect(path)
            c = conn.cursor()
            c.execute('CREATE TABLE keywords (keyword)')
            c.execute('INSERT INTO keywords VALUES (?)', ('redhead',))
            c.execute('CREATE TABLE custom_lists (name)')
            migrate_custom_list_schema(c)
            conn.commit()
            c.execute('SELECT keyword FROM keywords')
            self.assertEqual(c.fetchone()[0], 'redhead')
            conn.close()
        finally:
            os.remove(path)


if __name__ == '__main__':
    unittest.main()
