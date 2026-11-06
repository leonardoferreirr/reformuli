#!/usr/bin/env python3
"""Monta o site da Reformuli Reformas a partir de _src/ e gera os arquivos da raiz.

    python3 tools/fotos.py   # converte as fotos de ~/dev/_massuo-imagens/geradas (rodar antes, e de novo quando chegarem mais)
    python3 build.py

- Junta head, cabeçalho e rodapé em cada página (index, franquia, obrigado).
- Minifica assets/css/site.css e injeta no <head>.
- Carimba site.js com o hash do conteúdo (o Vercel guarda /assets/ em cache por um ano).
- Gera robots.txt, sitemap.xml, llms.txt, o schema (JSON-LD) e ajusta o vercel.json.

Tudo que é dado do negócio mora aqui em cima. O que ainda falta do cliente está marcado
com [A PREENCHER], e o que a Reformuli faria mas o Paulo não confirmou está em constante
com o comentário "a confirmar com o Paulo".
"""
import hashlib, json, re
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).parent
SRC = RAIZ / "_src"
CSS = RAIZ / "assets/css/site.css"
JS = RAIZ / "assets/js/site.js"
IMG = RAIZ / "assets/img"
ORIGEM = Path.home() / "dev/_massuo-imagens/geradas"   # PNGs gerados; tools/fotos.py converte para webp
LOGOS = Path.home() / "dev/_massuo-imagens/logos"

# ---------------------------------------------------------------- dados da empresa
DOMINIO = "https://reformuli.vercel.app"   # [A PREENCHER] domínio próprio quando o Paulo registrar
VERCEL = "reformuli.vercel.app"
INDEXAR = False                             # True só quando o domínio estiver ligado na Vercel
WHATSAPP = "5524998593556"                  # só dígitos com DDI; o mesmo nos três sites até o Paulo passar outro
INSTAGRAM = ""                              # [A PREENCHER] perfil da Reformuli
SITE_GRUPO = "https://massuogroup.vercel.app"
SITE_CITYSTEEL = "https://citysteel.vercel.app"
SITE_MULTIHALL = "https://multihall.vercel.app"
OG_BASE = DOMINIO if INDEXAR else f"https://{VERCEL}"
ROBOS_IA = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
            "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "CCBot", "meta-externalagent"]

# ---------------------------------------------------------------- simulador
# Planos, valores por m², prazos, perfis e listas vieram do Paulo em 05/11/2026
# (~/dev/_massuo-imagens/cliente/planos-reformuli.md). Texto das listas copiado como está.
PRECOS_CONFIRMADOS = True        # False volta a mostrar "Valores de exemplo, a confirmar" junto do resultado
# O valor por m² já cobre material e mão de obra; o cliente não mandou percentual. Se mandar, por exemplo
# DIVISAO = dict(material=58, mao_de_obra=42), o simulador passa a mostrar a divisão com barra.
DIVISAO = None
METRAGEM = dict(min=20, max=300, inicial=60)   # m² úteis; fora da faixa o simulador trava no limite
PLANO_INICIAL = "confort"
PLANOS = [
    dict(id="essencial", nome="Reformuli Essencial", curto="Essencial", m2=832, prazo="30 a 40 dias",
         perfil="clientes que desejam deixar o apartamento pronto para morar ou alugar, com acabamento simples e funcional.",
         inclui=[("Piso", "Cerâmica ou porcelanato econômico"), ("Paredes", "Pintura acrílica branca"),
                 ("Banheiro", "Revestimento cerâmico básico"), ("Cozinha", "Revestimento nas áreas molhadas"),
                 ("Gesso", "Acabamento simples, sem decoração"), ("Iluminação", "Plafons LED básicos"),
                 ("Rodapé", "PVC ou cerâmico"), ("Mão de obra", "Equipe completa de instalação")]),
    dict(id="confort", nome="Reformuli Confort", curto="Confort", m2=1332, prazo="40 a 50 dias",
         perfil="famílias que procuram um apartamento moderno, confortável e com melhor acabamento.",
         inclui=[("Piso", "Porcelanato ou vinílico de qualidade"), ("Paredes", "Pintura premium e parede decorativa"),
                 ("Banheiro", "Porcelanato e nicho"), ("Cozinha", "Revestimento moderno"),
                 ("Gesso", "Forro parcial com cortineiro"), ("Iluminação", "Spots e LED"),
                 ("Rodapé", "Poliestireno"), ("Portas", "Pintura e acabamento"), ("Mão de obra", "Equipe especializada")]),
    dict(id="premium", nome="Reformuli Premium", curto="Premium", m2=2165, prazo="50 a 65 dias",
         perfil="clientes que desejam uma estética sofisticada e valorização do imóvel.",
         inclui=[("Piso", "Porcelanato premium de grandes formatos"), ("Paredes", "Pintura premium e revestimentos decorativos"),
                 ("Banheiro", "Porcelanato, nichos e metais sofisticados"), ("Cozinha", "Revestimentos especiais"),
                 ("Gesso", "Forro completo com iluminação indireta"), ("Iluminação", "Projeto de LED e spots"),
                 ("Rodapé", "Poliestireno premium"), ("Acabamentos", "Detalhes decorativos e paredes especiais"),
                 ("Mão de obra", "Equipe especializada de alto padrão")]),
]
AMBIENTES = [("sala", "Sala"), ("cozinha", "Cozinha"), ("banheiro", "Banheiro")]
# foto de cada ambiente em cada plano, na ordem de PLANOS (Essencial, Confort, Premium).
# Se uma faltar, o simulador usa a mais próxima do mesmo ambiente e o build avisa.
FOTOS_SIM = {
    "sala": ["rf-sala-1b", "rf-sala-2", "rf-sala-3"],
    "cozinha": ["rf-cozinha-1", "rf-cozinha-2", "rf-cozinha-3"],
    "banheiro": ["rf-banheiro-1", "rf-banheiro-2", "rf-banheiro-3"],
}
# a confirmar com o Paulo: o orçamento fechado sai mesmo depois de uma visita técnica?
FRASE_ESTIMATIVA = "Valor estimado pela metragem. O orçamento fechado sai depois da visita técnica."
FRASE_EXEMPLO = "Valores de exemplo, a confirmar."
FRASE_INCLUSO = "Material e mão de obra incluídos."
# não veio do Paulo: decisão do Leonardo até ele validar. As fotos mostram box, louças e marcenaria, então essas
# linhas entram na lista de cada plano (depois das linhas do arquivo do Paulo) para a foto e a lista baterem.
ITENS_A_VALIDAR = {
    "essencial": [("Box", "Vidro temperado padrão"), ("Louças e metais", "Linha básica"), ("Marcenaria", "Armários básicos de cozinha")],
    "confort": [("Box", "Vidro com perfil slim"), ("Louças e metais", "Linha intermediária"), ("Marcenaria", "Cozinha sob medida")],
    "premium": [("Box", "Vidro sob medida sem perfil"), ("Louças e metais", "Linha premium"), ("Marcenaria", "Projeto completo sob medida")],
}
for _p in PLANOS:
    _p["inclui"] = list(_p["inclui"]) + ITENS_A_VALIDAR.get(_p["id"], [])

