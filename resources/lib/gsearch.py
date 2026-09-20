# -*- coding: utf-8 -*-
"""Aggregated 'Search all sites' for Cumination (Andrew)."""
from __future__ import absolute_import

import inspect
import socket
import sys
import threading
import traceback

try:
    from inspect import getargspec
except ImportError:
    from inspect import getfullargspec as getargspec

from six.moves import urllib_parse
from kodi_six import xbmc, xbmcgui, xbmcplugin

from resources.lib import basics
from resources.lib import utils
from resources.lib.adultsite import AdultSite
from resources.lib.url_dispatcher import URL_Dispatcher
from resources.lib.gsearch_lib import (
    clean_video_title, decorate_title, enrich_item, extract_search_url_from_source,
    is_search_mode, keyword_from_result_title, keyword_is_provided,
    normalize_plugin_queries, normalize_sort, parse_csv_names, site_allowed, sort_items,
    strip_colors, url_looks_complete,
)

url_dispatcher = URL_Dispatcher('gsearch')

_tls = threading.local()
_PATCHED = False
_PATCH_LOCK = threading.Lock()
_ORIG = {}
SORT_LABELS = {
    'relevance': 'Relevance',
    'date': 'Newest',
    'views': 'Most viewed',
    'rating': 'Top rated',
}
SORT_INDEX = {'relevance': '0', 'date': '1', 'views': '2', 'rating': '3'}


def _setting(key, default=''):
    try:
        val = basics.addon.getSetting(key)
    except Exception:
        val = ''
    return val if val not in (None, '') else default


def _setting_int(key, default):
    try:
        return int(_setting(key, str(default)))
    except Exception:
        return default


def _setting_bool(key, default=False):
    val = _setting(key, 'true' if default else 'false')
    return str(val).lower() == 'true'


def _kodilog(msg, level=None):
    try:
        utils.kodilog(u'gsearch: {0}'.format(msg), level if level is not None else xbmc.LOGDEBUG)
    except Exception:
        pass


def _is_collecting():
    return bool(getattr(_tls, 'collecting', False) or getattr(_tls, 'harvest', False))


def _capturing_addDownLink(name, url, mode, iconimage, desc='', stream=None, fav='add',
                           noDownload=False, contextm=None, fanart=None, duration='', quality=''):
    buf = getattr(_tls, 'items', None)
    if buf is not None:
        limit = getattr(_tls, 'limit', 9999)
        if len(buf) < limit:
            buf.append({
                'name': name,
                'url': url,
                'mode': mode,
                'iconimage': iconimage,
                'desc': desc or '',
                'stream': stream,
                'duration': duration or '',
                'quality': quality or '',
                'fanart': fanart,
            })
        return True
    return _ORIG['addDownLink'](name, url, mode, iconimage, desc, stream, fav, noDownload,
                                contextm, fanart, duration, quality)


def _capturing_addDir(name, url, mode, iconimage=None, page=None, channel=None, section=None,
                      keyword='', Folder=True, about=None, custom=False, list_avail=True,
                      listitem_id=None, custom_list=False, contextm=None, desc=''):
    if getattr(_tls, 'harvest', False):
        full = mode
        buf = getattr(_tls, 'dirs', None)
        if buf is not None:
            buf.append({'name': name, 'url': url, 'mode': full, 'iconimage': iconimage})
        return True
    if getattr(_tls, 'collecting', False):
        return True
    return _ORIG['addDir'](name, url, mode, iconimage, page, channel, section, keyword, Folder,
                           about, custom, list_avail, listitem_id, custom_list, contextm, desc)


def _capturing_eod(*args, **kwargs):
    if _is_collecting():
        return
    return _ORIG['eod'](*args, **kwargs)


def _capturing_notify(*args, **kwargs):
    if _is_collecting():
        return
    return _ORIG['notify'](*args, **kwargs)


def _capturing_addDirectoryItem(*args, **kwargs):
    if _is_collecting():
        return True
    return _ORIG['addDirectoryItem'](*args, **kwargs)


def _capturing_endOfDirectory(*args, **kwargs):
    if _is_collecting():
        return
    return _ORIG['endOfDirectory'](*args, **kwargs)


