# Install Cumination (Andrew) 1.2.10

## Skin search URL (Arctic Fuse 3)

Paste this in an AF3 / any-skin search widget. The skin appends the query after `keyword=`; the addon will **not** pop the keyboard:

```
plugin://plugin.video.cumination.andrew/?mode=skin_search&keyword=
```

See `SEARCH-URL.md` in this zip for aliases (`mode=search`, `mode=global_search`) and optional `&sort=date|views|rating`.

## Framing settings (read this)

**Add-ons → Cumination (Andrew) → Configure** (or context menu **Addon settings**) → first category **General** → **Thumbnail as fanart (Estuary / any skin)**.

1. Turn on **Use video thumbnail for poster/fanart**.
2. Keep **Also use portrait thumbs as fanart / background** on.
3. **Portrait fanart framing**
   - **A: Pillarbox** — portrait scaled to full fanart height, black bars left/right only
   - **B: Fill, top-aligned (no top cutoff)**
   - **C: Slow pan top → bottom** (set **Pan duration**)
4. Optional **Landscape thumb framing**.

With both toggles on, A/B/C download the https thumb once (cached) and bake a 16:9 JPEG. Site folders use a letterboxed 16:9 fanart so Estuary Fanart view keeps the full name; portrait/circle/poster views still use the padded square/poster.

Requires stock **script.module.pil** (Pillow) in addition to ResolveURL, six, kodi-six, …. Do not install dependency forks.

## Direct zip (fastest)

https://github.com/phantomgrimsalvo-svg/plugin.video.cumination.andrew/releases/download/v1.2.10/plugin.video.cumination.andrew-1.2.10.zip

If 1.2.9 (or 1.2.8) is already installed, install this zip over it (Unknown sources on). 1.2.8 would not open; 1.2.9 could crash on first-open changelog. Favorites and keywords databases are migrated in place. Site on/off flags and precache queue live in addon_data (`siteflags.json`, `precache.json`) and start empty (all sites on).

Release page: https://github.com/phantomgrimsalvo-svg/plugin.video.cumination.andrew/releases/tag/v1.2.10

## Site list + Precache (1.2.10)

- **Main menu → Sites manager** and **Main menu → Precache** — you do not need to hunt settings tabs.
- **Addon settings** (second and third tabs, after General): Sites / Precache.
- Disabled sites do not appear in Sites, Search all sites, or precache. Precache is images/lists only; never videos. Details: `PRECACHE.md` in this zip.

## Optional: repository 1.1.2 (this repo + existing deps)

1. Install `artifacts/repository.andrew-1.1.2.zip` (or `workshop/zips/repository.andrew-1.1.2.zip`).
2. **Add-ons → Install from repository → Andrew's Kodi Workshop → Cumination (Andrew)**.

`repository.andrew` 1.1.2 reads Cumination zips from **this** repo’s `workshop/` on **main**, and still uses the existing `skin.arctic.fuse.3.andrew` workshop + Gujal smrzips for stock ResolveURL.
