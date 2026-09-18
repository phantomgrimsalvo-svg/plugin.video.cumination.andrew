#!/usr/bin/env python3
"""Build plugin.video.cumination.andrew-<version>.zip with framed site logos."""
from __future__ import print_function

import hashlib
import os
import shutil
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ADDON_ID = 'plugin.video.cumination.andrew'
EXCLUDE_DIRS = {'.git', '__pycache__', 'artifacts', 'tests', 'scripts', 'workshop'}
EXCLUDE_FILES = {'.gitignore'}


def addon_version():
    path = os.path.join(ROOT, 'addon.xml')
    with open(path, 'r', encoding='utf-8') as fh:
        for line in fh:
            if 'version="' in line and 'addon id=' in line:
                return line.split('version="')[1].split('"')[0]
    raise RuntimeError('Could not read addon version')


def should_skip(rel):
    parts = rel.split(os.sep)
    if parts[0] in EXCLUDE_DIRS:
        return True
    if parts[-1] in EXCLUDE_FILES:
        return True
    if parts[-1].endswith('.pyc'):
        return True
    return False


def pack(dest_dir=None, include_framed=True):
    sys.path.insert(0, ROOT)
    version = addon_version()
    dest_dir = dest_dir or os.path.join(ROOT, 'artifacts')
    os.makedirs(dest_dir, exist_ok=True)
    zip_path = os.path.join(dest_dir, '{0}-{1}.zip'.format(ADDON_ID, version))

    staging = os.path.join(dest_dir, '_staging_' + ADDON_ID)
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)
    staged_addon = os.path.join(staging, ADDON_ID)

    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = os.path.relpath(dirpath, ROOT)
        if rel_dir == '.':
            rel_dir = ''
        if rel_dir.split(os.sep)[0] in EXCLUDE_DIRS:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and d != '__pycache__']
        for name in filenames:
            rel = os.path.join(rel_dir, name) if rel_dir else name
            if should_skip(rel):
                continue
            src = os.path.join(ROOT, rel)
            dst = os.path.join(staged_addon, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

    if include_framed:
        from resources.lib.andrew_art import generate_shipped_framed_logos
        img_dir = os.path.join(staged_addon, 'resources', 'images')
        framed_dir = os.path.join(img_dir, 'framed')
        n = generate_shipped_framed_logos(img_dir, framed_dir)
        print('framed logos:', n)

    if os.path.isfile(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(staged_addon):
            for name in filenames:
                full = os.path.join(dirpath, name)
                arc = os.path.relpath(full, staging)
                zf.write(full, arc)
    shutil.rmtree(staging)
    md5 = hashlib.md5()
    with open(zip_path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            md5.update(chunk)
    print('wrote', zip_path, 'md5', md5.hexdigest(), 'bytes', os.path.getsize(zip_path))
    return zip_path


if __name__ == '__main__':
    pack()
