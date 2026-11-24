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
        "espectacularidad": {"type": "INTEGER", "description":
            "1 a 10: ¿haría parar el dedo a alguien que desliza Shorts? 9-10: pasa algo impactante "
            "(caza, ataque, nacimiento, pelea, salto, rescate, algo nunca visto). 6-8: acción clara o "
            "comportamiento curioso. 3-5: el animal se mueve sin más. 1-2: animal quieto o paisaje."},
        "que_pasa": {"type": "STRING", "description":
            "Lo que pasa en el clip como titular corto en español (máx. 8 palabras), p. ej. "
            "«La garza se traga un pez entero». Vacío si no pasa nada."},
    },
    "required": ["especie_vista", "es_la_especie_buscada", "confianza", "descripcion", "acciones",
                 "calidad_visual", "problemas", "posicion_x", "apto_para_short", "mejores_fotogramas",
                 "espectacularidad", "que_pasa"],
}

PROMPT = """Eres el editor de imagen de un canal de documentales de fauna.
{intro}
Animal que buscamos: {especie} ({cientifico}).
Contexto de la fuente (puede ser incorrecto): {contexto}

Analiza SOLO lo que se ve. Si no estás seguro de la especie, baja la confianza.
"apto_para_short" es true solo si el animal se ve claramente, es la especie buscada, hay algo
interesante que mostrar y no hay problemas graves (marcas de agua, texto, personas en primer plano).
En una foto, exige además que sea nítida, bien expuesta y con el animal vivo y bien encuadrado
(nada de ejemplares de museo, dibujos, láminas o mapas)."""

INTRO_VIDEO = ("La imagen es una hoja de contacto: {n} fotogramas numerados (#1, #2…) de un mismo clip "
               "de vídeo, con su segundo.")
INTRO_FOTO = "La imagen es una fotografía (no un vídeo). En mejores_fotogramas responde [1]."


def _llamar(modelo, imagen_jpg, prompt, esquema=ESQUEMA):
    r = requests.post(
        f"{API}/{modelo}:generateContent",
        headers={"x-goog-api-key": env("GEMINI_API_KEY", requerido=True), "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(imagen_jpg).decode()}},
            ]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": esquema,
                                 "temperature": 0.2},
        },
        timeout=120,
    )
    return r


ENCAJA = {"type": "INTEGER", "description":
          "0 a 10: ¿se ve EXACTAMENTE lo que pide la escena? 10 = se ve justo eso; 7 = se ve lo "
          "esencial; 4 = es el animal pero haciendo otra cosa; 0 = nada que ver"}


def juzgar(imagen_jpg, n_fotogramas, especie, cientifico="", contexto="", foto=False, pedido=None):
    """pedido: lo que tiene que verse (vídeos largos). Añade la nota «encaja» 0-10."""
    intro = INTRO_FOTO if foto else INTRO_VIDEO.format(n=n_fotogramas)
    prompt = PROMPT.format(intro=intro, especie=especie, cientifico=cientifico or "?",
                           contexto=(contexto or "sin datos")[:400])
    esquema = ESQUEMA
    if pedido:
        prompt += (f"\nLa escena del documental necesita que se vea: «{pedido}». Puntúa en «encaja» si "
                   "se ve exactamente eso. Sé exigente: un plano del mismo animal haciendo otra cosa no encaja.")
        esquema = {**ESQUEMA, "properties": {**ESQUEMA["properties"], "encaja": ENCAJA},
                   "required": ESQUEMA["required"] + ["encaja"]}
    ultimo = None
    for modelo in MODELOS:
        for intento in range(3):
            try:
                r = _llamar(modelo, imagen_jpg, prompt, esquema)
            except requests.RequestException as e:  # p. ej. tiempo de espera agotado
                ultimo = type(e).__name__
                time.sleep(10)
                continue
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
