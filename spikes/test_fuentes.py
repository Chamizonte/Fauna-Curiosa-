"""Prueba de riesgo 1 y 2: ¿podemos conseguir material real desde GitHub Actions?

- YouTube con filtro Creative Commons (yt-dlp): búsqueda, licencia y descarga.
- Internet Archive y Wikimedia Commons: búsqueda y descarga de vídeo.

Escribe un informe en spikes_out/fuentes.json.
"""
import json
import os
import subprocess
import time
from pathlib import Path

import requests

OUT = Path("spikes_out")
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "CuriosaFaunaBot/2.0 (canal educativo de fauna)"}
informe = {}

# Filtro "Creative Commons" de la búsqueda de YouTube (parámetro sp).
CC_FILTER = "EgIwAQ%3D%3D"
BUSQUEDAS = ["polar bear swimming", "octopus camouflage", "chameleon tongue"]


def yt_dlp(*args, timeout=300):
    t0 = time.time()
    r = subprocess.run(["yt-dlp", *args], capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr[-1500:], round(time.time() - t0, 1)


def probar_youtube():
    res = {"busquedas": []}
    primer_cc = None
    for q in BUSQUEDAS:
        url = f"https://www.youtube.com/results?search_query={q.replace(' ', '+')}&sp={CC_FILTER}"
        code, out, err, secs = yt_dlp("--flat-playlist", "--playlist-end", "8", "-J", url)
        item = {"q": q, "code": code, "segundos": secs}
        if code == 0:
            data = json.loads(out)
            entradas = data.get("entries", [])
            item["resultados"] = [
                {"id": e.get("id"), "titulo": e.get("title"), "duracion": e.get("duration")}
                for e in entradas
            ]
            if entradas and not primer_cc:
                primer_cc = entradas[0].get("id")
        else:
            item["error"] = err
        res["busquedas"].append(item)

    if primer_cc:
        url = f"https://www.youtube.com/watch?v={primer_cc}"
        code, out, err, secs = yt_dlp("-J", "--skip-download", url)
        meta = {"code": code, "segundos": secs}
        if code == 0:
            d = json.loads(out)
            meta.update({k: d.get(k) for k in ("title", "channel", "license", "duration", "width", "height")})
        else:
            meta["error"] = err
        res["metadatos"] = meta

        code, out, err, secs = yt_dlp(
            "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]",
            "--download-sections", "*0-20",
            "-o", str(OUT / "yt_cc.%(ext)s"), url, timeout=600,
        )
        res["descarga"] = {"code": code, "segundos": secs, "error": err if code else None,
                           "archivos": [p.name for p in OUT.glob("yt_cc.*")]}
    return res


def probar_archive():
    res = {}
    q = '(wildlife OR animals) AND mediatype:movies AND (licenseurl:*publicdomain* OR licenseurl:*creativecommons.org/licenses/by/*)'
    r = requests.get("https://archive.org/advancedsearch.php", params={
        "q": q, "fl[]": ["identifier", "title", "licenseurl"], "rows": 10, "output": "json",
    }, headers=UA, timeout=60)
    docs = r.json().get("response", {}).get("docs", [])
    res["resultados"] = docs
    for d in docs:
        files = requests.get(f"https://archive.org/metadata/{d['identifier']}", headers=UA, timeout=60).json().get("files", [])
        mp4 = [f for f in files if f.get("name", "").lower().endswith(".mp4")]
        if mp4:
            f = sorted(mp4, key=lambda x: int(x.get("size", 0) or 0))[0]
            url = f"https://archive.org/download/{d['identifier']}/{f['name']}"
            t0 = time.time()
            with requests.get(url, headers=UA, stream=True, timeout=120) as resp:
                resp.raise_for_status()
                with open(OUT / "archive.mp4", "wb") as fh:
                    for i, chunk in enumerate(resp.iter_content(1 << 16)):
                        fh.write(chunk)
                        if i > 400:  # ~25 MB como máximo para la prueba
                            break
            res["descarga"] = {"url": url, "segundos": round(time.time() - t0, 1),
                               "bytes": (OUT / "archive.mp4").stat().st_size}
            break
    return res


def probar_wikimedia():
    r = requests.get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": "polar bear filetype:video", "gsrnamespace": 6, "gsrlimit": 8,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
    }, headers=UA, timeout=60).json()
    out = []
    for p in r.get("query", {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        lic = (ii.get("extmetadata") or {}).get("LicenseShortName", {}).get("value")
        out.append({"titulo": p.get("title"), "mime": ii.get("mime"), "ancho": ii.get("width"),
                    "duracion": ii.get("duration"), "licencia": lic})
    return {"resultados": out}


for nombre, fn in [("youtube_cc", probar_youtube), ("internet_archive", probar_archive), ("wikimedia", probar_wikimedia)]:
    try:
        informe[nombre] = fn()
    except Exception as e:  # la prueba debe informar, no romperse
        informe[nombre] = {"excepcion": repr(e)[:500]}

(OUT / "fuentes.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(informe, ensure_ascii=False, indent=2)[:6000])
