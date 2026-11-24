"""Pone nota de espectacularidad (1-10) a los clips de la biblioteca que aún no la tienen.

Los clips nuevos ya la traen del juez de visión. Los antiguos se puntúan a partir de lo que
la visión describió (descripción, acciones, momento destacado), en lotes de 25 por llamada
a Gemini (gratis), sin volver a descargar nada. Si Gemini falla, no se toca nada.

Uso: python -m cf.espectacularidad
"""
import json
import time

import requests

from .util import DATOS, env, leer_jsonl, log
from .vision import API, MODELOS, PAUSA_S

MOMENTOS = DATOS / "biblioteca" / "momentos.jsonl"
LOTE = 25
ESQUEMA = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
    "clave": {"type": "STRING"},
    "espectacularidad": {"type": "INTEGER"},
    "que_pasa": {"type": "STRING"}},
    "required": ["clave", "espectacularidad", "que_pasa"]}}
PROMPT = """Eres el editor de un canal de Shorts de animales. Para cada clip (descrito por un analista
que lo vio) da:
- espectacularidad, 1 a 10: ¿haría parar el dedo a alguien que desliza Shorts? 9-10: pasa algo
  impactante (caza, ataque, nacimiento, pelea, salto, rescate, algo nunca visto). 6-8: acción clara
  o comportamiento curioso. 3-5: el animal se mueve sin más. 1-2: quieto, foto o paisaje.
- que_pasa: lo que pasa, como titular corto en español (máx. 8 palabras); vacío si no pasa nada.
Sé exigente: la mayoría de clips de archivo son 3-5.

Clips:
{clips}"""


def _pedir(texto):
    clave = env("GEMINI_API_KEY")
    if not clave:
        return None
    cuerpo = {"contents": [{"parts": [{"text": texto}]}],
              "generationConfig": {"responseMimeType": "application/json", "responseSchema": ESQUEMA,
                                   "temperature": 0}}
    for modelo in MODELOS:
        for intento in range(2):
            try:
                r = requests.post(f"{API}/{modelo}:generateContent", json=cuerpo, timeout=120,
                                  headers={"x-goog-api-key": clave, "Content-Type": "application/json"})
            except requests.RequestException:
                time.sleep(5)
                continue
            time.sleep(PAUSA_S)
            if r.status_code == 429:
                time.sleep(15 * (intento + 1))
                continue
            if r.status_code != 200:
                break
            try:
                return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
            except (KeyError, IndexError, ValueError):
                break
    return None


def main():
    regs = leer_jsonl(MOMENTOS)
    faltan = [r for r in regs if "espectacularidad" not in (r.get("vision") or {})]
    log(f"Clips sin nota de espectacularidad: {len(faltan)}")
    notas = {}
    for i in range(0, len(faltan), LOTE):
        lote = faltan[i:i + LOTE]
        clips = "\n".join(
            f"- {r['clave']} ({r['animal']}, {'FOTO' if r.get('tipo') == 'foto' else 'vídeo'}): "
            f"{(r.get('vision') or {}).get('descripcion', '')} | acciones: "
            f"{', '.join((r.get('vision') or {}).get('acciones') or [])} | destacado: "
            f"{(r.get('vision') or {}).get('momento_destacado', '')}" for r in lote)
        res = _pedir(PROMPT.format(clips=clips)) or []
        for x in res:
            if isinstance(x.get("espectacularidad"), int):
                notas[x["clave"]] = (max(1, min(10, x["espectacularidad"])), x.get("que_pasa", ""))
    if not notas:
        log("Sin notas nuevas (Gemini no respondió o no faltaba ninguna).")
        return
    with open(MOMENTOS, "w", encoding="utf-8", newline="\n") as fh:
        for r in regs:
            if r["clave"] in notas and "espectacularidad" not in (r.get("vision") or {}):
                r.setdefault("vision", {})
                r["vision"]["espectacularidad"], r["vision"]["que_pasa"] = notas[r["clave"]]
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    log(f"Notas puestas: {len(notas)}")


if __name__ == "__main__":
    main()
