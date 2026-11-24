---
name: guion-largos-curiosa-fauna
description: Escribe el guion (brief JSON) de un vídeo largo de Curiosa Fauna (8–10 minutos, publicado los días 1, 11 y 21). Usar en la sala de redacción de largos o cuando se pida escribir, revisar o mejorar un vídeo largo del canal. Cubre estructura de retención, capítulos, el plan de imagen escena a escena (clip que encaje o animación propia), miniatura, estilo y el formato exacto que consumen cf/material_largo.py y cf/montaje_largo.py.
---

# Guiones de vídeos largos — Curiosa Fauna

Lee también `verificacion-fauna` (todo dato con 2 fuentes) y `youtube-scriptwriting`
(principios de retención).

## La regla que manda: nada de «clips juntos»
Un vídeo largo NO es una sucesión de planos bonitos del animal mientras habla la voz. Cada
escena tiene que **enseñar lo que se está contando**. Hay dos maneras:
1. **Un clip que muestre exactamente eso** (si se habla de una cría mamando, una cría
   mamando; no «un elefante caminando»). La visión puntúa si encaja (0-10) y solo entra con 7+.
2. **Una animación propia** (cifras que cuentan, comparativas, mapas con rutas, líneas de
   tiempo, procesos, listas, citas, titulares). Todo lo que sea una cifra, una fecha, un lugar,
   una comparación, una explicación o un hecho histórico va como animación.

Objetivo: **40–60 % de las escenas son animaciones** (mínimo 30 %, lo exige el control) y el
resto, clips que muestren lo que se cuenta. Si dudas de que exista un clip gratuito de algo
(«un elefante con armadura en una batalla», «el parto de una elefanta»), es animación.

**Elige el tema también por el material**: si del animal casi no hay vídeo bueno en Pexels,
Pixabay o Wikimedia, el vídeo quedará pobre. Mejor temas con acción grabable (caza, crías,
migraciones, comportamiento) o temas de historia/ciencia que se cuenten con animaciones.

## Estructura (8–10 minutos, 1.100–1.500 palabras de locución)
1. **Gancho (0–30 s):** la imagen o el dato más potente (una cifra animada o el mejor clip),
   una pregunta abierta y la promesa del vídeo. Nada de «hola, bienvenidos».
2. **4–6 capítulos** con título corto. Cada capítulo responde a una pregunta y termina con
   una pregunta nueva (re-gancho) para que siga viendo.
3. **Cada 60–90 s** un pico: un dato sorprendente, una cifra o un giro (buen sitio para una animación).
4. **Cierre:** responde la pregunta del gancho, resume en una frase y pide la suscripción
   de forma natural, ligada al tema («si te ha sorprendido esto, en el canal hay…»).
- Alterna: nunca más de 3 clips seguidos sin una animación, ni más de 3 animaciones seguidas.

## Escenas
- Una escena = 1–3 frases de locución (12–45 palabras, 5–15 s). Entre 50 y 90 escenas.
- **Escena de clip** (`visual.tipo`: `video`, o `foto` para especies raras/detalles):
  - `visual.busqueda`: 2–5 palabras **en inglés** como en un banco de vídeo, describiendo la
    ACCIÓN («elephant calf drinking milk», no «elephant»).
  - `visual.describe`: en español, lo que TIENE que verse para que encaje con la voz.
  - `visual.animal` y `visual.cientifico` si es de una especie concreta.
  - `respaldo` (obligatorio): la animación que sale si no hay ningún clip que lo muestre.
    Normalmente un `titular` con la idea de la frase, o la cifra/lista que cuenta esa escena.
  - `rotulo` (opcional): texto corto en pantalla (máx. 6 palabras) para nombres o cifras.
- **Escena de animación**: `"visual": {"tipo": "grafico", "grafico": {…}}`. Detrás se ve el
  último clip desenfocado, así que encaja con el resto del vídeo.

