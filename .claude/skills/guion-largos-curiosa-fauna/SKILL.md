---
name: guion-largos-curiosa-fauna
description: Escribe el guion (brief JSON) de un vídeo largo de Curiosa Fauna (8–10 minutos, publicado los días 1, 11 y 21). Usar en la sala de redacción de largos o cuando se pida escribir, revisar o mejorar un vídeo largo del canal. Cubre estructura de retención, capítulos, escenas con su petición de imagen, miniatura, estilo y el formato exacto que consumen cf/material_largo.py y cf/montaje_largo.py.
---

# Guiones de vídeos largos — Curiosa Fauna

Lee también `verificacion-fauna` (todo dato con 2 fuentes) y `youtube-scriptwriting`
(principios de retención).

## Diferencia con los Shorts
En los Shorts el clip manda. En los largos manda la **historia**: primero se escribe el guion
y después el sistema busca material para cada escena. Por eso cada escena debe pedir una
imagen **que exista con facilidad** en bancos gratuitos (Pexels, Pixabay, Wikimedia,
iNaturalist): animales reales haciendo cosas comunes, paisajes, primeros planos.
Evita pedir cosas imposibles de encontrar («un elefante con armadura en una batalla»):
cuéntalas con la voz y pide un plano que acompañe («elephant walking dust slow motion»).

## Estructura (8–10 minutos, 1.100–1.500 palabras de locución)
1. **Gancho (0–30 s):** la imagen o el dato más potente, una pregunta abierta y la promesa
   del vídeo. Nada de «hola, bienvenidos».
2. **4–6 capítulos** con título corto. Cada capítulo responde a una pregunta y termina con
   una pregunta nueva (re-gancho) para que siga viendo.
3. **Cada 60–90 s** un pico: un dato sorprendente, una cifra o un giro.
4. **Cierre:** responde la pregunta del gancho, resume en una frase y pide la suscripción
   de forma natural, ligada al tema («si te ha sorprendido esto, en el canal hay…»).

## Escenas
- Una escena = 1–3 frases de locución (12–45 palabras, 5–15 s).
- Entre 50 y 90 escenas en total.
- `visual.busqueda`: 2–5 palabras **en inglés**, como se buscaría en un banco de vídeo.
- `visual.describe`: en español, qué debe verse (lo usa el juez de visión para aceptar o no un clip).
- `visual.animal` y `visual.cientifico`: si la escena es de una especie concreta.
- `visual.tipo`: `video` (por defecto), `foto` (especies raras o detalles anatómicos) o
  `mapa`/`texto` (un rótulo grande sobre fondo: cifras clave, fechas, lugares).
- `rotulo` (opcional): texto corto en pantalla (máx. 6 palabras) para cifras o nombres.
- Varía los planos: general, medio, detalle. No pidas el mismo plano dos escenas seguidas.

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
  "id": "20261121-elefantes-guerra",
  "fecha_publicacion": "2026-11-21",
  "tema": "Elefantes de guerra en la Antigüedad",
  "titulo": "Elefantes de guerra: el tanque del mundo antiguo",
  "descripcion": "2–4 frases con el resumen y la promesa del vídeo.",
  "etiquetas": ["elefantes", "historia", "animales"],
  "miniatura": {"texto": "EL PRIMER TANQUE", "busqueda": "elephant portrait close up", "animal": "elefante"},
  "capitulos": [{"titulo": "Introducción", "escena": 0}, {"titulo": "Los orígenes", "escena": 6}],
  "escenas": [
    {"narracion": "Hace más de dos mil años…",
     "visual": {"tipo": "video", "busqueda": "elephant walking savanna", "describe": "elefante caminando por la sabana", "animal": "elefante", "cientifico": "Elephantidae"},
     "rotulo": ""}
  ],
  "datos": [{"afirmacion": "…", "fuentes": ["url1", "url2"], "verificado": true}]
}
```
El sistema añade después `planos` a cada escena, los créditos y la locución: no los escribas.

## Comprobación antes de guardar
- [ ] 1.100–1.500 palabras, 50–90 escenas, 4–6 capítulos (el primero en la escena 0).
- [ ] Cada afirmación verificable está en `datos` con 2 fuentes independientes.
- [ ] Cada `busqueda` es realista para un banco de vídeo gratuito.
- [ ] El gancho funciona sin contexto y el cierre responde a su pregunta.
