# -*- coding: utf-8 -*-
"""Pure helpers for aggregated global search (no Kodi imports)."""
from __future__ import absolute_import

import re
import time

COLOR_RE = re.compile(r'\[/?COLOR[^\]]*\]', re.IGNORECASE)
BBCODE_RE = re.compile(r'\[/?[BI]\]', re.IGNORECASE)
SITE_PREFIX_RE = re.compile(r'^\[[^\]]+\]\s*')
TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)

SEARCH_FUNC_ALLOW = (
    'search', 'xtsearch', 'ptsearch', 'hanime_search', 'animeidhentai_search'
)
SEARCH_FUNC_DENY = (
    'globalsearch', 'search_user', 'searchresults', 'listsearch', 'search_user'
)

VIEWS_RE = re.compile(
    r'(?P<num>\d[\d.,]*)\s*(?P<suf>[kKmMbB])?\s*(?:views?|watched|plays?)',
    re.IGNORECASE,
)
VIEWS_ALT_RE = re.compile(
    r'(?:views?|watched|plays?)\s*[:\-]?\s*(?P<num>\d[\d.,]*)\s*(?P<suf>[kKmMbB])?',
    re.IGNORECASE,
)
RATING_PCT_RE = re.compile(r'(?P<num>\d{1,3}(?:\.\d+)?)\s*%')
RATING_STARS_RE = re.compile(
    r'(?P<num>\d(?:\.\d+)?)\s*(?:/\s*(?P<den>[0-9.]+)|stars?)',
    re.IGNORECASE,
)
RELATIVE_DATE_RE = re.compile(
    r'(?P<num>\d+)\s*(?P<unit>sec(?:ond)?s?|min(?:ute)?s?|hours?|days?|weeks?|months?|years?)\s*ago',
    re.IGNORECASE,
)
ISO_DATE_RE = re.compile(r'(?P<y>20\d{2})[-/](?P<m>\d{1,2})[-/](?P<d>\d{1,2})')
EU_DATE_RE = re.compile(r'(?P<d>\d{1,2})[./](?P<m>\d{1,2})[./](?P<y>20\d{2})')
MONTHS = {
    'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
    'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
    'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9, 'oct': 10,
    'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12,
}
NAMED_DATE_RE = re.compile(
    r'(?:(?P<mon>[A-Za-z]{3,9})\s+(?P<d>\d{1,2}),?\s+(?P<y>20\d{2})|(?P<d2>\d{1,2})\s+(?P<mon2>[A-Za-z]{3,9})\s+(?P<y2>20\d{2}))'
)

ADD_DIR_SEARCH_RE = re.compile(
    r"add_dir\s*\(\s*[^,]+,\s*(.+?),\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE | re.DOTALL,
)

SORT_KEYS = ('relevance', 'date', 'views', 'rating')
SORT_ALIASES = {
    'relevance': 'relevance',
    'rel': 'relevance',
    '0': 'relevance',
    'date': 'date',
    'newness': 'date',
    'newest': 'date',
    'new': 'date',
    '1': 'date',
    'views': 'views',
    'view': 'views',
    'most viewed': 'views',
    '2': 'views',
    'rating': 'rating',
    'rated': 'rating',
    'top rated': 'rating',
    '3': 'rating',
}

UNIT_SECONDS = {
    'sec': 1, 'second': 1, 'seconds': 1,
    'min': 60, 'minute': 60, 'minutes': 60,
    'hour': 3600, 'hours': 3600,
    'day': 86400, 'days': 86400,
    'week': 604800, 'weeks': 604800,
    'month': 2592000, 'months': 2592000,
    'year': 31536000, 'years': 31536000,
}


def strip_colors(text):
    if not text:
        return ''
    text = COLOR_RE.sub('', text)
    text = BBCODE_RE.sub('', text)
    return text.strip()


def clean_video_title(name):
    title = strip_colors(name)
    title = SITE_PREFIX_RE.sub('', title).strip()
    return title


def decorate_title(site_name, title):
    clean = strip_colors(title)
    site_name = strip_colors(site_name) or 'Site'
    return u'[{0}] {1}'.format(site_name, clean)


