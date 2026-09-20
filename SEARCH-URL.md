# Skin / Arctic Fuse 3 search plugin URLs

Cumination (Andrew) **1.2.7** exposes a stable plugin path that skins (including Arctic Fuse 3 search widgets / search fields) can call. When `keyword` is present and non-empty, the addon **does not open the keyboard** — it runs aggregated search and returns **one combined video list**.

## Use this URL in AF3 (recommended)

```
plugin://plugin.video.cumination.andrew/?mode=skin_search&keyword=
```

Put that string in the skin search widget / custom search field. The skin appends the typed query after `keyword=`.

Optional sort (overrides the last saved sort for that request):

```
plugin://plugin.video.cumination.andrew/?mode=skin_search&keyword=&sort=relevance
plugin://plugin.video.cumination.andrew/?mode=skin_search&keyword=&sort=date
plugin://plugin.video.cumination.andrew/?mode=skin_search&keyword=&sort=views
plugin://plugin.video.cumination.andrew/?mode=skin_search&keyword=&sort=rating
```

`query=` and `q=` are accepted as aliases of `keyword=`.

## Aliases (same combined list)

These are equivalent once a keyword is supplied:

```
plugin://plugin.video.cumination.andrew/?mode=search&keyword=
plugin://plugin.video.cumination.andrew/?mode=global_search&keyword=
plugin://plugin.video.cumination.andrew/?mode=main.skin_search&keyword=
plugin://plugin.video.cumination.andrew/?mode=main.global_search&keyword=
```

| mode | Empty keyword |
|---|---|
| `skin_search` / `search` | No keyboard. Shows a short hint item (safe for home-screen widgets). |
| `global_search` | Opens the Kodi keyboard (addon menu **Search all sites**). |

## What you get

- One Kodi directory mixing playable hits from enabled site Search handlers.
- Titles look like `[SiteName] Video title`.
- A site timeout or scrape error is skipped; the rest of the list still appears.
- Sort: **Relevance** (default), **Newest**, **Most viewed**, **Top rated**. Last choice is stored in addon settings. Missing metadata sorts last.
- Context: **Add to keywords** (from a result title) and **Save this search as keyword** (uses the existing `keywords` table).

Tune include/exclude, webcam sites, timeout, concurrency, and caps under **Settings → Global search**.

Adult content: this addon does not host videos; keep Kodi restricted-profiles / PIN as you already do.
