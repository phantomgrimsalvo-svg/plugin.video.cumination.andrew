# Install Cumination (Andrew) 1.2.5

## Framing settings (read this)

**Add-ons → Cumination (Andrew) → Configure** (or context menu **Addon settings**) → first category **General** → **Thumbnail as fanart (Estuary / any skin)**.

1. Turn on **Use video thumbnail for poster/fanart**.
2. Keep **Also use portrait thumbs as fanart / background** on.
3. **Portrait fanart framing**
   - **A: Pillarbox (black bars, no face crop)**
   - **B: Fill, top-aligned (no top cutoff)**
   - **C: Slow pan top → bottom** (set **Pan duration**)
4. Optional **Landscape thumb framing**.

With both toggles on, A/B/C download the https thumb once (cached) and bake a 16:9 JPEG, so the modes look different. Site names on portrait/circle/poster views are padded automatically (local packed logos plus a one-time fetch for remote site icons).

Requires stock **script.module.pil** (Pillow) in addition to ResolveURL, six, kodi-six, …. Do not install dependency forks.

## Direct zip (fastest)

https://github.com/phantomgrimsalvo-svg/plugin.video.cumination.andrew/releases/download/v1.2.5/plugin.video.cumination.andrew-1.2.5.zip

If 1.2.4 (or 1.2.3) is already installed, install this zip over it (Unknown sources on).

Release page: https://github.com/phantomgrimsalvo-svg/plugin.video.cumination.andrew/releases/tag/v1.2.5

## Optional: repository 1.1.2 (this repo + existing deps)

1. Install `artifacts/repository.andrew-1.1.2.zip` (or `workshop/zips/repository.andrew-1.1.2.zip`).
2. **Add-ons → Install from repository → Andrew's Kodi Workshop → Cumination (Andrew)**.

`repository.andrew` 1.1.2 reads Cumination zips from **this** repo’s `workshop/` on **main**, and still uses the existing `skin.arctic.fuse.3.andrew` workshop + Gujal smrzips for stock ResolveURL.
