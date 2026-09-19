# -*- coding: utf-8 -*-
"""Cumination (Andrew) ListItem art: logo framing + portrait fanart modes.

Works without Kodi for tests. Image generation uses Pillow when available.
Framed site logos may also be shipped under resources/images/framed/.
"""
from __future__ import absolute_import, print_function

import hashlib
import os
import time

try:
    from PIL import Image
except ImportError:
    Image = None

ART_CACHE_VERSION = '126'
FANART_W, FANART_H = 1280, 720
POSTER_W, POSTER_H = 512, 768
SQUARE_W, SQUARE_H = 512, 512
PAN_FRAMES = 6

MODE_PILLARBOX = 'pillarbox'
MODE_TOPFILL = 'topfill'
MODE_PAN = 'pan'
MODE_ORIGINAL = 'original'
MODE_LETTERBOX = 'letterbox'
MODE_CENTER = 'center'

PORTRAIT_MODES = (MODE_PILLARBOX, MODE_TOPFILL, MODE_PAN)
LANDSCAPE_MODES = (MODE_ORIGINAL, MODE_LETTERBOX, MODE_CENTER)


def _import_pil():
    global Image
    if Image is not None:
        return Image
    try:
        from PIL import Image as _Image
        Image = _Image
        return Image
    except ImportError:
        pass
    try:
        import sys
        import xbmcaddon
        pil_path = xbmcaddon.Addon('script.module.pil').getAddonInfo('path')
        for sub in ('lib', 'resources/lib', ''):
            candidate = os.path.join(pil_path, sub) if sub else pil_path
            if candidate not in sys.path:
                sys.path.append(candidate)
        from PIL import Image as _Image
        Image = _Image
        return Image
    except Exception:
        return None


def default_settings():
    return {
        'posterfanart': True,
        'portrait_fanart_extras': True,
        'portrait_fanart_mode': MODE_PILLARBOX,
        'portrait_fanart_pan_duration': 20,
        'landscape_fanart_mode': MODE_ORIGINAL,
        'addon_fanart': '',
        'cache_dir': '',
        'framed_dir': '',
        'images_dir': '',
        'allow_remote_fetch': False,
        'remote_timeout': 4,
    }


def settings_from_addon(addon, cache_dir, framed_dir, addon_fanart, images_dir=''):
    """Read Cumination (Andrew) settings into a plain dict."""
    extras = addon.getSetting('portrait_fanart_extras')
    mode_idx = addon.getSetting('portrait_fanart_mode') or '0'
    land_idx = addon.getSetting('landscape_fanart_mode') or '0'
    duration = addon.getSetting('portrait_fanart_pan_duration') or '20'
    portrait_modes = (MODE_PILLARBOX, MODE_TOPFILL, MODE_PAN)
    landscape_modes = (MODE_ORIGINAL, MODE_LETTERBOX, MODE_CENTER)
    try:
        p_mode = portrait_modes[int(mode_idx)]
    except (TypeError, ValueError, IndexError):
        p_mode = MODE_PILLARBOX
    try:
        l_mode = landscape_modes[int(land_idx)]
    except (TypeError, ValueError, IndexError):
        l_mode = MODE_ORIGINAL
    try:
        pan_secs = int(duration)
    except (TypeError, ValueError):
        pan_secs = 20
    posterfanart = addon.getSetting('posterfanart') == 'true'
    extras_on = extras != 'false'
    return {
        'posterfanart': posterfanart,
        'portrait_fanart_extras': extras_on,
        'portrait_fanart_mode': p_mode,
        'portrait_fanart_pan_duration': max(6, min(60, pan_secs)),
        'landscape_fanart_mode': l_mode,
        'addon_fanart': addon_fanart,
        'cache_dir': cache_dir,
        'framed_dir': framed_dir,
        'images_dir': images_dir,
        'allow_remote_fetch': bool(posterfanart and extras_on),
        'remote_timeout': 4,
    }


def _ensure_dir(path):
    if path and not os.path.isdir(path):
        try:
            os.makedirs(path)
        except OSError:
            pass


def _is_url(path):
    path = (path or '').lower()
    return path.startswith('http://') or path.startswith('https://')


