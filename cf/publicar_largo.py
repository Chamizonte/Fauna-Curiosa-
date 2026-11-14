"""Publicador de vídeos largos.

La víspera de cada publicación (días 1, 11 y 21) monta el vídeo y lo sube a YouTube
PROGRAMADO: queda privado y YouTube lo hace público solo a las 09:00 UTC del día.
Así hay unas horas para revisarlo en YouTube Studio antes de que salga.

Uso: python -m cf.publicar_largo [--fecha AAAA-MM-DD] [--no-subir] [--ya]
  --fecha     fecha de publicación a preparar (por defecto, mañana)
  --no-subir  solo monta (prueba)
  --ya        publica en público inmediatamente en vez de programarlo
Sale con código 3 si no hay guion para esa fecha.
"""
import argparse
import datetime as dt
import json
import sys

from .montaje_largo import montar
from .util import DATOS, env, log

PEND = DATOS / "largos" / "pendientes"
PUBL = DATOS / "largos" / "publicados"
HORA_PUBLICACION = "09:00:00Z"


def buscar_brief(fecha):
    for f in sorted(PEND.glob("*.json")):
        if json.loads(f.read_text(encoding="utf-8")).get("fecha_publicacion") == fecha:
            return f
    return None


def _mmss(seg):
    seg = int(seg)
    return f"{seg // 3600}:{seg // 60 % 60:02d}:{seg % 60:02d}" if seg >= 3600 else f"{seg // 60:02d}:{seg % 60:02d}"


def descripcion(b, capitulos):
    lineas = [b["descripcion"], ""]
    if len(capitulos) >= 3:
        lineas += ["⏱️ Capítulos:"] + [f"{_mmss(0 if i == 0 else t)} {titulo}"
                                        for i, (t, titulo) in enumerate(capitulos)] + [""]
    fuentes = []
    for d in b.get("datos", []):
        fuentes += [u for u in d.get("fuentes", []) if u not in fuentes]
    if fuentes:
        lineas += ["📚 Fuentes:"] + [f"• {u}" for u in fuentes[:25]] + [""]
    creditos = []
    for s in b["escenas"]:
        for p in s.get("planos", []):
            if p["atribucion"] not in creditos:
                creditos.append(p["atribucion"])
    if creditos:
        lineas += ["🎥 Imágenes:"] + [f"• {c}" for c in creditos] + [""]
    lineas.append(" ".join("#" + t.replace(" ", "") for t in b.get("etiquetas", [])[:3]))
    texto = "\n".join(lineas)
    return texto if len(texto) <= 4900 else texto[:4850] + "\n…"


def subir(mp4, miniatura, b, desc, programar):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    from .google import credenciales

    yt = build("youtube", "v3", cache_discovery=False, credentials=credenciales(
        "YOUTUBE_REFRESH_TOKEN", ["https://www.googleapis.com/auth/youtube.upload"]))
    estado = {"selfDeclaredMadeForKids": False}
    if programar:
        estado |= {"privacyStatus": "private", "publishAt": f"{b['fecha_publicacion']}T{HORA_PUBLICACION}"}
    else:
        estado |= {"privacyStatus": env("PRIVACIDAD_YOUTUBE", "public")}
    body = {"snippet": {"title": b["titulo"][:100], "description": desc, "tags": b.get("etiquetas", [])[:15],
                        "categoryId": "15", "defaultLanguage": "es", "defaultAudioLanguage": "es"},
            "status": estado}
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(mp4), mimetype="video/mp4", resumable=True,
                                                        chunksize=16 * 1024 * 1024))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    try:  # requiere el canal verificado por teléfono
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(miniatura), mimetype="image/jpeg")).execute()
        log("  miniatura subida")
    except Exception as e:
        log(f"  ⚠️ no se pudo poner la miniatura ({type(e).__name__}); ¿canal sin verificar?")
    return "https://youtube.com/watch?v=" + vid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", default=(dt.date.today() + dt.timedelta(days=1)).isoformat())
    ap.add_argument("--no-subir", action="store_true")
    ap.add_argument("--ya", action="store_true")
    a = ap.parse_args()

    f = buscar_brief(a.fecha)
    if not f:
        log(f"No hay guion de vídeo largo para {a.fecha}.")
        sys.exit(3)
    b = json.loads(f.read_text(encoding="utf-8"))
    log(f"Vídeo largo: {f.name} — {b['titulo']}")
    mp4, mini, capitulos = montar(f)
    if a.no_subir:
        log("Montado sin subir (--no-subir).")
        return
    url = subir(mp4, mini, b, descripcion(b, capitulos), programar=not a.ya)
    log(f"✅ Subido: {url} ({'público ya' if a.ya else 'programado para ' + a.fecha + ' ' + HORA_PUBLICACION})")
    b["publicacion"] = {"url": url, "subido": dt.datetime.utcnow().isoformat(timespec="minutes") + "Z",
                        "programado": None if a.ya else f"{a.fecha}T{HORA_PUBLICACION}"}
    PUBL.mkdir(parents=True, exist_ok=True)
    (PUBL / f.name).write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")
    f.unlink()


if __name__ == "__main__":
    main()
