# -*- coding: utf-8 -*-
"""Import default.py the way Kodi loads the plugin, then run INDEX()."""
from __future__ import absolute_import

import os
import sys
import types
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _install_kodi_stubs(profile):
    xbmc = types.ModuleType('xbmc')
    xbmc.LOGDEBUG = 0
    xbmc.LOGERROR = 1
    xbmc.LOGINFO = 2
    xbmc.LOGNOTICE = 2
    xbmc.log = lambda *a, **k: None
    xbmc.getSkinDir = lambda: 'estuary'
    xbmc.translatePath = lambda p: p
    xbmc.executebuiltin = lambda *a, **k: None
    xbmc.sleep = lambda *a, **k: None
    xbmc.getInfoLabel = lambda *a, **k: ''

    class Monitor(object):
        def abortRequested(self):
            return False

        def waitForAbort(self, t=0):
            return False

    xbmc.Monitor = Monitor
    xbmc.Keyboard = object

    xbmcaddon = types.ModuleType('xbmcaddon')

    class Addon(object):
        def __init__(self, aid=None, *a, **k):
            self._id = aid

        def getSetting(self, key):
            return {
                'content': '0',
                'custom_sites': 'false',
                'enh_debug': 'false',
                'cuminationage': 'true',
                'changelog_seen_version': '1.2.9',
                'customview': 'false',
                'posterfanart': 'false',
                'cache_time': '4',
                'filter_listing': '',
            }.get(key, '')

        def setSetting(self, *a, **k):
            return None

        def getAddonInfo(self, key):
            if self._id == 'xbmc.addon':
                return {'version': '19.80.0'}.get(key, '')
            return {
                'path': ROOT,
                'profile': profile,
                'version': '1.2.9',
            }.get(key, '')

        def getLocalizedString(self, i):
            return str(i)

    xbmcaddon.Addon = Addon

    xbmcplugin = types.ModuleType('xbmcplugin')
    xbmcplugin.setContent = lambda *a, **k: None
    xbmcplugin.addDirectoryItem = lambda *a, **k: True
    xbmcplugin.endOfDirectory = lambda *a, **k: None
    xbmcplugin.setResolvedUrl = lambda *a, **k: None

    xbmcgui = types.ModuleType('xbmcgui')

    class ListItem(object):
        def __init__(self, name='', *a, **k):
            self._name = name
            self.art = {}
            self.props = {}

        def setArt(self, mapping):
            self.art.update(mapping or {})

        def setProperty(self, key, value):
            self.props[key] = value

        def setInfo(self, *a, **k):
            return None

        def addContextMenuItems(self, *a, **k):
            return None

        def getVideoInfoTag(self):
            class Tag(object):
                def setMediaType(self, *a, **k):
                    return None

                def setTitle(self, *a, **k):
                    return None

                def setPlot(self, *a, **k):
                    return None

                def setPlotOutline(self, *a, **k):
                    return None

            return Tag()

    class Dialog(object):
        def ok(self, *a, **k):
            return True

        def yesno(self, *a, **k):
            return True

        def notification(self, *a, **k):
            return None

        def select(self, *a, **k):
            return -1

        def multiselect(self, *a, **k):
            return None

        def browse(self, *a, **k):
            return ''

    class DialogProgress(object):
        def create(self, *a, **k):
            return None

        def update(self, *a, **k):
            return None

        def close(self, *a, **k):
            return None

        def iscanceled(self):
            return False

    xbmcgui.ListItem = ListItem
    xbmcgui.Dialog = Dialog
    xbmcgui.DialogProgress = DialogProgress
    xbmcgui.DialogProgressBG = DialogProgress
    xbmcgui.Window = type(
        'Window', (),
        {'__init__': lambda s, *a, **k: None, 'setProperty': lambda *a, **k: None},
    )

    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda p: p
    xbmcvfs.exists = lambda p: False
    xbmcvfs.delete = lambda p: False

    kodi_six = types.ModuleType('kodi_six')
    kodi_six.xbmc = xbmc
    kodi_six.xbmcaddon = xbmcaddon
    kodi_six.xbmcplugin = xbmcplugin
    kodi_six.xbmcgui = xbmcgui
    kodi_six.xbmcvfs = xbmcvfs
    for name, mod in (
        ('xbmc', xbmc),
        ('xbmcaddon', xbmcaddon),
        ('xbmcplugin', xbmcplugin),
        ('xbmcgui', xbmcgui),
        ('xbmcvfs', xbmcvfs),
        ('kodi_six', kodi_six),
    ):
        sys.modules[name] = mod

    storage = types.ModuleType('StorageServer')

    class StorageServer(object):
        def __init__(self, *a, **k):
            return None

        def cacheFunction(self, fn, *a, **k):
            return fn(*a, **k)

        def cacheDelete(self, *a, **k):
            return None

    storage.StorageServer = StorageServer
    sys.modules['StorageServer'] = storage
    return xbmcplugin, ListItem


class PluginOpenSmokeTests(unittest.TestCase):
    def test_default_imports_and_index_builds_main_menu(self):
        import tempfile
        profile = tempfile.mkdtemp(prefix='cumi-smoke-')
        os.makedirs(os.path.join(profile, 'custom_sites'), exist_ok=True)
        os.makedirs(os.path.join(profile, 'temp'), exist_ok=True)
        xbmcplugin, _ListItem = _install_kodi_stubs(profile)
        sys.path.insert(0, ROOT)
        sys.argv = ['plugin://plugin.video.cumination.andrew/', '-1', '']
        names = []

        def capture(*args, **kwargs):
            liz = kwargs.get('listitem')
            if liz is None and len(args) > 2:
                liz = args[2]
            names.append(getattr(liz, '_name', '') or '')
            return True

        xbmcplugin.addDirectoryItem = capture
        import default as plugin
        self.assertTrue(hasattr(plugin, 'INDEX'))
        self.assertTrue(hasattr(plugin, 'precache'))
        plugin.INDEX()
        blob = ' '.join(names).lower()
        self.assertGreaterEqual(len(names), 3)
        self.assertIn('search all sites', blob)


if __name__ == '__main__':
    unittest.main()
