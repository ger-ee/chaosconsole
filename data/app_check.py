#!/usr/bin/env python3
"""Check manifest, app navigation, responsive layouts and offline recovery.

Uses the same Playwright setup and CC_BROWSER_CHANNEL as render_check.py.
"""
import asyncio
import json
import os
from pathlib import Path
from render_check import serve
from app_build import ROOT, pages


async def main():
    from playwright.async_api import async_playwright
    server, port = serve()
    base = f'http://127.0.0.1:{port}'
    manifest = json.loads((ROOT / 'manifest.webmanifest').read_text())
    assert manifest['name'] == manifest['short_name'] == 'ChaosConsole'
    assert manifest['scope'] == manifest['start_url'] == manifest['id'] == '/'
    assert manifest['display'] == 'standalone'
    for icon in manifest['icons']:
        assert (ROOT / icon['src'].lstrip('/')).is_file()
    for name in pages():
        html = (ROOT / name).read_text()
        assert html.count('rel="manifest"') == 1, name
        assert html.count('name="theme-color"') == 1, name
        assert 'apple-touch-icon' in html, name
    output = Path('/tmp/chaosconsole-app-behavior')
    output.mkdir(exist_ok=True)
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(**({'channel': os.environ['CC_BROWSER_CHANNEL']} if os.environ.get('CC_BROWSER_CHANNEL') else {}))
            ctx = await browser.new_context()
            await ctx.add_init_script("Object.defineProperty(navigator, 'standalone', {get: () => true});")
            page = await ctx.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.goto(base)
            print('Opened app:', page.url, await page.title(), 'errors:', errors, flush=True)
            await page.screenshot(path=str(output/'launch.png'))
            # Exercise the actual gate; don't bypass it in this check.
            await page.locator('#cc-gate-input').fill('trop')
            await page.locator('#cc-gate-host').wait_for(state='detached')
            await page.locator('.cc-app-nav').wait_for()
            assert not await page.locator('.cc-install-link').is_visible()
            for label, width, height in [('iphone',390,844),('ipad-portrait',834,1194),('ipad-landscape',1194,834),('mac',1440,1000)]:
                await page.set_viewport_size({'width':width,'height':height})
                assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth'), label
                await page.screenshot(path=str(output / f'{label}-home.png'), full_page=True)
                await page.goto(base+'/install/')
                assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth'), label+' install'
                assert await page.locator('.cc-app-nav').is_visible()
                await page.screenshot(path=str(output / f'{label}-install.png'), full_page=True)
                await page.get_by_role('link',name='ChaosConsole home',exact=True).click()
            group = page.get_by_role('button',name='Open Studio rooms',exact=True)
            if await group.count():
                await group.click()
            else:
                await page.get_by_role('button',name='Open Archives',exact=True).click()
            await page.locator('#room-sheet a[href="/readwise-highlights/"]').click()
            assert '/readwise-highlights/' in page.url
            assert await page.locator('.cc-app-nav').is_visible()
            assert await page.locator('#cc-gate-host').count() == 0
            await page.get_by_role('button',name='Go back',exact=True).click()
            await page.wait_for_url(base+'/')
            await page.get_by_role('button',name='Reload this page',exact=True).click()
            await page.wait_for_load_state('networkidle')
            await page.evaluate('navigator.serviceWorker.ready')
            await page.wait_for_function('!!navigator.serviceWorker.controller')
            # Only the generic reconnect document may be cached by this feature.
            cached = await page.evaluate("async () => (await (await caches.open('chaosconsole-offline-v1')).keys()).map(r => new URL(r.url).pathname)")
            assert cached == ['/offline.html'], cached
            await ctx.set_offline(True)
            await page.goto(base+'/the-ledger/')
            assert await page.get_by_role('heading',name='A moment to reconnect.').is_visible()
            await page.screenshot(path=str(output/'offline.png'))
            await ctx.set_offline(False)
            await page.get_by_role('button',name='Try again').click()
            await page.wait_for_load_state('networkidle')
            assert await page.locator('.cc-app-nav').is_visible()
            assert '/the-ledger/' in page.url
            assert not errors, errors
            await ctx.close()
            await browser.close()
        print(f'PASS: {len(pages())} page metadata checks; four device layouts; gate; standalone navigation; offline recovery; zero page errors')
        print(f'Screenshots: {output}')
    finally:
        server.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
