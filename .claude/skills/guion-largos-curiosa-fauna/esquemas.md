# Esquemas animados (Explainroo) — guía para el guionista

Resumen de la API de Explainroo 0.6 (MIT, github.com/vincentsch/explainroo) con nuestras
reglas de estilo. Ejemplo completo y probado:
`datos/largos/esquemas/20261121-elefantes-guerra/pasillos/` (cópialo como plantilla).

No puedes ejecutar Explainroo: el código tiene que funcionar a la primera. Usa solo lo que
aparece aquí y en el ejemplo. Si un esquema falla al montar, el vídeo usa el material de
respaldo de esas escenas, pero ese esquema se pierde.

## Archivos
`datos/largos/esquemas/<id del brief>/<nombre>/`
- `script.md`:
  ```
  # Título

  ## <nombre>
  [#inicio] Texto exacto de la narración de las escenas... [#otra] ...sigue el texto.
  ```
  Una sola sección `## <nombre>`. Quitando los marcadores `[#algo]`, el texto debe ser
  **idéntico** a la `narracion` de esas escenas unidas por un espacio (el control lo comprueba).
  Los marcadores van justo delante de la palabra en la que debe pasar algo.
- `scenes.js`: `export default { <nombre>(s) { ... } };` con una sola función.
  El sistema pone el resto: 1920x1080, fondo oscuro (look `midnight`), sin música ni
  marca de agua, nuestra voz.

## Estilo del canal
- Fondo oscuro. Colores fijos con significado: un bando o grupo en rojo `#c8463a`, el otro en
  gris `#a8a399`; azul `#5b9bd5` para un tercer elemento; amarillo `#f4c430` para lo que hay
  que mirar; texto claro `#f1ece2`; secundario `#b4aea2`.
- **Rótulos arriba** (y = 112, centrados, tamaño 56, máx. 6 palabras): abajo van los
  subtítulos del vídeo. Nada importante por debajo de y = 930.
- Un rótulo cada vez: el anterior sale con `exit: 'none'` cuando entra el siguiente (ver la
  función `rotulo` del ejemplo). `*palabra*` sale en amarillo con `mark`.
- Esquemas sencillos: pocas piezas grandes que se mueven con sentido. Todo `sfx: false`.
- Nada de emojis. Formas con `s.draw` (canvas) o `s.box`/`s.circle`/`s.arrow`/`s.icon`.

## Tiempo
La función se llama en **cada fotograma**; `s.t` son los segundos desde el inicio.
- `at` / `out` de cualquier elemento: segundos (`2.5`), un marcador (`'#carga'`) o una palabra
  dicha (`'muro'`; mejor marcadores para que no falle).
- `s.time('#marca')` → segundos de ese marcador.
- `s.p(at, dur = 0.6, ease = 'inOut')` → progreso 0..1 desde `at` durante `dur` s
  (para mover cosas: `x: s.lerp(100, 800, s.p('#avanza', 3))`).
- `s.lerp(a, b, p)`, `s.clamp(v, lo, hi)`, `s.ease.out(p)`, `s.ease.inOut(p)`.

## Elementos
Opciones comunes: `at`, `out`, `enter` (`fade`, `pop`, `rise`, `draw`, `write`, `none`),
`exit` (`fade`, `none`…), `dur`, `outDur`, `color`, `opacity`, `scale`, `id`, `sfx: false`,
`overlap: true` (si se solapa a propósito).
- `s.text(str, { x, y, size, font: 'display'|'body', align: 'left'|'center'|'right', color, mark, maxWidth })`
- `s.box(label, { x, y, w, h, color, fill, radius })`, `s.circle({ x, y, r, color, fill, label })`
- `s.arrow(from, to, { color, width, headSize, label, bend, dashed })` con `[x, y]` o un `id`
- `s.line([[x1, y1], [x2, y2]], { color, width, dashed })`, `s.path('M… C…', { color, width, fill })`
- `s.icon('nombre-lucide', { x, y, size, color, label })` (p. ej. `sun`, `eye`, `fish`, `bird`,
  `waves`, `mountain`, `swords`, `shield`, `footprints`, `paw-print`, `thermometer`,
  `droplet`, `clock`). No hay icono de elefante ni de la mayoría de animales: dibújalos.
- `s.draw({ x, y, at, out, enter, box: { x: 0, y: 0, w, h } }, (ctx, life) => { ... })`:
  canvas 2D con el origen en (x, y). `life.local` = segundos desde `at`. Para piezas que se
  mueven, recalcula `x`/`y` en cada fotograma (como el elefante del ejemplo).
- `s.annotate(idOCaja, { type: 'circle'|'underline'|'highlight', color, at })`

## Cámara
`s.camera([{ at: 0, x: 960, y: 540, zoom: 1 }, { at: '#detalle', x, y, zoom: 1.4, dur: 2 }])`
como primera línea. Con zoom los textos de los bordes se salen: acerca solo al final, cuando ya
no hacen falta los rótulos. `s.camera([])` = cámara fija.

## Comprobación
- [ ] Texto de script.md sin marcadores = narración de las escenas.
- [ ] La función de scenes.js se llama igual que el esquema.
- [ ] Todos los marcadores usados en scenes.js existen en script.md.
- [ ] Nada fuera del cuadro 1920x1080 salvo lo que entra o sale a propósito.