def _strip_kodi_suffix(src):
    path = src or ''
    if '|' in path:
        path = path.split('|', 1)[0]
    if '?' in path and not _is_url(path):
        path = path.split('?', 1)[0]
    return path


def _translate_special(path):
    if not path:
        return path
    if path.startswith('special://') or path.startswith('resource://'):
        try:
            from kodi_six import xbmc, xbmcvfs
            translate = xbmcvfs.translatePath if hasattr(xbmcvfs, 'translatePath') else xbmc.translatePath
            return translate(path)
        except Exception:
            return path
    return path


def _image_stem(src):
    name = os.path.basename(_strip_kodi_suffix(src).replace('\\', '/'))
    stem, _ext = os.path.splitext(name)
    return stem or name


def _local_image_candidates(src, settings=None):
    """Resolve special://, addon-relative, and basename matches under images_dir.

    Basename matching is for Kodi special:// / addon paths that point at
    resources/images. Remote http(s) URLs are not matched by basename so a
    generic ``logo.png`` on a site CDN cannot pick the wrong packed image.
    """
    settings = settings or {}
    raw = _strip_kodi_suffix(src)
    translated = _translate_special(raw)
    images_dir = settings.get('images_dir') or ''
    stem = _image_stem(translated or raw)
    out = []
    if translated and os.path.isfile(translated):
        out.append(translated)
    elif raw and (not _is_url(raw)) and os.path.isfile(raw):
        out.append(raw)
    marker = '/resources/images/'
    norm = raw.replace('\\', '/')
    allow_basename = (not _is_url(raw)) or (marker in norm)
    if images_dir and stem and allow_basename:
        base = os.path.basename(norm)
        if base:
            direct = os.path.join(images_dir, base)
            if os.path.isfile(direct):
                out.append(direct)
        for ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
            candidate = os.path.join(images_dir, stem + ext)
            if os.path.isfile(candidate):
                out.append(candidate)
    if images_dir and marker in norm:
        fname = norm.split(marker, 1)[-1]
        if fname and '/' not in fname:
            candidate = os.path.join(images_dir, fname)
            if os.path.isfile(candidate):
                out.append(candidate)
    seen = set()
    uniq = []
    for path in out:
        if path not in seen:
            seen.add(path)
            uniq.append(path)
    return uniq


def _cache_name(src, kind, extra=''):
    key = u'{0}|{1}|{2}|{3}'.format(ART_CACHE_VERSION, kind, src, extra)
    digest = hashlib.md5(key.encode('utf-8', 'replace')).hexdigest()
    ext = '.png' if kind.startswith('logo') else '.jpg'
    return digest + ext


def _src_cache_path(url, settings):
    cache_dir = settings.get('cache_dir')
    if not cache_dir:
        return None
    ext = os.path.splitext(_strip_kodi_suffix(url).split('?')[0])[-1].lower()
    if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
        ext = '.img'
    return os.path.join(cache_dir, 'src', _cache_name(url, 'src', '')[:-4] + ext)


def _open_image(src, settings=None):
    ImageMod = _import_pil()
    if ImageMod is None or not src:
        return None
    settings = settings or {}
    path = None
    locals_found = _local_image_candidates(src, settings)
    if locals_found:
        path = locals_found[0]
    elif _is_url(src):
        if not settings.get('allow_remote_fetch'):
            path = _cached_url_original(src, settings)
            if not path:
                return None
        else:
            path = _fetch_url(src, settings)
            if not path:
                return None
    elif os.path.isfile(src):
        path = src
    if not path or not os.path.isfile(path):
        return None
    try:
        im = ImageMod.open(path)
        im.load()
        return im
    except Exception:
        return None


def _cached_url_original(url, settings):
    path = _src_cache_path(url, settings)
    if path and os.path.isfile(path) and os.path.getsize(path) > 32:
        return path
    return None


