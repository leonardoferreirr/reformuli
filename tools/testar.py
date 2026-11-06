#!/usr/bin/env python3
"""Testa o simulador, o arraste do antes e depois e a ponte /obrigado no Chromium próprio.

    python3 tools/testar.py [url]

Confere: os três planos em 20, 60 e 300 m² (total = metragem x valor por m²); valor digitado fora da faixa;
troca de plano e de ambiente; prazo e lista do incluído; mensagem de WhatsApp; arraste com mouse e
com toque (e que o toque vertical ainda rola a página); teclado no puxador; no celular, o total aparece na
mesma tela do simulador.
"""
import os, sys, asyncio, json, re, urllib.parse
from playwright.async_api import async_playwright

CHROME = os.path.expanduser('~/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell')
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:4240/'
falhas = []


def ok(cond, msg):
    print(('  ok  ' if cond else '  FALHA ') + msg)
    if not cond:
        falhas.append(msg)


def num(s):
    return [int(x.replace('.', '')) for x in re.findall(r'R\$ ([\d.]+)', s)]


async def estado(pg):
    return await pg.evaluate('''() => ({
      m2: document.querySelector('#sim-m2').value, range: document.querySelector('.ctl__range').value,
      total: document.querySelector('[data-k=total]').textContent, base: document.querySelector('.sim__base').textContent,
      prazo: document.querySelector('.sim__prazo').textContent,
      plano: document.querySelector('.seg__b[aria-pressed=true]').dataset.plano,
      amb: document.querySelector('.tabs__b[aria-pressed=true]').dataset.amb,
      foto: (document.querySelector('.sim__palco img.on') || {dataset:{}}).dataset.b || '',
      href: document.querySelector('.sim__cta').getAttribute('href'), msg: document.querySelector('.sim__cta').dataset.msg,
      inclui: [...document.querySelectorAll('.sim__inclui li')].map(l => l.textContent),
      legenda: document.querySelector('.sim__legenda').textContent, para: document.querySelector('.sim__para').textContent,
      split: !!document.querySelector('.split'),
    })''')