## Catálogo de animaciones (`grafico`)
Textos cortos: se leen mientras habla la voz. Todo dato que aparezca va en `datos` con fuentes.
| tipo | para qué | campos |
|---|---|---|
| `cifra` | un número que impacta (cuenta desde 0) | `valor` (número), `unidad`, `texto` (qué es), opcional `prefijo`, `decimales`, `comparar`: [{`etiqueta`, `valor`}] para ponerlo junto a otros |
| `comparativa` | tamaños, pesos, velocidades… (barras) | `titulo`, `unidad`, `items`: [{`nombre`, `valor`, `nota`?}] (2–6) |
| `linea_tiempo` | historia, evolución, etapas de la vida | `titulo`, `eventos`: [{`fecha`, `texto`}] (2–6), `destacado` (índice) |
| `mapa` | dónde vive, rutas, migraciones, batallas | `titulo`, `puntos`: [{`nombre`, `lat`, `lon`}], `rutas`: [[i, j]] (flechas de un punto a otro), `mundo`: true para el planeta entero |
| `lista` | razones, características, récords | `titulo`, `puntos`: 2–5 frases cortas |
| `proceso` | cómo funciona algo, pasos de una táctica o de un ciclo | `titulo`, `pasos`: 2–5 frases cortas |
| `cita` | lo que dijo una fuente histórica o un científico | `texto`, `autor`, `obra` |
| `titular` | una idea fuerte en grande (también como respaldo) | `texto` (máx. 8 palabras), `subtitulo` |

Ejemplos:
```json
{"tipo": "cifra", "valor": 22, "unidad": "meses", "texto": "dura el embarazo de una elefanta",
 "comparar": [{"etiqueta": "9 meses · humano", "valor": 9}]}
{"tipo": "mapa", "titulo": "La ruta de Aníbal", "puntos": [{"nombre": "Cartagena", "lat": 37.6, "lon": -0.98},
 {"nombre": "Alpes", "lat": 45.0, "lon": 6.9}, {"nombre": "Roma", "lat": 41.9, "lon": 12.5}], "rutas": [[0, 1], [1, 2]]}
{"tipo": "proceso", "titulo": "Cómo los frenaba Roma", "pasos": ["Abrir pasillos", "Dejar pasar al elefante", "Atacar al cornaca"]}
```
Los esquemas de Explainroo (`visual.tipo: "esquema"`) ya no se usan: lo mismo se hace con
`proceso`, `mapa` o `comparativa`, que son más fiables.

## Estilo
Español de España, tono de documental cercano (tuteo), frases cortas y concretas.
Prohibido: relleno («increíble», «asombroso» sin dato), sufrimiento animal gratuito,
antropomorfizar con datos falsos, afirmaciones sin fuente.

## Miniatura y título
- Título: palabra clave al principio, curiosidad sin mentir, máx. 70 caracteres.
- `miniatura.texto`: 2–4 palabras que NO repitan el título (lo complementan).
- `miniatura.busqueda`: plano del animal, de cerca, mirando a cámara si es posible.

## Formato del brief (datos/largos/pendientes/AAAAMMDD-tema.json)
```json
{
  "id": "20261201-elefantes-crias",
  "fecha_publicacion": "2026-12-01",
  "tema": "…",
  "titulo": "…",
  "descripcion": "2–4 frases con el resumen y la promesa del vídeo.",
  "etiquetas": ["elefantes", "animales"],
  "miniatura": {"texto": "22 MESES", "busqueda": "elephant calf close up", "animal": "elefante"},
  "capitulos": [{"titulo": "Introducción", "escena": 0}, {"titulo": "El embarazo más largo", "escena": 7}],
  "escenas": [
    {"narracion": "Una elefanta pasa casi dos años embarazada.",
     "visual": {"tipo": "grafico", "grafico": {"tipo": "cifra", "valor": 22, "unidad": "meses",
                "texto": "dura el embarazo de una elefanta"}}},
    {"narracion": "Y cuando nace, la cría ya pesa como un adulto humano.",
     "visual": {"tipo": "video", "busqueda": "baby elephant walking with mother",
                "describe": "una cría de elefante recién nacida junto a su madre", "animal": "elefante",
                "cientifico": "Elephantidae"},
     "respaldo": {"tipo": "cifra", "valor": 100, "unidad": "kg", "texto": "pesa un elefante al nacer"},
     "rotulo": ""}
  ],
  "datos": [{"afirmacion": "…", "fuentes": ["url1", "url2"], "verificado": true}]
}
```
El sistema añade después `planos` a cada escena, los créditos y la locución: no los escribas.

## Comprobación antes de guardar
- [ ] 1.100–1.500 palabras, 50–90 escenas, 4–6 capítulos (el primero en la escena 0).
- [ ] 40–60 % de escenas son animaciones; nunca más de 3 clips seguidos sin una.
- [ ] Cada escena de clip pide una ACCIÓN concreta que exista en bancos gratuitos y tiene `respaldo`.
- [ ] Cada cifra, fecha o lugar que sale en pantalla está en `datos` con 2 fuentes independientes.
- [ ] El gancho funciona sin contexto y el cierre responde a su pregunta.
