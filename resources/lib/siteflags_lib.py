# -*- coding: utf-8 -*-
"""Site enable/disable and precache-site allowlists (no Kodi)."""
from __future__ import absolute_import

import json
import os

STATE_VERSION = 1


def default_state():
    return {
        'version': STATE_VERSION,
        'disabled': [],
        'precache_sites': None,  # None = follow currently enabled sites
    }


def _lower_unique(names):
    seen = set()
    out = []
    for name in names or []:
        key = (name or '').strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def normalize_state(data):
    state = default_state()
    if not isinstance(data, dict):
        return state
    try:
        state['version'] = int(data.get('version') or STATE_VERSION)
    except (TypeError, ValueError):
        state['version'] = STATE_VERSION
    state['disabled'] = _lower_unique(data.get('disabled') or [])
    precache = data.get('precache_sites', None)
    if precache is None:
        state['precache_sites'] = None
    else:
        state['precache_sites'] = _lower_unique(precache)
    return state


def load_state(path):
    if not path or not os.path.isfile(path):
        return default_state()
    try:
        with open(path, 'r') as fh:
            data = json.load(fh)
    except Exception:
        return default_state()
    return normalize_state(data)


def save_state(path, state):
    if not path:
        return False
    payload = normalize_state(state)
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    tmp = path + '.tmp'
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


def is_site_enabled(name, state=None):
    key = (name or '').strip().lower()
    if not key:
        return False
    state = normalize_state(state or {})
    return key not in set(state.get('disabled') or [])


def filter_enabled_names(names, state=None):
    state = normalize_state(state or {})
    return [n for n in (names or []) if is_site_enabled(n, state)]


def disabled_from_selection(all_names, selected_names):
    """Persist a disabled list so newly added sites stay ON by default."""
    selected = set(_lower_unique(selected_names))
    disabled = []
    for name in all_names or []:
        key = (name or '').strip().lower()
        if key and key not in selected:
            disabled.append(key)
    return disabled


def is_precache_site(name, state=None):
    key = (name or '').strip().lower()
    if not key:
        return False
    state = normalize_state(state or {})
    names = state.get('precache_sites')
    if names is None:
        return is_site_enabled(name, state)
    return key in set(names)


def filter_precache_names(names, state=None):
    state = normalize_state(state or {})
    return [n for n in (names or []) if is_precache_site(n, state)]


def enabled_summary(all_names, state=None):
    names = [n for n in (all_names or []) if (n or '').strip()]
    enabled = filter_enabled_names(names, state)
    total = len(names)
    on = len(enabled)
    if total == 0:
        return 'No sites loaded'
    if on == total:
        return 'All {0} sites enabled'.format(total)
    if on == 0:
        return 'All {0} sites disabled'.format(total)
    return '{0} of {1} sites enabled'.format(on, total)
