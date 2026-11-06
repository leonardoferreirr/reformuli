# Reformuli Reformas

Site estático da Reformuli (reforma de apartamento novo em três padrões, simulador e franquia). Uma empresa do Massuo Group.

## Rodar

```bash
python3 tools/fotos.py      # converte as fotos de ~/dev/_massuo-imagens/geradas para webp (reexecutável)
python3 build.py            # monta index.html, franquia.html, obrigado.html, robots, sitemap, llms.txt
python3 tools/serve.py 4240 # http://127.0.0.1:4240
python3 tools/testar.py     # testa simulador, arraste e ponte /obrigado no Chromium próprio
python3 tools/shots.py <pasta> [url]   # capturas em 1440 e 390
```

## Onde mexer

Tudo que é dado mora no topo do `build.py`:

- `DOMINIO`, `INDEXAR`, `WHATSAPP`, `INSTAGRAM`.
- Simulador: `PLANOS` (nome, valor por m², prazo, perfil e lista do incluído, do arquivo do Paulo), `ITENS_A_VALIDAR` (box, louças e metais e marcenaria, decisão do Leonardo até o Paulo validar), `PRECOS_CONFIRMADOS` (False mostra "Valores de exemplo, a confirmar"), `DIVISAO` (None; com percentuais, mostra material x mão de obra), `METRAGEM`, `FOTOS_SIM`, `FRASE_ESTIMATIVA`.
- `IMAGENS`: lista única de fotos (base e alt). O `tools/fotos.py` lê daqui.
- `OBRAS`: ordem da galeria. `PASSOS`, `ETAPAS_FRANQUIA`, `MODELOS`, `FRANQUIA_RECEBE`, `FRANQUIA_PERFIL`.
- Constantes "a confirmar com o Paulo": `PAPELADA_PELA_REFORMULI`, `VISITA_GRATUITA`, `PASSOS`, `ETAPAS_FRANQUIA`.

Os textos ficam em `_src/`. O CSS é `assets/css/site.css` (o build minifica e injeta no `<head>`). O JS é `assets/js/site.js` (carimbado com hash no build).

## Pendências para o Paulo

Validar box, louças e metais e marcenaria em cada plano (`ITENS_A_VALIDAR`); divisão material x mão de obra, se quiser mostrar; se o orçamento fechado sai depois da visita técnica e se ela é gratuita; o que o franqueado recebe e perfil; se a Reformuli entrega o plano de reforma e a ART/RRT ao síndico; WhatsApp, Instagram, unidades e fotos reais de obra.
