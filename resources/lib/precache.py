# -*- coding: utf-8 -*-
"""Image/list precache runner (never downloads videos)."""
from __future__ import absolute_import

import os
import threading
import time

from kodi_six import xbmc, xbmcgui

from resources.lib import andrew_art
from resources.lib import basics
from resources.lib import precache_lib
from resources.lib import siteflags
from resources.lib import utils
from resources.lib.adultsite import AdultSite
from resources.lib.url_dispatcher import URL_Dispatcher

url_dispatcher = URL_Dispatcher('precache')

_SITES_LOADED = False
_BG = {'dialog': None}


def job_path():
    return os.path.join(basics.profileDir, 'precache.json')


def stop_path():
    return os.path.join(basics.profileDir, 'precache.stop')


def art_settings():
    return {
        'cache_dir': basics._art_cache_dir(),
        'framed_dir': '',
        'images_dir': basics.imgDir,
        'allow_remote_fetch': False,
        'remote_timeout': 12,
    }


def refresh_status_setting(job=None):
    if job is None:
        job = precache_lib.load_job(job_path())
    text = precache_lib.format_status(job)
    try:
        basics.addon.setSetting('precache_status', text)
    except Exception:
        pass
    return text


def _notify(msg, ms=3500):
    try:
        xbmcgui.Dialog().notification('Cumination precache', msg, basics.cuminationicon, ms, False)
    except Exception:
        try:
            utils.notify('Cumination precache', msg)
        except Exception:
            pass


def _setting_int(key, default):
    try:
        return int(basics.addon.getSetting(key) or default)
    except Exception:
        return default


def request_stop():
    path = stop_path()
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, 'w') as fh:
        fh.write('1')


def stop_requested():
    return os.path.isfile(stop_path())


def clear_stop():
    path = stop_path()
    if os.path.isfile(path):
        try:
            os.remove(path)
        except Exception:
            pass


def ensure_sites_loaded():
    global _SITES_LOADED
    if _SITES_LOADED:
        return
    try:
        from resources.lib.sites import *  # noqa: F401,F403
    except Exception as exc:
        utils.kodilog('precache: site import {0}'.format(exc))
    try:
        if basics.addon.getSetting('custom_sites') == 'true':
            import importlib
            import sys
            from resources.lib import favorites
            sys.path.append(basics.customSitesDir)
            for module_name in favorites.enabled_custom_sites():
                try:
                    importlib.import_module(module_name)
                except Exception:
                    pass
    except Exception:
        pass
    _SITES_LOADED = True


def _site_jobs_from_selection():
    ensure_sites_loaded()
    jobs = []
    for site in sorted(AdultSite.get_all_sites(),
                       key=lambda s: (s.get_clean_title() or s.name or '').lower()):
        if not siteflags.is_precache_site(site.name):
            continue
        if not site.default_mode:
            continue
        jobs.append({
            'site': site.name,
            'mode': site.default_mode,
            'url': site.url,
            'depth': 1,
            'name': site.get_clean_title() or site.name,
        })
    return jobs


def _session():
    try:
        import requests
        from requests.adapters import HTTPAdapter
        sess = requests.Session()
        adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8, max_retries=0)
        sess.mount('http://', adapter)
        sess.mount('https://', adapter)
        sess.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
            'Connection': 'keep-alive',
        })
        return sess
    except Exception:
        return None


