"""Prueba de riesgo 3: voz de los shorts.

Genera el mismo texto con Chatterbox Multilingual (gratis, CPU) y con ElevenLabs
para compararlos a ciegas. Mide el tiempo de Chatterbox en el runner de GitHub.
"""
import json
import os
import time
from pathlib import Path

import requests

OUT = Path("spikes_out")
OUT.mkdir(exist_ok=True)
TEXTO = (
    "¿Por qué este pulpo cambia de color en menos de un segundo? "
    "Bajo su piel tiene miles de células llamadas cromatóforos, como pequeños globos de pintura. "
    "Y lo más raro: probablemente no distingue los colores."
)
informe = {"caracteres": len(TEXTO)}

# --- Chatterbox ---
try:
    import torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    t0 = time.time()
    model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    informe["chatterbox_carga_s"] = round(time.time() - t0, 1)
    t0 = time.time()
    wav = model.generate(TEXTO, language_id="es")
    informe["chatterbox_generacion_s"] = round(time.time() - t0, 1)
    ta.save(str(OUT / "voz_A.wav"), wav, model.sr)
    informe["chatterbox_duracion_audio_s"] = round(wav.shape[-1] / model.sr, 1)
except Exception as e:
    informe["chatterbox_error"] = repr(e)[:800]

# --- ElevenLabs (misma voz que los vídeos largos) ---
try:
    voice = os.environ.get("VOICE_ID", "o0SveC0zgHFuCsEO3vHR")
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"},
        json={"text": TEXTO, "model_id": "eleven_multilingual_v2",
              "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
        timeout=120,
    )
    r.raise_for_status()
    (OUT / "voz_B.mp3").write_bytes(r.content)
    informe["elevenlabs_ok"] = True
except Exception as e:
    informe["elevenlabs_error"] = repr(e)[:500]

(OUT / "voz.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(informe, ensure_ascii=False, indent=2))