def keyword_from_result_title(name):
    title = clean_video_title(name)
    title = re.sub(r'\s+\d{1,2}:\d{2}(?::\d{2})?\s*$', '', title)
    return title.strip()


def parse_csv_names(text):
    if not text:
        return []
    parts = re.split(r'[,;\n]+', text)
    return [p.strip().lower() for p in parts if p.strip()]


def site_allowed(site_key, include=None, exclude=None):
    key = (site_key or '').lower()
    if include:
        return key in include
    if exclude and key in exclude:
        return False
    return True


def is_search_func_name(name):
    if not name:
        return False
    low = name.lower()
    if low in SEARCH_FUNC_DENY:
        return False
    if low in SEARCH_FUNC_ALLOW:
        return True
    if low.endswith('_search') and 'user' not in low:
        return True
    return False


def is_search_mode(mode):
    if not mode:
        return False
    return is_search_func_name(str(mode).split('.')[-1])


def normalize_sort(value, default='relevance'):
    if value is None or value == '':
        return default
    key = str(value).strip().lower()
    return SORT_ALIASES.get(key, default if default in SORT_KEYS else 'relevance')


def _to_float(num_str):
    try:
        return float(num_str.replace(',', ''))
    except Exception:
        return None


def _apply_suffix(value, suf):
    if not suf:
        return value
    s = suf.lower()
    if s == 'k':
        return value * 1000.0
    if s == 'm':
        return value * 1000000.0
    if s == 'b':
        return value * 1000000000.0
    return value


def parse_views(text):
    if not text:
        return None
    for rx in (VIEWS_RE, VIEWS_ALT_RE):
        m = rx.search(text)
        if m:
            num = _to_float(m.group('num'))
            if num is None:
                continue
            return _apply_suffix(num, m.group('suf'))
    return None


def parse_rating(text):
    if not text:
        return None
    m = RATING_PCT_RE.search(text)
    if m:
        val = _to_float(m.group('num'))
        if val is not None and 0 <= val <= 100:
            return val
    m = RATING_STARS_RE.search(text)
    if m:
        num = _to_float(m.group('num'))
        den = _to_float(m.group('den')) if m.groupdict().get('den') else None
        if num is None:
            return None
        if den and den > 0:
            return (num / den) * 100.0
        if num <= 5:
            return (num / 5.0) * 100.0
        if num <= 10:
            return (num / 10.0) * 100.0
        return num
    return None


def _safe_mktime(y, m, d):
    try:
        return time.mktime((int(y), int(m), int(d), 12, 0, 0, 0, 0, -1))
    except Exception:
        return None


def parse_date(text, now=None):
    """Return a unix timestamp (newer = larger) or None."""
    if not text:
        return None
    now = now if now is not None else time.time()
    low = text.lower()
    if 'yesterday' in low:
        return now - 86400
    if re.search(r'\btoday\b', low):
        return now - 3600
    m = RELATIVE_DATE_RE.search(text)
    if m:
        num = int(m.group('num'))
        unit = m.group('unit').lower()
        secs = UNIT_SECONDS.get(unit)
        if not secs and unit.endswith('s'):
            secs = UNIT_SECONDS.get(unit[:-1])
        if secs:
            return now - (num * secs)
    m = ISO_DATE_RE.search(text)
    if m:
        return _safe_mktime(m.group('y'), m.group('m'), m.group('d'))
    m = EU_DATE_RE.search(text)
    if m:
        return _safe_mktime(m.group('y'), m.group('m'), m.group('d'))
    m = NAMED_DATE_RE.search(text)
    if m:
        mon = (m.group('mon') or m.group('mon2') or '').lower()
        month = MONTHS.get(mon)
        day = m.group('d') or m.group('d2')
        year = m.group('y') or m.group('y2')
        if month and day and year:
            return _safe_mktime(year, month, day)
    return None