def _install_patches():
    global _PATCHED
    with _PATCH_LOCK:
        if _PATCHED:
            return
        from resources.lib import basics as basics_mod
        from resources.lib import utils as utils_mod
        from resources.lib import url_dispatcher as ud_mod

        _ORIG['addDownLink'] = basics_mod.addDownLink
        _ORIG['addDir'] = basics_mod.addDir
        _ORIG['eod'] = basics_mod.eod
        _ORIG['notify'] = utils_mod.notify
        _ORIG['ud_addDownLink'] = ud_mod.addDownLink
        _ORIG['ud_addDir'] = ud_mod.addDir
        _ORIG['ud_eod'] = getattr(ud_mod, 'eod', None)
        _ORIG['utils_eod'] = utils_mod.eod
        _ORIG['URL_add_dir'] = URL_Dispatcher.add_dir
        _ORIG['addDirectoryItem'] = xbmcplugin.addDirectoryItem
        _ORIG['endOfDirectory'] = xbmcplugin.endOfDirectory

        basics_mod.addDownLink = _capturing_addDownLink
        basics_mod.addDir = _capturing_addDir
        basics_mod.eod = _capturing_eod
        ud_mod.addDownLink = _capturing_addDownLink
        ud_mod.addDir = _capturing_addDir
        utils_mod.eod = _capturing_eod
        utils_mod.notify = _capturing_notify
        URL_Dispatcher.add_dir = _patched_add_dir
        xbmcplugin.addDirectoryItem = _capturing_addDirectoryItem
        xbmcplugin.endOfDirectory = _capturing_endOfDirectory
        _PATCHED = True


def _patched_add_dir(self, name, url, mode, iconimage=None, page=None, channel=None, section=None,
                     keyword='', Folder=True, about=None, custom=False, list_avail=True,
                     listitem_id=None, custom_list=False, contextm=None, desc=''):
    mode = self.get_full_mode(mode)
    if getattr(_tls, 'harvest', False):
        buf = getattr(_tls, 'dirs', None)
        if buf is not None:
            buf.append({'name': name, 'url': url, 'mode': mode, 'iconimage': iconimage,
                        'site': getattr(self, 'name', '')})
        return True
    if getattr(_tls, 'collecting', False):
        return True
    return _ORIG['URL_add_dir'](
        self, name, url, mode, iconimage, page, channel, section, keyword, Folder, about,
        custom, list_avail, listitem_id, custom_list, contextm, desc
    )


def _call_registered(mode, url, keyword=None):
    func = URL_Dispatcher.func_registry.get(mode)
    if not func:
        raise RuntimeError('unregistered mode {0}'.format(mode))
    spec = getargspec(func)
    args = list(spec.args or [])
    defaults = spec.defaults or ()
    kwarg_names = args[-len(defaults):] if defaults else []
    pos_names = args[:-len(defaults)] if defaults else args
    call_args = []
    call_kwargs = {}
    values = {'url': url, 'keyword': keyword, 'name': keyword}
    for name in pos_names:
        if name == 'self':
            continue
        if name in values and values[name] is not None:
            call_args.append(values[name])
        elif name == 'url':
            call_args.append(url or '')
        else:
            raise RuntimeError('cannot fill required arg {0} for {1}'.format(name, mode))
    for name in kwarg_names:
        if name in values and values[name] is not None:
            call_kwargs[name] = values[name]
    return func(*call_args, **call_kwargs)


def _search_url_from_source(site):
    func = URL_Dispatcher.func_registry.get(site.default_mode)
    if not func:
        return None, None
    try:
        src = inspect.getsource(func)
    except Exception:
        return None, None
    return extract_search_url_from_source(src, site.url)


