"""Mide cuántos créditos de ElevenLabs gasta de verdad cada modelo.

Lee el contador de la suscripción antes y después de generar el mismo texto
con Multilingual v2 y con Flash v2.5. No guarda audio (ya se compararon)."""
import json
import os
import time
from pathlib import Path

import requests

OUT = Path("spikes_out")
OUT.mkdir(exist_ok=True)
KEY = os.environ["ELEVENLABS_API_KEY"].strip()
H = {"xi-api-key": KEY, "Content-Type": "application/json"}
VOICE = os.environ.get("VOICE_ID", "o0SveC0zgHFuCsEO3vHR")
TEXTO = (
    "¿Por qué este pulpo cambia de color en menos de un segundo? "
    "Bajo su piel tiene miles de células llamadas cromatóforos, como pequeños globos de pintura. "
    "Y lo más raro: probablemente no distingue los colores."
)


def usados():
    s = requests.get("https://api.elevenlabs.io/v1/user/subscription", headers=H, timeout=60).json()
    return s.get("character_count"), s.get("character_limit"), s.get("tier"), s.get("next_character_count_reset_unix")


informe = {"caracteres_texto": len(TEXTO)}
c0, limite, tier, reset = usados()
informe.update({"plan": tier, "limite": limite, "usados_inicio": c0,
                "renovacion": time.strftime("%Y-%m-%d", time.gmtime(reset)) if reset else None})
for modelo in ["eleven_multilingual_v2", "eleven_flash_v2_5"]:
    antes = usados()[0]
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}", headers=H,
                      json={"text": TEXTO, "model_id": modelo}, timeout=120)
    time.sleep(3)
    informe[modelo] = {"status": r.status_code, "creditos_gastados": usados()[0] - antes}
(OUT / "cuota.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
print(json.dumps(informe, indent=2))
