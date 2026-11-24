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
from .encuadre import caja_animal
from .util import DATOS, RAIZ, descargar, env, leer_jsonl, log, run, sondear

REMOTION = RAIZ / "remotion"
PUBLICO = REMOTION / "public" / "render"
SALIDA = RAIZ / "out"
FPS = 30
MUSICA_DRIVE = env("MUSICA_DRIVE_NOMBRE", "shorts_musica_piano_chill.mp3")
CAMARA_LENTA_MAX = 1.6


def biblioteca():
    return {r["clave"]: r for r in leer_jsonl(DATOS / "biblioteca" / "momentos.jsonl")}


MARGEN_CAJA = 1.15     # aire alrededor de lo que tiene que verse
SIN_CAJA = 0.5         # si Gemini no responde: la mitad del ancho, centrado


def ventana(iw, ih, w, h, caja, posx):
    """Qué parte del ancho del original se enseña (fracción), dónde se centra y si llena la pantalla.
    Hay tres encuadres: pantalla llena, término medio (la mitad del ancho) y ancho (todo).
    Se elige el más cerrado en el que cabe el FOCO (lo que tiene que verse: la cara del lobo
    que aúlla) y se centra en el foco."""
    llena = min(1.0, (w / h) / (iw / ih))   # fracción del ancho que llena la pantalla sin bandas
    if not caja:
        ancho = max(llena, SIN_CAJA)
        centro = min(max(posx, ancho / 2), 1 - ancho / 2)
        return ancho, centro, ancho <= llena * 1.05
    foco = caja.get("foco") or caja["animal"]
    necesario = (foco[1] - foco[0]) * MARGEN_CAJA
    ancho = next(a for a in sorted({llena, max(llena, 0.5), 1.0}) if a * 1.1 >= necesario or a == 1.0)
    centro = (foco[0] + foco[1]) / 2          # lo que importa, en el centro de la pantalla
    centro = min(max(centro, ancho / 2), 1 - ancho / 2)
    return ancho, centro, ancho <= llena * 1.05