# ---------------------------------------------------------------- imagens (lista única; tools/fotos.py lê daqui)
# base -> alt. O PNG de origem é ORIGEM/<base>.png; sai <base>-900.webp e <base>-1600.webp em assets/img.
# rf-sala-0 e rf-sala-1 ficaram desalinhadas e não entram.
IMAGENS = {
    "rf-sala-0b": "Sala de apartamento recém-entregue pela construtora: paredes brancas, contrapiso cinza e fios no teto",
    "rf-sala-1b": "Sala no plano Reformuli Essencial: piso claro e pintura branca",
    "rf-sala-2": "Sala no plano Reformuli Confort: porcelanato, parede decorativa e forro com cortineiro",
    "rf-sala-3": "Sala no plano Reformuli Premium: porcelanato de grande formato, revestimento decorativo e iluminação indireta",
    "rf-cozinha-1": "Cozinha no plano Reformuli Essencial: revestimento nas áreas molhadas",
    "rf-cozinha-2": "Cozinha no plano Reformuli Confort: revestimento moderno e LED",
    "rf-cozinha-3": "Cozinha no plano Reformuli Premium: revestimentos especiais e iluminação indireta",
    "rf-banheiro-1": "Banheiro no plano Reformuli Essencial: revestimento cerâmico básico",
    "rf-banheiro-2": "Banheiro no plano Reformuli Confort: porcelanato e nicho",
    "rf-banheiro-3": "Banheiro no plano Reformuli Premium: porcelanato, nichos e metais sofisticados",
    "rf-fachada": "Fachada de uma loja Reformuli Reformas, com letreiro dourado e amostras de pedras na vitrine",
    "rf-equipe": "Equipe da Reformuli de uniforme preto assentando piso e instalando forro num apartamento novo",
    "rf-capacete": "Engenheira da Reformuli de capacete, com a planta do apartamento no tablet, num apartamento novo",
    "rf-showroom": "Showroom da Reformuli com amostras de porcelanato, madeira e pedras",
    "rf-homeoffice": "Mesa de trabalho em casa com notebook mostrando a marca Reformuli, planta e amostras de acabamento",
    "rf-chaves": "Casal com as chaves na mão, no apartamento novo ainda vazio",
}
# galeria de obras: a ordem é a de exibição; só entra o que existir em assets/img
OBRAS = ["rf-sala-3", "rf-cozinha-3", "rf-banheiro-2", "rf-sala-2", "rf-equipe", "rf-cozinha-2", "rf-banheiro-3",
         "rf-sala-1b", "rf-cozinha-1", "rf-banheiro-1"]
OBRAS_MAX = 6

# ---------------------------------------------------------------- regras e processo
# A Reformuli prepara o plano de reforma e a ART ou RRT e entrega ao síndico pelo cliente?
PAPELADA_PELA_REFORMULI = False   # a confirmar com o Paulo
# A visita técnica é gratuita?
VISITA_GRATUITA = False           # a confirmar com o Paulo
# a confirmar com o Paulo: como a obra realmente anda do primeiro contato à entrega
PASSOS = [
    ("Simulação", "Você coloca a metragem, escolhe o plano e já vê o valor estimado, aqui no site, sem deixar telefone."),
    ("Visita técnica", "A equipe vai ao apartamento, confere o que a construtora entregou e fecha o orçamento por escrito."),
    ("Obra", "Material e mão de obra num contrato só, com cronograma combinado antes de começar."),
    ("Entrega", "Vistoria final com você e o apartamento pronto para a mudança."),
]