async def confere(pg, D, m2, plano, rotulo):
    await pg.wait_for_timeout(800)
    s = await estado(pg)
    P = next(p for p in D['planos'] if p['id'] == plano)
    total = m2 * P['m2']
    ok(int(s['m2']) == m2 and int(s['range']) == m2, f'{rotulo}: campo e barra em {m2} m² (campo={s["m2"]}, barra={s["range"]})')
    ok(num(s['total']) == [total], f'{rotulo}: total {s["total"]} = {m2} x {P["m2"]} ({total})')
    ok(num(s['base'])[:1] == [P['m2']] and 'Material e mão de obra incluídos' in s['base'], f'{rotulo}: "{s["base"].strip()}"')
    ok(s['prazo'] == P['prazo'], f'{rotulo}: prazo {s["prazo"]} do plano')
    ok(s['plano'] == plano and P['nome'] in s['para'] and P['nome'] in s['legenda'], f'{rotulo}: {P["nome"]} no botão, no resumo e na legenda')
    ok([re.sub(r'^(\S.*?)(?=[A-ZÀ-Ú])', '', x, 1) for x in s['inclui']] and len(s['inclui']) == len(P['inclui'])
       and all(k in x and v in x for x, (k, v) in zip(s['inclui'], P['inclui'])), f'{rotulo}: {len(s["inclui"])} itens incluídos, texto igual ao do plano')
    ok(not s['split'], f'{rotulo}: sem barra de divisão material x mão de obra')
    ok(s['href'] == f'/obrigado?c=simulador&a={plano}&m2={m2}', f'{rotulo}: href {s["href"]}')
    esperado = f'Plano: {P["nome"]}\nApartamento: {m2} m²\nValor estimado: R$ {total:,}'.replace(',', '.')
    ok(esperado in s['msg'] and f'Prazo estimado: {P["prazo"]}' in s['msg'], f'{rotulo}: mensagem de WhatsApp com plano, metragem, valor e prazo')
    return s


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME)
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
        pg = await ctx.new_page()
        erros = []
        pg.on('console', lambda m: m.type == 'error' and erros.append(m.text))
        pg.on('pageerror', lambda e: erros.append(str(e)))
        await pg.goto(URL, wait_until='load')
        await pg.wait_for_timeout(1200)
        D = json.loads(await pg.evaluate('document.getElementById("sim-dados").textContent'))
        M = D['metragem']
        ids = [x['id'] for x in D['planos']]

        print('\n[simulador, computador]')
        await confere(pg, D, M['inicial'], D['inicial'], 'inicial')
        for m2 in (20, 60, 300):
            await pg.fill('#sim-m2', str(m2)); await pg.press('#sim-m2', 'Enter')
            for pid in ids:
                await pg.click(f'.seg__b[data-plano="{pid}"]')
                s = await confere(pg, D, m2, pid, f'{m2} m² {pid}')
                ok(s['foto'] == D['fotos'][s['amb']][ids.index(pid)]['b'], f'{m2} m² {pid}: foto {s["foto"]}')
        await pg.click(f'.seg__b[data-plano="{D["inicial"]}"]')
        await pg.fill('#sim-m2', '999'); await pg.press('#sim-m2', 'Enter')
        await confere(pg, D, M['max'], D['inicial'], 'acima da faixa (999)')
        await pg.fill('#sim-m2', '5'); await pg.press('#sim-m2', 'Enter')
        await confere(pg, D, M['min'], D['inicial'], 'abaixo da faixa (5)')
        await pg.fill('#sim-m2', ''); await pg.press('#sim-m2', 'Enter')
        await confere(pg, D, M['min'], D['inicial'], 'campo vazio mantém o último valor')
        await pg.evaluate('''() => { const r = document.querySelector('.ctl__range'); r.value = 120; r.dispatchEvent(new Event('input', {bubbles:true})); }''')
        await confere(pg, D, 120, D['inicial'], 'barra em 120')
        for amb, nome in D['ambientes']:
            await pg.click(f'.tabs__b[data-amb="{amb}"]')
            await pg.wait_for_timeout(900)
            s = await estado(pg)
            ok(s['amb'] == amb and nome in s['legenda'], f'ambiente {amb}: aba e legenda')
            ok(s['foto'].startswith(f'rf-{amb}'), f'ambiente {amb}: foto {s["foto"]}')
        fotos = await pg.evaluate('[...document.querySelectorAll(".sim__palco img")].filter(i => i.complete && !i.naturalWidth).length')
        ok(fotos == 0, 'nenhuma foto quebrada no simulador')
        n_on = await pg.evaluate('document.querySelectorAll(".sim__palco img.on").length')
        ok(n_on == 1, f'só uma foto acesa no palco ({n_on})')
        await pg.click('.pad .btn[data-plano="premium"]')
        await pg.wait_for_timeout(900)
        ok((await estado(pg))['plano'] == 'premium', '"Simular neste plano" no cartão Premium muda o simulador')

        print('\n[ponte /obrigado]')
        await pg.route('**/wa.me/**', lambda r: r.abort())
        href = await pg.get_attribute('.sim__cta', 'href')
        msg = await pg.evaluate('document.querySelector(".sim__cta").dataset.msg')
        await pg.click('.sim__cta')
        await pg.wait_for_timeout(600)
        go = await pg.get_attribute('#go', 'href')
        ok(go.startswith('https://wa.me/') and urllib.parse.unquote(go.split('text=')[1]) == msg, 'obrigado monta o wa.me com a mensagem guardada')
        await pg.goto(URL + href.lstrip('/'), wait_until='load')
        await pg.wait_for_timeout(300)
        go2 = await pg.get_attribute('#go', 'href')
        ok(urllib.parse.unquote(go2.split('text=')[1]) == msg, 'sem sessionStorage, a /obrigado refaz a mesma mensagem pela URL')
        print('    mensagem:\n      ' + msg.replace('\n', '\n      '))

        print('\n[antes e depois, mouse e teclado]')
        await pg.goto(URL, wait_until='load')
        await pg.wait_for_timeout(4200)   # passa o balanço inicial
        box = await pg.evaluate('(() => { const r = document.querySelector(".cmpr").getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; })()')
        x, y, wd, ht = box
        p0 = await pg.evaluate('getComputedStyle(document.querySelector(".cmpr")).getPropertyValue("--p")')
        ok(abs(float(p0.strip().rstrip('%')) - 50) < 1.5, f'posição inicial volta a 50% depois do balanço ({p0.strip()})')
        await pg.mouse.move(x + wd / 2, y + ht / 2); await pg.mouse.down()
        await pg.mouse.move(x + wd * 0.25, y + ht / 2, steps=8); await pg.mouse.up()
        p1 = await pg.evaluate('getComputedStyle(document.querySelector(".cmpr")).getPropertyValue("--p")')
        ok(abs(float(p1.strip().rstrip('%')) - 25) < 2, f'arraste com mouse até 25% ({p1.strip()})')
        await pg.focus('.cmpr__handle'); await pg.keyboard.press('ArrowRight'); await pg.keyboard.press('Shift+ArrowRight')
        p2 = await pg.evaluate('getComputedStyle(document.querySelector(".cmpr")).getPropertyValue("--p")')
        ok(abs(float(p2.strip().rstrip('%')) - 38) < 2, f'teclado: seta direita e shift+seta somam 13 ({p2.strip()})')
        ok(await pg.get_attribute('.cmpr__handle', 'aria-valuenow') == '38', 'aria-valuenow acompanha')

        print('\n[celular, toque]')
        await ctx.close()
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
        pg = await ctx.new_page()
        pg.on('console', lambda m: m.type == 'error' and erros.append(m.text))
        pg.on('pageerror', lambda e: erros.append(str(e)))
        await pg.goto(URL, wait_until='load')
        await pg.wait_for_timeout(4200)
        cdp = await ctx.new_cdp_session(pg)
        box = await pg.evaluate('(() => { const r = document.querySelector(".cmpr").getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; })()')
        x, y, wd, ht = box
        async def toque(pontos):
            await cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': pontos[0][0], 'y': pontos[0][1]}]})
            for px, py in pontos[1:]:
                await cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': px, 'y': py}]})
                await pg.wait_for_timeout(30)
            await cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        cx, cy = x + wd / 2, y + ht / 2
        await toque([(cx, cy), (cx + 20, cy), (cx + 60, cy), (x + wd * 0.8, cy)])
        await pg.wait_for_timeout(200)
        p3 = await pg.evaluate('getComputedStyle(document.querySelector(".cmpr")).getPropertyValue("--p")')
        ok(abs(float(p3.strip().rstrip('%')) - 80) < 3, f'arraste com toque até 80% ({p3.strip()})')
        y0 = await pg.evaluate('scrollY')
        await toque([(cx, cy + 60), (cx, cy + 20), (cx, cy - 40), (cx, cy - 160), (cx, cy - 260)])
        await pg.wait_for_timeout(500)
        y1 = await pg.evaluate('scrollY')
        p4 = await pg.evaluate('getComputedStyle(document.querySelector(".cmpr")).getPropertyValue("--p")')
        ok(y1 > y0 + 40, f'toque vertical sobre a foto rola a página ({y0} -> {y1})')
        ok(abs(float(p4.strip().rstrip('%')) - float(p3.strip().rstrip('%'))) < 3, f'e não mexe no puxador ({p4.strip()})')

        print('\n[celular, simulador na mesma tela]')
        await pg.evaluate('document.querySelector("#simulador").scrollIntoView()')
        await pg.wait_for_timeout(600)
        r = await pg.evaluate('(() => { const t = document.querySelector(".sim__total").getBoundingClientRect(); const c = document.querySelector(".seg").getBoundingClientRect(); return [t.top, t.bottom, c.top, c.bottom, innerHeight]; })()')
        ok(r[1] <= r[4] and r[3] <= r[4], f'total (até {r[1]:.0f}px) e botões de plano (até {r[3]:.0f}px) cabem em {r[4]}px')
        await pg.tap('.seg__b[data-plano="premium"]')
        await confere(pg, D, M['inicial'], 'premium', 'toque no plano Premium')
        lateral = await pg.evaluate('document.documentElement.scrollWidth > innerWidth')
        ok(not lateral, 'sem rolagem lateral no celular')
        await ctx.close()
        await b.close()
    ok(not erros, f'console limpo ({erros[:3]})')
    print(f'\n{len(falhas)} falha(s)')
    sys.exit(1 if falhas else 0)

asyncio.run(main())