def relevance_score(title, keyword):
    """Higher is better. Exact title match beats token overlap."""
    title = strip_colors(title or '').lower()
    keyword = strip_colors(keyword or '').lower().strip()
    if not keyword:
        return 0.0
    if title == keyword:
        return 1000.0
    if keyword in title:
        # earlier occurrence scores higher
        pos = title.find(keyword)
        return 500.0 - min(pos, 400) + min(len(keyword), 80)
    k_tokens = TOKEN_RE.findall(keyword)
    t_tokens = set(TOKEN_RE.findall(title))
    if not k_tokens:
        return 0.0
    hits = sum(1 for tok in k_tokens if tok in t_tokens)
    return (float(hits) / float(len(k_tokens))) * 100.0


def enrich_item(item, keyword, site_name, position):
    name = item.get('name') or ''
    desc = item.get('desc') or ''
    blob = u' '.join([strip_colors(name), strip_colors(desc),
                      str(item.get('duration') or ''), str(item.get('quality') or '')])
    item['site_name'] = site_name
    item['position'] = position
    item['views'] = parse_views(blob)
    item['rating'] = parse_rating(blob)
    item['date'] = parse_date(blob)
    item['relevance'] = relevance_score(clean_video_title(name), keyword)
    return item


def sort_items(items, sort_key, keyword=None):
    key = normalize_sort(sort_key)
    keyword = keyword or ''

    def tup(item):
        pos = item.get('position', 0)
        if key == 'relevance':
            score = item.get('relevance')
            if score is None:
                score = relevance_score(clean_video_title(item.get('name')), keyword)
            return (0, -float(score), pos)
        field = {'date': 'date', 'views': 'views', 'rating': 'rating'}.get(key)
        val = item.get(field) if field else None
        if val is None:
            return (1, 0, pos)
        return (0, -float(val), pos)

    return sorted(list(items), key=tup)


def url_looks_complete(url):
    if not url:
        return False
    if re.search(r'\{[a-zA-Z_][a-zA-Z0-9_]*\}', url):
        return False
    return True


def eval_url_expr(expr, site_url):
    """Best-effort evaluation of a site.add_dir URL expression."""
    if expr is None:
        return site_url
    expr = expr.strip().rstrip(',')
    expr = re.sub(r'\bsite\d*\.url\b', repr(site_url), expr)
    try:
        value = eval(expr, {'__builtins__': {}}, {})  # nosec - addon source only
        if isinstance(value, (bytes, bytearray)):
            value = value.decode('utf-8', 'ignore')
        if isinstance(value, str) and value:
            return value
    except Exception:
        if '.format(' in expr:
            return None
        pass
    literals = re.findall(r"'([^']*)'|\"([^\"]*)\"", expr)
    suffix = ''.join(a or b for a, b in literals)
    if suffix:
        if suffix.startswith('?') or suffix.startswith('&'):
            return (site_url or '') + suffix
        if suffix.startswith('http'):
            return suffix
        base = site_url or ''
        if '{}' in suffix or '{0}' in suffix:
            return base + suffix
        return base + suffix
    return site_url


def extract_search_url_from_source(src, site_url):
    """Return (url, mode_name) from a site Main() source snippet."""
    if not src:
        return None, None
    for expr, mode in ADD_DIR_SEARCH_RE.findall(src):
        mode_name = (mode or '').split('.')[-1]
        if not is_search_func_name(mode_name):
            continue
        if 'user' in mode_name.lower():
            continue
        url = eval_url_expr(expr, site_url)
        if url:
            return url, mode_name
    return None, None


def plugin_mode_aliases():
    return {
        'global_search': 'main.global_search',
        'main.global_search': 'main.global_search',
        'skin_search': 'main.skin_search',
        'main.skin_search': 'main.skin_search',
        'search': 'main.search',
        'main.search': 'main.search',
    }


def normalize_plugin_queries(queries):
    """Map skin-friendly query args onto registered dispatcher modes."""
    q = dict(queries or {})
    if not q.get('keyword'):
        for alt in ('query', 'q'):
            val = q.get(alt)
            if val:
                q['keyword'] = val
                break
    mode = q.get('mode')
    aliases = plugin_mode_aliases()
    if mode in aliases:
        q['mode'] = aliases[mode]
    return q


def keyword_is_provided(keyword):
    if keyword is None:
        return False
    return bool(str(keyword).strip())