# ---------------------------------------------------------------- franquia
MODELOS = [
    dict(id="loja", nome="Loja ou escritório", preco="R$ 80.000", img=("rf-fachada",),
         texto="Para quem quer um ponto físico na região, com atendimento presencial e amostras à mão."),
    dict(id="home", nome="Home office", preco="R$ 8.000", img=("rf-homeoffice", "rf-capacete", "rf-equipe"),
         texto="Para começar com estrutura leve, atendendo pelo WhatsApp e no apartamento do cliente."),
]
FRANQUIA_RECEBE = ["[A PREENCHER] o que o franqueado recebe (treinamento, material, suporte, sistema)"]
FRANQUIA_PERFIL = "[A PREENCHER] perfil do franqueado"
# a confirmar com o Paulo
ETAPAS_FRANQUIA = [
    ("Conversa", "Você manda cidade e modelo de interesse e o time de expansão apresenta o negócio."),
    ("Circular de Oferta", "Você recebe a Circular de Oferta de Franquia, com regras e números, para avaliar com calma."),
    ("Contrato", "Assinatura do contrato e definição do ponto, ou do home office."),
    ("Implantação", "Treinamento, material e abertura da unidade com o suporte da Reformuli."),
]

ARROW = '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 8h11M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.5"/></svg>'
ZAP = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 1.8a8.2 8.2 0 1 1-4.2 15.3l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 0 1 12 3.8zm-3.3 4.4c-.2 0-.5 0-.7.3-.3.3-1 1-1 2.4s1 2.8 1.2 3c.1.2 2 3.2 5 4.4 2.5 1 3 .8 3.5.7.6-.1 1.8-.7 2-1.4.2-.7.2-1.3.2-1.4-.1-.1-.3-.2-.6-.3l-2-1c-.3-.1-.5-.2-.7.1l-1 1.2c-.2.2-.3.2-.6.1-.3-.2-1.3-.5-2.4-1.5-.9-.8-1.5-1.8-1.7-2.1-.2-.3 0-.5.1-.6l.5-.5.3-.5v-.5l-.9-2.2c-.2-.5-.5-.5-.7-.5h-.5z"/></svg>')


# ---------------------------------------------------------------- imagens
def existe(base):
    return (IMG / f"{base}-1600.webp").exists()


def primeira(*bases):
    """A primeira imagem da lista que já foi convertida, ou None."""
    for b in bases:
        if b and existe(b):
            return b
    return None


def medida(base):
    try:
        from PIL import Image
        with Image.open(IMG / f"{base}-1600.webp") as im:
            return im.size
    except Exception:
        return (1600, 900)


def img(base, alt=None, sizes="(max-width:860px) 92vw, 46vw", lazy=True, cls=""):
    """<img> responsivo a partir de base-900.webp e base-1600.webp. Sem a imagem, devolve vazio e avisa."""
    if not existe(base):
        print(f"  ! imagem faltando: {base} (rodar tools/fotos.py quando o PNG chegar)")
        return ""
    w, h = medida(base)
    alt = IMAGENS.get(base, "") if alt is None else alt
    p900 = (IMG / f"{base}-900.webp").exists()
    attrs = f'src="/assets/img/{base}-1600.webp"'
    if p900:
        attrs += f' srcset="/assets/img/{base}-900.webp 900w, /assets/img/{base}-1600.webp {w}w" sizes="{sizes}"'
    lz = ' loading="lazy"' if lazy else ' fetchpriority="high"'
    c = f' class="{cls}"' if cls else ""
    return f'<img{c} {attrs} alt="{alt}" width="{w}" height="{h}"{lz} decoding="async">'


def preload(base, sizes):
    if not existe(base):
        return ""
    w = medida(base)[0]
    return (f'<link rel="preload" as="image" imagesrcset="/assets/img/{base}-900.webp 900w, /assets/img/{base}-1600.webp {w}w" '
            f'imagesizes="{sizes}" fetchpriority="high">')


# ---------------------------------------------------------------- simulador
def brl(v):
    return "R$ " + f"{int(round(v)):,}".replace(",", ".")


def total_de(m2, plano):
    """metragem x valor por m², sem arredondar: é o número que o cliente confere na calculadora."""
    return m2 * plano["m2"]


def divisao(total):
    """(material, mão de obra) quando DIVISAO existe; o material arredonda a R$ 10 e o resto fecha a soma."""
    if not DIVISAO:
        return None
    mat = int(round(total * DIVISAO["material"] / 100.0 / 10.0)) * 10
    return mat, total - mat


def inclui_html(plano):
    return "".join(f"<li><b>{k}</b>{v}</li>" for k, v in plano["inclui"])


