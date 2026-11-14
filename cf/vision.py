"""Juez de visión: Gemini (nivel gratuito) describe qué se ve en un clip.

Recibe una hoja de contacto (varios fotogramas numerados en una sola imagen)
y devuelve un JSON estructurado. Prueba varios modelos por si alguno no está
disponible o ha agotado su cuota gratuita.
"""
import base64
import json
import time

import requests

from .util import env, log

API = "https://generativelanguage.googleapis.com/v1beta/models"
MODELOS = [m.strip() for m in (env("GEMINI_MODELOS") or
           "gemini-3.6-flash,gemini-3.8-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(",")]
PAUSA_S = float(env("GEMINI_PAUSA_S", "6"))  # respeta el límite por minuto del nivel gratuito

ESQUEMA = {
    "type": "OBJECT",
    "properties": {
        "especie_vista": {"type": "STRING", "description": "Nombre común en español del animal principal que se ve"},
        "nombre_cientifico": {"type": "STRING"},
        "es_la_especie_buscada": {"type": "BOOLEAN"},
        "confianza": {"type": "NUMBER", "description": "0 a 1"},
        "descripcion": {"type": "STRING", "description": "Qué se ve, en una o dos frases en español"},
        "acciones": {"type": "ARRAY", "items": {"type": "STRING"},
                     "description": "Comportamientos visibles: nadar, cazar, comer, saltar, acicalarse…"},
        "momento_destacado": {"type": "STRING", "description": "Lo más llamativo del clip, o vacío si no hay nada"},
        "mejores_fotogramas": {"type": "ARRAY", "items": {"type": "INTEGER"},
                               "description": "Números de los fotogramas más impactantes"},
        "calidad_visual": {"type": "INTEGER", "description": "1 (mala) a 5 (documental)"},
        "problemas": {"type": "ARRAY", "items": {"type": "STRING"},
                      "description": "marca de agua, texto en pantalla, personas, logotipo, barrotes o cristal de zoo, desenfocado, animal muy pequeño, animal muerto o herido"},
        "posicion_x": {"type": "NUMBER", "description": "Posición horizontal media del animal, 0 izquierda a 1 derecha"},
        "apto_para_short": {"type": "BOOLEAN"},
    },
    "required": ["especie_vista", "es_la_especie_buscada", "confianza", "descripcion", "acciones",
                 "calidad_visual", "problemas", "posicion_x", "apto_para_short", "mejores_fotogramas"],
}

PROMPT = """Eres el editor de imagen de un canal de documentales de fauna.
La imagen es una hoja de contacto: {n} fotogramas numerados (#1, #2…) de un mismo clip de vídeo, con su segundo.
Animal que buscamos: {especie} ({cientifico}).
Contexto de la fuente (puede ser incorrecto): {contexto}

Analiza SOLO lo que se ve. Si no estás seguro de la especie, baja la confianza.
"apto_para_short" es true solo si el animal se ve claramente, es la especie buscada, hay algo
interesante que mostrar y no hay problemas graves (marcas de agua, texto, personas en primer plano)."""


def _llamar(modelo, imagen_jpg, prompt):
    r = requests.post(
        f"{API}/{modelo}:generateContent",
        headers={"x-goog-api-key": env("GEMINI_API_KEY", requerido=True), "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(imagen_jpg).decode()}},
            ]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": ESQUEMA,
                                 "temperature": 0.2},
        },
        timeout=120,
    )
    return r


def juzgar(imagen_jpg, n_fotogramas, especie, cientifico="", contexto=""):
    prompt = PROMPT.format(n=n_fotogramas, especie=especie, cientifico=cientifico or "?",
                           contexto=(contexto or "sin datos")[:400])
    ultimo = None
    for modelo in MODELOS:
        for intento in range(3):
            r = _llamar(modelo, imagen_jpg, prompt)
            time.sleep(PAUSA_S)
            if r.status_code == 200:
                try:
                    texto = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    res = json.loads(texto)
                    res["modelo"] = modelo
                    return res
                except (KeyError, IndexError, ValueError):
                    ultimo = "respuesta no válida"
                    break
            if r.status_code == 429:
                ultimo = "cuota agotada (429)"
                time.sleep(20 * (intento + 1))
                continue
            ultimo = f"HTTP {r.status_code}"
            break  # 404 (modelo no disponible) u otro: probar el siguiente modelo
        log(f"    visión: {modelo} -> {ultimo}, pruebo otro modelo")
    raise RuntimeError(f"Ningún modelo de visión respondió ({ultimo})")
