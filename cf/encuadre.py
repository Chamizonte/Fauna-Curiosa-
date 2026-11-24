"""Encuadre vertical: dónde está el animal en el tramo que se va a usar.

Antes el recorte a vertical usaba una sola "posición media" por clip (casi siempre 0,5)
y cortaba un tercio del ancho del vídeo: si el animal no estaba justo en el centro, o
llenaba media pantalla, salía cortado.

Ahora, para cada plano, se sacan 3 fotogramas del tramo exacto y Gemini (nivel gratuito)
devuelve dos cajas (izquierda y derecha): la del animal y la del FOCO, lo que tiene que
verse sí o sí según la nota del plano (la cara del lobo que aúlla, las fauces que muerden…).
Con eso el montaje elige el encuadre más cerrado en el que cabe el foco: pantalla llena,
término medio o ancho, sobre el plano desenfocado.
Si Gemini falla, devuelve None y el montaje usa un encuadre prudente: nunca hace fallar
el short.
"""
import base64
import json
import subprocess
import tempfile
import time
from pathlib import Path

import requests

from .util import env, log
from .vision import API, MODELOS, PAUSA_S

ESQUEMA = {
    "type": "OBJECT",
    "properties": {
        "animal_visible": {"type": "BOOLEAN"},
        "x_min": {"type": "INTEGER", "description": "Borde izquierdo del animal principal, 0 a 1000"},
        "x_max": {"type": "INTEGER", "description": "Borde derecho del animal principal, 0 a 1000"},
        "foco_min": {"type": "INTEGER", "description": "Borde izquierdo de lo que tiene que verse sí o sí, 0 a 1000"},
        "foco_max": {"type": "INTEGER", "description": "Borde derecho de lo que tiene que verse sí o sí, 0 a 1000"},
    },
    "required": ["animal_visible", "x_min", "x_max", "foco_min", "foco_max"],
}
PROMPT = ("Imagen de un vídeo de fauna que vamos a recortar en vertical para un Short. Animal: {animal}. "
          "Qué cuenta el short y para qué es este plano: {nota}\n"
          "Coordenadas horizontales de 0 (borde izquierdo de la imagen) a 1000 (borde derecho).\n"
          "- x_min/x_max: el animal principal entero (lo que se ve de él).\n"
          "- foco_min/foco_max: lo que TIENE que verse para que el plano tenga sentido con lo que se "
          "cuenta: normalmente la cabeza y la cara; si se habla de una acción, la parte que la hace "
          "(las fauces que muerden, las patas que corren, la boca que aúlla…). Si importa el animal "
          "entero, la misma caja que el animal.\n"
          "Si no se ve ningún animal, animal_visible=false.")


def _fotograma(src, t, destino, foto):
    cmd = ["ffmpeg", "-y", "-v", "error"] + ([] if foto else ["-ss", f"{t:.2f}"]) + [
        "-i", str(src), "-frames:v", "1", "-vf", "scale=768:-2", "-q:v", "4", str(destino)]
    subprocess.run(cmd, capture_output=True, timeout=120, check=True)
    return Path(destino).read_bytes()


def _preguntar(jpg, animal, nota=""):
    clave = env("GEMINI_API_KEY")
    if not clave:
        return None
    cuerpo = {
        "contents": [{"parts": [{"text": PROMPT.format(animal=animal, nota=nota or "—")},
                                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpg).decode()}}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": ESQUEMA, "temperature": 0},
    }
    for modelo in MODELOS:
        for intento in range(2):
            try:
                r = requests.post(f"{API}/{modelo}:generateContent", json=cuerpo, timeout=60,
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


def caja_animal(src, desde, dur, animal, foto=False, nota=""):
    """{"animal": (izq, der), "foco": (izq, der)} en fracciones 0-1 del ancho, unidas en
    3 fotogramas del tramo; None si no se pudo saber."""
    instantes = [0] if foto else [desde + dur * k for k in (0.15, 0.5, 0.85)]
    cajas = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            for i, t in enumerate(instantes):
                r = _preguntar(_fotograma(src, t, Path(tmp) / f"f{i}.jpg", foto), animal, nota)
                if r and r.get("animal_visible") and 0 <= r["x_min"] < r["x_max"] <= 1000:
                    a = (r["x_min"] / 1000, r["x_max"] / 1000)
                    fmin, fmax = r.get("foco_min", -1), r.get("foco_max", -1)
                    f = (fmin / 1000, fmax / 1000) if 0 <= fmin < fmax <= 1000 else a
                    cajas.append((a, f))
    except Exception as e:
        log(f"    encuadre: {type(e).__name__}, uso el encuadre prudente")
        return None
    if not cajas:
        return None
    return {"animal": (min(c[0][0] for c in cajas), max(c[0][1] for c in cajas)),
            "foco": (min(c[1][0] for c in cajas), max(c[1][1] for c in cajas))}
