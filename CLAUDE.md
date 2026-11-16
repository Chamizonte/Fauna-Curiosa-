# Curiosa Fauna — guía para Claude

Canal de YouTube de divulgación sobre animales (@CuriosaFauna-y3s), en español de España.
Este repositorio produce y publica automáticamente:
- 4 Shorts al día.
- 3 vídeos largos al mes (días 1, 11 y 21).

## Principios (no negociables)
1. **Coste cero extra.** Solo se paga Claude Pro y ElevenLabs Starter (30.000 créditos/mes, reservados para vídeos largos). No añadir servicios de pago.
2. **Nada sin verificar.** Todo dato que se publique necesita al menos 2 fuentes fiables guardadas junto al guion (URL incluida).
3. **El material manda.** Primero se reúne y describe el material visual; después se escribe sobre lo que de verdad se ve.
4. **Licencias limpias.** Solo YouTube Creative Commons (CC BY), dominio público (NOAA, NPS, USFWS, NASA…), Wikimedia/Internet Archive con licencia compatible y Pexels/Pixabay. Nunca NC ni ND. Toda atribución obligatoria va en la descripción.
5. **Claude solo en tareas de criterio.** La producción diaria (descarga, montaje, render, subida) es código determinista en GitHub Actions y no usa Claude.
6. **Cambios de código por PR.** Los agentes pueden editar `playbook.yaml` y datos, pero los cambios de código se proponen en un PR para revisión humana. Nunca auto-merge.

## Mapa del repositorio
- Shorts (v2, en producción): `explorador.yml` (00:30 UTC, llena `datos/biblioteca`) →
  `sala-redaccion.yml` (02:30 UTC, Claude escribe guiones en `datos/shorts/pendientes`) →
  `publicar-short.yml` (08, 12, 16 y 20 UTC; mueve el guion a `datos/shorts/publicados`).
  Código en `cf/`, montaje en `remotion/`.
- `generador_shorts.py`: v1, solo como respaldo si no hay guion v2. `generador_video.py`: vídeos largos (v1, aún en producción).
- Vídeos largos (v2): `largo-guion.yml` (Claude escribe el guion 5 días antes) →
  material en el explorador nocturno → `largo-publicar.yml` (víspera, sube programado).
  Escenas `esquema`: dibujos animados con Explainroo (`cf/esquemas.py`,
  `datos/largos/esquemas/<id>/<nombre>/`), solo donde hay que explicar algo.
- `spikes/`: pruebas de riesgo técnicas.
- Material: no se usa YouTube (bloqueado desde Actions).

## Ahorro de tokens
- Leer solo los ficheros necesarios; los datos grandes (biblioteca de momentos, métricas) se consultan con scripts que devuelven resúmenes.
- Preferir scripts y APIs REST a servidores MCP.
