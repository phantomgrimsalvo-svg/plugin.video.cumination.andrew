# -*- coding: utf-8 -*-
"""Pure helpers for image/list precache (no Kodi, never downloads videos)."""
from __future__ import absolute_import

import json
import os
import re
import time

from resources.lib.gsearch_lib import is_search_mode, strip_colors

STATE_VERSION = 1
MIN_DEPTH = 1
MAX_DEPTH = 4
DEFAULT_DEPTH = 2
DEFAULT_MAX_ITEMS = 2500
DEFAULT_MAX_MB = 400
DEFAULT_CONCURRENCY = 4
MAX_IMAGE_BYTES = int(2.5 * 1024 * 1024)
MAX_QUEUE = 8000

VIDEO_EXT = (
    '.mp4', '.m3u8', '.mkv', '.avi', '.ts', '.wmv', '.flv', '.mov', '.webm',
    '.mpg', '.mpeg', '.mpd', '.ism',
)
IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')

SKIP_FUNC_EXACT = {
    'setpin', 'login', 'logout', 'resetfilters', 'noop', 'smrsettings',
    'opendownloadfolder', 'about_site',
}
SKIP_FUNC_PREFIX = ('context', 'play', 'download')
SKIP_FUNC_SUBSTR = ('playvid', 'playvideo', 'playstream')
NEXT_PAGE_RE = re.compile(r'\bnext(\s+page)?\b', re.IGNORECASE)
HTTP_RE = re.compile(r'^https?://', re.IGNORECASE)

JOB_STATUS = ('idle', 'running', 'cancelled', 'complete', 'error')


def clamp_depth(value, minimum=MIN_DEPTH, maximum=MAX_DEPTH, default=DEFAULT_DEPTH):
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = default
    return max(minimum, min(maximum, n))


def parse_limit(value, default=0):
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = default
    return max(0, n)


def mb_to_bytes(max_mb):
    n = parse_limit(max_mb, 0)
    if n <= 0:
        return 0
    return int(n) * 1024 * 1024


def clamp_concurrency(value, default=DEFAULT_CONCURRENCY):
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = default
    return max(1, min(8, n))


def _clean_url(url):
    path = url or ''
    if '|' in path:
        path = path.split('|', 1)[0]
    return path.strip()


def looks_like_video_url(url):
    clean = _clean_url(url).split('#', 1)[0]
    low = clean.lower()
    if not low:
        return False
    path = low.split('?', 1)[0]
    if any(path.endswith(ext) for ext in VIDEO_EXT):
        return True
    if 'm3u8' in low or '/hls/' in low or 'mime_type=video' in low:
        return True
    if '/videoplayback' in low and 'itag=' in low:
        return True
    return False


def looks_like_image_url(url):
    clean = _clean_url(url)
    if not HTTP_RE.match(clean):
        return False
    if looks_like_video_url(clean):
        return False
    return True


def image_urls_from_entry(entry):
    urls = []
    seen = set()
    if not isinstance(entry, dict):
        return urls
    for key in ('iconimage', 'fanart', 'image', 'poster'):
        val = entry.get(key)
        if not looks_like_image_url(val):
            continue
        clean = _clean_url(val)
        if clean in seen:
            continue
        seen.add(clean)
        urls.append(clean)
    return urls


def mode_func(mode):
    if not mode:
        return ''
    return str(mode).split('.')[-1].lower()


def listing_kind(mode, name=''):
    """follow | next | skip — never follow playback or search."""
    func = mode_func(mode)
    label = strip_colors(name or '').lower()
    if not func:
        return 'skip'
    if func in SKIP_FUNC_EXACT:
        return 'skip'
    if any(func.startswith(p) for p in SKIP_FUNC_PREFIX):
        return 'skip'
    if any(s in func for s in SKIP_FUNC_SUBSTR):
        return 'skip'
    if is_search_mode(mode):
        return 'skip'
    if NEXT_PAGE_RE.search(label):
        return 'next'
    return 'follow'


def should_follow_dir(mode, name, depth, max_depth, folder=True):
    if not folder:
        return False
    if depth >= clamp_depth(max_depth):
        return False
    return listing_kind(mode, name) == 'follow'


def visit_key(site, mode, url, page=None):
    page_s = '' if page in (None, '', 'None', 'none') else str(page)
    return u'{0}|{1}|{2}|{3}'.format(site or '', mode or '', _clean_url(url), page_s)


def default_stats():
    return {
        'sites_done': 0,
        'sites_total': 0,
        'pages': 0,
        'images': 0,
        'bytes': 0,
        'errors': 0,
        'skipped_video': 0,
    }


def new_job(site_jobs, depth=DEFAULT_DEPTH, max_items=DEFAULT_MAX_ITEMS,
            max_bytes=0, concurrency=DEFAULT_CONCURRENCY):
    queue = []
    for item in site_jobs or []:
        job = dict(item)
        job.setdefault('depth', 1)
        job.setdefault('page', None)
        job.setdefault('channel', None)
        job.setdefault('section', None)
        job.setdefault('keyword', '')
        job.setdefault('name', '')
        queue.append(job)
    sites = []
    seen = set()
    for item in queue:
        name = (item.get('site') or '').strip()
        if name and name not in seen:
            seen.add(name)
            sites.append(name)
    return {
        'version': STATE_VERSION,
        'status': 'running',
        'started': time.time(),
        'finished': None,
        'depth': clamp_depth(depth),
        'max_items': parse_limit(max_items, DEFAULT_MAX_ITEMS),
        'max_bytes': parse_limit(max_bytes, 0),
        'concurrency': clamp_concurrency(concurrency),
        'queue': queue,
        'visited': [],
        'stats': default_stats(),
        'sites': sites,
        'done_sites': [],
        'current': '',
        'stop_reason': '',
        'message': 'Starting',
    }


