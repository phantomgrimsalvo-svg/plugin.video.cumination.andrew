# -*- coding: utf-8 -*-
"""UTF-8 text file reads that stay safe on ASCII-locale Kodi (no kodi imports)."""
from __future__ import absolute_import

import io
import os


def read_utf8(path, default=''):
    """Read a text file as UTF-8, replacing undecodable bytes."""
    if not path:
        return default
    try:
        if not os.path.isfile(path):
            return default
    except Exception:
        return default
    try:
        with io.open(path, 'r', encoding='utf-8', errors='replace') as fh:
            return fh.read()
    except Exception:
        try:
            with open(path, 'rb') as fh:
                data = fh.read()
            if not isinstance(data, bytes):
                return data or default
            return data.decode('utf-8', 'replace')
        except Exception:
            return default


def read_utf8_lines(path):
    text = read_utf8(path, default='')
    if not text:
        return []
    return text.splitlines(True)
