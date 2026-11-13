/* Reformuli: núcleo do site, sem dependência. Menu, revelações, antes e depois,
   simulador, linha dos passos e formulários que viram mensagem de WhatsApp. */
(() => {
  const d = document, h = d.documentElement, w = window;
  const rm = w.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const brl = v => 'R$ ' + Math.round(v).toLocaleString('pt-BR');

  /* ---------- cabeçalho e menu ---------- */
  const top = d.querySelector('.top'), burger = d.querySelector('.burger');
  if (burger) burger.addEventListener('click', () => {
    const open = !h.classList.contains('menu-open');
    h.classList.toggle('menu-open', open);
    burger.setAttribute('aria-expanded', open);
    burger.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
  });
  d.querySelectorAll('.nav a').forEach(a => a.addEventListener('click', () => {
    h.classList.remove('menu-open');
    burger && burger.setAttribute('aria-expanded', 'false');
  }));

  /* âncoras da mesma página: rolagem suave e, se o link traz um padrão, o simulador muda junto */
  d.addEventListener('click', e => {
    const a = e.target.closest('a[href*="#"]');
    if (!a) return;
    const url = new URL(a.href, location.href);
    if (url.pathname.replace(/\/$/, '') !== location.pathname.replace(/\/$/, '') || !url.hash) return;
    const alvo = d.querySelector(url.hash);
    if (!alvo) return;
    e.preventDefault();
    alvo.scrollIntoView({ behavior: rm ? 'auto' : 'smooth' });
    history.replaceState(null, '', url.hash);
    if (a.dataset.plano && w.rfSim) w.rfSim.plano(a.dataset.plano);
    if (a.dataset.modelo) {
      const sel = d.querySelector('#f-modelo');
      if (sel) sel.value = a.dataset.modelo;
    }
  });

  /* ---------- revelações (com reserva: nada fica invisível) ---------- */
  const rvs = [...d.querySelectorAll('.rv')];
  const mostrar = el => el.classList.add('in');
  if ('IntersectionObserver' in w) {
    const io = new IntersectionObserver(es => es.forEach(en => {
      if (en.isIntersecting) { mostrar(en.target); io.unobserve(en.target); }
    }), { rootMargin: '0px 0px -8% 0px' });
    rvs.forEach(el => io.observe(el));
  } else rvs.forEach(mostrar);
  setTimeout(() => rvs.forEach(el => { if (el.getBoundingClientRect().top < innerHeight) mostrar(el); }), 2500);
  setTimeout(() => rvs.forEach(mostrar), 6000);

  /* ---------- bolinha do WhatsApp: entra depois do topo, para não cobrir o texto dele ---------- */
  const zap = d.querySelector('.zap');
  if (zap) {
    /* em Quem somos ela espera o texto sair da tela, para não cobrir a última linha */
    const palcoQuem = d.querySelector('.quem');
    const verZap = () => {
      const rq = palcoQuem && palcoQuem.getBoundingClientRect();
      const naQuem = rq && rq.top < innerHeight * 0.5 && rq.bottom > innerHeight * 0.92;
      zap.classList.toggle('ver', !naQuem && (w.scrollY > innerHeight * 0.45 || !d.querySelector('.hero')));
    };
    w.addEventListener('scroll', verZap, { passive: true });
    verZap();
  }

  /* ---------- antes e depois: a mesma sala, como a construtora entrega e como fica ---------- */
  const cmp = d.querySelector('.cmpr');
  if (cmp) {
    const handle = cmp.querySelector('.cmpr__handle');
    let p = 50, intro = !rm, t0 = 0, arrastando = false;
    const set = v => {
      p = Math.min(100, Math.max(0, v));
      cmp.style.setProperty('--p', p.toFixed(2) + '%');
      const r = Math.round(p);
      handle.setAttribute('aria-valuenow', r);
      handle.setAttribute('aria-valuetext', r <= 2 ? 'só a sala pronta' : r >= 98 ? 'só a sala como a construtora entrega' : `${r}% da sala como a construtora entrega`);
    };
    /* leve balanço inicial: mostra que dá para arrastar e para na primeira interação */
    const balanco = t => {
      if (!intro) return;
      if (!t0) t0 = t;
      const k = (t - t0) / 2800;
      if (k >= 1) { set(50); intro = false; return; }
      set(50 + Math.sin(k * Math.PI * 2) * 9 * (1 - k));
      requestAnimationFrame(balanco);
    };
    setTimeout(() => { if (intro) requestAnimationFrame(balanco); }, 900);
    const pos = e => set((e.clientX - cmp.getBoundingClientRect().left) / cmp.offsetWidth * 100);
    const comeca = e => {
      intro = false; arrastando = true;
      cmp.classList.add('drag');
      try { cmp.setPointerCapture(e.pointerId); } catch (_) {}
      pos(e);
    };
    /* no toque, o arraste só começa depois de um movimento horizontal: quem começa a rolar a página
       em cima da foto continua rolando, e o puxador não pula para o dedo */
    let toque = null;
    cmp.addEventListener('pointerdown', e => {
      if (e.button) return;
      if (e.pointerType === 'touch') { toque = { x: e.clientX, y: e.clientY }; return; }
      comeca(e);
    });
    cmp.addEventListener('pointermove', e => {
      if (toque) {
        const dx = Math.abs(e.clientX - toque.x), dy = Math.abs(e.clientY - toque.y);
        if (dx > 6 && dx > dy) { toque = null; comeca(e); }
        else if (dy > 6) toque = null;
        return;
      }
      if (arrastando) pos(e);
    });
    const solta = () => { arrastando = false; toque = null; cmp.classList.remove('drag'); };
    cmp.addEventListener('pointerup', solta);
    cmp.addEventListener('pointercancel', solta);
    /* o puxador tem captura implícita no toque; quando ela passa para o contêiner, o evento dele sobe e não pode encerrar o arraste */
    cmp.addEventListener('lostpointercapture', e => { if (e.target === cmp) solta(); });
    handle.addEventListener('keydown', e => {
      const passo = e.shiftKey ? 10 : 3;
      const k = { ArrowLeft: p - passo, ArrowRight: p + passo, ArrowDown: p - passo, ArrowUp: p + passo, Home: 0, End: 100 }[e.key];
      if (k === undefined) return;
      e.preventDefault(); intro = false; set(k);
    });
  }

  /* ---------- simulador ---------- */
  const sim = d.querySelector('.sim'), dadosEl = d.getElementById('sim-dados');
  if (sim && dadosEl) {
    let D = null;
    try { D = JSON.parse(dadosEl.textContent); } catch (_) {}
    if (D) {
      const raiz = d.getElementById('simulador') || sim;   /* o que está incluído fica fora do .sim, no bloco de baixo */
      const q = s => raiz.querySelector(s), qa = s => [...raiz.querySelectorAll(s)];
      const numero = q('#sim-m2'), faixa = q('.ctl__range'), palco = q('.sim__palco');
      const segs = qa('.seg__b'), tabs = qa('.tabs__b');
      const nums = {}; qa('.num').forEach(el => { nums[el.dataset.k] = el; });
      const lista = q('.sim__inclui'), cta = q('.sim__cta');
      const M = D.metragem, DIV = D.divisao;
      const st = { m2: M.inicial, plano: D.inicial, amb: (D.ambientes[0] || [])[0] };
      const planoDe = id => D.planos.find(x => x.id === id) || D.planos[0];
      const calc = () => {
        const P = planoDe(st.plano), total = st.m2 * P.m2;
        let mat = 0, mo = 0;
        if (DIV) { mat = Math.round(total * DIV.material / 100 / 10) * 10; mo = total - mat; }
        return { P, total, mat, mo };
      };
      /* números que correm: cada .num guarda o valor atual e desliza até o novo */
      const atual = {};
      const corre = (k, alvo) => {
        const el = nums[k];
        if (!el) return;
        const de = atual[k] === undefined ? alvo : atual[k];
        atual[k] = alvo;
        if (rm || de === alvo) { el.textContent = brl(alvo); return; }
        const ini = performance.now(), dur = 650;
        el.classList.add('run');
        const passo = t => {
          const k2 = Math.min(1, (t - ini) / dur), e = 1 - Math.pow(1 - k2, 3);
          el.textContent = brl(de + (alvo - de) * e);
          if (k2 < 1) requestAnimationFrame(passo); else el.classList.remove('run');
        };
        requestAnimationFrame(passo);
      };
      let fotoAtual = '';
      const foto = () => {
        const lista_ = D.fotos[st.amb];
        if (!lista_ || !palco) return;
        const idx = D.planos.findIndex(x => x.id === st.plano);
        const f = lista_[Math.max(0, idx)];
        if (!f || f.b === fotoAtual) return;
        fotoAtual = f.b;
        let im = palco.querySelector(`img[data-b="${f.b}"]`);
        if (!im) {
          im = new Image(f.w, f.h);
          im.dataset.b = f.b;
          im.src = `/assets/img/${f.b}-1600.webp`;
          im.srcset = `/assets/img/${f.b}-900.webp 900w, /assets/img/${f.b}-1600.webp ${f.w}w`;
          im.sizes = '(max-width:860px) 92vw, 52vw';
          im.alt = f.alt; im.decoding = 'async';
          palco.appendChild(im);
        } else im.dataset.b = f.b;
        const liga = () => {
          if (fotoAtual !== f.b) return;
          palco.querySelectorAll('img').forEach(x => x.classList.toggle('on', x === im));
        };
        if (im.complete && im.naturalWidth) liga();
        else { im.addEventListener('load', liga, { once: true }); im.addEventListener('error', liga, { once: true }); }
      };
      const render = () => {
        const c = calc();
        qa('.sim__m2v').forEach(el => { el.textContent = st.m2; });
        qa('.sim__pn').forEach(el => { el.textContent = c.P.nome; });
        const ambNome = (D.ambientes.find(x => x[0] === st.amb) || [])[1];
        qa('.sim__amb').forEach(el => { if (ambNome) el.textContent = ambNome; });
        corre('total', c.total);
        if (DIV) { corre('mat', c.mat); corre('mo', c.mo); }
        qa('.sim__m2valor').forEach(el => { el.textContent = brl(c.P.m2); });
        qa('.sim__prazo').forEach(el => { el.textContent = c.P.prazo; });
        if (lista) lista.innerHTML = c.P.inclui.map(i => `<li><b>${i[0]}</b>${i[1]}</li>`).join('');
        segs.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.plano === st.plano)));
        tabs.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.amb === st.amb)));
        if (faixa) { faixa.value = st.m2; faixa.style.setProperty('--f', ((st.m2 - M.min) / (M.max - M.min) * 100).toFixed(1) + '%'); }
        if (numero && d.activeElement !== numero) numero.value = st.m2;
        if (cta) {
          const linhas = ['Olá! Fiz uma simulação no site da Reformuli.', '', `Plano: ${c.P.nome}`, `Apartamento: ${st.m2} m²`,
            `Valor estimado: ${brl(c.total)} (${brl(c.P.m2)} por m², material e mão de obra incluídos)`];
          if (DIV) linhas.push(`Material: ${brl(c.mat)}`, `Mão de obra: ${brl(c.mo)}`);
          linhas.push(`Prazo estimado: ${c.P.prazo}`, '', 'Quero este orçamento.');
          cta.dataset.msg = linhas.join('\n');
          cta.href = `/obrigado?c=simulador&a=${encodeURIComponent(st.plano)}&m2=${st.m2}`;
        }
        foto();
      };
      const limpa = v => {
        const n = Math.round(parseFloat(String(v).replace(',', '.')));
        if (!isFinite(n)) return st.m2;
        return Math.min(M.max, Math.max(M.min, n));
      };
      if (faixa) faixa.addEventListener('input', () => { st.m2 = limpa(faixa.value); render(); });
      if (numero) {
        numero.addEventListener('input', () => {
          const n = Math.round(parseFloat(numero.value));
          if (!isFinite(n)) return;
          /* enquanto digita, só trava em cima: "3" ainda pode virar "30" */
          st.m2 = Math.min(M.max, Math.max(M.min, n));
          if (n > M.max) numero.value = M.max;
          render();
        });
        const fecha = () => { st.m2 = limpa(numero.value); numero.value = st.m2; render(); };
        numero.addEventListener('change', fecha);
        numero.addEventListener('blur', fecha);
        numero.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); fecha(); numero.blur(); } });
      }
      segs.forEach(b => b.addEventListener('click', () => { st.plano = b.dataset.plano; render(); }));
      tabs.forEach(b => b.addEventListener('click', () => { st.amb = b.dataset.amb; render(); }));
      if (cta) cta.addEventListener('click', () => { try { sessionStorage.setItem('rf_msg', cta.dataset.msg || ''); } catch (_) {} });
      w.rfSim = { plano(id) { if (planoDe(id).id === id) { st.plano = id; render(); } }, estado: () => ({ ...st, ...calc() }) };
      /* o HTML já nasce com os valores iniciais; aqui só sincroniza a barra e a foto */
      const c0 = calc(); atual.total = c0.total; atual.mat = c0.mat; atual.mo = c0.mo;
      const primeira = palco && palco.querySelector('img');
      if (primeira) { fotoAtual = (primeira.getAttribute('src') || '').replace(/.*\/|-1600\.webp$/g, ''); primeira.dataset.b = fotoAtual; }
      render();
    }
  }

  /* ---------- linha dos passos que preenche no scroll ---------- */
  const steps = [...d.querySelectorAll('.steps')];
  const moverSteps = () => steps.forEach(s => {
    const r = s.getBoundingClientRect();
    const p = Math.min(1, Math.max(0, (innerHeight * 0.78 - r.top) / (r.height + innerHeight * 0.1)));
    s.style.setProperty('--p', p.toFixed(3));
  });

  /* ---------- um único laço de scroll ---------- */
  let pendente = false;
  const quadro = () => {
    pendente = false;
    top && top.classList.toggle('solid', w.scrollY > 30);
    moverSteps();
  };
  const pedir = () => { if (!pendente) { pendente = true; requestAnimationFrame(quadro); } };
  w.addEventListener('scroll', pedir, { passive: true });
  w.addEventListener('resize', pedir, { passive: true });
  quadro();

  /* ---------- formulários: mensagem pronta para o WhatsApp, pela /obrigado ---------- */
  d.querySelectorAll('form.form').forEach(form => form.addEventListener('submit', e => {
    e.preventDefault();
    if (!form.reportValidity()) return;
    const f = new FormData(form), v = k => (f.get(k) || '').toString().trim();
    const fr = form.dataset.c === 'franquia';
    const linhas = [fr ? 'Olá! Quero ser franqueado Reformuli.' : 'Olá! Vim pelo site da Reformuli e quero reformar meu apartamento.',
      '', `Nome: ${v('nome')}`, `WhatsApp: ${v('whatsapp')}`, `Cidade: ${v('cidade')}`];
    if (v('metragem')) linhas.push(`Metragem: ${v('metragem')} m²`);
    if (v('modelo')) linhas.push(`Modelo: ${v('modelo')}`);
    if (v('mensagem')) linhas.push(`Mensagem: ${v('mensagem')}`);
    try { sessionStorage.setItem('rf_msg', linhas.join('\n')); } catch (_) {}
    location.href = `/obrigado?c=${encodeURIComponent(form.dataset.c || 'form')}&a=${fr ? 'franquia' : 'reforma'}`;
  }));
  /* ---------- quem somos: o texto acende palavra a palavra enquanto a seção fica parada ---------- */
  const secQuem = d.querySelector('.quem'), manif = d.querySelector('[data-manifesto]');
  const palavras = manif ? [...manif.querySelectorAll('span')] : [];
  if (secQuem) {
    if ('IntersectionObserver' in w) new IntersectionObserver(([en]) => secQuem.classList.toggle('perto', en.isIntersecting), { rootMargin: '30% 0px' }).observe(secQuem);
    else secQuem.classList.add('perto');
  }
  if (palavras.length && secQuem && !rm) {
    let acesas = -1;
    const acender = () => {
      const r = secQuem.getBoundingClientRect(), H = innerHeight, curso = r.height - H;
      const p = curso > 0 ? Math.min(1, Math.max(0, (-r.top + H * 0.12) / (curso * 0.78))) : 1;
      const n = Math.round(p * palavras.length);
      if (n !== acesas) { palavras.forEach((s, i) => s.classList.toggle('on', i < n)); acesas = n; }
    };
    w.addEventListener('scroll', acender, { passive: true });
    w.addEventListener('resize', acender);
    acender();
  } else palavras.forEach(s => s.classList.add('on'));

})();
