# v-signals: Cambios y convenciones

Bitacora de patrones adoptados durante la creacion de `v-signals.html` y `v-signals-es.html`. Usar como plantilla cuando se cree una nueva presentacion del mismo estilo (`v-foo`, `v-bar`, etc.).

---

## 0. Pareja bilingue + directorio propio

Toda presentacion vive en su **propio directorio** dentro de `docs/`, como pareja:

```
docs/v-NAME/
  v-NAME.html              (ingles, dialecto principal)
  v-NAME-es.html           (español, gemelo)
  v-NAME-notes-en.md       (fuente de verdad notas EN)
  v-NAME-notes-es.md       (fuente de verdad notas ES)
  v-NAME-cambios.md        (este archivo: bitacora estructural)
  v-NAME-aclaraciones.md   (opcional: FAQ para Q&A)
  inject-notes.py          (script local notas .md ↔ HTML)
  images/                  (imagenes propias + fondos compartidos copiados)
  video/                   (videos del deck)
  extras/                  (iframes interactivos y otros assets)
```

Cada presentacion es **self-contained**: si comparte un asset con otra (ej. `background-code.png`), se **copia**, no se referencia con `../`. Evita acoplamientos al mover/publicar decks por separado.

Regla: **cualquier cambio estructural en una se propaga a la otra en el mismo turno**. Las diferencias solo son linguisticas (traduccion).

Diferencias intencionales documentadas:
- En el slide del video, el orden de `<source>` se invierte: `-es.html` carga primero el `.mp4` español, `.html` carga primero el `.webm` ingles.
- En `-es.html` el caption del video lleva `(doblado al español)`.

---

## 1. Speaker notes en `.md` con `inject-notes.py`

**Fuente de verdad:** las notas se editan en `v-NAME-notes-{en,es}.md`. Nunca a mano en el HTML.

**Formato del `.md`:**

```markdown
# Speaker notes for v-NAME-es.html

_Auto-extracted from `v-NAME-es.html`: edit me, then run `./inject-notes.py es`._

## Slide 1: Titulo del slide

- Primer parrafo de la nota.
- Segundo parrafo.
- Tercer parrafo.

## Slide 2: ...
```

Cada bullet (`- `) se convierte en un `<p>` dentro de `<aside class="notes">`. El emparejamiento es **por orden secuencial** (slide N en el `.md` → N-esimo `<aside>` en el HTML). El titulo despues del `—` es decorativo, el script lo ignora.

**Renderizado en el HTML:**

```html
<aside class="notes">
  <p>Primer parrafo de la nota.</p>
  <p>Segundo parrafo.</p>
  <p>Tercer parrafo.</p>
</aside>
```

Un `<p>` por linea = un parrafo separado en la vista del presenter (tecla `S` de Reveal.js).

**Script:** `inject-notes.py` en el mismo directorio.

```bash
./inject-notes.py es               # inyecta v-signals-notes-es.md en v-signals-es.html
./inject-notes.py en               # inyecta v-signals-notes-en.md en v-signals.html
./inject-notes.py all              # ambos
./inject-notes.py extract es       # bootstrap: extrae HTML → md (sobrescribe el md)
./inject-notes.py extract all      # ambos
```

El round-trip extract → inject es **lossless** (verificado con diff).

**Para añadir una presentacion nueva al script:** editar las constantes `LANG_TO_HTML` y `LANG_TO_MD` al principio de `inject-notes.py`.

---

## 2. Stack base

- **Reveal.js 5** vía CDN jsdelivr
- Tema `black.css` + Monokai para syntax highlight
- Plugins: `RevealHighlight`, `RevealNotes`
- Slide nativo de Reveal: **960×700 px** (no usar `vh`, Reveal escala el slide entero)
- Config: `hash: true`, `transition: 'slide'`, `slideNumber: true`, `center: true`, `controlsLayout: 'edges'`
- Atajos numericos (`keyboard: {49: Reveal.slide(2), ...}`) para saltar a las section dividers

## 3. Paleta de colores

```css
background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)
text:       #e6edf3
muted:      #8899aa
accent:     #00d2ff (cyan) y #1676f3 (azul)
code:       #a5d6ff
red:        #f87171 (errores, "antes")
green:      #34d399 ("despues", server)
amber:      #fbbf24 (computed, channel)
blue:       #60a5fa (signal, browser)
```

## 4. Componentes visuales reutilizables

- **`.gradient-text`**: texto con gradiente blanco-azul en palabras clave del titulo
- **`.card`** + **`.three-cards`**: tarjeta de cristal esmerilado (3 columnas tipicas)
- **`.dx-grid`** + **`.dx-card`**: grid de iconos con hover translateY
- **`.section-divider`**: slide de transicion con numero gigante semi-transparente al fondo
- **`.timeline`** + **`.tl-item`**: fila horizontal de tarjetas año/nombre/nota
- **`.before-after`** + **`.ba-bad`** + **`.ba-good`**: comparacion side-by-side con borde rojo/verde
- **`.prim-badge`** + variantes `prim-signal`/`prim-computed`/`prim-effect`: etiquetas tipo "chip" con codigo monoespaciado
- **`.multi-user`** + **`.mu-browser`** + **`.mu-server`**: diagrama browser ↔ server
- **`.bg-rotated`**: clase para fondo de imagen ligeramente girado en el slide titulo