def sim_dados():
    """JSON lido pelo site.js e pela /obrigado: planos, metragem, fotos disponíveis."""
    fotos = {}
    for amb, _nome in AMBIENTES:
        lista = FOTOS_SIM[amb]
        tem = [i for i, b in enumerate(lista) if existe(b)]
        if not tem:
            print(f"  ! simulador: nenhuma foto de {amb}; o ambiente fica fora das abas")
            continue
        por_plano = []
        for i, b in enumerate(lista):
            if i in tem:
                j = i
            else:
                j = min(tem, key=lambda k: (abs(k - i), -k))
                print(f"  ! simulador: {b} faltando, {amb}/{PLANOS[i]['curto'].lower()} usa {lista[j]} por enquanto")
            base = lista[j]
            w, h = medida(base)
            por_plano.append({"b": base, "w": w, "h": h, "alt": IMAGENS.get(base, ""), "aprox": j != i})
        fotos[amb] = por_plano
    dados = {
        "planos": [{"id": p["id"], "nome": p["nome"], "curto": p["curto"], "m2": p["m2"], "prazo": p["prazo"],
                    "perfil": p["perfil"], "inclui": [[k, v] for k, v in p["inclui"]]} for p in PLANOS],
        "divisao": DIVISAO, "metragem": METRAGEM, "inicial": PLANO_INICIAL,
        "ambientes": [[a, n] for a, n in AMBIENTES if a in fotos], "fotos": fotos,
        "confirmado": PRECOS_CONFIRMADOS, "estimativa": FRASE_ESTIMATIVA, "exemplo": FRASE_EXEMPLO, "incluso": FRASE_INCLUSO,
    }
    return json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def sim_inicial():
    """Estado inicial já renderizado no HTML, para a página nascer com números e foto, sem depender do JS."""
    p = next(x for x in PLANOS if x["id"] == PLANO_INICIAL)
    m2 = METRAGEM["inicial"]
    total = total_de(m2, p)
    amb0 = next((a for a, _ in AMBIENTES if any(existe(b) for b in FOTOS_SIM[a])), None)
    foto = ""
    if amb0:
        idx = [x["id"] for x in PLANOS].index(PLANO_INICIAL)
        lista_f = FOTOS_SIM[amb0]
        tem = [i for i, b in enumerate(lista_f) if existe(b)]
        j = idx if idx in tem else min(tem, key=lambda k: (abs(k - idx), -k))
        foto = img(lista_f[j], sizes="(max-width:860px) 92vw, 52vw", cls="on")
    div = divisao(total)
    split = ""
    if div:
        split = (f'<div class="split" aria-hidden="true"><i style="--w:{DIVISAO["material"]}%"></i></div>'
                 f'<dl class="sim__parts"><div><dt>Material <small>({DIVISAO["material"]}%)</small></dt><dd class="num" data-k="mat">{brl(div[0])}</dd></div>'
                 f'<div><dt>Mão de obra <small>({DIVISAO["mao_de_obra"]}%)</small></dt><dd class="num" data-k="mo">{brl(div[1])}</dd></div></dl>')
    return {
        "SIM_M2": str(m2), "SIM_PLANO_NOME": p["nome"], "SIM_TOTAL": brl(total), "SIM_M2_VALOR": brl(p["m2"]),
        "SIM_PRAZO": p["prazo"], "SIM_PERFIL": p["perfil"], "SIM_INCLUI": inclui_html(p), "SIM_FOTO": foto,
        "SIM_SPLIT": split, "SIM_AMB_NOME": dict(AMBIENTES).get(amb0, "Ambiente"),
        "SIM_EXEMPLO": "" if PRECOS_CONFIRMADOS else f' <span class="sim__exemplo">{FRASE_EXEMPLO}</span>',
        "FRASE_INCLUSO": FRASE_INCLUSO,
        "SIM_DADOS": f'<script type="application/json" id="sim-dados">{sim_dados()}</script>',
    }


def sim_planos():
    out = []
    for p in PLANOS:
        on = ' aria-pressed="true"' if p["id"] == PLANO_INICIAL else ' aria-pressed="false"'
        out.append(f'<button type="button" class="seg__b" data-plano="{p["id"]}"{on}><b>{p["curto"]}</b>'
                   f'<small>{brl(p["m2"])} por m²</small></button>')
    return "".join(out)


def sim_ambientes():
    out = []
    first = True
    for a, n in AMBIENTES:
        if not any(existe(b) for b in FOTOS_SIM[a]):
            continue
        on = ' aria-pressed="true"' if first else ' aria-pressed="false"'
        first = False
        out.append(f'<button type="button" class="tabs__b" data-amb="{a}"{on}>{n}</button>')
    return "".join(out)


# ---------------------------------------------------------------- blocos
def planos_cards():
    out = []
    for i, p in enumerate(PLANOS):
        base = primeira(FOTOS_SIM["sala"][i], *FOTOS_SIM["sala"][::-1])
        foto = img(base, sizes="(max-width:860px) 92vw, 44vw") if base else ""
        out.append(
            f'<article class="pad" id="plano-{p["id"]}" style="--i:{i}">'
            f'<div class="pad__ph">{foto}</div>'
            f'<div class="pad__txt"><h3>{p["nome"]}</h3>'
            f'<p class="pad__m2">{brl(p["m2"])} <small>por m². {FRASE_INCLUSO}</small></p>'
            f'<p class="pad__prazo">Prazo estimado: {p["prazo"]}</p>'
            f'<p class="pad__perfil">Para {p["perfil"]}</p>'
            f'<ul class="pad__lista">{inclui_html(p)}</ul>'
            f'<a class="btn btn--pri" href="#simulador" data-plano="{p["id"]}">Simular neste plano {ARROW}</a>'
            f'</div></article>')
    return "\n        ".join(out)