def recortar_plano(src, desde, disponible, necesario, posx, destino, w=1080, h=1920, foto=False, caja=None):
    """Recorta un tramo a w x h (vertical 1080x1920 por defecto) sin cortar al animal.
    - Si el animal cabe, recorte que llena la pantalla centrado en él.
    - Si no cabe, se abre el encuadre (término medio o ancho, según haga falta para que se
      vea el foco) sobre un fondo desenfocado del mismo plano.
    Vídeo: si el tramo es más corto de lo necesario, lo ralentiza (hasta 1,6x).
    Foto: barrido lento (efecto Ken Burns) cuando llena la pantalla."""
    info = sondear(src)
    iw, ih = info["ancho"] or 1920, info["alto"] or 1080
    ancho, centro, llena = ventana(iw, ih, w, h, caja, posx)
    velocidad = "" if foto else f"setpts={min(CAMARA_LENTA_MAX, max(1.0, necesario / max(disponible, 0.1))):.3f}*PTS,"
    if llena and foto:
        vf = (f"scale={int(w * 1.12)}:{int(h * 1.12)}:force_original_aspect_ratio=increase,"
              f"crop={w}:{h}:'min(max(iw*{centro:.3f}-{w / 2}+(t/{necesario:.2f}-0.5)*{w * 0.1:.0f},0),iw-{w})'"
              f":'(ih-{h})/2',fps={FPS},format=yuv420p")
    elif llena:
        vf = (f"{velocidad}scale={w}:{h}:force_original_aspect_ratio=increase,"
              f"crop={w}:{h}:'min(max(iw*{centro:.3f}-{w / 2},0),iw-{w})':'(ih-{h})/2',"
              f"fps={FPS},format=yuv420p")
    else:
        x0 = (centro - ancho / 2)
        vf = (f"{velocidad}split[a][b];"
              f"[a]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
              f"boxblur=30:2,eq=brightness=-0.12[fondo];"
              f"[b]crop=iw*{ancho:.4f}:ih:iw*{x0:.4f}:0,scale={w}:-2[frente];"
              f"[fondo][frente]overlay=(W-w)/2:(H-h)/2,fps={FPS},format=yuv420p")
    if foto:
        entrada = ["-loop", "1", "-t", f"{necesario:.2f}", "-i", str(src)]
    else:
        entrada = ["-ss", f"{desde:.2f}", "-t", f"{disponible:.2f}", "-i", str(src)]
    modo = "pantalla llena" if llena else f"entero sobre fondo ({ancho:.0%} del ancho)"
    log(f"    encuadre: {modo}, centro {centro:.2f}" + ("" if caja else " (sin caja del animal)"))
    run(["ffmpeg", "-y", "-v", "error", *entrada, "-filter_complex" if not llena else "-vf", vf, "-an",
         "-t", f"{necesario:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(destino)])
    return sondear(destino)["duracion"]


def preparar_planos(brief, bib, duracion, tmp, w=1080, h=1920):
    """Descarga y recorta los planos del brief repartiendo la duración total en
    proporción al tramo pedido para cada uno."""
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
        foto = m.get("tipo") == "foto"
        caja = caja_animal(descargados[p["clave"]], p["desde"], tramo, m.get("animal") or brief["animal"], foto,
                           f"nota del plano: «{p.get('nota', '')}»; guion: «{brief.get('guion') or brief.get('texto_tarjeta', '')}»")
        real = recortar_plano(descargados[p["clave"]], p["desde"], tramo, necesario, posx,
                              PUBLICO / f"p{i}.mp4", w, h, foto=foto, caja=caja)
        planos.append({"src": f"render/p{i}.mp4", "duracion": round(min(real, necesario), 3)})
    # el último plano cubre cualquier diferencia de redondeo
    falta = duracion - sum(p["duracion"] for p in planos)
    planos[-1]["duracion"] = round(planos[-1]["duracion"] + max(0, falta), 3)
    return planos


def musica():
    try:
        from .google import descargar_de_drive
        descargar_de_drive(MUSICA_DRIVE, PUBLICO / "musica.mp3")
        return "render/musica.mp3"
    except Exception as e:
        log(f"  sin música: {type(e).__name__}")
        return None


def numero_tarjeta():
    """Número correlativo de la serie de tarjetas (#1, #2…)."""
    n = 0
    for f in (DATOS / "shorts" / "publicados").glob("*.json"):
        try:
            n += json.loads(f.read_text(encoding="utf-8")).get("formato") == "tarjeta"
        except ValueError:
            pass
    return n + 1


def montar_tarjeta(brief, bib, tmp):
    from .validar_briefs import texto_plano
    palabras = len(texto_plano(brief["texto_tarjeta"]).split())
    if brief["formato"] == "momento":
        # un solo momento: dura lo que el clip (6-12 s), con tiempo para leer el cartel
        tramo = sum(max(0.5, x["hasta"] - x["desde"]) for x in brief["planos"])
        duracion = round(min(12.0, max(6.0, tramo, palabras / 3.0 + 1.0)), 2)
    else:
        # tiempo de lectura: ~3 palabras por segundo más margen para ver el vídeo
        duracion = round(max(10.0, palabras / 3.0 + 3.0), 2)
    log(f"  duración de la {brief['formato']}: {duracion:.1f} s ({palabras} palabras, sin voz)")
    planos = preparar_planos(brief, bib, duracion, tmp, 1000, 760)  # ANCHO_MEDIA x ALTO_MEDIA de Tarjeta.tsx
    numero = numero_tarjeta() if brief["formato"] == "tarjeta" else None
    props = {"duracion": duracion, "titular": brief["gancho_pantalla"], "numero": numero,
             "texto": brief["texto_tarjeta"], "planos": planos, "musica": musica(), "volMusica": 0.45}
    return props, "Tarjeta"


def montar(brief_path, sin_voz=False):
    brief = json.loads(Path(brief_path).read_text(encoding="utf-8"))
    bib = biblioteca()
    if PUBLICO.exists():
        shutil.rmtree(PUBLICO)
    PUBLICO.mkdir(parents=True)
    SALIDA.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp())

    if brief["formato"] in ("tarjeta", "momento"):
        props, composicion = montar_tarjeta(brief, bib, tmp)
        return _finalizar(brief, props, composicion, tmp), False

    # 1) Voz
    texto = brief["guion"]
    voz_rel = None
    if not sin_voz and voz.hay_presupuesto_short(texto):
        try:
            palabras = voz.generar(texto, PUBLICO / "voz.mp3")
            voz_rel = "render/voz.mp3"
        except Exception as e:
            log(f"  la voz falló ({e}); se monta sin voz")
    if voz_rel:
        duracion = palabras[-1]["fin"] + 0.9
    else:
        palabras = voz.palabras_sin_voz(texto)
        duracion = palabras[-1]["fin"] + 1.2
    log(f"  duración del short: {duracion:.1f} s ({'con voz' if voz_rel else 'sin voz'})")

    # 2) Planos y 3) música
    planos = preparar_planos(brief, bib, duracion, tmp)
    musica_rel = musica()

    # El gancho en pantalla sustituye a los subtítulos de la primera frase.
    fin_primera = next((p["fin"] for p in palabras if p["t"].endswith(("?", ".", "!", "…"))), 2.5)
    props = {
        "duracion": round(duracion, 3), "planos": planos, "palabras": palabras,
        "gancho": brief["gancho_pantalla"], "ganchoFin": round(max(2.0, fin_primera + 0.3), 2),
        "voz": voz_rel, "musica": musica_rel,
        "volMusica": 0.10 if voz_rel else 0.35,
    }
    return _finalizar(brief, props, "Short", tmp), bool(voz_rel)


def _finalizar(brief, props, composicion, tmp):
    props_path = tmp / "props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    bruto = tmp / "bruto.mp4"
    _render(props_path, bruto, composicion)

    # 4) Volumen estándar de YouTube
    final = SALIDA / f"{brief['id']}.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(bruto), "-c:v", "copy",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", str(final)])
    shutil.rmtree(tmp, ignore_errors=True)
    log(f"✅ Short listo: {final} ({sondear(final)['duracion']:.1f} s)")
    return final


def _render(props_path, destino, composicion="Short"):
    import subprocess
    p = subprocess.run(["npx", "remotion", "render", "src/index.ts", composicion, str(destino),
                        "--enforce-audio-track",
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