def _download_one(session, url, dest, timeout=12):
    """Fetch one image. Returns bytes written, 0 if already cached, None on skip/error."""
    if precache_lib.looks_like_video_url(url):
        return None
    if dest and os.path.isfile(dest) and os.path.getsize(dest) > 32:
        return 0
    andrew_art._ensure_dir(os.path.dirname(dest))
    delays = precache_lib.backoff_delays(3, 0.35)
    last_err = None
    for delay in delays:
        if stop_requested():
            return None
        try:
            if session is not None:
                resp = session.get(url, timeout=timeout, stream=True)
                status = getattr(resp, 'status_code', 0)
                if status in (429, 500, 502, 503, 504):
                    time.sleep(delay)
                    continue
                if status != 200:
                    last_err = 'http {0}'.format(status)
                    time.sleep(delay)
                    continue
                ctype = (resp.headers.get('content-type') or '').lower()
                if ctype.startswith('video') or 'mpegurl' in ctype or 'application/vnd.apple' in ctype:
                    return None
                clen = resp.headers.get('content-length')
                if clen and int(clen) > precache_lib.MAX_IMAGE_BYTES:
                    return None
                chunks = []
                total = 0
                for chunk in resp.iter_content(64 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > precache_lib.MAX_IMAGE_BYTES:
                        return None
                    chunks.append(chunk)
                data = b''.join(chunks)
            else:
                from six.moves import urllib_request
                req = urllib_request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                resp = urllib_request.urlopen(req, timeout=timeout)
                ctype = ''
                try:
                    ctype = (resp.info().get('Content-Type') or '').lower()
                except Exception:
                    pass
                if ctype.startswith('video') or 'mpegurl' in ctype:
                    return None
                data = resp.read(precache_lib.MAX_IMAGE_BYTES + 1)
                if data and len(data) > precache_lib.MAX_IMAGE_BYTES:
                    return None
            if not data:
                last_err = 'empty'
                time.sleep(delay)
                continue
            tmp = dest + '.part'
            with open(tmp, 'wb') as fh:
                fh.write(data)
            try:
                os.replace(tmp, dest)
            except Exception:
                if os.path.exists(dest):
                    os.remove(dest)
                os.rename(tmp, dest)
            return len(data)
        except Exception as exc:
            last_err = str(exc)
            time.sleep(delay)
    if last_err:
        utils.kodilog(u'precache image fail {0}: {1}'.format(url[:120], last_err), xbmc.LOGDEBUG)
    return None


def _cache_images(urls, job, session):
    settings = art_settings()
    pending = []
    seen = set()
    for url in urls:
        if precache_lib.looks_like_video_url(url):
            job['stats']['skipped_video'] = int(job['stats'].get('skipped_video') or 0) + 1
            continue
        dest = andrew_art.src_cache_path_for_url(url, settings)
        if not dest or url in seen:
            continue
        seen.add(url)
        pending.append((url, dest))

    workers = precache_lib.clamp_concurrency(job.get('concurrency'))
    lock = threading.Lock()

    def work(pair):
        url, dest = pair
        if stop_requested():
            return
        reason = precache_lib.cap_reached(job.get('stats'), job.get('max_items'), job.get('max_bytes'))
        if reason:
            return
        written = _download_one(session, url, dest)
        with lock:
            if written is None:
                job['stats']['errors'] = int(job['stats'].get('errors') or 0) + 1
            elif written == 0:
                pass
            else:
                job['stats']['images'] = int(job['stats'].get('images') or 0) + 1
                job['stats']['bytes'] = int(job['stats'].get('bytes') or 0) + written

    if workers <= 1 or len(pending) <= 1:
        for pair in pending:
            if stop_requested():
                break
            work(pair)
        return

    threads = []
    idx = [0]

    def worker():
        while True:
            with lock:
                if idx[0] >= len(pending) or stop_requested():
                    return
                pair = pending[idx[0]]
                idx[0] += 1
            work(pair)

    for _ in range(min(workers, len(pending))):
        t = threading.Thread(target=worker)
        t.daemon = True
        t.start()
        threads.append(t)
    for t in threads:
        t.join()


def _enqueue_children(job, item, dirs):
    depth = int(item.get('depth') or 1)
    max_depth = precache_lib.clamp_depth(job.get('depth'))
    site_name = item.get('site') or ''
    for entry in dirs:
        mode = entry.get('mode') or ''
        if site_name and mode.split('.')[0] not in (site_name,):
            # still follow same-module listings (txxx family shares handlers)
            pass
        if not precache_lib.should_follow_dir(
            mode, entry.get('name') or '', depth, max_depth,
            folder=entry.get('Folder', True),
        ):
            continue
        child = {
            'site': site_name or entry.get('site') or mode.split('.')[0],
            'mode': mode,
            'url': entry.get('url') or '',
            'depth': depth + 1,
            'name': entry.get('name') or '',
            'page': entry.get('page'),
            'channel': entry.get('channel'),
            'section': entry.get('section'),
            'keyword': entry.get('keyword') or '',
        }
        precache_lib.enqueue_child(job, child)


def process_one(job, session=None):
    """Process a single queued listing. Returns False when nothing left / stopped."""
    if stop_requested():
        job['status'] = 'cancelled'
        job['stop_reason'] = 'user'
        job['finished'] = time.time()
        job['message'] = 'Stopped'
        return False
    reason = precache_lib.cap_reached(job.get('stats'), job.get('max_items'), job.get('max_bytes'))
    if reason:
        job['status'] = 'complete'
        job['stop_reason'] = reason
        job['finished'] = time.time()
        job['message'] = 'Reached {0}'.format(reason)
        return False
    item = precache_lib.pop_next(job)
    if not item:
        job['status'] = 'complete'
        job['finished'] = time.time()
        job['message'] = 'Done'
        return False
    key = precache_lib.visit_key(item.get('site'), item.get('mode'), item.get('url'), item.get('page'))
    if key in set(job.get('visited') or []):
        precache_lib.maybe_complete_site(job, item.get('site'))
        return True
    if precache_lib.listing_kind(item.get('mode'), item.get('name')) == 'skip':
        precache_lib.mark_visited(job, item)
        precache_lib.maybe_complete_site(job, item.get('site'))
        return True

    job['current'] = item.get('site') or item.get('mode') or ''
    job['message'] = 'Listing {0}'.format(job['current'])
    from resources.lib import gsearch
    dirs, items, error = gsearch.harvest_listing(
        item.get('mode'), item.get('url') or '', extra=item, timeout=18,
    )
    job['stats']['pages'] = int(job['stats'].get('pages') or 0) + 1
    if error:
        job['stats']['errors'] = int(job['stats'].get('errors') or 0) + 1
        utils.kodilog(u'precache page {0}: {1}'.format(item.get('mode'), error), xbmc.LOGDEBUG)

    urls = []
    for entry in list(dirs) + list(items):
        urls.extend(precache_lib.image_urls_from_entry(entry))
    _cache_images(urls, job, session)

    precache_lib.mark_visited(job, item)
    _enqueue_children(job, item, dirs)
    precache_lib.maybe_complete_site(job, item.get('site'))
    job['stats']['sites_done'] = len(job.get('done_sites') or [])
    job['stats']['sites_total'] = max(int(job['stats'].get('sites_total') or 0), len(job.get('sites') or []))
    return True


def _close_bg():
    dlg = _BG.get('dialog')
    if dlg is not None:
        try:
            dlg.close()
        except Exception:
            pass
        _BG['dialog'] = None


def _update_bg(job):
    stats = job.get('stats') or {}
    total = max(1, int(stats.get('sites_total') or 1))
    done = int(stats.get('sites_done') or 0)
    pct = min(99, int(100.0 * done / total)) if job.get('status') == 'running' else 100
    msg = precache_lib.format_status(job)
    dlg = _BG.get('dialog')
    if dlg is None:
        try:
            dlg = xbmcgui.DialogProgressBG()
            dlg.create('Cumination precache', msg)
            _BG['dialog'] = dlg
        except Exception:
            return
    try:
        dlg.update(pct, 'Cumination precache', msg)
    except Exception:
        pass


def start_job():
    ensure_sites_loaded()
    clear_stop()
    site_jobs = _site_jobs_from_selection()
    if not site_jobs:
        _notify('No sites selected for precache')
        return None
    depth = precache_lib.clamp_depth(_setting_int('precache_depth', 2))
    max_items = precache_lib.parse_limit(_setting_int('precache_max_items', 2500))
    max_mb = precache_lib.parse_limit(_setting_int('precache_max_mb', 400))
    concurrency = precache_lib.clamp_concurrency(_setting_int('precache_concurrency', 4))
    job = precache_lib.new_job(
        site_jobs,
        depth=depth,
        max_items=max_items,
        max_bytes=precache_lib.mb_to_bytes(max_mb),
        concurrency=concurrency,
    )
    job['message'] = precache_lib.expected_disk_note(max_items, max_mb, depth, len(site_jobs))
    job['stats']['sites_total'] = len(site_jobs)
    precache_lib.save_job(job_path(), job)
    refresh_status_setting(job)
    _notify('Started ({0}). Safe to leave settings.'.format(job['message']))
    return job


def service_tick(monitor=None, budget_sec=2.0):
    """Continue a persisted job. Called from the addon service."""
    path = job_path()
    job = precache_lib.load_job(path)
    if not job or job.get('status') != 'running':
        _close_bg()
        return False
    if stop_requested():
        job['status'] = 'cancelled'
        job['stop_reason'] = 'user'
        job['finished'] = time.time()
        job['message'] = 'Stopped'
        precache_lib.save_job(path, job)
        refresh_status_setting(job)
        _notify('Stopped')
        clear_stop()
        _close_bg()
        return False

    ensure_sites_loaded()
    session = _session()
    deadline = time.time() + max(0.4, float(budget_sec))
    progressed = False
    try:
        while time.time() < deadline:
            if monitor is not None:
                try:
                    if monitor.abortRequested():
                        precache_lib.save_job(path, job)
                        refresh_status_setting(job)
                        return True
                except Exception:
                    pass
            latest = precache_lib.load_job(path)
            if latest and latest.get('status') != 'running':
                _close_bg()
                return False
            if stop_requested():
                job['status'] = 'cancelled'
                job['stop_reason'] = 'user'
                job['finished'] = time.time()
                break
            keep = process_one(job, session=session)
            progressed = True
            precache_lib.save_job(path, job)
            refresh_status_setting(job)
            _update_bg(job)
            if not keep:
                break
    finally:
        try:
            if session is not None:
                session.close()
        except Exception:
            pass

    if job.get('status') != 'running':
        refresh_status_setting(job)
        _notify(precache_lib.format_status(job), ms=5000)
        _close_bg()
        clear_stop()
    return progressed


@url_dispatcher.register()
def start():
    start_job()


@url_dispatcher.register()
def stop():
    request_stop()
    job = precache_lib.load_job(job_path())
    if job and job.get('status') == 'running':
        job['status'] = 'cancelled'
        job['stop_reason'] = 'user'
        job['finished'] = time.time()
        job['message'] = 'Stopped'
        precache_lib.save_job(job_path(), job)
        refresh_status_setting(job)
    _notify('Stop requested')


@url_dispatcher.register()
def choose_sites():
    ensure_sites_loaded()
    sites = siteflags.catalog()
    if not sites:
        _notify('No sites are loaded yet')
        return
    state = siteflags.get_state()
    if state.get('precache_sites') is None:
        current = [s.name for s in sites if siteflags.is_enabled(s.name)]
    else:
        current = list(state.get('precache_sites') or [])
    choice = siteflags._multiselect('Precache these sites (images/lists only)', sites, current)
    if choice is None:
        return
    selected = [sites[i].name for i in choice if 0 <= i < len(sites)]
    state['precache_sites'] = [n.lower() for n in selected]
    siteflags.save_state(state)
    _notify('{0} site(s) selected for precache'.format(len(selected)))


@url_dispatcher.register()
def sync_enabled():
    state = siteflags.get_state()
    state['precache_sites'] = None
    siteflags.save_state(state)
    names = [n for n in siteflags.catalog_names() if siteflags.is_enabled(n)]
    _notify('Precache list follows {0} enabled site(s)'.format(len(names)))