def passos(lista):
    return "\n        ".join(
        f'<li class="step rv" data-d="{min(i,3)}"><b>0{i+1}</b><div><h3>{t}</h3><p>{p}</p></div></li>'
        for i, (t, p) in enumerate(lista))


def obras_grid():
    """Mosaico: a primeira foto ocupa 2x2; com 5 fotos, a quarta alarga para a grade fechar sem buraco."""
    bases = [b for b in OBRAS if existe(b)][:OBRAS_MAX]
    out = []
    for n, base in enumerate(bases):
        sizes = "(max-width:860px) 92vw, 62vw" if n == 0 else "(max-width:860px) 92vw, 30vw"
        cls = " obra--wide" if (len(bases) == 5 and n == 3) else ""
        out.append(f'<figure class="obra{cls} rv" data-d="{min(n,3)}">{img(base, sizes=sizes)}<figcaption>{IMAGENS[base]}</figcaption></figure>')
    if len(bases) < 3:
        print(f"  ! obras: só {len(bases)} imagem(ns) na galeria")
    return "\n        ".join(out)


def modelos(completo):
    out = []
    for i, m in enumerate(MODELOS):
        base = primeira(*m["img"])
        foto = img(base, sizes="(max-width:860px) 92vw, 46vw") if base else ""
        if completo:
            cta = f'<a class="btn btn--pri" href="#form" data-modelo="{m["nome"]}">Quero este modelo {ARROW}</a>'
        else:
            cta = f'<a class="btn btn--line" href="/franquia#modelos">Ver o modelo {ARROW}</a>'
        out.append(f'<article class="model rv" data-d="{i}"><div class="model__ph">{foto}</div>'
                   f'<div class="model__body"><h3>{m["nome"]}</h3><p>{m["texto"]}</p>'
                   f'<p class="model__preco"><small>Investimento</small><strong>{m["preco"]}</strong></p>{cta}</div></article>')
    return "\n        ".join(out)


def lista(itens, cls=""):
    c = f' class="{cls}"' if cls else ""
    return f"<ul{c}>" + "".join(f"<li>{x}</li>" for x in itens) + "</ul>"


def fone():
    w = WHATSAPP
    return f"+{w[:2]} {w[2:4]} {w[4:-4]}-{w[-4:]}" if len(w) >= 12 else ""


def texto(frag):
    from html import unescape
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", frag))).strip()


def regras_papelada():
    if PAPELADA_PELA_REFORMULI:
        return "<p>A Reformuli prepara o plano de reforma e a ART ou RRT e entrega tudo ao síndico por você.</p>"
    return ""


