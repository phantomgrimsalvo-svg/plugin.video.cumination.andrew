# -*- coding: utf-8 -*-
"""Background monitor for Mode C (slow top→bottom pan).

Kodi cannot animate ListItem.Art(fanart) from a plugin. This service:
  * watches the focused item's Andrew.FanartMode=pan property
  * cycles Window(Home) properties skins can bind to
  * generates pan frames on demand when Pillow can open the source

Skin hook (Arctic Fuse 3 Andrew, or any skin):
  Window(Home).Property(Cumination.PanFanart)     current 16:9 frame
  Window(Home).Property(Cumination.FanartMode)    pillarbox|topfill|pan|off
  Window(Home).Property(Cumination.FanartAlignY)  top|center
  Window(Home).Property(Cumination.FanartAspect)  keep|scale
  Window(Home).Property(Cumination.FanartPanDuration)  seconds
  ListItem.Property(Andrew.FanartPanFrames)       pipe-separated frame paths
"""
from __future__ import absolute_import

import time

HOME_WINDOW_ID = 10000
PROP_PREFIX = 'Cumination.'


def _info(key):
    try:
        from kodi_six import xbmc
        value = xbmc.getInfoLabel(key) or ''
        return value
    except Exception:
        return ''


def _focused_property(name):
    return (
        _info('ListItem.Property({0})'.format(name))
        or _info('Container.ListItem.Property({0})'.format(name))
    )


def _set_home(home, key, value):
    try:
        home.setProperty(PROP_PREFIX + key, value or '')
    except Exception:
        pass


def _clear_home(home):
    for key in (
        'PanFanart', 'FanartMode', 'FanartAlignY', 'FanartAspect',
        'FanartPanDuration', 'FanartSource',
    ):
        _set_home(home, key, '')


def _frames_from_item(settings):
    packed = _focused_property('Andrew.FanartPanFrames')
    if packed:
        frames = [p for p in packed.split('|') if p]
        if frames:
            return frames
    source = _focused_property('Andrew.FanartSource')
    if not source:
        source = (
            _info('ListItem.Art(thumb)')
            or _info('Container.ListItem.Art(thumb)')
        )
    if not source:
        return []
    try:
        from resources.lib import andrew_art
        allow = dict(settings)
        allow['allow_remote_fetch'] = True
        return andrew_art.pan_frame_paths(source, allow)
    except Exception:
        return []


def run():
    from kodi_six import xbmc, xbmcgui, xbmcaddon, xbmcvfs
    from resources.lib import andrew_art

    monitor = xbmc.Monitor()
    addon = xbmcaddon.Addon()
    home = xbmcgui.Window(HOME_WINDOW_ID)
    translate = xbmcvfs.translatePath if hasattr(xbmcvfs, 'translatePath') else xbmc.translatePath
    profile = translate(addon.getAddonInfo('profile'))
    cache_dir = os_join_cache(profile)
    framed_dir = os_join_framed(translate(addon.getAddonInfo('path')))

    last_sig = None
    frames = []
    index = 0
    last_tick = 0.0
    direction = 1
    last_precache = 0.0

    while not monitor.abortRequested():
        now = time.time()
        if now - last_precache >= 0.8:
            last_precache = now
            try:
                from resources.lib import precache
                precache.service_tick(monitor, budget_sec=1.4)
            except Exception:
                pass

        try:
            settings = andrew_art.settings_from_addon(
                addon,
                cache_dir=cache_dir,
                framed_dir=framed_dir,
                addon_fanart='',
                images_dir=os_join_images(translate(addon.getAddonInfo('path'))),
            )
            mode = _focused_property('Andrew.FanartMode') or ''
            if settings.get('portrait_fanart_mode') == andrew_art.MODE_PAN:
                if not mode:
                    mode = andrew_art.MODE_PAN if (
                        settings.get('posterfanart') and settings.get('portrait_fanart_extras')
                    ) else ''
            duration = int(_focused_property('Andrew.FanartPanDuration') or settings.get('portrait_fanart_pan_duration') or 20)
            duration = max(6, min(60, duration))
            source = _focused_property('Andrew.FanartSource')
            sig = '{0}|{1}|{2}'.format(mode, source, duration)

            _set_home(home, 'FanartMode', mode)
            _set_home(home, 'FanartAlignY', _focused_property('Andrew.FanartAlignY') or 'top')
            _set_home(home, 'FanartAspect', _focused_property('Andrew.FanartAspect') or 'scale')
            _set_home(home, 'FanartPanDuration', str(duration))
            _set_home(home, 'FanartSource', source)

            if mode != andrew_art.MODE_PAN:
                if last_sig is not None:
                    _set_home(home, 'PanFanart', '')
                    last_sig = None
                    frames = []
                monitor.waitForAbort(0.8)
                continue

            if sig != last_sig:
                last_sig = sig
                index = 0
                direction = 1
                frames = _frames_from_item(settings)
                last_tick = time.time()
                if frames:
                    _set_home(home, 'PanFanart', frames[0])

            if len(frames) >= 2:
                step = max(0.35, float(duration) / float(len(frames)))
                now = time.time()
                if now - last_tick >= step:
                    last_tick = now
                    index += direction
                    if index >= len(frames) - 1:
                        index = len(frames) - 1
                        direction = -1
                    elif index <= 0:
                        index = 0
                        direction = 1
                    _set_home(home, 'PanFanart', frames[index])
            monitor.waitForAbort(0.35)
        except Exception:
            monitor.waitForAbort(2.0)

    _clear_home(home)


def os_join_cache(profile):
    import os
    path = os.path.join(profile, 'artcache')
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except OSError:
            pass
    return path


def os_join_framed(root):
    import os
    return os.path.join(root, 'resources', 'images', 'framed')


def os_join_images(root):
    import os
    return os.path.join(root, 'resources', 'images')
