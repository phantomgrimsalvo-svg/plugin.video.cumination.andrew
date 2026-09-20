# -*- coding: utf-8 -*-
"""Tests for site enable/disable allowlist helpers (no Kodi)."""
from __future__ import absolute_import

import os
import tempfile
import unittest

from resources.lib import siteflags_lib as flags


class SiteFlagsTests(unittest.TestCase):
    def test_default_all_enabled(self):
        state = flags.default_state()
        self.assertTrue(flags.is_site_enabled('pornhub', state))
        self.assertTrue(flags.is_site_enabled('xvideos', state))
        self.assertEqual(flags.filter_enabled_names(['pornhub', 'xvideos'], state),
                         ['pornhub', 'xvideos'])

    def test_disabled_hidden_and_new_sites_stay_on(self):
        state = flags.normalize_state({'disabled': ['XVideos', 'chaturbate']})
        names = ['pornhub', 'xvideos', 'chaturbate', 'txxx']
        self.assertEqual(flags.filter_enabled_names(names, state), ['pornhub', 'txxx'])
        self.assertTrue(flags.is_site_enabled('brandnew', state))

    def test_selection_writes_disabled_not_enabled_list(self):
        all_names = ['pornhub', 'xvideos', 'txxx']
        disabled = flags.disabled_from_selection(all_names, ['PornHub'])
        self.assertEqual(sorted(disabled), ['txxx', 'xvideos'])
        state = flags.normalize_state({'disabled': disabled})
        self.assertEqual(flags.filter_enabled_names(all_names, state), ['pornhub'])

    def test_precache_defaults_to_enabled(self):
        state = flags.normalize_state({'disabled': ['xvideos']})
        self.assertTrue(flags.is_precache_site('pornhub', state))
        self.assertFalse(flags.is_precache_site('xvideos', state))
        state['precache_sites'] = ['xvideos']
        self.assertFalse(flags.is_precache_site('pornhub', state))
        self.assertTrue(flags.is_precache_site('xvideos', state))

    def test_empty_precache_list_is_none_selected(self):
        state = flags.normalize_state({'precache_sites': []})
        self.assertFalse(flags.is_precache_site('pornhub', state))
        self.assertEqual(flags.filter_precache_names(['pornhub', 'txxx'], state), [])

    def test_summary_and_roundtrip(self):
        names = ['a', 'b', 'c']
        self.assertEqual(flags.enabled_summary(names, flags.default_state()),
                         'All 3 sites enabled')
        state = flags.normalize_state({'disabled': ['b', 'c']})
        self.assertEqual(flags.enabled_summary(names, state), '1 of 3 sites enabled')
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        try:
            flags.save_state(path, state)
            loaded = flags.load_state(path)
            self.assertEqual(loaded['disabled'], ['b', 'c'])
            self.assertIsNone(loaded['precache_sites'])
        finally:
            os.remove(path)

    def test_corrupt_file_defaults_open(self):
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        try:
            with open(path, 'w') as fh:
                fh.write('{not json')
            state = flags.load_state(path)
            self.assertTrue(flags.is_site_enabled('pornhub', state))
        finally:
            os.remove(path)


if __name__ == '__main__':
    unittest.main()