def harvest_search_entry(site):
    """Run a site Main() with listings stubbed and capture the Search add_dir."""
    _install_patches()
    from resources.lib import utils as utils_mod
    orig_get = utils_mod.getHtml
    orig_get2 = getattr(utils_mod, 'getHtml2', None)

    def _empty_html(*_a, **_k):
        return ''

    utils_mod.getHtml = _empty_html
    if orig_get2 is not None:
        utils_mod.getHtml2 = _empty_html
    _tls.harvest = True
    _tls.dirs = []
    _tls.items = None
    _tls.collecting = False
    prev_to = socket.getdefaulttimeout()
    socket.setdefaulttimeout(4)
    try:
        _call_registered(site.default_mode, site.url, keyword=None)
    except Exception:
        pass
    finally:
        socket.setdefaulttimeout(prev_to)
        utils_mod.getHtml = orig_get
        if orig_get2 is not None:
            utils_mod.getHtml2 = orig_get2
        dirs = list(getattr(_tls, 'dirs', None) or [])
        _tls.harvest = False
        _tls.dirs = None
    for item in dirs:
        mode = item.get('mode') or ''
        if is_search_mode(mode) and 'user' not in mode.lower():
            return item
    return None


def _target_for_site(site):
    src_url, src_mode = _search_url_from_source(site)
    if src_url and url_looks_complete(src_url):
        for cand in (
            '{0}.{1}'.format(site.name, src_mode) if src_mode else None,
            '{0}.Search'.format(site.name),
            '{0}.XTSearch'.format(site.name),
            '{0}.PTSearch'.format(site.name),
        ):
            if not cand:
                continue
            func = URL_Dispatcher.func_registry.get(cand)
            if not func:
                continue
            spec = getargspec(func)
            if 'keyword' not in list(spec.args or []):
                continue
            return cand, src_url

    harvested = harvest_search_entry(site)
    if harvested and harvested.get('url') is not None:
        mode = harvested.get('mode')
        func = URL_Dispatcher.func_registry.get(mode)
        if func:
            spec = getargspec(func)
            if 'keyword' in list(spec.args or []):
                return mode, harvested.get('url') or site.url

    for cand in (
        '{0}.Search'.format(site.name),
        '{0}.XTSearch'.format(site.name),
        '{0}.PTSearch'.format(site.name),
    ):
        func = URL_Dispatcher.func_registry.get(cand)
        if not func:
            continue
        spec = getargspec(func)
        if 'keyword' not in list(spec.args or []):
            continue
        return cand, src_url or site.url
    return None, None


def iter_search_targets(include=None, exclude=None, webcams=False, max_sites=30):
    sites = sorted(AdultSite.get_sites(), key=lambda s: (s.get_clean_title() or s.name or '').lower())
    count = 0
    for site in sites:
        if not site.default_mode:
            continue
        if site.webcam and not webcams:
            continue
        if not site_allowed(site.name, include, exclude):
            continue
        try:
            mode, url = _target_for_site(site)
        except Exception as exc:
            _kodilog(u'target fail {0}: {1}'.format(site.name, exc))
            continue
        if not mode:
            continue
        yield site, mode, url
        count += 1
        if max_sites and count >= max_sites:
            break


def _search_one_site(site, mode, url, keyword, limit, timeout):
    _install_patches()
    _tls.collecting = True
    _tls.harvest = False
    _tls.items = []
    _tls.limit = limit
    prev_to = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    error = None
    try:
        _call_registered(mode, url, keyword=keyword)
    except Exception as exc:
        error = str(exc)
        _kodilog(u'{0} search error: {1}'.format(site.name, traceback.format_exc()), xbmc.LOGDEBUG)
    finally:
        socket.setdefaulttimeout(prev_to)
        items = list(_tls.items or [])
        _tls.items = None
        _tls.collecting = False
    site_title = site.get_clean_title() if site else site.name
    out = []
    for idx, raw in enumerate(items):
        item = dict(raw)
        enrich_item(item, keyword, site_title, idx)
        item['site_key'] = site.name
        item['name'] = decorate_title(site_title, item.get('name') or '')
        out.append(item)
    return site.name, out, error


def _persist_sort(sort_key):
    sort_key = normalize_sort(sort_key)
    try:
        basics.addon.setSetting('global_search_sort', SORT_INDEX.get(sort_key, '0'))
    except Exception:
        pass
    return sort_key


def resolved_sort(sort_param=None):
    if sort_param not in (None, ''):
        return _persist_sort(sort_param)
    stored = _setting('global_search_sort', '0')
    return normalize_sort(stored)


