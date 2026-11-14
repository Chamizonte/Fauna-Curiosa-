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

## Mapa del repositorio (v2, en construcción en la rama `v2`)
- `generador_shorts.py`, `generador_video.py`: pipeline v1, en producción en `main` hasta que la v2 lo sustituya.
- `spikes/`: pruebas de riesgo técnicas de la v2.

## Ahorro de tokens
- Leer solo los ficheros necesarios; los datos grandes (biblioteca de momentos, métricas) se consultan con scripts que devuelven resúmenes.
- Preferir scripts y APIs REST a servidores MCP.
