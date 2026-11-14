"""Publicador de shorts: coge el guion pendiente más antiguo, lo monta y lo sube.

- Elige el primer brief de datos/shorts/pendientes/ (orden por nombre = por fecha).
- Lo monta con cf.montaje_short.
- Lo sube a YouTube con título, descripción, fuentes y créditos de los clips.
- Mueve el brief a datos/shorts/publicados/ con la URL y los datos de la prueba A/B
  (formato, con o sin voz). El workflow hace el commit después.

Si no queda ningún guion, termina sin error y lo avisa (el margen de dos semanas
de la sala de redacción debería evitarlo).

Uso: python -m cf.publicar_short [--no-subir]
"""
import argparse
import datetime as dt
import json
from pathlib import Path

from .montaje_short import biblioteca, montar
from .util import DATOS, env, log

PEND = DATOS / "shorts" / "pendientes"
PUBL = DATOS / "shorts" / "publicados"
PRIVACIDAD = env("PRIVACIDAD_YOUTUBE", "private")
CATEGORIA = "15"  # Mascotas y animales


def siguiente_brief():
    for f in sorted(PEND.glob("*.json")):
        if not f.name.startswith("prueba-"):
            return f
    return None


def descripcion(brief, bib):
    lineas = [brief["descripcion"], ""]
    fuentes = []
    for d in brief.get("datos", []):
        fuentes += [u for u in d.get("fuentes", []) if u not in fuentes]
    if fuentes:
        lineas += ["📚 Fuentes:"] + [f"• {u}" for u in fuentes[:6]] + [""]
    creditos = []
    for p in brief["planos"]:
        m = bib.get(p["clave"])
        if m and m["atribucion"] not in creditos:
            creditos.append(m["atribucion"])
    if creditos:
        lineas += ["🎥 Imágenes:"] + [f"• {c}" for c in creditos] + [""]
    etiquetas = " ".join("#" + t.replace(" ", "") for t in brief.get("etiquetas", [])[:4])
    lineas.append(f"{etiquetas} #Shorts")
    return "\n".join(lineas)[:4900]


def subir(mp4, titulo, desc, etiquetas):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    from .google import credenciales

    yt = build("youtube", "v3", cache_discovery=False, credentials=credenciales(
        "YOUTUBE_REFRESH_TOKEN", ["https://www.googleapis.com/auth/youtube.upload"]))
    body = {
        "snippet": {"title": titulo[:100], "description": desc, "tags": etiquetas[:15],
                    "categoryId": CATEGORIA, "defaultLanguage": "es", "defaultAudioLanguage": "es"},
        "status": {"privacyStatus": PRIVACIDAD, "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(mp4), mimetype="video/mp4", resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return "https://youtube.com/watch?v=" + resp["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-subir", action="store_true", help="monta el vídeo pero no lo sube")
    a = ap.parse_args()

    f = siguiente_brief()
    if not f:
        log("⚠️ No quedan guiones pendientes: hoy no se publica ningún short.")
        return
    brief = json.loads(f.read_text(encoding="utf-8"))
    log(f"Guion: {f.name} ({brief['formato']}, {brief['animal']})")
    mp4, con_voz = montar(f)
    if a.no_subir:
        log("Montado sin subir (--no-subir).")
        return
    url = subir(mp4, brief["titulo"], descripcion(brief, biblioteca()), brief.get("etiquetas", []))
    log(f"✅ Publicado: {url}")

    brief["publicacion"] = {"url": url, "fecha": dt.datetime.utcnow().isoformat(timespec="minutes") + "Z",
                            "con_voz": con_voz, "privacidad": PRIVACIDAD}
    PUBL.mkdir(parents=True, exist_ok=True)
    (PUBL / f.name).write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    f.unlink()


if __name__ == "__main__":
    main()
