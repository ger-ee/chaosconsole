# Room rebuild — October 6, 2026

The room content determines the interface. Threshold supplies the navigation, type families, and a visual relationship; its large architectural banner does not need to repeat on every tool.

## Insult Rolodex

One card, one draw, one copy action. A tactile pink filing tray and ivory index card make the humor the main event. Remove heat scores, history telemetry, explanatory panels, and duplicate counts. Use a compact category selector, reversible draws, and keyboard controls. All original lines stay unchanged.

Palette: rose `#e9b7bf`, burgundy `#421d2e`, card `#fff8e8`, coral `#b44855`, blue `#acc9d2`. Source Serif carries the quote; Barlow supplies controls and the condensed title. Motion only answers a draw.

## Film School

An editorial contents spread leading to a focused lesson reader. The eight existing phases are the actual sequence, so their numbering has meaning. Search reaches every lesson; deep links, previous/next, and a local reading bookmark support returning to the material. Original lesson content and quoted material remain intact.

Palette: ivory `#fff1dd`, oxblood `#3b1720`, muted red `#a64242`, paper `#fffaf0`, graphite `#484044`. Oversized condensed type shapes the contents; a measured Source Serif column carries the lessons. Avoid decorative callout grids and a wall of simultaneously expanded chapters.

## Playlists

A record collection first, with complete history one tab away. Large existing cover art, a manually controlled featured sleeve, search, and a compact catalog. The history view has one legible chart and an optional source table. Individual records retain follower history and Spotify links; snapshot entry and CSV export remain available. Existing data and browser-saved snapshots are preserved.

Palette: pale rose `#e4c0b8`, oxblood `#3b1720`, ivory `#fff1dd`, dusty pink `#cd9b91`, artwork colors. Local covers replace unreliable image CDN links where an existing cover is available. Cover absence has a deliberate text fallback rather than an empty rectangle.

## Critique before building

The previous pass imposed one hero and styling layer on three very different jobs. This rebuild changes their structure: a single playful interaction, a useful reader, and a music collection. No fabricated activity, genre labels, source attributions, or analytics are added. The original substantive collections remain the authority.

## Source locations and checks

- The original Rolodex lines and category rules now live in `insult-rolodex/quotes.js`.
- Playlist snapshots, Spotify destinations, and browser storage compatibility now live in `playlist-tracker/data.js`. Update `DEFAULT_DATA` and `SNAPSHOT_UPDATED_AT` there for future source refreshes. The browser storage key remains `spotify-tracker-v20`.
- All 66 original Film School lesson articles remain verbatim in its HTML; the reader reveals one at a time. Existing lesson anchors remain valid.
- Twelve interaction checks passed. These cover dialog centering at 390, 1440, and 2628 pixels; all three rooms at 320, 390, 768, and 1440 pixels; category draws and copying; lesson search and all 66 mobile deep links; cover loading; complete CSV export; and snapshot validation/persistence in an isolated browser.
- The required render check passed on all four affected pages at desktop and phone widths, with zero page errors. Ledger and status validation also passed.
