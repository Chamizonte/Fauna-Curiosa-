"""Montador de vídeos largos: guion con material -> MP4 1920x1080 + miniatura.

1. Locución con ElevenLabs Multilingual v2, una petición por capítulo (mejor
   entonación que escena a escena) con tiempos por palabra.
2. Reparte el tiempo entre escenas y prepara cada plano a 1920x1080.
   Escenas sin material reutilizan el plano anterior (otro tramo) o una cartela.
3. Renderiza con Remotion (composición "Largo") y la miniatura (still "Miniatura").
4. Volumen a -14 LUFS.

Uso: python -m cf.montaje_largo datos/largos/pendientes/XXXX.json
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import voz
from .montaje_short import PUBLICO, REMOTION, SALIDA, musica, recortar_plano
from .util import descargar, log, run, sondear

PAUSA_ESCENA = 0.25   # silencio entre escenas
PAUSA_CAPITULO = 1.2  # silencio entre capítulos (deja ver la cartela)
W, H = 1920, 1080


def _limites_capitulos(b):
    ini = sorted(c["escena"] for c in b["capitulos"])
    return [(a, (ini + [len(b["escenas"])])[k + 1]) for k, a in enumerate(ini)]


def locucion(b, tmp):
    """Genera la voz por capítulos. Devuelve (mp3_total, [ (ini, fin) por escena ], palabras)."""
    trozos, tiempos, palabras_todas = [], [None] * len(b["escenas"]), []
    t0 = 0.0
    for k, (a, z) in enumerate(_limites_capitulos(b)):
        escenas = b["escenas"][a:z]
        texto = " ".join(s["narracion"].strip() for s in escenas)
        mp3 = tmp / f"cap{k}.mp3"
        pal = voz.generar(texto, mp3, modelo=voz.MODELO_LARGOS)
        dur = sondear_audio(mp3)
        # asigna las palabras de la locución a cada escena por recuento
        idx = 0
        for j, s in enumerate(escenas):
            n = len(s["narracion"].split())
            grupo = pal[idx:idx + n] or pal[-1:]
            idx += n
            tiempos[a + j] = [t0 + grupo[0]["ini"], t0 + grupo[-1]["fin"]]
        palabras_todas += [{**p, "ini": p["ini"] + t0, "fin": p["fin"] + t0} for p in pal]
        trozos.append(mp3)
        t0 += dur + PAUSA_CAPITULO
        log(f"  capítulo {k + 1}: {dur:.1f} s de voz")
    # concatena los capítulos con su silencio
    lista = tmp / "lista.txt"
    sil = tmp / "sil.mp3"
    run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t",
         str(PAUSA_CAPITULO), "-c:a", "libmp3lame", "-b:a", "128k", str(sil)])
    lineas = []
    for m in trozos:
        lineas += [f"file '{m.as_posix()}'", f"file '{sil.as_posix()}'"]
    lista.write_text("\n".join(lineas), encoding="utf-8")
    total = PUBLICO / "voz.mp3"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
         "-c:a", "libmp3lame", "-b:a", "192k", str(total)])
    # cada escena dura hasta que empieza la siguiente
    limites = []
    for i, (ini, fin) in enumerate(tiempos):
        sig = tiempos[i + 1][0] if i + 1 < len(tiempos) else fin + 2.0
        limites.append((0.0 if i == 0 else ini - 0.15, sig - 0.15 if i + 1 < len(tiempos) else sig))
    return total, limites, palabras_todas


def sondear_audio(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(out.strip() or 0)


def subtitulos(palabras, max_palabras=9):
    """Frases cortas para subtítulos (corta en puntuación o cada ~9 palabras)."""
    out, actual = [], []
    for p in palabras:
        actual.append(p)
        if len(actual) >= max_palabras or p["t"].endswith((".", "?", "!", ",", ";", ":")) and len(actual) >= 4:
            out.append({"texto": " ".join(x["t"] for x in actual), "ini": actual[0]["ini"], "fin": actual[-1]["fin"] + 0.15})
            actual = []
    if actual:
        out.append({"texto": " ".join(x["t"] for x in actual), "ini": actual[0]["ini"], "fin": actual[-1]["fin"] + 0.3})
    return out


def planos(b, limites, tmp):
    descargados, out, ultimo = {}, [], None
    for i, (s, (ini, fin)) in enumerate(zip(b["escenas"], limites)):
        dur = max(0.5, fin - ini)
        p = (s.get("planos") or [None])[0] or ultimo
        if not p:  # primera escena sin material: busca el primer plano disponible
            p = next((x["planos"][0] for x in b["escenas"] if x.get("planos")), None)
        if not p:
            raise RuntimeError("El guion no tiene ningún plano: falta ejecutar cf.material_largo")
        if p["clave"] not in descargados:
            dst = tmp / f"clip{len(descargados)}"
            descargar(p["url"], dst)
            descargados[p["clave"]] = dst
        reutilizado = p is ultimo and not s.get("planos")
        desde = p["desde"]
        disponible = max(0.5, (p["hasta"] or p.get("duracion_clip") or dur) - desde)
        if reutilizado and p["tipo"] == "video":
            # otro tramo del mismo clip para que no se note la repetición
            desde = min(desde + disponible / 2, max(0, (p.get("duracion_clip") or 0) - 2))
            disponible = max(0.5, disponible / 2)
        if p["tipo"] == "video" and dur > disponible * 1.6:
            disponible = min(dur, max(disponible, (p.get("duracion_clip") or disponible) - desde))
        real = recortar_plano(descargados[p["clave"]], desde, disponible, dur, p.get("posicion_x", 0.5),
                              PUBLICO / f"e{i}.mp4", W, H, foto=p["tipo"] == "foto")
        if real < dur - 0.05 and p["tipo"] == "video":
            # clip demasiado corto incluso a cámara lenta: se completa congelando el final
            run(["ffmpeg", "-y", "-v", "error", "-i", str(PUBLICO / f"e{i}.mp4"), "-vf",
                 f"tpad=stop_mode=clone:stop_duration={dur - real + 0.1:.2f}", "-t", f"{dur:.2f}",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(PUBLICO / f"e{i}b.mp4")])
            (PUBLICO / f"e{i}b.mp4").replace(PUBLICO / f"e{i}.mp4")
        out.append({"src": f"render/e{i}.mp4", "duracion": round(dur, 3)})
        if s.get("planos"):
            ultimo = s["planos"][0]
    return out


def miniatura(b, tmp):
    p = b["miniatura"].get("plano")
    if not p:  # sin foto elegida: el plano de la escena más destacada (la primera con material)
        p = next((s["planos"][0] for s in b["escenas"] if s.get("planos")), None)
    src = tmp / "mini_src"
    descargar(p["url"], src)
    img = PUBLICO / "miniatura.jpg"
    if p["tipo"] == "foto":
        run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", "scale=1600:-2", str(img)])
    else:
        t = (p["desde"] + p["hasta"]) / 2 if p.get("hasta") else 1
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1", str(img)])
    props = {"imagen": "render/miniatura.jpg", "texto": b["miniatura"]["texto"], "posicionX": p.get("posicion_x", 0.5)}
    pp = tmp / "mini.json"
    pp.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    destino = SALIDA / f"{b['id']}.jpg"
    _remotion(["still", "src/index.ts", "Miniatura", str(destino), f"--props={pp}", "--image-format=jpeg"])
    return destino


def _remotion(args, timeout=5400):
    p = subprocess.run(["npx", "remotion", *args], cwd=REMOTION, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError("Remotion falló:\n" + (p.stderr or p.stdout)[-2000:])


def montar(brief_path):
    b = json.loads(Path(brief_path).read_text(encoding="utf-8"))
    if PUBLICO.exists():
        shutil.rmtree(PUBLICO)
    PUBLICO.mkdir(parents=True)
    SALIDA.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp())

    voz_mp3, limites, palabras = locucion(b, tmp)
    duracion = round(limites[-1][1], 2)
    log(f"  duración: {duracion / 60:.1f} min")
    lista_planos = planos(b, limites, tmp)

    capitulos = [{"titulo": c["titulo"], "ini": round(limites[c["escena"]][0] + (0.3 if k else 0), 2), "numero": k}
                 for k, c in enumerate(sorted(b["capitulos"], key=lambda c: c["escena"]))]
    rotulos, cartelas = [], []
    for s, (ini, fin) in zip(b["escenas"], limites):
        tipo = (s.get("visual") or {}).get("tipo", "video")
        if tipo in ("mapa", "texto"):
            cartelas.append({"texto": s.get("rotulo") or (s.get("visual") or {}).get("describe", ""),
                             "ini": ini, "fin": fin})
        elif s.get("rotulo"):
            rotulos.append({"texto": s["rotulo"], "ini": ini + 0.3, "fin": min(fin, ini + 4.5)})

    props = {"duracion": duracion, "planos": lista_planos, "subtitulos": subtitulos(palabras),
             "rotulos": rotulos, "capitulos": capitulos, "cartelas": cartelas,
             "voz": "render/voz.mp3", "musica": musica(), "volMusica": 0.07}
    pp = tmp / "props.json"
    pp.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    bruto = tmp / "bruto.mp4"
    log("  renderizando (puede tardar ~30 min)…")
    _remotion(["render", "src/index.ts", "Largo", str(bruto), f"--props={pp}", "--enforce-audio-track",
               "--concurrency=100%"])
    final = SALIDA / f"{b['id']}.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(bruto), "-c:v", "copy",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", str(final)])
    mini = miniatura(b, tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    log(f"✅ Vídeo largo listo: {final} ({sondear(final)['duracion'] / 60:.1f} min) + {mini.name}")
    # minutos de inicio de cada capítulo (para la descripción de YouTube)
    return final, mini, [(c["ini"], c["titulo"]) for c in capitulos]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brief")
    a = ap.parse_args()
    montar(a.brief)


if __name__ == "__main__":
    main()
