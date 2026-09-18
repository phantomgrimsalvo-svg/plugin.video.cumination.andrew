# plugin.video.cumination.andrew

Personal Kodi fork for Andrew Webber. **Not** an official Cumination release.

- Addon id: `plugin.video.cumination.andrew` **1.2.5**
- Features: **Search all sites**, **Use thumbnail as fanart**, **portrait thumbs as fanart**, **site logo art that stays readable on portrait/circle views**, **portrait fanart framing A/B/C**
- Portrait fanart and site thumbs are **addon ListItem art** — they work in **any skin** (Estuary, Arctic Fuse 3, …). Arctic Fuse 3 (Andrew) is optional extra polish.
- Dependencies are **stock** (`script.module.resolveurl`, `script.module.six`, `script.module.pil`, …). No dependency forks.
- Install from **Andrew's Kodi Workshop** repository so ResolveURL and the other requires resolve from that repo.

## Where the new framing settings live

In Kodi: **Add-ons → Cumination (Andrew) → Configure** (or context menu **Addon settings**) → first category **General**, section **Thumbnail as fanart (Estuary / any skin)**.

1. Turn on **Use video thumbnail for poster/fanart**.
2. Keep **Also use portrait thumbs as fanart / background** on.
3. Choose **Portrait fanart framing**:
   - **A: Pillarbox (black bars, no face crop)**
   - **B: Fill, top-aligned (no top cutoff)**
   - **C: Slow pan top → bottom** (set **Pan duration** when C is selected)
4. Optional: **Landscape thumb framing** (Original / Letterbox / Center crop).

## Skin hook (Mode C pan)

A plugin cannot animate Estuary’s built-in fanart by itself. Cumination (Andrew) therefore:

- Bakes a **top-aligned 16:9 start frame** into `ListItem.Art(fanart)` (Estuary / any skin).
- Writes extra frames on `ListItem.Art(fanart1)` / `extrafanart` and `ListItem.Property(Andrew.FanartPanFrames)`.
- A small service updates **Window(Home)** properties the skin can bind:

| Property | Meaning |
|---|---|
| `Window(Home).Property(Cumination.PanFanart)` | current 16:9 pan frame |
| `Window(Home).Property(Cumination.FanartMode)` | `pillarbox` / `topfill` / `pan` / `off` |
| `Window(Home).Property(Cumination.FanartAlignY)` | `top` or `center` |
| `Window(Home).Property(Cumination.FanartAspect)` | `keep` or `scale` |
| `Window(Home).Property(Cumination.FanartPanDuration)` | seconds |

Arctic Fuse 3 (Andrew) 3.3.3+ uses those properties when present.

- Zip: [`artifacts/plugin.video.cumination.andrew-1.2.5.zip`](artifacts/plugin.video.cumination.andrew-1.2.5.zip)
- Public download: https://github.com/phantomgrimsalvo-svg/plugin.video.cumination.andrew/releases/download/v1.2.5/plugin.video.cumination.andrew-1.2.5.zip
- Release: https://github.com/phantomgrimsalvo-svg/plugin.video.cumination.andrew/releases/tag/v1.2.5
- Workshop on this repo: [`workshop/`](workshop/) (`repository.andrew` 1.1.2 reads `main/workshop/addons.xml` plus the existing AF3 workshop for stock ResolveURL)

Upstream Cumination / dobbelina, GPL v2. Do not PR this tree to dobbelina.

