---
name: guion-shorts-curiosa-fauna
description: Escribe los guiones (briefs JSON) de los Shorts de Curiosa Fauna a partir de la biblioteca de momentos verificada. Usar en la sala de redacción semanal o cuando se pida escribir, revisar o mejorar un short del canal. Cubre los cuatro formatos de la prueba A/B (por_que, comparativa, mito, tarjeta), el gancho, la estructura, el estilo en español de España y el formato exacto del brief que consume cf/montaje_short.py.
---

# Guiones de Shorts — Curiosa Fauna

Antes de escribir, lee también:
- `youtube-scriptwriting` (instalada): principios de retención. Aquí se adaptan a Shorts.
- `verificacion-fauna`: ningún dato entra en un guion sin pasar su protocolo.

## Regla de oro: el clip manda
Se escribe **sobre lo que se ve**. Primero eliges momentos de la biblioteca
(`python -m cf.biblioteca --resumen`), después buscas el dato que explica ESO.
Si el dato es fantástico pero ningún clip lo muestra, no sirve para un short.

## Lo que decide si un Short vive
1. **0–2 s, no deslizar.** El primer plano es el más impactante del material y el
   gancho en pantalla se lee sin sonido. Objetivo: que más del 70 % se quede.
2. **Una sola idea**, ritmo constante, un plano nuevo cada 3–4 s.
3. **Recompensa** al final: el dato más sorprendente se guarda para el cierre.
4. **Bucle**: la última frase conecta con la primera para invitar a volver a verlo.

## Los cuatro formatos (prueba A/B: rotar en partes iguales)
| formato | nombre en el canal | gancho en pantalla | estructura |
|---|---|---|---|
| `por_que` | ¿Sabías que…? con voz | «¿Por qué…?» / «¿Cómo…?» sobre algo que se VE | pregunta → explicación en 2 pasos → giro final |
| `comparativa` | Comparativa | «X contra Y» / «3 animales que…» | presentación rápida → criterio concreto → ganador sorprendente |
| `mito` | ¿Verdad o mentira? | «¿Mito o realidad?» + creencia popular | creencia → qué dice la ciencia → matiz inesperado |
| `tarjeta` | ¿Sabías que…? en tarjeta (sin voz) | titular corto, p. ej. «¿Sabías que…?» o «Esto NO es una avispa» | texto que se lee en pantalla sobre un vídeo o foto horizontal |

### Formato `tarjeta`
- Sin voz: se LEE. Va el campo `texto_tarjeta` (30–60 palabras) en lugar de `guion`.
- Primera frase = el gancho («Esto **no es una avispa**.»). Después 2–3 datos encadenados y
  un cierre con la cifra más sorprendente.
- Marca con `**así**` 3–5 palabras clave (se pintan en colores). No resaltes frases enteras.
- 1–3 planos: aquí funcionan muy bien las **fotos** (FOTO en la biblioteca) y los vídeos
  horizontales tranquilos. `desde`/`hasta` de una foto = segundos que se ve (2–12).
- Ideal para animales con buena foto pero poco vídeo, y para identificar especies concretas
  (las fotos de iNaturalist indican la especie exacta en la ficha).

## Estilo
- Español de España, tuteo, frases cortas, verbos activos. Nada de «increíble» vacío:
  la sorpresa la ponen los datos.
- 55–75 palabras de locución (20–30 s). Cifras con palabras si son cortas («tres corazones»).
- Gancho en pantalla: máximo 6 palabras, sin nombres propios innecesarios.
- Prohibido: dramatizar sufrimiento animal, antropomorfizar con datos falsos,
  afirmaciones sin fuente, clickbait que el vídeo no cumple.
- No repetir animal + ángulo de un short publicado en los últimos 60 días.

## Elegir planos
- 4–6 planos de 2–3 clips, primero el de `momento_destacado` más llamativo.
- Las líneas FOTO de la biblioteca son fotografías: puedes usarlas también en los formatos
  con voz (1–2 por short como mucho, 2–4 s cada una); se animan con un barrido lento.
- Usa los tramos `escenas` de la biblioteca: `desde`/`hasta` dentro de una escena.
- Evita clips con `problemas` graves (marca de agua, personas, texto) salvo que no haya otro.
- Puedes repetir un clip con tramos distintos; no repitas el mismo tramo.

## Formato del brief (datos/shorts/pendientes/AAAAMMDD-N-animal.json)
```json
{
  "id": "20261116-1-pulpo",
  "formato": "por_que",
  "animal": "pulpo",
  "gancho_pantalla": "¿Cómo desaparece un pulpo?",
  "guion": "Texto exacto de la locución… (en tarjeta: \"texto_tarjeta\" con **resaltados**)",
  "datos": [{"afirmacion": "…", "fuentes": ["url1", "url2"], "verificado": true}],
  "planos": [{"clave": "pexels:31496835", "desde": 3.0, "hasta": 8.5, "nota": "por qué este plano"}],
  "titulo": "Título con palabra clave al principio (máx. 70 caracteres)",
  "descripcion": "1–2 frases con el dato principal.",
  "etiquetas": ["pulpo", "animales", "curiosidades"]
}
```
Los créditos de los clips los añade el publicador a partir de la biblioteca: no los escribas.

## Lista de comprobación antes de guardar
- [ ] Cada afirmación del guion está en `datos` con 2 fuentes independientes.
- [ ] El primer plano es el visualmente más fuerte y coincide con el gancho.
- [ ] Lo que dice la voz se corresponde con lo que se ve en cada plano.
- [ ] 55–75 palabras (tarjeta: 30–60); el gancho se entiende sin sonido.
- [ ] Formato asignado según la rotación de la semana.