def prompt_keyword(heading='Search all sites'):
    keyboard = xbmc.Keyboard('', heading)
    keyboard.doModal()
    if not (keyboard.isConfirmed() and keyboard.getText()):
        return None
    text = keyboard.getText()
    if not text or not text.strip():
        return None
    return text.strip()


def _progress_dialog():
    try:
        return xbmcgui.DialogProgress()
    except Exception:
        return None


def run(keyword=None, sort=None, prompt=True):
    """Build one combined Kodi directory of search hits."""
    if not keyword_is_provided(keyword):
        if prompt:
            keyword = prompt_keyword()
            if not keyword:
                utils.eod(basics.addon_handle, False)
                return
        else:
            basics.addDir(
                '[COLOR white]Skin search — type a query in the search box[/COLOR]',
                '', 'main.INDEX', basics.cum_image('cum-search.png'), Folder=True, list_avail=False,
            )
            utils.eod(basics.addon_handle, False)
            return
    keyword = str(keyword).strip()
    sort_key = resolved_sort(sort)

    include = parse_csv_names(_setting('global_search_include', ''))
    exclude = parse_csv_names(_setting('global_search_exclude', ''))
    webcams = _setting_bool('global_search_webcams', False)
    timeout = max(5, _setting_int('global_search_timeout', 12))
    workers = max(1, min(12, _setting_int('global_search_concurrency', 6)))
    max_sites = max(1, _setting_int('global_search_max_sites', 30))
    per_site = max(1, _setting_int('global_search_max_per_site', 24))

    progress = _progress_dialog()
    if progress:
        progress.create('Search all sites', u'Searching for "{0}"'.format(keyword))

    targets = []
    try:
        for row in iter_search_targets(include, exclude, webcams, max_sites):
            targets.append(row)
            if progress and progress.iscanceled():
                progress.close()
                utils.eod(basics.addon_handle, False)
                return
            if progress:
                progress.update(
                    min(20, int(10.0 * len(targets) / max(max_sites, 1))),
                    u'Preparing {0}/{1} sites'.format(len(targets), max_sites),
                )
    except Exception as exc:
        _kodilog(u'target list failed: {0}'.format(exc), xbmc.LOGERROR)

    if not targets:
        utils.dialog.ok('Cumination (Andrew)', 'No site Search handlers are available for global search.')
        if progress:
            progress.close()
        utils.eod(basics.addon_handle, False)
        return

    results = []
    errors = 0
    done = 0
    total = len(targets)

    def _work(row):
        site, mode, url = row
        holder = {}

        def inner():
            holder['r'] = _search_one_site(site, mode, url, keyword, per_site, timeout)

        worker = threading.Thread(target=inner)
        worker.daemon = True
        worker.start()
        worker.join(timeout + 1)
        if worker.is_alive():
            return site.name, [], 'timeout'
        return holder.get('r') or (site.name, [], 'failed')

    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
    except ImportError:
        ThreadPoolExecutor = None

    if ThreadPoolExecutor and workers > 1:
        pool = ThreadPoolExecutor(max_workers=workers)
        try:
            futs = {pool.submit(_work, row): row for row in targets}
            for fut in as_completed(futs):
                done += 1
                if progress and progress.iscanceled():
                    break
                try:
                    _name, items, err = fut.result(timeout=timeout + 2)
                    results.extend(items)
                    if err:
                        errors += 1
                except Exception:
                    errors += 1
                if progress:
                    pct = 20 + int(75.0 * done / max(total, 1))
                    progress.update(min(95, pct), u'{0}/{1} sites · {2} videos'.format(
                        done, total, len(results)))
        finally:
            try:
                pool.shutdown(wait=False)
            except Exception:
                pass
    else:
        for row in targets:
            if progress and progress.iscanceled():
                break
            try:
                _name, items, err = _work(row)
                results.extend(items)
                if err:
                    errors += 1
            except Exception:
                errors += 1
            done += 1
            if progress:
                pct = 20 + int(75.0 * done / max(total, 1))
                progress.update(min(95, pct), u'{0}/{1} sites · {2} videos'.format(
                    done, total, len(results)))

    if progress:
        progress.close()

    results = sort_items(results, sort_key, keyword)
    _render_results(keyword, sort_key, results, total, errors)


