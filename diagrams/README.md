# Diagramas de artículo

Los gráficos que acompañan los artículos se generan desde acá, no a mano.
Este archivo explica cómo, para que se puedan rehacer en el futuro.

## Por qué así

Antes eran PNG exportados de un editor: el texto quedaba con tipografías que
no eran las de la marca, el contenido se apilaba arriba dejando un tercio del
lienzo vacío, y no había forma cómoda de corregir un número.

Ahora cada diagrama es una página HTML con el CSS de marca (Oswald para los
títulos, Latin Modern Roman para el texto, verde `#5e8f3d` sobre crema
`#fff6d5`) que el navegador renderiza a PNG. Ventajas:

- usan exactamente las tipografías y la paleta del sitio;
- se corrige un dato editando el HTML y volviendo a renderizar;
- el alto se ajusta al contenido en vez de dejar aire.

## Cómo se regeneran

```bash
# 1. compilar el sitio (los .woff2 y el CSS de marca tienen que existir)
hugo --destination /tmp/lautea-v3

# 2. renderizar
python3 -I diagrams/render.py
```

`render.py` levanta un servidor efímero en 127.0.0.1, abre Chrome con el
protocolo de DevTools, espera a que carguen las tipografías, mide el alto real
del documento y recorta la captura exacto a ese alto (a 2x, para pantallas
retina). Escribe los PNG en `assets/images/`.

Si el build está en otra carpeta, se pasa con `BUILD_DIR=/ruta`. Si Chrome no
está en la ruta por defecto de Playwright, se pasa con `CHROME=/ruta/a/chrome`.

Nota: el ancho tiene que medirse con la ventana en el mismo ancho que el
lienzo, porque `scrollHeight` nunca devuelve menos que la ventana. Por eso
`render.py` fija primero el ancho y un alto chico antes de medir.

## Archivos

| HTML | Salida | Se usa en |
|---|---|---|
| `te-verde.html` | `diagram-te-verde.png` | `content/es/como-preparar-te-verde.md` |
| `hebras-vs-saquito.html` | `diagram-hebras-vs-saquito.png` | `content/es/hebras-vs-saquito.md` |
| `green-tea.html` | `diagram-green-tea.png` | `content/en/how-to-brew-green-tea.md` |
| `loose-leaf-vs-bags.html` | `diagram-loose-leaf-vs-bags.png` | `content/en/loose-leaf-vs-tea-bags.md` |

Las páginas de producto (reloj de arena) no usan diagrama: llevan foto real.