def _fetch_url(url, settings):
    dest = _src_cache_path(url, settings)
    if not dest:
        return None
    _ensure_dir(os.path.dirname(dest))
    if os.path.isfile(dest) and os.path.getsize(dest) > 32:
        return dest
    timeout = settings.get('remote_timeout') or 4
    try:
        from six.moves import urllib_request
        req = urllib_request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = urllib_request.urlopen(req, timeout=timeout).read()
        if not data:
            return None
        with open(dest, 'wb') as fh:
            fh.write(data)
        return dest
    except Exception:
        try:
            import requests
            resp = requests.get(url, timeout=timeout, headers={'User-Agent': 'Mozilla/5.0'})
            if resp.status_code != 200 or not resp.content:
                return None
            with open(dest, 'wb') as fh:
                fh.write(resp.content)
            return dest
        except Exception:
            return None


def image_size(src, settings=None):
    im = _open_image(src, settings)
    if im is None:
        return None
    try:
        return im.size
    finally:
        try:
            im.close()
        except Exception:
            pass


def aspect_kind(src, settings=None, default='unknown'):
    size = image_size(src, settings)
    if not size:
        return default
    width, height = size
    if height <= 0 or width <= 0:
        return default
    if height > width * 1.08:
        return 'portrait'
    if width > height * 1.18:
        return 'landscape'
    return 'square'


def _save(im, dest, as_jpeg=False):
    _ensure_dir(os.path.dirname(dest))
    tmp = dest + '.tmp'
    if as_jpeg:
        rgb = im.convert('RGB')
        rgb.save(tmp, 'JPEG', quality=82, optimize=True)
        rgb.close()
    else:
        im.convert('RGBA').save(tmp, 'PNG', optimize=True)
    os.replace(tmp, dest)
    return dest


def _contain_scale(sw, sh, tw, th):
    """Scale so the full image fits inside the target (never crop)."""
    if sw <= 0 or sh <= 0:
        return 1.0
    return min(float(tw) / float(sw), float(th) / float(sh))


def _cover_scale(sw, sh, tw, th):
    """Scale so the image covers the target (may crop). Always upscales."""
    if sw <= 0 or sh <= 0:
        return 1.0
    return max(float(tw) / float(sw), float(th) / float(sh))


def _resize_exact(src, nw, nh, ImageMod):
    nw = max(1, int(nw))
    nh = max(1, int(nh))
    return src.resize((nw, nh), ImageMod.LANCZOS)


def fit_on_canvas(im, canvas_w, canvas_h, margin=0.12, bgcolor=(0, 0, 0, 255)):
    """Letterbox/pillarbox `im` onto a canvas so the full wordmark stays visible."""
    ImageMod = _import_pil()
    canvas = ImageMod.new('RGBA', (canvas_w, canvas_h), bgcolor)
    src = im.convert('RGBA')
    max_w = max(1, int(canvas_w * (1.0 - 2.0 * margin)))
    max_h = max(1, int(canvas_h * (1.0 - 2.0 * margin)))
    scale = _contain_scale(src.size[0], src.size[1], max_w, max_h)
    resized = _resize_exact(src, src.size[0] * scale, src.size[1] * scale, ImageMod)
    src.close()
    x = (canvas_w - resized.size[0]) // 2
    y = (canvas_h - resized.size[1]) // 2
    canvas.alpha_composite(resized, (x, y))
    resized.close()
    return canvas


def pillarbox_to_fanart(im, tw=FANART_W, th=FANART_H):
    """Mode A / letterbox: contain-scale onto 16:9, then center.

    Portraits fill the full fanart height (black bars left/right only).
    Wide images fill the full width (black bars top/bottom). Small thumbs
    are upscaled — never pasted 1:1 onto the 1280×720 canvas.
    """
    ImageMod = _import_pil()
    src = im.convert('RGB')
    sw, sh = src.size
    scale = _contain_scale(sw, sh, tw, th)
    nw = max(1, int(round(sw * scale)))
    nh = max(1, int(round(sh * scale)))
    if nw > tw:
        nw = tw
        nh = max(1, int(round(sh * (float(tw) / float(sw)))))
    if nh > th:
        nh = th
        nw = max(1, int(round(sw * (float(th) / float(sh)))))
    resized = _resize_exact(src, nw, nh, ImageMod)
    src.close()
    canvas = ImageMod.new('RGB', (tw, th), (0, 0, 0))
    x = (tw - resized.size[0]) // 2
    y = (th - resized.size[1]) // 2
    canvas.paste(resized, (x, y))
    resized.close()
    return canvas