def _plugin_root():
    return sys.argv[0] if sys.argv else 'plugin://plugin.video.cumination.andrew/'


def _current_mode():
    try:
        q = utils.parse_query(sys.argv[2] if len(sys.argv) > 2 else '')
        q = normalize_plugin_queries(q)
        return q.get('mode') or 'main.global_search'
    except Exception:
        return 'main.global_search'


def _runplugin(mode, **params):
    parts = ['mode=' + urllib_parse.quote_plus(str(mode))]
    for key, val in params.items():
        if val is None:
            continue
        parts.append('{0}={1}'.format(key, urllib_parse.quote_plus(six_text(val))))
    return 'RunPlugin({0}?{1})'.format(_plugin_root(), '&'.join(parts))


def six_text(val):
    if val is None:
        return ''
    try:
        import six
        return six.ensure_str(val)
    except Exception:
        return str(val)


def _render_results(keyword, sort_key, results, site_count, errors):
    sort_label = SORT_LABELS.get(sort_key, sort_key)
    status = u'[COLOR white]{0} videos from {1} sites[/COLOR]'.format(len(results), site_count)
    if errors:
        status += u' [COLOR orange]({0} sites skipped)[/COLOR]'.format(errors)
    basics.addDir(
        '[COLOR hotpink]Sort: {0}[/COLOR]'.format(sort_label),
        '', 'gsearch.change_sort', basics.cum_image('cum-search.png'),
        keyword=keyword, Folder=False, list_avail=False,
        contextm=('[COLOR hotpink]Change sort[/COLOR]',
                  _runplugin('gsearch.change_sort', keyword=keyword)),
    )
    basics.addDir(
        u'[COLOR hotpink]Save search "{0}" as keyword[/COLOR]'.format(keyword),
        '', 'gsearch.save_keyword', basics.cum_image('cum-search.png'),
        keyword=keyword, Folder=False, list_avail=False,
    )
    basics.addDir(status, '', 'gsearch.noop', basics.cum_image('cum-search.png'),
                  Folder=False, list_avail=False)

    save_query_cm = ('[COLOR hotpink]Save this search as keyword[/COLOR]',
                     _runplugin('gsearch.save_keyword', keyword=keyword))
    for item in results:
        title = item.get('name') or ''
        raw_title = clean_video_title(title)
        add_kw_cm = ('[COLOR hotpink]Add to keywords[/COLOR]',
                     _runplugin('gsearch.save_keyword',
                                keyword=keyword_from_result_title(raw_title) or keyword))
        basics.addDownLink(
            title,
            item.get('url') or '',
            item.get('mode'),
            item.get('iconimage'),
            desc=item.get('desc') or '',
            stream=item.get('stream'),
            contextm=[add_kw_cm, save_query_cm],
            fanart=item.get('fanart'),
            duration=item.get('duration') or '',
            quality=item.get('quality') or '',
        )
    utils.eod(basics.addon_handle, False)


@url_dispatcher.register()
def change_sort(keyword=None):
    options = ['Relevance', 'Newest', 'Most viewed', 'Top rated']
    keys = ['relevance', 'date', 'views', 'rating']
    choice = utils.dialog.select('Sort combined results', options)
    if choice < 0:
        return
    _persist_sort(keys[choice])
    mode = _current_mode()
    if mode not in ('main.global_search', 'main.skin_search', 'main.search'):
        mode = 'main.global_search'
    path = '{0}?mode={1}&keyword={2}'.format(
        _plugin_root(), mode, urllib_parse.quote_plus(keyword or ''))
    xbmc.executebuiltin('Container.Update({0},replace)'.format(path))


@url_dispatcher.register()
def save_keyword(keyword=None, name=None):
    kw = (keyword or name or '').strip()
    kw = strip_colors(kw)
    if not kw:
        utils.notify('Keywords', 'Nothing to save')
        return
    from resources.lib.utils import addKeyword, check_if_keyword_exists
    if check_if_keyword_exists(kw):
        utils.notify('Keywords', u'Already saved: {0}'.format(kw))
        return
    addKeyword(kw)
    utils.notify('Keywords', u'Added: {0}'.format(kw))


@url_dispatcher.register()
def noop():
    return