# ---------------------------------------------------------------- SEO
def schema(nome, pg):
    """Organization (marca e franquia), HomeAndConstructionBusiness (a reforma), WebSite e WebPage.
    Os padrões entram como serviço, sem preço: os valores do simulador são estimativa."""
    S, url = DOMINIO, DOMINIO + pg["path"]
    org, neg = {"@id": f"{S}/#organizacao"}, {"@id": f"{S}/#reformas"}
    oferta = lambda n, desc, tipo, quem: {"@type": "Offer", "itemOffered": {
        "@type": "Service", "name": n, "description": desc, "serviceType": tipo, "provider": quem}}
    franquia = []
    for m in MODELOS:
        o = oferta(f"Franquia Reformuli, modelo {m['nome'].lower()}", m["texto"], "Franquia de reforma de apartamentos", org)
        o.update({"name": f"Investimento na franquia Reformuli, modelo {m['nome'].lower()}",
                  "price": re.sub(r"\D", "", m["preco"]), "priceCurrency": "BRL", "url": f"{S}/franquia#modelos",
                  "category": "Franquia", "seller": org})
        franquia.append(o)
    servicos = []
    for p in PLANOS:
        o = oferta(p["nome"], f"Para {p['perfil']} Prazo estimado: {p['prazo']}. Inclui: "
                   + "; ".join(f"{k.lower()}: {v.lower()}" for k, v in p["inclui"]) + f". {FRASE_INCLUSO} {FRASE_ESTIMATIVA}",
                   "Reforma de apartamento", neg)
        if PRECOS_CONFIRMADOS:
            o["priceSpecification"] = {"@type": "UnitPriceSpecification", "price": p["m2"], "priceCurrency": "BRL",
                                       "unitCode": "MTK", "unitText": "m²"}
        servicos.append(o)
    marca = {"@type": "Organization", **org, "name": "Reformuli Reformas", "alternateName": "Reformuli",
             "description": "Reforma de apartamentos entregues pela construtora, em três planos (Reformuli Essencial, Confort e Premium), "
                            "com simulador de valor por metro quadrado e franquia. Uma empresa do Massuo Group.",
             "url": f"{S}/", "logo": {"@type": "ImageObject", "url": f"{S}/assets/img/logo-preto.svg"},
             "image": f"{S}/assets/img/og-image.jpg", "parentOrganization": {"@type": "Organization", "name": "Massuo Group", "url": SITE_GRUPO},
             "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Franquia Reformuli", "itemListElement": franquia}}
    if INSTAGRAM:
        marca["sameAs"] = [INSTAGRAM]
    negocio = {"@type": "HomeAndConstructionBusiness", **neg, "name": "Reformuli Reformas", "parentOrganization": org,
               "description": "Reforma de apartamento novo em três planos, com material e mão de obra incluídos no valor por m².",
               "url": f"{S}/", "image": f"{S}/assets/img/og-image.jpg", "logo": f"{S}/assets/img/logo-preto.svg",
               "areaServed": {"@type": "Country", "name": "Brasil"},
               "knowsAbout": ["Reforma de apartamento", "NBR 16280", "Acabamento residencial"],
               "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Reforma de apartamento novo", "itemListElement": servicos}}
    if WHATSAPP:
        negocio["telephone"] = fone()
        marca["contactPoint"] = {"@type": "ContactPoint", "telephone": fone(), "contactType": "sales", "availableLanguage": "pt-BR"}
    pagina = {"@type": "WebPage", "@id": f"{url}#pagina", "url": url, "name": pg["title"], "description": pg["desc"],
              "isPartOf": {"@id": f"{S}/#site"}, "about": org if nome == "franquia" else neg, "inLanguage": "pt-BR",
              "primaryImageOfPage": {"@type": "ImageObject", "url": f"{S}/assets/img/og-image.jpg", "width": 1200, "height": 630}}
    grafo = [marca, negocio, {"@type": "WebSite", "@id": f"{S}/#site", "url": f"{S}/", "name": "Reformuli Reformas",
                              "inLanguage": "pt-BR", "publisher": org}, pagina]
    if pg["path"] != "/":
        pagina["breadcrumb"] = {"@id": f"{url}#trilha"}
        grafo.append({"@type": "BreadcrumbList", "@id": f"{url}#trilha", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Início", "item": f"{S}/"},
            {"@type": "ListItem", "position": 2, "name": pg["trilha"], "item": url}]})
    js = json.dumps({"@context": "https://schema.org", "@graph": grafo}, ensure_ascii=False, separators=(",", ":"))
    return '<script type="application/ld+json">' + js.replace("</", "<\\/") + "</script>"


def llms():
    S = DOMINIO
    lin = ["# Reformuli Reformas", "",
           "> Reforma de apartamento entregue pela construtora, em três planos (Reformuli Essencial, Confort e Premium), com simulador "
           "de valor por metro quadrado no site. Material e mão de obra incluídos. Também é uma franquia: "
           + " ou ".join(f"{m['nome'].lower()} ({m['preco']})" for m in MODELOS) + ". Uma empresa do Massuo Group.", "",
           "## Em poucas palavras", "",
           "- Empresa: Reformuli Reformas, do Massuo Group (com a City Steel, que constrói, e a Multihall, que fornece material).",
           "- O que faz: reforma de apartamento novo em três planos, com piso, paredes, banheiro, cozinha, gesso, iluminação, rodapé e mão de obra.",
           "- Valor por metro quadrado: " + "; ".join(f"{p['nome']} {brl(p['m2'])}" for p in PLANOS)
           + f". O total é a metragem vezes o valor do plano. {FRASE_INCLUSO} {FRASE_ESTIMATIVA}" + ("" if PRECOS_CONFIRMADOS else f" {FRASE_EXEMPLO}"),
           "- Prazo estimado: " + "; ".join(f"{p['curto']} {p['prazo']}" for p in PLANOS) + ".",
           "- As fotos do site são ilustrativas.",
           "- Unidades: a rede está começando; o site pergunta a cidade do cliente pelo WhatsApp.",
           "- Franquia: " + "; ".join(f"{m['nome'].lower()}, investimento de {m['preco']}" for m in MODELOS) + ".",
           f"- Contato: WhatsApp {fone()}." if WHATSAPP else "- Contato: pelo formulário do site.",
           "", "## Os três planos", ""]
    for p in PLANOS:
        lin += [f"### {p['nome']} ({brl(p['m2'])} por m², prazo estimado {p['prazo']})", "", f"Para {p['perfil']}", ""]
        lin += [f"- {k}: {v}" for k, v in p["inclui"]]
        lin.append("")
    lin += ["## Reforma em apartamento tem regra", "",
            "- NBR 16280: antes da obra, o síndico recebe o plano de reforma e a ART (engenheiro) ou RRT (arquiteto) do responsável técnico. Pintura não exige.",
            "- NBR 17170: o que é reformado, ou feito fora da NBR 16280, perde a cobertura da garantia da construtora.",
            "", "## Como funciona", ""] + [f"{i}. **{t}.** {p}" for i, (t, p) in enumerate(PASSOS, 1)]
    lin += ["", "## Franquia Reformuli", ""]
    for m in MODELOS:
        lin += [f"- **{m['nome']}, investimento de {m['preco']}:** {m['texto']}"]
    lin += ["", "### Como virar franqueado", ""] + [f"{i}. **{t}.** {p}" for i, (t, p) in enumerate(ETAPAS_FRANQUIA, 1)]
    lin += ["", "## Páginas", "",
            f"- [Início]({S}/): simulador, padrões, regras do condomínio, obras, unidades, franquia e contato.",
            f"- [Franquia]({S}/franquia): modelos, investimento e etapas.",
            "", "## Contato", ""]
    if WHATSAPP:
        lin += [f"- WhatsApp: {fone()} (https://wa.me/{WHATSAPP})"]
    lin += [f"- Simular a reforma: {S}/#simulador", f"- Fale com a gente: {S}/#contato", f"- Ser franqueado: {S}/franquia#form",
            f"- Massuo Group: {SITE_GRUPO}", ""]
    return "\n".join(lin)


