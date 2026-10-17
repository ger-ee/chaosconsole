# ChaosConsole app

The existing site is the app. `manifest.webmanifest` supplies one stable identity,
root scope, home launch URL, name, icons and standalone display mode. Apple touch
metadata is present on the landing page and every route. Icons are derived from
the site's existing `favicon.svg`; no new brand mark was introduced.

`/install/` explains installation on Mac, iPhone and iPad. Browsers that expose an
install prompt get a direct install button. Safari uses its native Add to Dock /
Add to Home Screen action. Installation remains a user action on each device.

## Runtime behavior

- App windows get Back, Home and Refresh controls. Browser tabs retain normal
  site navigation and a small Get the app link on the landing page.
- App chrome accounts for screen cutouts and the home indicator. Portrait and
  landscape are both allowed.
- The existing session gate is unchanged. Its card now fits narrow screens.
  This remains a client-side gate, not server-side access control.
- Site updates appear online; local preferences and unlock sessions are not
  synchronized across devices.
- `sw.js` caches only `offline.html`, a generic reconnect screen. It does not
  cache rooms, account information, legal records or status JSON. Navigation
  uses the network; a network failure offers retry at the requested URL.
- Worker updates wait for old app windows to close. When changing the reconnect
  page, bump `CACHE` in `sw.js`. Only ChaosConsole-owned offline caches are removed.

## Maintenance and checks

Run `python3 data/app_build.py` after a generator replaces a routed HTML file.
It updates only app metadata, viewport support and the home installation link.
It never rewrites the dashboard's FALLBACK data.

Checks:

```sh
python3 data/app_build.py --check
python3 data/ledger_close.py check
python3 data/status_build.py --check
CC_BROWSER_CHANNEL=chrome python3 data/render_check.py
CC_BROWSER_CHANNEL=chrome python3 data/app_check.py
```

The browser checks require Playwright. `app_check.py` covers metadata, four device
viewports, the real gate, standalone controls, and offline/reconnect behavior.
Physical Safari installation should be checked on each Apple device after release.
