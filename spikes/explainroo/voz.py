"""Genera la locución de cada escena de un proyecto Explainroo con nuestra voz de ElevenLabs.

Uso: python spikes/explainroo/voz.py spikes/explainroo/zama
Escribe assets/narration/<escena>.mp3 (Explainroo la trata como una grabación propia).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from cf.voz import MODELO_LARGOS, generar  # noqa: E402

proyecto = Path(sys.argv[1])
dest = proyecto / "assets" / "narration"
dest.mkdir(parents=True, exist_ok=True)
escena = None
textos = {}
for linea in (proyecto / "script.md").read_text(encoding="utf-8").splitlines():
    m = re.match(r"##\s+(\S+)", linea)
    if m:
        escena = m.group(1)
        continue
    if escena and linea.strip() and not linea.startswith("#"):
        limpio = re.sub(r"\[[^\]]*\]\s*", "", linea)
        limpio = re.sub(r"\{([^|}]*)\|([^}]*)\}", r"\2", limpio)
        textos[escena] = (textos.get(escena, "") + " " + limpio).strip()
for nombre, texto in textos.items():
    generar(texto, dest / f"{nombre}.mp3", MODELO_LARGOS)
    print(f"{nombre}: {len(texto)} caracteres")
