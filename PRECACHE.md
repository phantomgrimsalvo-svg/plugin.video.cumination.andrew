# Precache (Cumination Andrew 1.2.8)

Adult addon: this tool **never downloads videos**. It only fetches **list/HTML pages** and **thumbnails / fanart / logos** into Kodi addon data so browsing and search feel faster when the cache is hot.

The author does not host or distribute the sites or images this addon displays.

## Settings paths

In Kodi: **Add-ons → Cumination (Andrew) → Configure** (or context **Addon settings**).

| What | Where |
|---|---|
| Which sites appear at all | **Sites** |
| Global search skips disabled sites | **Global search** → **Global search: only enabled sites** (default on) |
| Image/list crawl | **Precache** |

Disabled sites are hidden from the **Sites** list, from **Search all sites** (when the setting above is on), and from precache. Favorites/keywords you already saved are not wiped.

Site toggles are stored as `siteflags.json` under the addon profile (a disabled-list, so **new sites stay on** until you uncheck them). Precache progress is `precache.json` in the same folder.

## Pick sites

1. Open **Sites → Choose enabled sites**. Scroll the checkbox list; unchecked sites are off.
2. Optional shortcuts: **Enable all**, **Disable all**, **Disable webcam sites**.
3. Open **Precache → Choose sites to precache** if you want a smaller crawl than “everything still enabled”. **Precache list: use enabled sites** resets that to follow the Sites list.

## Hit Precache now

1. Set **Levels deep**:
   - **1** — site root (categories / homepage thumbs)
   - **2** — into category folders
   - **3** — into model / video list pages for thumbs
   - **4** — one more folder level (cap)
2. Optional caps: **Max images** (default 2500; `0` = no limit) and **Max storage MB** (default 400; `0` = no limit).
3. **Precache now**. You can leave settings; the addon **service** keeps going. Status shows **In progress…** then **Last precache: …** (sites, images, size, errors).
4. **Stop precache** cancels. If Kodi exits mid-run the queue is on disk and resumes next time the service runs.

Progress uses a background notification / progress bar. It records sites done, images cached, bytes, and errors.

## Expected disk use

Thumbs are typically 20–80 KB each. A conservative planning number:

- **~50–150 MB** for a handful of sites at depth 2 with the default 2500-image cap
- **up to the Max storage MB** you set (default **400 MB**) if you raise the image cap or crawl many sites at depth 3–4

Cache lives under the addon profile `artcache/src/` (same tree already used for portrait fanart framing). It is **not** your Kodi video download folder. Clearing Kodi’s texture cache does not delete these files; **Clear cache** in the addon still only clears HTML StorageServer rows.

## Speed notes

- While browsing, ListItem thumbs/fanart use a **local cached file** when precache (or a previous framed download) already saved it.
- **Search all sites** skips disabled sites by default (large win).
- Precache reuses HTTP connections and downloads a few images at a time with backoff on 429/5xx. Playback modes (`Playvid`, streams, `.mp4` / `.m3u8`) are never followed.

Not in this release (pitch later if you want them): stripping unused site modules from the zip, a separate “fast mode” package, TMDb Helper, or AF3 skin changes.
