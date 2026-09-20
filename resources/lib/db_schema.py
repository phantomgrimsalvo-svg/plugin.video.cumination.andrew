# -*- coding: utf-8 -*-
"""SQLite schema helpers that must not depend on Kodi."""
from __future__ import absolute_import


def migrate_custom_list_schema(cursor):
    """Add thumb/fanart/poster columns without rebuilding existing lists."""
    cursor.execute('PRAGMA table_info(custom_lists)')
    cols = [row[1] for row in cursor.fetchall()]
    if not cols:
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS custom_lists (name, thumb, fanart, poster)'
        )
        return
    for col in ('thumb', 'fanart', 'poster'):
        if col not in cols:
            cursor.execute('ALTER TABLE custom_lists ADD COLUMN {0} TEXT'.format(col))
