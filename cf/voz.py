"""Voz con ElevenLabs y marcas de tiempo por palabra (para subtítulos y cortes).

Lleva un presupuesto de créditos: los vídeos largos tienen prioridad. Si generar
la voz de un short dejaría sin créditos a los vídeos largos que quedan antes de
la renovación, devuelve None y el short se publica con texto animado sin voz.
"""
import base64
import datetime as dt
import re

import requests

from .util import env, log

API = "https://api.elevenlabs.io/v1"
VOZ = env("VOICE_ID", "o0SveC0zgHFuCsEO3vHR")  # la misma voz documental de los vídeos largos
MODELO_SHORTS = "eleven_flash_v2_5"           # mitad de créditos; en la prueba a ciegas sonaba igual
MODELO_LARGOS = "eleven_multilingual_v2"
CREDITOS_POR_CARACTER = {MODELO_SHORTS: 0.5, MODELO_LARGOS: 1.0}
RESERVA_POR_LARGO = int(env("RESERVA_POR_LARGO", "12000"))
DIAS_LARGOS = (1, 11, 21)


def _h():
    return {"xi-api-key": env("ELEVENLABS_API_KEY", requerido=True), "Content-Type": "application/json"}


def estado_creditos():
    s = requests.get(f"{API}/user/subscription", headers=_h(), timeout=60).json()
    reset = s.get("next_character_count_reset_unix")
    return {
        "restantes": (s.get("character_limit") or 0) - (s.get("character_count") or 0),
        "renovacion": dt.date.fromtimestamp(reset) if reset else dt.date.today() + dt.timedelta(days=30),
    }


def largos_pendientes(hoy, hasta):
    """Vídeos largos (días 1, 11, 21) que quedan antes de la renovación de créditos."""
    n, d = 0, hoy + dt.timedelta(days=1)
    while d <= hasta:  # el día de la renovación también cuenta (el largo sale por la mañana)
        if d.day in DIAS_LARGOS:
            n += 1
        d += dt.timedelta(days=1)
    return n


def hay_presupuesto_short(texto):
    est = estado_creditos()
    reserva = largos_pendientes(dt.date.today(), est["renovacion"]) * RESERVA_POR_LARGO
    coste = len(texto) * CREDITOS_POR_CARACTER[MODELO_SHORTS]
    ok = est["restantes"] - coste >= reserva
    log(f"  créditos ElevenLabs: quedan {est['restantes']}, reserva largos {reserva}, coste short {coste:.0f} -> {'OK' if ok else 'SIN VOZ'}")
    return ok


def _palabras(al):
    """Convierte la alineación por caracteres en palabras con inicio y fin."""
    palabras, actual, ini, fin = [], "", None, None
    for ch, a, b in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        if ch.isspace():
            if actual:
                palabras.append({"t": actual, "ini": round(ini, 3), "fin": round(fin, 3)})
            actual, ini = "", None
            continue
        if ini is None:
            ini = a
        actual += ch
        fin = b
    if actual:
        palabras.append({"t": actual, "ini": round(ini, 3), "fin": round(fin, 3)})
    return palabras


def generar(texto, destino_mp3, modelo=MODELO_SHORTS):
    """Genera la voz y devuelve la lista de palabras con sus tiempos."""
    r = requests.post(
        f"{API}/text-to-speech/{VOZ}/with-timestamps",
        headers=_h(),
        json={"text": texto, "model_id": modelo,
              "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.15}},
        timeout=180,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs respondió HTTP {r.status_code}")
    d = r.json()
    with open(destino_mp3, "wb") as f:
        f.write(base64.b64decode(d["audio_base64"]))
    return _palabras(d.get("alignment") or d["normalized_alignment"])


def palabras_sin_voz(texto, palabras_por_segundo=2.4, inicio=0.4):
    """Tiempos de lectura para shorts sin voz (texto animado)."""
    out, t = [], inicio
    for w in texto.split():
        dur = 1 / palabras_por_segundo + (0.25 if re.search(r"[.,;:?!…]$", w) else 0)
        out.append({"t": w, "ini": round(t, 3), "fin": round(t + dur * 0.9, 3)})
        t += dur
    return out
