"""Compara ElevenLabs Multilingual v2 (1 crédito/carácter) con Flash v2.5
(más barato) usando la misma voz y el mismo texto. Guarda voz_C.mp3 y voz_D.mp3
en orden aleatorio y escribe la clave en voz_flash.json."""
import json
import os
import random
from pathlib import Path

import requests

OUT = Path("spikes_out")
OUT.mkdir(exist_ok=True)
TEXTO = (
    "¿Por qué este pulpo cambia de color en menos de un segundo? "
    "Bajo su piel tiene miles de células llamadas cromatóforos, como pequeños globos de pintura. "
    "Y lo más raro: probablemente no distingue los colores."
)
VOICE = os.environ.get("VOICE_ID", "o0SveC0zgHFuCsEO3vHR")
modelos = ["eleven_multilingual_v2", "eleven_flash_v2_5"]
random.shuffle(modelos)
clave = {}
for letra, modelo in zip("CD", modelos):
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"},
        json={"text": TEXTO, "model_id": modelo, "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
        timeout=120,
    )
    clave[letra] = {"modelo": modelo, "status": r.status_code,
                    "creditos": r.headers.get("x-character-count") or r.headers.get("character-cost")}
    if r.ok:
        (OUT / f"voz_{letra}.mp3").write_bytes(r.content)
(OUT / "voz_flash.json").write_text(json.dumps(clave, indent=2), encoding="utf-8")
print("Audios generados:", [k for k, v in clave.items() if v["status"] == 200])
