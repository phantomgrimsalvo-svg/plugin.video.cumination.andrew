# -*- coding: utf-8 -*-
"""UTF-8 changelog/about reads and settings category order."""
from __future__ import absolute_import

import os
import tempfile
import unittest

from resources.lib import textio

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class Utf8TextTests(unittest.TestCase):
    def test_changelog_em_dash_does_not_raise(self):
        path = os.path.join(ROOT, 'changelog.txt')
        text = textio.read_utf8(path)
        self.assertIn('1.2.8', text)
        self.assertIn(u'\u2014', text)
        lines = textio.read_utf8_lines(path)
        self.assertTrue(lines)
        self.assertTrue(any(u'\u2014' in line for line in lines))

    def test_ascii_locale_style_replace_on_latin1_file(self):
        fd, path = tempfile.mkstemp(suffix='.txt')
        os.close(fd)
        try:
            with open(path, 'wb') as fh:
                fh.write(b'hello \xe2\x80\x94 world\n')
            text = textio.read_utf8(path)
            self.assertIn(u'\u2014', text)
            self.assertIn('hello', text)
        finally:
            os.remove(path)

    def test_missing_file_is_empty(self):
        self.assertEqual(textio.read_utf8('/no/such/changelog.txt'), '')
        self.assertEqual(textio.read_utf8_lines('/no/such/changelog.txt'), [])


class SettingsOrderTests(unittest.TestCase):
    def test_sites_and_precache_follow_general(self):
        path = os.path.join(ROOT, 'resources', 'settings.xml')
        with open(path, 'r', encoding='utf-8') as fh:
            xml = fh.read()
        cats = []
        needle = '<category label="'
        start = 0
        while True:
            idx = xml.find(needle, start)
            if idx < 0:
                break
            end = xml.find('"', idx + len(needle))
            cats.append(xml[idx + len(needle):end])
            start = end + 1
        self.assertGreaterEqual(len(cats), 4)
        self.assertEqual(cats[0], '30051')
        self.assertEqual(cats[1], '33200')
        self.assertEqual(cats[2], '33210')
        self.assertIn('33100', cats)


if __name__ == '__main__':
    unittest.main()
