"""Esquemas animados con Explainroo para los vídeos largos.

Una escena con visual.tipo == "esquema" no usa material de archivo: muestra un dibujo
animado (mapa táctico, proceso, comparación…) que Claude programa al escribir el guion.
Escenas seguidas con el mismo visual.esquema forman un único esquema.

Cada esquema vive en datos/largos/esquemas/<id del guion>/<nombre>/ con:
  script.md   una sola sección "## <nombre>" con la MISMA locución de esas escenas
              (puede llevar marcadores [#algo] para sincronizar los dibujos)
  scenes.js   export default { <nombre>(s) { ... } }  (API de Explainroo)

El montaje recorta nuestra locución de ElevenLabs para ese tramo, se la da a Explainroo
como "grabación" (no gasta créditos), renderiza el esquema a 1920x1080 sin música ni
marca de agua y lo ajusta a la duración exacta del tramo. Si algo falla, esas escenas
usan su material de archivo de respaldo (visual.busqueda) como cualquier otra.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

from .util import DATOS, log, run

EXPLAINROO = "explainroo@0.6.0"
CARPETA = DATOS / "largos" / "esquemas"
VIDEO_JSON = {
    "theme": "midnight", "size": "youtube", "language": "es",
    "voice": {"provider": "recording", "src": "assets/narration/"},
    "music": False, "sfx": False, "captions": False, "watermark": False, "transition": "cut",
}


def grupos(b):
    """[(nombre, primera, última)] de escenas seguidas con el mismo esquema."""
    out = []
    for i, s in enumerate(b["escenas"]):
        v = s.get("visual") or {}
        if v.get("tipo") != "esquema":
            continue
        if out and out[-1][0] == v.get("esquema") and out[-1][2] == i - 1:
            out[-1] = (out[-1][0], out[-1][1], i)
        else:
            out.append((v.get("esquema"), i, i))
    return out


def texto_plano(md_seccion):
    t = re.sub(r"\[[^\]]*\]", " ", md_seccion)
    t = re.sub(r"\{([^|}]*)\|[^}]*\}", r"\1", t)
    return " ".join(t.split())


def seccion(script_md, nombre):
    m = re.search(rf"^##\s+{re.escape(nombre)}\b[^\n]*\n(.*?)(?=^##\s|\Z)", script_md, re.S | re.M)
    return m.group(1) if m else None


def errores(b):
    """Comprobaciones para cf.validar_largo."""
    e = []
    nombres = [g[0] for g in grupos(b)]
    for nombre, a, z in grupos(b):
        if not nombre or not re.fullmatch(r"[a-z][a-z0-9_]*", nombre):
            e.append(f"escena {a}: visual.esquema debe ser un nombre en minúsculas sin espacios")
            continue
        if nombres.count(nombre) > 1:
            e.append(f"esquema {nombre}: sus escenas deben ir seguidas")
        if z - a > 7:
            e.append(f"esquema {nombre}: más de 8 escenas seguidas")
        d = CARPETA / b["id"] / nombre
        if not (d / "script.md").exists() or not (d / "scenes.js").exists():
            e.append(f"esquema {nombre}: falta {d.relative_to(DATOS.parent)}/script.md o scenes.js")
            continue
        sec = seccion((d / "script.md").read_text(encoding="utf-8"), nombre)
        if sec is None:
            e.append(f"esquema {nombre}: script.md no tiene la sección '## {nombre}'")
            continue
        esperado = " ".join(" ".join(s["narracion"].split()) for s in b["escenas"][a:z + 1])
        if texto_plano(sec) != esperado:
            e.append(f"esquema {nombre}: el texto de script.md (sin marcadores) no coincide con la "
                     f"narración de las escenas {a}-{z}")
        js = (d / "scenes.js").read_text(encoding="utf-8")
        if not re.search(rf"\b{nombre}\s*\(\s*s\s*\)", js):
            e.append(f"esquema {nombre}: scenes.js no define la función {nombre}(s)")
    if len(grupos(b)) > 4:
        e.append("más de 4 esquemas: úsalos solo donde haga falta explicar algo")
    return e


def _npx(args, cwd, timeout=1800):
    p = subprocess.run(["npx", "--yes", EXPLAINROO, *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"explainroo {args[0]} falló:\n" + (p.stdout + p.stderr)[-1500:])
    return p.stdout


def renderizar(b, voz_mp3, limites, destino_dir, tmp):
    """Renderiza cada esquema. Devuelve {primera_escena: (mp4, última_escena, duración)}."""
    gs = grupos(b)
    if not gs:
        return {}
    try:
        _npx(["doctor", "--fetch", "--language", "es"], tmp, timeout=1200)
    except Exception as ex:
        log(f"  ⚠️ Explainroo no está disponible ({ex}); los esquemas usarán material de respaldo")
        return {}
    hechos = {}
    for nombre, a, z in gs:
        ini, fin = limites[a][0], limites[z][1]
        dur = fin - ini
        try:
            proy = tmp / "esquemas" / nombre
            shutil.copytree(CARPETA / b["id"] / nombre, proy)
            (proy / "video.json").write_text(json.dumps({"title": nombre, **VIDEO_JSON}, ensure_ascii=False),
                                             encoding="utf-8")
            (proy / "assets" / "narration").mkdir(parents=True, exist_ok=True)
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{ini:.3f}", "-t", f"{dur:.3f}", "-i", str(voz_mp3),
                 "-c:a", "libmp3lame", "-b:a", "192k", str(proy / "assets" / "narration" / f"{nombre}.mp3")])
            _npx(["voice", str(proy)], tmp)
            _npx(["render", str(proy)], tmp, timeout=2400)
            bruto = proy / "out" / "video.mp4"
            real = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              str(bruto)]).strip())
            mp4 = destino_dir / f"esquema_{a}.mp4"
            # ajusta el ritmo para que dure exactamente lo mismo que su tramo de voz
            run(["ffmpeg", "-y", "-v", "error", "-i", str(bruto), "-an", "-vf",
                 f"setpts={dur / real:.5f}*PTS,scale=1920:1080,fps=30", "-t", f"{dur:.3f}",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(mp4)])
            hechos[a] = (mp4, z, dur)
            log(f"  ✏️ esquema {nombre}: escenas {a}-{z}, {dur:.1f} s (Explainroo {real:.1f} s)")
        except Exception as ex:
            log(f"  ⚠️ esquema {nombre} no se pudo renderizar; se usa material de respaldo:\n{ex}")
    return hechos