def normalize_job(data):
    if not isinstance(data, dict):
        return None
    job = new_job([], depth=data.get('depth'), max_items=data.get('max_items'),
                  max_bytes=data.get('max_bytes'), concurrency=data.get('concurrency'))
    job['status'] = data.get('status') or 'idle'
    if job['status'] not in JOB_STATUS:
        job['status'] = 'idle'
    job['started'] = data.get('started')
    job['finished'] = data.get('finished')
    job['queue'] = list(data.get('queue') or [])
    job['visited'] = list(data.get('visited') or [])
    stats = default_stats()
    stats.update(data.get('stats') or {})
    job['stats'] = stats
    job['sites'] = list(data.get('sites') or [])
    job['done_sites'] = list(data.get('done_sites') or [])
    job['current'] = data.get('current') or ''
    job['stop_reason'] = data.get('stop_reason') or ''
    job['message'] = data.get('message') or ''
    job['stats']['sites_total'] = job['stats'].get('sites_total') or len(job['sites'])
    return job


def load_job(path):
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, 'r') as fh:
            data = json.load(fh)
    except Exception:
        return None
    return normalize_job(data)


def save_job(path, job):
    if not path or not job:
        return False
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    tmp = path + '.tmp'
    payload = normalize_job(job) or job
    with open(tmp, 'w') as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except Exception:
            pass
    try:
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        os.rename(tmp, path)
    return True


def cap_reached(stats, max_items, max_bytes):
    stats = stats or {}
    if max_items and int(stats.get('images') or 0) >= int(max_items):
        return 'max_items'
    if max_bytes and int(stats.get('bytes') or 0) >= int(max_bytes):
        return 'max_bytes'
    return None


def enqueue_child(job, child):
    if not job or not child:
        return False
    queue = job.setdefault('queue', [])
    if len(queue) >= MAX_QUEUE:
        return False
    visited = set(job.get('visited') or [])
    key = visit_key(child.get('site'), child.get('mode'), child.get('url'), child.get('page'))
    if key in visited:
        return False
    for existing in queue:
        if visit_key(existing.get('site'), existing.get('mode'),
                     existing.get('url'), existing.get('page')) == key:
            return False
    queue.append(child)
    return True


def pop_next(job):
    queue = job.get('queue') or []
    if not queue:
        return None
    item = queue.pop(0)
    job['queue'] = queue
    return item


def mark_visited(job, item):
    key = visit_key(item.get('site'), item.get('mode'), item.get('url'), item.get('page'))
    visited = job.setdefault('visited', [])
    if key not in visited:
        visited.append(key)
    return key


def maybe_complete_site(job, site_name):
    if not site_name:
        return
    remaining = [q for q in (job.get('queue') or []) if q.get('site') == site_name]
    if remaining:
        return
    done = job.setdefault('done_sites', [])
    if site_name not in done:
        done.append(site_name)
        job.setdefault('stats', default_stats())
        job['stats']['sites_done'] = len(done)


def format_bytes(n):
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        n = 0
    if n < 1024:
        return '{0} B'.format(n)
    if n < 1024 * 1024:
        return '{0:.1f} KB'.format(n / 1024.0)
    return '{0:.1f} MB'.format(n / (1024.0 * 1024.0))


def format_status(job):
    if not job:
        return 'Never run'
    status = job.get('status') or 'idle'
    stats = job.get('stats') or {}
    images = int(stats.get('images') or 0)
    pages = int(stats.get('pages') or 0)
    errors = int(stats.get('errors') or 0)
    size = format_bytes(stats.get('bytes') or 0)
    sites_done = int(stats.get('sites_done') or len(job.get('done_sites') or []))
    sites_total = int(stats.get('sites_total') or len(job.get('sites') or []) or 0)
    current = job.get('current') or ''
    if status == 'running':
        msg = 'In progress: {0}/{1} sites, {2} images, {3}'.format(
            sites_done, sites_total, images, size)
        if current:
            msg += ' ({0})'.format(current)
        return msg
    if status == 'cancelled':
        return 'Stopped: {0} images · {1} · {2} errors'.format(images, size, errors)
    if status == 'error':
        return 'Error: {0}'.format(job.get('message') or job.get('stop_reason') or 'failed')
    if status == 'complete':
        when = _format_when(job.get('finished') or job.get('started'))
        return 'Last precache: {0} · {1} images · {2} pages · {3} · {4} errors'.format(
            when, images, pages, size, errors)
    if job.get('finished') or images:
        when = _format_when(job.get('finished') or job.get('started'))
        return 'Last precache: {0} · {1} images · {2}'.format(when, images, size)
    return 'Never run'


def _format_when(ts):
    try:
        return time.strftime('%Y-%m-%d %H:%M', time.localtime(float(ts)))
    except Exception:
        return 'unknown'


def backoff_delays(attempts=3, initial=0.4):
    delay = float(initial)
    out = []
    for _ in range(max(1, int(attempts))):
        out.append(delay)
        delay *= 2.0
    return out


def expected_disk_note(max_items, max_mb, depth, site_count):
    items = parse_limit(max_items, DEFAULT_MAX_ITEMS)
    mb = parse_limit(max_mb, DEFAULT_MAX_MB)
    bits = [
        '{0} site(s)'.format(site_count),
        'depth {0}/{1}'.format(clamp_depth(depth), MAX_DEPTH),
    ]
    if items:
        bits.append('cap {0} images'.format(items))
    else:
        bits.append('no image cap')
    if mb:
        bits.append('cap {0} MB'.format(mb))
    else:
        bits.append('no size cap')
    bits.append('thumbs/fanart/logos only — never videos')
    return ', '.join(bits)