def robots_txt():
    if INDEXAR:
        corpo = "User-agent: *\nAllow: /\n\n"
    else:
        corpo = ("# Pré-lançamento (INDEXAR = False): o Google lê as páginas para ver o noindex delas,\n"
                 "# e os robôs de IA ficam fora até o domínio entrar no ar.\n"
                 "User-agent: *\nAllow: /\n\n" + "".join(f"User-agent: {b}\nDisallow: /\n\n" for b in ROBOS_IA))
    return corpo + f"Sitemap: {DOMINIO}/sitemap.xml\n"


def vercel_json():
    arq = RAIZ / "vercel.json"
    atual = arq.read_text()
    cfg = json.loads(atual)
    redir = [r for r in cfg.get("redirects", []) if not any(h.get("value") == VERCEL for h in r.get("has", []))]
    if INDEXAR and VERCEL not in DOMINIO:
        host = [{"type": "host", "value": VERCEL}]
        redir += [{"source": "/", "has": host, "destination": f"{DOMINIO}/", "permanent": True},
                  {"source": "/:path*", "has": host, "destination": f"{DOMINIO}/:path*", "permanent": True}]
    if redir:
        cfg["redirects"] = redir
    else:
        cfg.pop("redirects", None)
    cab = [h for h in cfg.get("headers", []) if not any(x["key"] == "X-Robots-Tag" for x in h["headers"])]
    if not INDEXAR:
        cab.append({"source": "/(.*)", "headers": [{"key": "X-Robots-Tag", "value": "noindex"}]})
    cfg["headers"] = cab
    if cfg != json.loads(atual):
        arq.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")


