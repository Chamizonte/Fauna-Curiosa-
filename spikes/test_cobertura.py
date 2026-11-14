"""Prueba de cobertura: ¿cuánto material de vídeo reutilizable hay por animal
en fuentes públicas sin YouTube?

Para cada animal cuenta vídeos >= 1280 px de ancho y >= 8 s, por fuente y licencia.
Escribe spikes_out/cobertura.json.
"""
import json
import os
from collections import Counter
from pathlib import Path

import requests

OUT = Path("spikes_out")
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "CuriosaFaunaBot/2.0 (canal educativo de fauna)"}
ANIMALES = {
    "pulpo": "octopus", "oso polar": "polar bear", "camaleón": "chameleon", "lobo": "wolf",
    "beluga": "beluga whale", "manatí": "manatee", "león": "lion", "colibrí": "hummingbird",
    "tiburón": "shark", "elefante": "elephant", "pingüino": "penguin", "mantis religiosa": "praying mantis",
}
LIC_OK = ("cc0", "public domain", "pd", "cc by 2", "cc by 3", "cc by 4", "cc-by-2", "cc-by-3", "cc-by-4")


def lic_tipo(lic):
    l = (lic or "").lower()
    if "nc" in l.split("-") or " nc" in l or "-nc" in l or "nd" in l.split("-") or "-nd" in l:
        return "no_valida"
    if "sa" in l.replace("usa", "").split("-") or "-sa" in l or " sa" in l:
        return "by_sa"
    if any(k in l for k in ("cc0", "public domain", "pdm", "pd-")) or l.strip() in ("pd", "public domain"):
        return "dominio_publico"
    if "by" in l:
        return "cc_by"
    return "otra:" + l[:30]


def wikimedia(q):
    c = Counter()
    ejemplos = []
    cont = {}
    for _ in range(3):  # hasta 150 resultados
        params = {"action": "query", "format": "json", "generator": "search",
                  "gsrsearch": f"{q} filetype:video", "gsrnamespace": 6, "gsrlimit": 50,
                  "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", **cont}
        r = requests.get("https://commons.wikimedia.org/w/api.php", params=params, headers=UA, timeout=60).json()
        for p in r.get("query", {}).get("pages", {}).values():
            ii = (p.get("imageinfo") or [{}])[0]
            if (ii.get("width") or 0) < 1280 or (ii.get("duration") or 0) < 8:
                continue
            lic = (ii.get("extmetadata") or {}).get("LicenseShortName", {}).get("value", "")
            t = lic_tipo(lic)
            c[t] += 1
            if len(ejemplos) < 3 and t in ("dominio_publico", "cc_by"):
                ejemplos.append(p.get("title"))
        if "continue" not in r:
            break
        cont = r["continue"]
    return {"conteo": dict(c), "ejemplos": ejemplos}


def internet_archive(q):
    r = requests.get("https://archive.org/advancedsearch.php", params={
        "q": f'title:("{q}") AND mediatype:(movies)', "fl[]": ["identifier", "title", "licenseurl"],
        "rows": 100, "output": "json"}, headers=UA, timeout=60).json()
    docs = r.get("response", {}).get("docs", [])
    c = Counter()
    for d in docs:
        lic = d.get("licenseurl") or ""
        if "publicdomain" in lic:
            c["dominio_publico"] += 1
        elif "/by/" in lic:
            c["cc_by"] += 1
        elif "/by-sa/" in lic:
            c["by_sa"] += 1
        elif lic:
            c["no_valida"] += 1
        else:
            c["sin_licencia"] += 1
    return {"conteo": dict(c), "total": r.get("response", {}).get("numFound")}


def nasa(q):
    r = requests.get("https://images-api.nasa.gov/search", params={"q": q, "media_type": "video"}, timeout=60).json()
    return {"total": r.get("collection", {}).get("metadata", {}).get("total_hits")}


def pexels(q):
    key = os.environ.get("PEXELS_API_KEY")
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                     params={"query": q, "per_page": 80, "size": "medium"}, timeout=60).json()
    vids = r.get("videos", [])
    return {"total": r.get("total_results"), "en_pagina_>=8s": sum(1 for v in vids if v.get("duration", 0) >= 8)}


def pixabay(q):
    key = os.environ.get("PIXABAY_API_KEY")
    r = requests.get("https://pixabay.com/api/videos/", params={"key": key, "q": q, "per_page": 100}, timeout=60).json()
    return {"total": r.get("totalHits")}


informe = {}
for es, en in ANIMALES.items():
    fila = {}
    for nombre, fn in [("wikimedia", wikimedia), ("internet_archive", internet_archive),
                       ("nasa", nasa), ("pexels", pexels), ("pixabay", pixabay)]:
        try:
            fila[nombre] = fn(en)
        except Exception as e:
            fila[nombre] = {"error": repr(e)[:200]}
    informe[es] = fila
    print(es, json.dumps(fila, ensure_ascii=False))

(OUT / "cobertura.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
