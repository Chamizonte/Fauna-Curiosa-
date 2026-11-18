"""Encuadre vertical: dónde está el animal en el tramo que se va a usar.

Antes el recorte a vertical usaba una sola "posición media" por clip (casi siempre 0,5)
y cortaba un tercio del ancho del vídeo: si el animal no estaba justo en el centro, o
llenaba media pantalla, salía cortado.

Ahora, para cada plano, se sacan 3 fotogramas del tramo exacto y Gemini (nivel gratuito)
devuelve la caja del animal (izquierda y derecha). Con eso el montaje decide:
- animal estrecho → recorte vertical completo centrado en él;
- animal ancho → se enseña entero (más ancho que la pantalla) sobre un fondo
  desenfocado del mismo plano, en vez de cortarlo.
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
    },
    "required": ["animal_visible", "x_min", "x_max"],
}
PROMPT = ("Imagen de un vídeo de fauna. Animal: {animal}. Da la caja horizontal del animal principal "
          "(cuerpo entero si se ve; si es un primer plano, la cara o la parte que se ve), en coordenadas "
          "de 0 (borde izquierdo de la imagen) a 1000 (borde derecho). Si no se ve ningún animal, "
          "animal_visible=false.")


def _fotograma(src, t, destino, foto):
    cmd = ["ffmpeg", "-y", "-v", "error"] + ([] if foto else ["-ss", f"{t:.2f}"]) + [
        "-i", str(src), "-frames:v", "1", "-vf", "scale=768:-2", "-q:v", "4", str(destino)]
    subprocess.run(cmd, capture_output=True, timeout=120, check=True)
    return Path(destino).read_bytes()


def _preguntar(jpg, animal):
    clave = env("GEMINI_API_KEY")
    if not clave:
        return None
    cuerpo = {
        "contents": [{"parts": [{"text": PROMPT.format(animal=animal)},
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


def caja_animal(src, desde, dur, animal, foto=False):
    """(izquierda, derecha) del animal en fracciones 0-1 del ancho, unidas en 3 fotogramas
    del tramo; None si no se pudo saber."""
    instantes = [0] if foto else [desde + dur * k for k in (0.15, 0.5, 0.85)]
    cajas = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            for i, t in enumerate(instantes):
                r = _preguntar(_fotograma(src, t, Path(tmp) / f"f{i}.jpg", foto), animal)
                if r and r.get("animal_visible") and 0 <= r["x_min"] < r["x_max"] <= 1000:
                    cajas.append((r["x_min"] / 1000, r["x_max"] / 1000))
    except Exception as e:
        log(f"    encuadre: {type(e).__name__}, uso el encuadre prudente")
        return None
    if not cajas:
        return None
    return min(c[0] for c in cajas), max(c[1] for c in cajas)
