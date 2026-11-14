"""Montador de shorts: convierte un guion (brief) en un MP4 vertical listo para subir.

1. Voz con ElevenLabs (o texto animado si no hay presupuesto).
2. Descarga los clips de la biblioteca y recorta cada plano a 1080x1920,
   centrando el encuadre donde el juez de visión vio al animal.
3. Renderiza con Remotion (planos, gancho, subtítulos palabra a palabra, música).
4. Normaliza el volumen a -14 LUFS (estándar de YouTube).

Uso: python -m cf.montaje_short datos/shorts/pendientes/XXXX.json [--sin-voz]
"""
import argparse
import json
import shutil
import tempfile
from pathlib import Path

from . import voz
from .util import DATOS, RAIZ, descargar, env, leer_jsonl, log, run, sondear

REMOTION = RAIZ / "remotion"
PUBLICO = REMOTION / "public" / "render"
SALIDA = RAIZ / "out"
FPS = 30
MUSICA_DRIVE = env("MUSICA_DRIVE_NOMBRE", "shorts_musica_piano_chill.mp3")
CAMARA_LENTA_MAX = 1.6


def biblioteca():
    return {r["clave"]: r for r in leer_jsonl(DATOS / "biblioteca" / "momentos.jsonl")}


def recortar_plano(src, desde, disponible, necesario, posx, destino):
    """Recorta un tramo a vertical 1080x1920. Si el tramo es más corto de lo
    necesario, lo ralentiza (hasta 1,6x); si es más largo, lo corta."""
    factor = min(CAMARA_LENTA_MAX, max(1.0, necesario / max(disponible, 0.1)))
    vf = (f"setpts={factor:.3f}*PTS,"
          "scale=1080:1920:force_original_aspect_ratio=increase,"
          f"crop=1080:1920:'min(max(iw*{posx:.3f}-540,0),iw-1080)':'(ih-1920)/2',"
          f"fps={FPS},format=yuv420p")
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{desde:.2f}", "-t", f"{disponible:.2f}", "-i", str(src),
         "-vf", vf, "-an", "-t", f"{necesario:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         str(destino)])
    real = sondear(destino)["duracion"]
    return real


def montar(brief_path, sin_voz=False):
    brief = json.loads(Path(brief_path).read_text(encoding="utf-8"))
    bib = biblioteca()
    if PUBLICO.exists():
        shutil.rmtree(PUBLICO)
    PUBLICO.mkdir(parents=True)
    SALIDA.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp())

    # 1) Voz
    texto = brief["guion"]
    voz_rel = None
    if not sin_voz and voz.hay_presupuesto_short(texto):
        palabras = voz.generar(texto, PUBLICO / "voz.mp3")
        voz_rel = "render/voz.mp3"
        duracion = palabras[-1]["fin"] + 0.9
    else:
        palabras = voz.palabras_sin_voz(texto)
        duracion = palabras[-1]["fin"] + 1.2
    log(f"  duración del short: {duracion:.1f} s ({'con voz' if voz_rel else 'sin voz'})")

    # 2) Planos: reparto proporcional al tramo pedido para cada uno
    planos_brief = brief["planos"]
    tramos = [max(0.5, p["hasta"] - p["desde"]) for p in planos_brief]
    escala = duracion / sum(tramos)
    descargados, planos = {}, []
    for i, (p, tramo) in enumerate(zip(planos_brief, tramos)):
        m = bib[p["clave"]]
        if p["clave"] not in descargados:
            dst = tmp / f"clip{len(descargados)}"
            descargar(m["url"], dst)
            descargados[p["clave"]] = dst
        necesario = tramo * escala
        posx = p.get("posicion_x", (m.get("vision") or {}).get("posicion_x", 0.5))
        real = recortar_plano(descargados[p["clave"]], p["desde"], tramo, necesario, posx, PUBLICO / f"p{i}.mp4")
        planos.append({"src": f"render/p{i}.mp4", "duracion": round(min(real, necesario), 3)})
    # el último plano cubre cualquier diferencia de redondeo
    falta = duracion - sum(p["duracion"] for p in planos)
    planos[-1]["duracion"] = round(planos[-1]["duracion"] + max(0, falta), 3)

    # 3) Música
    musica_rel = None
    try:
        from .google import descargar_de_drive
        descargar_de_drive(MUSICA_DRIVE, PUBLICO / "musica.mp3")
        musica_rel = "render/musica.mp3"
    except Exception as e:
        log(f"  sin música: {type(e).__name__}")

    props = {
        "duracion": round(duracion, 3), "planos": planos, "palabras": palabras,
        "gancho": brief["gancho_pantalla"], "voz": voz_rel, "musica": musica_rel,
        "volMusica": 0.10 if voz_rel else 0.35,
    }
    props_path = tmp / "props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    bruto = tmp / "bruto.mp4"
    _render(props_path, bruto)

    # 4) Volumen estándar de YouTube
    final = SALIDA / f"{brief['id']}.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(bruto), "-c:v", "copy",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", str(final)])
    shutil.rmtree(tmp, ignore_errors=True)
    log(f"✅ Short listo: {final} ({sondear(final)['duracion']:.1f} s)")
    return final, bool(voz_rel)


def _render(props_path, destino):
    import subprocess
    p = subprocess.run(["npx", "remotion", "render", "src/index.ts", "Short", str(destino),
                        f"--props={props_path}"], cwd=REMOTION, capture_output=True, text=True, timeout=3600)
    if p.returncode != 0:
        raise RuntimeError("Remotion falló:\n" + (p.stderr or p.stdout)[-2000:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brief")
    ap.add_argument("--sin-voz", action="store_true")
    a = ap.parse_args()
    montar(a.brief, a.sin_voz)


if __name__ == "__main__":
    main()