## 5. Talk progress bar

Barra fija en el bottom con N segmentos (uno por parte de la charla). El JS `updateTalkProgress(slideIndex)` activa el segmento actual segun el indice de slide. Cada presentacion ajusta los rangos:

```js
if (slideIndex >= 2 && slideIndex <= 6) part = 1;
else if (slideIndex >= 7 && slideIndex <= 12) part = 2;
else if (slideIndex >= 13 && slideIndex <= 18) part = 3;
else if (slideIndex >= 19) part = 4;
```

## 6. Iframes interactivos (`extras/`)

Iframes con animaciones paso a paso viven en `extras/` con altura tipica de **520px**. Patron del JS:

- Boton **Next** + atajos `ArrowRight`/`Space`/`Enter`
- Array `steps[]` con `caption`, `show[]`, `arrows[]`, `highlight[]`, etc.
- Step dots en la parte inferior
- Caption fijo al pie

Ejemplos: `extras/signals-pipeline.html`. (Convencion: el directorio se llamaba `specs/` en versiones antiguas; ahora `extras/` para no confundir con specs tecnicas.)

## 7. Slide de video embebido

Reveal escala el slide a 960×700 fijos. Por eso el video usa **pixeles fijos**, no `vh`:

```css
.video-slide .video-wrap { display: flex; justify-content: center; }
.video-slide video {
  max-height: 540px;     /* 700 - titulo ~80 - caption ~40 - margenes */
  max-width: 100%;
  object-fit: contain;
  border-radius: 12px;
}
```

Usar `<source>` con ambos formatos (mp4 ES y webm EN); orden distinto en cada idioma para que el doblaje correcto cargue por defecto.

JS extra: pausar todos los `<video>` que no estan en el slide actual al hacer `slidechanged`.

## 8. Convenciones de contenido

- **Section dividers** numerados (1, 2, 3, 4) con titulo corto y subtitulo opcional.
- **Talk progress bar** con etiquetas en el idioma del archivo.
- **Codigo side-by-side**: cuando hay equivalencia entre dos lenguajes (JS vs Java), poner cada uno en columna con `<h3>` pequeñito de cabecera (amber para JS, green para Java).
- **Iframes** se usan para los conceptos que se benefician de animacion paso a paso (arquitectura, ciclos, propagacion).
- **Video** al final, despues del contenido tecnico.

## 9. Companion `aclaraciones.md`

Documento separado con preguntas/respuestas detalladas que no caben en speaker notes pero pueden surgir en Q&A. Se mantiene a mano. Ejemplo: `v-signals-aclaraciones.md` cubre que es Knockout, glitch-free, TC39, etc.

---

## Historial de cambios v-signals

- **Speaker notes a `.md`** + `inject-notes.py` con extract/inject. `<p>` por parrafo.
- **Multi-user diagram**: cambiado de "Browser 1/2/3" a "User 1/2/3" / "Usuario 1/2/3" porque vendia mejor el caso (gente, no pestañas).
- **Timeline TC39**: añadido "(ECMA)" y "fase 1/4" (vs "Stage 1") para clarificar.
- **Slide 14 titulo**: "Vaadin's twist" / "La solución de Vaadin" (cambiado desde "giro" que sonaba raro en español).
- **Slide 13 card**: "Naive push" / "Observable clásico" (cambiado desde "Push ingenuo" que sonaba peyorativo).
- **Slide 5 Pull card**: añadido "(React, Preact, Vue 2)" para mostrar que comparten modelo.
- **Slide 6 timeline 2022**: cambiado "Preact" → "@preact/signals" (es la libreria, no el framework Preact).
- **Slide del video**: titulo simplificado a "Video" / "Vídeo"; CSS pasado de `vh` a `px` para no salirse del slide.
- **Slide screenshots eliminado**: redundante con el video que viene despues.
- **Slide 16 titulo**: "Hello world with Vaadin Signals" / "El Hola Mundo con Vaadin Signals".
- **Refactor de directorio**: movido de `docs/v-learn/` a `docs/v-signals/` propio, self-contained.
- **`specs/` → `extras/`**: renombrado el subdirectorio de iframes para no confundir con specs tecnicas.
- **Estilo de `<blockquote>`**: sin comillas dobles envolventes, cada frase en su linea separada por `<br/>` con bullet `&middot;` al inicio. El borde izquierdo azul ya identifica visualmente que es una cita.
- **Em-dash a colon**: en todos los HTML/MD se cambia ` — ` (em-dash con espacios) por `: `. Solo se preservan los em-dashes al inicio de linea (atribuciones tipo "&mdash; Autor").
- **Estilo de `.caption`**: tamaño aumentado a `0.7em` (de `0.55em`), margen superior a `1.2em` (de `0.3em`) para separar visualmente del bloque previo. Frases separadas por `<br/>` igual que los blockquotes.
