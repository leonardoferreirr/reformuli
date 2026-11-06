#!/usr/bin/env python3
"""Converte as fotos da Reformuli para o site. Pode rodar quantas vezes quiser.

    python3 tools/fotos.py            # converte o que existir, pula o que já está em dia
    python3 tools/fotos.py --forcar   # reconverte tudo

A lista de imagens é a constante IMAGENS do build.py (um lugar só). Para cada base:
~/dev/_massuo-imagens/geradas/<base>.png  ->  assets/img/<base>-900.webp e <base>-1600.webp.
O que ainda não chegou é listado no fim, e o site segue funcionando sem ele.

Também copia os logos de ~/dev/_massuo-imagens/logos e gera favicon (transparente),
apple-touch-icon (preto com o símbolo dourado) e a imagem de compartilhamento (og-image.jpg).
"""
import subprocess, sys
from pathlib import Path
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from build import IMAGENS, ORIGEM, LOGOS, IMG  # noqa: E402

FORCAR = "--forcar" in sys.argv
LARGURAS = ((1600, 82), (900, 80))   # (largura, qualidade webp)
LOGO_MAP = {   # nome na pasta de logos -> nome no site
    "reformuli-preto.svg": "logo-preto.svg",
    "reformuli-dourado.svg": "logo-dourado.svg",
    "reformuli-branco.svg": "logo-branco.svg",
    "reformuli-simbolo.svg": "favicon.svg",
    "reformuli-simbolo-preto.svg": "simbolo-preto.svg",
}


def converter(base):
    png = ORIGEM / f"{base}.png"
    if not png.exists():
        return False
    feitos = 0
    with Image.open(png) as im:
        im = im.convert("RGB")
        for w, q in LARGURAS:
            dest = IMG / f"{base}-{w}.webp"
            if dest.exists() and not FORCAR and dest.stat().st_mtime >= png.stat().st_mtime:
                continue
            h = round(im.height * w / im.width)
            im.resize((w, h), Image.LANCZOS).save(dest, "WEBP", quality=q, method=6)
            feitos += 1
            print(f"  {dest.name}: {dest.stat().st_size // 1024} KB")
    if not feitos:
        print(f"  {base}: em dia")
    return True


def logos():
    IMG.mkdir(parents=True, exist_ok=True)
    for origem, dest in LOGO_MAP.items():
        src = LOGOS / origem
        if not src.exists():
            print(f"  ! logo faltando: {src}")
            continue
        svg = src.read_text()
        (IMG / dest).write_text(svg)
    # favicon-32.png transparente e apple-touch-icon com fundo preto (os únicos com fundo)
    simbolo = IMG / "favicon.svg"
    if simbolo.exists():
        subprocess.run(["magick", "-background", "none", "-density", "600", str(simbolo), "-resize", "32x32",
                        "-gravity", "center", "-extent", "32x32", str(IMG / "favicon-32.png")], check=True)
        subprocess.run(["magick", "-background", "none", "-density", "600", str(simbolo), "-resize", "116x116",
                        "-gravity", "center", "-background", "#14110C", "-extent", "180x180", str(IMG / "apple-touch-icon.png")], check=True)
        print("  favicon-32.png e apple-touch-icon.png")
    # og-image.jpg: preto com o logo dourado, 1200x630
    logo = IMG / "logo-dourado.svg"
    if logo.exists():
        subprocess.run(["magick", "-background", "none", "-density", "400", str(logo), "-resize", "760x",
                        "-gravity", "center", "-background", "#14110C", "-extent", "1200x630", "-quality", "88",
                        str(IMG / "og-image.jpg")], check=True)
        print("  og-image.jpg")


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    logos()
    faltam = []
    for base in IMAGENS:
        if not converter(base):
            faltam.append(base)
    if faltam:
        print("\n  Ainda não chegaram (o site funciona sem elas):")
        for b in faltam:
            print(f"    - {b}.png")
    print("\n  Agora rode: python3 build.py")


if __name__ == "__main__":
    main()
