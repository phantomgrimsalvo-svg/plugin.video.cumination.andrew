# -*- coding: utf-8 -*-
"""Kodi settings actions for per-site enable/disable."""
from __future__ import absolute_import

import os

from kodi_six import xbmcgui

from resources.lib import basics
from resources.lib import siteflags_lib
from resources.lib import utils
from resources.lib.adultsite import AdultSite
from resources.lib.url_dispatcher import URL_Dispatcher

url_dispatcher = URL_Dispatcher('siteflags')


def _refresh_container():
    try:
        from kodi_six import xbmc
        xbmc.executebuiltin('Container.Refresh')
    except Exception:
        pass

_STATE_CACHE = {'mtime': None, 'state': None, 'path': None}


def flags_path():
    return os.path.join(basics.profileDir, 'siteflags.json')


def get_state():
    path = flags_path()
    mtime = None
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = None
    if (
        _STATE_CACHE['state'] is not None
        and _STATE_CACHE['path'] == path
        and _STATE_CACHE['mtime'] == mtime
    ):
        return _STATE_CACHE['state']
    state = siteflags_lib.load_state(path)
    _STATE_CACHE['mtime'] = mtime
    _STATE_CACHE['state'] = state
    _STATE_CACHE['path'] = path
    return state


def save_state(state):
    path = flags_path()
    ok = siteflags_lib.save_state(path, state)
    _STATE_CACHE['state'] = siteflags_lib.normalize_state(state)
    try:
        _STATE_CACHE['mtime'] = os.path.getmtime(path)
    except Exception:
        _STATE_CACHE['mtime'] = None
    _STATE_CACHE['path'] = path
    refresh_status_setting()
    return ok


def is_enabled(name):
    try:
        return siteflags_lib.is_site_enabled(name, get_state())
    except Exception:
        return True


def is_precache_site(name):
    try:
        return siteflags_lib.is_precache_site(name, get_state())
    except Exception:
        return is_enabled(name)


def catalog():
    sites = []
    seen = set()
    for site in AdultSite.get_all_sites():
        name = site.name or ''
        if not name or name in seen:
            continue
        seen.add(name)
        sites.append(site)
    sites.sort(key=lambda s: (s.get_clean_title() or s.name or '').lower())
    return sites


def catalog_names():
    return [s.name for s in catalog()]


def refresh_status_setting():
    names = catalog_names()
    text = siteflags_lib.enabled_summary(names, get_state())
    try:
        basics.addon.setSetting('sites_status', text)
    except Exception:
        pass
    return text


def _notify(msg):
    try:
        utils.notify('Cumination', msg)
    except Exception:
        pass


def _multiselect(heading, sites, preselected_names):
    labels = []
    for site in sites:
        title = site.get_clean_title() or site.name
        extra = ' [webcam]' if site.webcam else ''
        labels.append(u'{0}{1}  ({2})'.format(title, extra, site.name))
    wanted = set((n or '').lower() for n in (preselected_names or []))
    preselect = [i for i, site in enumerate(sites) if (site.name or '').lower() in wanted]
    try:
        choice = xbmcgui.Dialog().multiselect(heading, labels, preselect=preselect)
    except TypeError:
        choice = xbmcgui.Dialog().multiselect(heading, labels)
    return choice


@url_dispatcher.register()
def choose_enabled():
    sites = catalog()
    if not sites:
        _notify('No sites are loaded yet')
        return
    state = get_state()
    current = [s.name for s in sites if siteflags_lib.is_site_enabled(s.name, state)]
    choice = _multiselect('Enabled sites (unchecked are hidden)', sites, current)
    if choice is None:
        return
    selected = [sites[i].name for i in choice if 0 <= i < len(sites)]
    state['disabled'] = siteflags_lib.disabled_from_selection(catalog_names(), selected)
    save_state(state)
    _notify(siteflags_lib.enabled_summary(catalog_names(), state))
    _refresh_container()


@url_dispatcher.register()
def enable_all():
    state = get_state()
    state['disabled'] = []
    save_state(state)
    _notify(siteflags_lib.enabled_summary(catalog_names(), state))
    _refresh_container()


@url_dispatcher.register()
def disable_all():
    if not xbmcgui.Dialog().yesno(
        'Cumination',
        'Hide every site from the Sites list, global search, and precache?\nFavorites already saved are kept.',
    ):
        return
    state = get_state()
    state['disabled'] = [n.lower() for n in catalog_names()]
    save_state(state)
    _notify(siteflags_lib.enabled_summary(catalog_names(), state))
    _refresh_container()


@url_dispatcher.register()
def disable_webcams():
    state = get_state()
    disabled = set(state.get('disabled') or [])
    added = 0
    for site in catalog():
        if site.webcam:
            key = (site.name or '').lower()
            if key and key not in disabled:
                disabled.add(key)
                added += 1
    state['disabled'] = sorted(disabled)
    save_state(state)
    _notify('Disabled {0} webcam site(s). {1}'.format(
        added, siteflags_lib.enabled_summary(catalog_names(), state)))
    _refresh_container()


@url_dispatcher.register()
def refresh_status():
    refresh_status_setting()


@url_dispatcher.register()
def menu():
    """Directory of site enable/disable actions (reachable from INDEX)."""
    summary = refresh_status_setting()
    basics.addDir(
        '[COLOR hotpink]{0}[/COLOR]'.format(summary),
        '', 'siteflags.refresh_status', basics.cum_image('cum-sites.png'),
        Folder=False, list_avail=False,
    )
    basics.addDir(
        '[COLOR white]Choose enabled sites[/COLOR]',
        '', 'siteflags.choose_enabled', basics.cum_image('cum-sites.png'),
        Folder=False, list_avail=False,
    )
    basics.addDir(
        '[COLOR white]Enable all sites[/COLOR]',
        '', 'siteflags.enable_all', basics.cum_image('cum-sites.png'),
        Folder=False, list_avail=False,
    )
    basics.addDir(
        '[COLOR white]Disable all sites[/COLOR]',
        '', 'siteflags.disable_all', basics.cum_image('cum-sites.png'),
        Folder=False, list_avail=False,
    )
    basics.addDir(
        '[COLOR white]Disable webcam sites[/COLOR]',
        '', 'siteflags.disable_webcams', basics.cum_image('cum-sites.png'),
        Folder=False, list_avail=False,
    )
    utils.eod(basics.addon_handle, False)
