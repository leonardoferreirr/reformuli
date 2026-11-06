#!/usr/bin/env python3
"""Fotos de conferência em Chromium próprio (nunca o Chrome do usuário).

    python3 tools/shots.py <saida> [url] [--w 1440,390]

Rola a página inteira em passos de uma tela e salva um JPEG por passo e largura,
além de acusar rolagem lateral, imagens quebradas e erros de console.
"""
import os, sys, asyncio
from pathlib import Path
from playwright.async_api import async_playwright

CHROME = os.path.expanduser('~/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell')


async def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    url = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else 'http://127.0.0.1:4240/'
    larguras = [1440, 390]
    if '--w' in sys.argv:
        larguras = [int(x) for x in sys.argv[sys.argv.index('--w') + 1].split(',')]
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME)
        for w in larguras:
            h = 900 if w > 800 else 844
            ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1,
                                      is_mobile=w < 800, has_touch=w < 800)
            pg = await ctx.new_page()
            erros = []
            pg.on('console', lambda m: m.type == 'error' and erros.append(m.text))
            pg.on('pageerror', lambda e: erros.append(str(e)))
            await pg.goto(url, wait_until='load')
            await pg.wait_for_timeout(1500)
            total = await pg.evaluate('document.documentElement.scrollHeight')
            n = min(40, int(total / h) + 1)
            nome = url.rstrip('/').split('/')[-1] or 'home'
            if nome.startswith('127.') or nome.startswith('localhost'):
                nome = 'home'
            for i in range(n):
                y = int(i * (total - h) / max(1, n - 1))
                await pg.evaluate(f'window.scrollTo(0,{y})')
                await pg.wait_for_timeout(700)
                await pg.screenshot(path=str(out / f'{nome}-{w}-{i:02d}.jpg'), type='jpeg', quality=70)
            info = await pg.evaluate('''() => ({
              lateral: document.documentElement.scrollWidth > innerWidth,
              quebradas: [...document.images].filter(i => i.complete && !i.naturalWidth).map(i => i.getAttribute('src')),
            })''')
            print(w, 'altura', total, info, 'erros', erros[:5])
            await ctx.close()
        await b.close()

asyncio.run(main())