def cover_top_fanart(im, tw=FANART_W, th=FANART_H):
    """Mode B: scale to COVER 16:9, anchored to the TOP (faces stay visible)."""
    ImageMod = _import_pil()
    src = im.convert('RGB')
    sw, sh = src.size
    scale = _cover_scale(sw, sh, tw, th)
    nw = max(tw, int(round(sw * scale)))
    nh = max(th, int(round(sh * scale)))
    resized = _resize_exact(src, nw, nh, ImageMod)
    src.close()
    left = max(0, (resized.size[0] - tw) // 2)
    cropped = resized.crop((left, 0, left + tw, th))
    resized.close()
    return cropped


def cover_center_fanart(im, tw=FANART_W, th=FANART_H):
    ImageMod = _import_pil()
    src = im.convert('RGB')
    sw, sh = src.size
    scale = _cover_scale(sw, sh, tw, th)
    nw = max(tw, int(round(sw * scale)))
    nh = max(th, int(round(sh * scale)))
    resized = _resize_exact(src, nw, nh, ImageMod)
    src.close()
    left = max(0, (resized.size[0] - tw) // 2)
    top = max(0, (resized.size[1] - th) // 2)
    cropped = resized.crop((left, top, left + tw, top + th))
    resized.close()
    return cropped


def pan_frame_fanart(im, progress, tw=FANART_W, th=FANART_H):
    """progress 0.0 = top (face), 1.0 = bottom. Always covers 16:9."""
    ImageMod = _import_pil()
    src = im.convert('RGB')
    sw, sh = src.size
    # Cover, preferring fill-width so a portrait is taller than 16:9 and can pan.
    scale = max(_cover_scale(sw, sh, tw, th), float(tw) / float(sw) if sw else 1.0)
    nw = max(tw, int(round(sw * scale)))
    nh = max(th, int(round(sh * scale)))
    resized = _resize_exact(src, nw, nh, ImageMod)
    src.close()
    left = max(0, (resized.size[0] - tw) // 2)
    max_top = max(0, resized.size[1] - th)
    top = int(round(max(0.0, min(1.0, float(progress))) * max_top))
    cropped = resized.crop((left, top, left + tw, top + th))
    resized.close()
    return cropped


def _shipped_stems(src, settings):
    """Basenames to look up under framed/ (local + special:// images only)."""
    if not src:
        return []
    raw = _strip_kodi_suffix(src)
    stems = []
    marker = '/resources/images/'
    norm = raw.replace('\\', '/')
    if not _is_url(raw):
        stem = _image_stem(raw)
        if stem:
            stems.append(stem)
    if marker in norm:
        fname = norm.split(marker, 1)[-1]
        if fname and '/' not in fname:
            stems.append(os.path.splitext(fname)[0])
    for path in _local_image_candidates(src, settings):
        stems.append(os.path.splitext(os.path.basename(path))[0])
    seen = set()
    out = []
    for stem in stems:
        if stem and stem not in seen:
            seen.add(stem)
            out.append(stem)
    return out


def _shipped_framed(src, kind, settings):
    """Use pack-time framed logos, matching basename even for special:// paths."""
    if not src:
        return None
    framed_dir = settings.get('framed_dir')
    if not framed_dir:
        locals_found = _local_image_candidates(src, settings)
        if locals_found:
            framed_dir = os.path.join(os.path.dirname(locals_found[0]), 'framed')
        elif not _is_url(src):
            framed_dir = os.path.join(os.path.dirname(_strip_kodi_suffix(src)), 'framed')
        else:
            return None
    for stem in _shipped_stems(src, settings):
        path = os.path.join(framed_dir, kind, stem + '.png')
        if os.path.isfile(path):
            return path
    return None


def framed_logo_paths(src, settings):
    """Return (square_path, poster_path) for a site logo, generating if needed."""
    shipped_sq = _shipped_framed(src, 'square', settings)
    shipped_po = _shipped_framed(src, 'poster', settings)
    if shipped_sq and shipped_po:
        return shipped_sq, shipped_po

    cache_dir = settings.get('cache_dir')
    square = shipped_sq
    poster = shipped_po
    if cache_dir:
        _ensure_dir(os.path.join(cache_dir, 'logo'))
        if not square:
            square = os.path.join(cache_dir, 'logo', _cache_name(src, 'logo-square'))
        if not poster:
            poster = os.path.join(cache_dir, 'logo', _cache_name(src, 'logo-poster'))
        if os.path.isfile(square) and os.path.isfile(poster):
            return square, poster

    open_settings = dict(settings)
    # Site-folder logos: fetch a remote icon once (cached under cache_dir/src)
    # even when video thumb fetch is off, so portrait/circle views can pad it.
    if _is_url(src) and not (shipped_sq and shipped_po):
        open_settings['allow_remote_fetch'] = True
    im = _open_image(src, open_settings)
    if im is None:
        return shipped_sq, shipped_po
    try:
        if square and not os.path.isfile(square):
            canvas = fit_on_canvas(im, SQUARE_W, SQUARE_H, margin=0.16)
            _save(canvas, square, as_jpeg=False)
            canvas.close()
        if poster and not os.path.isfile(poster):
            canvas = fit_on_canvas(im, POSTER_W, POSTER_H, margin=0.10)
            _save(canvas, poster, as_jpeg=False)
            canvas.close()
    finally:
        try:
            im.close()
        except Exception:
            pass
    if square and os.path.isfile(square) and poster and os.path.isfile(poster):
        return square, poster
    return (
        square if square and os.path.isfile(square) else None,
        poster if poster and os.path.isfile(poster) else None,
    )


def framed_fanart_path(src, mode, settings, progress=None):
    cache_dir = settings.get('cache_dir')
    if not cache_dir:
        return None
    extra = '' if progress is None else '{0:.3f}'.format(progress)
    dest = os.path.join(cache_dir, 'fanart', _cache_name(src, 'fanart-' + mode, extra))
    if os.path.isfile(dest):
        return dest
    im = _open_image(src, settings)
    if im is None:
        return None
    try:
        if mode == MODE_PILLARBOX or mode == MODE_LETTERBOX:
            framed = pillarbox_to_fanart(im)
        elif mode == MODE_TOPFILL:
            framed = cover_top_fanart(im)
        elif mode == MODE_CENTER:
            framed = cover_center_fanart(im)
        elif mode == MODE_PAN:
            framed = pan_frame_fanart(im, 0.0 if progress is None else progress)
        else:
            return None
        _save(framed, dest, as_jpeg=True)
        framed.close()
        return dest if os.path.isfile(dest) else None
    finally:
        try:
            im.close()
        except Exception:
            pass


def pan_frame_paths(src, settings, count=PAN_FRAMES):
    paths = []
    for i in range(count):
        progress = 0.0 if count <= 1 else float(i) / float(count - 1)
        path = framed_fanart_path(src, MODE_PAN, settings, progress=progress)
        if path:
            paths.append(path)
    return paths


def _folder_is_logo(src, settings):
    if _shipped_framed(src, 'square', settings) or _shipped_framed(src, 'poster', settings):
        return True
    # Remote / unreadable icons default to logo (wide site wordmark). Only skip
    # padding when we can open a local portrait still.
    kind = aspect_kind(src, settings, default='landscape')
    return kind != 'portrait'


def build_art(iconimage, fanart=None, is_folder=False, settings=None):
    """Return (art_dict, properties_dict) for a ListItem.

    Folder/site logos: full wordmark on clearlogo/banner/landscape; padded
    square/poster so portrait/circle/poster viewtypes do not chop the name.

    Videos: when thumb-as-fanart + portrait extras are on, fanart is framed
    with Mode A (pillarbox), B (top-aligned fill), or C (pan start + frames).
    """
    settings = dict(default_settings(), **(settings or {}))
    posterfanart = settings.get('posterfanart')
    extras = settings.get('portrait_fanart_extras')
    p_mode = settings.get('portrait_fanart_mode') or MODE_PILLARBOX
    l_mode = settings.get('landscape_fanart_mode') or MODE_ORIGINAL
    default_fanart = settings.get('addon_fanart') or ''
    props = {}
    now = str(int(time.time()))
    props['Andrew.ArtStamp'] = now

    if is_folder:
        return _build_folder_art(iconimage, settings, posterfanart, extras, default_fanart, p_mode)

    art = {
        'thumb': iconimage,
        'icon': iconimage,
        'poster': iconimage,
        'fanart': fanart or default_fanart,
        'keyart': iconimage,
        'landscape': fanart or default_fanart or iconimage,
    }
    props['Andrew.ArtType'] = 'video'
    props['Andrew.ArtAspect'] = 'landscape'
    props['Andrew.FanartMode'] = 'off'

    use_thumb_fanart = posterfanart and (extras or not fanart)
    if not posterfanart:
        if extras:
            art['fanart1'] = iconimage
            art['extrafanart'] = fanart or iconimage
        return art, props

    if not extras and fanart:
        art['fanart'] = fanart
        art['landscape'] = fanart
        return art, props

    source = iconimage
    kind = aspect_kind(source, settings, default='portrait' if extras else 'unknown')
    if kind == 'landscape':
        return _build_landscape_fanart(art, source, l_mode, settings, extras, props)
    return _build_portrait_fanart(art, source, p_mode, settings, extras, props)


def _build_folder_art(iconimage, settings, posterfanart, extras, default_fanart, p_mode):
    props = {
        'Andrew.ArtType': 'logo',
        'Andrew.ArtAspect': 'logo',
        'Andrew.FanartMode': 'off',
    }
    square, poster = (None, None)
    if _folder_is_logo(iconimage, settings):
        square, poster = framed_logo_paths(iconimage, settings)
        if square or poster:
            props['Andrew.LogoSafe'] = 'true'
    else:
        props['Andrew.ArtType'] = 'portrait'
        props['Andrew.ArtAspect'] = 'portrait'

    safe_thumb = square or iconimage
    safe_poster = poster or square or iconimage
    art = {
        'thumb': safe_thumb,
        'icon': safe_thumb,
        'poster': safe_poster,
        'clearlogo': iconimage,
        'banner': iconimage,
        'landscape': iconimage,
        'fanart': default_fanart,
    }
    if posterfanart:
        if props.get('Andrew.ArtType') == 'logo':
            # Estuary Fanart view cover-crops raw wide PNGs. Bake a 16:9
            # letterboxed JPEG so the full wordmark stays visible.
            logo_settings = dict(settings)
            if _is_url(iconimage):
                logo_settings['allow_remote_fetch'] = True
            logo_fanart = framed_fanart_path(iconimage, MODE_LETTERBOX, logo_settings)
            art['fanart'] = logo_fanart or iconimage
            if logo_fanart:
                art['landscape'] = logo_fanart
                props['Andrew.FanartFramed'] = 'true'
                props['Andrew.FanartMode'] = MODE_LETTERBOX
                props['Andrew.FanartAspect'] = 'keep'
        elif extras:
            framed, fprops = _framed_thumb_fanart(iconimage, p_mode, settings)
            art['fanart'] = framed or iconimage
            props.update(fprops)
            props['Andrew.PortraitFanart'] = 'true'
        else:
            art['fanart'] = iconimage
        art['fanart1'] = art['fanart']
        art['extrafanart'] = iconimage
        if extras:
            props['Andrew.PortraitFanart'] = 'true'
    return art, props


def _framed_thumb_fanart(source, mode, settings):
    props = {
        'Andrew.FanartMode': mode,
        'Andrew.FanartSource': source or '',
        'Andrew.FanartAlignY': 'top' if mode in (MODE_TOPFILL, MODE_PAN) else 'center',
        'Andrew.FanartAspect': 'keep' if mode == MODE_PILLARBOX else 'scale',
        'Andrew.FanartPanDuration': str(settings.get('portrait_fanart_pan_duration') or 20),
    }
    framed = None
    if mode == MODE_PAN:
        frames = pan_frame_paths(source, settings)
        if frames:
            props['Andrew.FanartPanFrames'] = '|'.join(frames)
            framed = frames[0]
            props['Andrew.FanartFramed'] = 'true'
        else:
            framed = framed_fanart_path(source, MODE_TOPFILL, settings)
            if framed:
                props['Andrew.FanartFramed'] = 'true'
    else:
        framed = framed_fanart_path(source, mode, settings)
        if framed:
            props['Andrew.FanartFramed'] = 'true'
    return framed, props


def _build_portrait_fanart(art, source, mode, settings, extras, props):
    props['Andrew.ArtType'] = 'portrait'
    props['Andrew.ArtAspect'] = 'portrait'
    props['Andrew.PortraitFanart'] = 'true'
    framed, fprops = _framed_thumb_fanart(source, mode, settings)
    props.update(fprops)
    fanart = framed or source
    art['fanart'] = fanart
    art['landscape'] = fanart if framed else source
    art['fanart1'] = source
    art['extrafanart'] = fanart
    if mode == MODE_PAN and props.get('Andrew.FanartPanFrames'):
        frames = props['Andrew.FanartPanFrames'].split('|')
        if len(frames) > 1:
            art['fanart1'] = frames[min(2, len(frames) - 1)]
            art['extrafanart'] = frames[-1]
    return art, props


def _build_landscape_fanart(art, source, mode, settings, extras, props):
    props['Andrew.ArtType'] = 'video'
    props['Andrew.ArtAspect'] = 'landscape'
    props['Andrew.FanartMode'] = mode
    fanart = source
    if mode == MODE_LETTERBOX:
        framed = framed_fanart_path(source, MODE_LETTERBOX, settings)
        if framed:
            fanart = framed
            props['Andrew.FanartFramed'] = 'true'
            props['Andrew.FanartAspect'] = 'scale'
    elif mode == MODE_CENTER:
        framed = framed_fanart_path(source, MODE_CENTER, settings)
        if framed:
            fanart = framed
            props['Andrew.FanartFramed'] = 'true'
            props['Andrew.FanartAspect'] = 'scale'
    else:
        props['Andrew.FanartMode'] = MODE_ORIGINAL
        props['Andrew.FanartAspect'] = 'scale'
    art['fanart'] = fanart
    art['landscape'] = source
    if extras:
        art['fanart1'] = source
        art['extrafanart'] = fanart
        props['Andrew.PortraitFanart'] = 'true'
    return art, props


def apply_to_listitem(liz, iconimage, fanart=None, is_folder=False, settings=None):
    art, props = build_art(iconimage, fanart=fanart, is_folder=is_folder, settings=settings)
    if hasattr(liz, 'setArt'):
        liz.setArt(art)
    if hasattr(liz, 'setProperty'):
        for key, value in props.items():
            if value is None:
                continue
            liz.setProperty(key, str(value))
        fanart_path = art.get('fanart')
        if fanart_path:
            liz.setProperty('Fanart_Image', fanart_path)
            liz.setProperty('fanart', fanart_path)
    return art, props


def generate_shipped_framed_logos(img_dir, framed_dir):
    """Pack-time helper: write square/poster padded logos for every local image."""
    if _import_pil() is None:
        raise RuntimeError('Pillow is required to generate framed logos')
    written = 0
    settings = default_settings()
    settings['framed_dir'] = framed_dir
    settings['cache_dir'] = ''
    for name in sorted(os.listdir(img_dir)):
        ext = os.path.splitext(name)[1].lower()
        if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
            continue
        src = os.path.join(img_dir, name)
        if not os.path.isfile(src):
            continue
        im = _open_image(src, settings)
        if im is None:
            continue
        try:
            stem = os.path.splitext(name)[0] + '.png'
            sq = os.path.join(framed_dir, 'square', stem)
            po = os.path.join(framed_dir, 'poster', stem)
            if not os.path.isfile(sq):
                canvas = fit_on_canvas(im, SQUARE_W, SQUARE_H, margin=0.16)
                _save(canvas, sq, as_jpeg=False)
                canvas.close()
            if not os.path.isfile(po):
                canvas = fit_on_canvas(im, POSTER_W, POSTER_H, margin=0.10)
                _save(canvas, po, as_jpeg=False)
                canvas.close()
            written += 1
        finally:
            try:
                im.close()
            except Exception:
                pass
    return written