# ---------------------------------------------------------------- montagem
def minificar(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s*\n\s*", "\n", css)
    css = re.sub(r"\s*([{}:;,>])\s*", r"\1", css)
    css = re.sub(r";}", "}", css)
    css = re.sub(r"\n+", "", css)
    return css.replace("../fonts/", "/assets/fonts/").strip()


def hash_de(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()[:10] if p.exists() else "0"


PAGINAS = {
    "index": dict(
        arquivo="index.html", path="/",
        title="Reforma de apartamento novo com valor por m² | Reformuli Reformas",
        desc="Pegou as chaves? A Reformuli reforma o apartamento entregue pela construtora em três planos, a partir de R$ 832 por m², com material e mão de obra incluídos. Simule a metragem e veja o valor na hora.",
        nav_franquia="", cta=("Fale com a gente", "/#contato")),
    "franquia": dict(
        arquivo="franquia.html", path="/franquia", trilha="Franquia",
        title="Franquia de reforma de apartamentos a partir de R$ 8.000 | Reformuli",
        desc="Abra uma Reformuli na sua cidade: loja ou escritório (R$ 80.000) ou home office (R$ 8.000), com a marca, o método e os três planoes por trás.",
        nav_franquia=' aria-current="page"', cta=("Quero ser franqueado", "#form")),
    "obrigado": dict(
        arquivo="obrigado.html", path="/obrigado",
        title="Reformuli | Abrindo a conversa", desc="Estamos abrindo a conversa com a equipe da Reformuli.",
        nav_franquia="", cta=("", ""), robots="noindex,nofollow"),
}


def main():
    css = minificar(CSS.read_text())
    head_t, top_t, foot_t = (SRC / "head.html").read_text(), (SRC / "top.html").read_text(), (SRC / "foot.html").read_text()
    pre_home = "\n".join(x for x in [preload("rf-sala-3", "(max-width:860px) 92vw, 1320px"),
                                     preload("rf-sala-0b", "(max-width:860px) 92vw, 1320px")] if x)
    PAGINAS["index"]["preload"] = pre_home
    PAGINAS["franquia"]["preload"] = preload(primeira("rf-fachada") or "", "(max-width:860px) 92vw, 1320px") if primeira("rf-fachada") else ""
    PAGINAS["obrigado"]["preload"] = ""
    blocos = {
        "ARROW": ARROW, "ZAP": ZAP, "WHATSAPP": WHATSAPP, "ANO": str(date.today().year),
        "SITE_GRUPO": SITE_GRUPO, "SITE_CITYSTEEL": SITE_CITYSTEEL, "SITE_MULTIHALL": SITE_MULTIHALL,
        "PLANOS_CARDS": planos_cards(), "PASSOS": passos(PASSOS), "ETAPAS_FRANQUIA": passos(ETAPAS_FRANQUIA),
        "OBRAS": obras_grid(), "MODELOS_HOME": modelos(False), "MODELOS_FULL": modelos(True),
        "FRANQUIA_RECEBE": lista(FRANQUIA_RECEBE, "recebe__lista"), "FRANQUIA_PERFIL": FRANQUIA_PERFIL,
        "SIM_PLANOS": sim_planos(), "SIM_AMBIENTES": sim_ambientes(), "REGRAS_PAPELADA": regras_papelada(),
        "FRASE_ESTIMATIVA": FRASE_ESTIMATIVA,
        "IMG_ANTES": img("rf-sala-0b", sizes="(max-width:860px) 92vw, 1320px", lazy=False, cls="cmpr__img"),
        "IMG_DEPOIS": img("rf-sala-3", sizes="(max-width:860px) 92vw, 1320px", lazy=False, cls="cmpr__img"),
        "IMG_UNIDADES": img(primeira("rf-showroom", "rf-chaves", "rf-equipe") or "", sizes="(max-width:860px) 92vw, 46vw"),
        "IMG_FRANQUIA": img(primeira("rf-fachada") or "", sizes="100vw"),
        "IMG_COMO": img(primeira("rf-capacete") or "", sizes="(max-width:860px) 92vw, 34vw"),
        "IMG_CONTATO": img(primeira("rf-chaves") or "", sizes="(max-width:860px) 92vw, 40vw"),
        "IMG_REGRAS": img(primeira("rf-capacete", "rf-equipe") or "", sizes="(max-width:860px) 92vw, 40vw"),
        "IMG_FHERO": img(primeira("rf-fachada") or "", sizes="(max-width:860px) 92vw, 1320px", lazy=False),
        "PRECOS_AVISO": "" if PRECOS_CONFIRMADOS else FRASE_EXEMPLO,
    }
    blocos.update(sim_inicial())
    jsv = hash_de(JS)
    mudou = set()
    for nome, pg in PAGINAS.items():
        robots = pg.get("robots") or ("index,follow,max-image-preview:large" if INDEXAR else "noindex,nofollow")
        head = (head_t.replace("{{CSS}}", css).replace("{{TITLE}}", pg["title"]).replace("{{DESC}}", pg["desc"])
                .replace("{{URL}}", DOMINIO + pg["path"]).replace("{{DOMINIO}}", DOMINIO).replace("{{ROBOTS}}", robots)
                .replace("{{OG_BASE}}", OG_BASE).replace("{{PRELOAD}}", pg["preload"])
                .replace("{{SCHEMA}}", schema(nome, pg) if nome != "obrigado" else ""))
        top = (top_t.replace("{{NAV_FRANQUIA}}", pg["nav_franquia"])
               .replace("{{TOP_CTA}}", pg["cta"][0]).replace("{{TOP_CTA_HREF}}", pg["cta"][1]))
        foot = foot_t.replace("{{JSV}}", jsv)
        html = (SRC / f"{nome}.html").read_text()
        html = html.replace("{{HEAD}}", head).replace("{{TOP}}", top).replace("{{FOOT}}", foot)
        for k, v in blocos.items():
            html = html.replace("{{" + k + "}}", v)
        # sem o que o franqueado recebe confirmado pelo Paulo, a seção não vai ao ar com marcador à vista
        if "[A PREENCHER]" in " ".join(FRANQUIA_RECEBE) + FRANQUIA_PERFIL:
            html = re.sub(r"\s*<!--RECEBE-->.*?<!--/RECEBE-->", "", html, flags=re.S)
        sobra = re.findall(r"\{\{[A-Z_0-9]+\}\}", html)
        if sobra:
            print(f"  ! {nome}: marcadores sem valor {sorted(set(sobra))}")
        if "—" in html:
            print(f"  ! {nome}: travessão no HTML gerado")
        destino = RAIZ / pg["arquivo"]
        if not destino.exists() or destino.read_text() != html:
            mudou.add(pg["path"])
            destino.write_text(html)
        print(f"  {pg['arquivo']}: {len(html.encode())/1024:.1f} KB")
    (RAIZ / "robots.txt").write_text(robots_txt())
    mapa = RAIZ / "sitemap.xml"
    antes = dict(re.findall(r"<loc>https?://[^/<]+(/[^<]*)</loc><lastmod>([\d-]+)</lastmod>", mapa.read_text())) if mapa.exists() else {}
    hoje = date.today().isoformat()
    urls = "".join(f"  <url><loc>{DOMINIO}{p}</loc><lastmod>{hoje if p in mudou or p not in antes else antes[p]}</lastmod></url>\n"
                   for p in ["/", "/franquia"])
    mapa.write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')
    (RAIZ / "llms.txt").write_text(llms())
    vercel_json()
    print(f"  site.js v={jsv}  indexar={INDEXAR}  precos_confirmados={PRECOS_CONFIRMADOS}  whatsapp={'sim' if WHATSAPP else 'NÃO'}")


if __name__ == "__main__":
    main()
