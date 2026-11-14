"""¿Por qué upload.wikimedia.org responde 429 desde GitHub Actions?
Prueba varias formas de descargar el mismo archivo y anota el resultado."""
import json
import time

import requests

API = "https://commons.wikimedia.org/w/api.php"
UA_A = "CuriosaFaunaBot/2.0 (canal educativo de fauna; github.com/Chamizonte)"
UA_B = ("CuriosaFaunaBot/2.0 (https://www.youtube.com/@CuriosaFauna-y3s; educational wildlife channel) "
        f"python-requests/{requests.__version__}")

# Un vídeo conocido de lobo (Canis lupus) en Commons, buscado por nombre científico.
r = requests.get(API, params={
    "action": "query", "format": "json", "generator": "search", "gsrsearch": '"Canis lupus" filetype:video',
    "gsrnamespace": 6, "gsrlimit": 5, "prop": "imageinfo|videoinfo", "iiprop": "url|size",
    "viprop": "derivatives", }, headers={"User-Agent": UA_B}, timeout=60).json()
paginas = list(r.get("query", {}).get("pages", {}).values())
informe = {"titulos": [p.get("title") for p in paginas]}
p = paginas[0]
original = p["imageinfo"][0]["url"]
derivados = [d.get("src") for d in (p.get("videoinfo") or [{}])[0].get("derivatives", [])]
informe["derivados"] = derivados[:6]


def probar(nombre, url, ua):
    time.sleep(3)
    try:
        resp = requests.get(url, headers={"User-Agent": ua}, stream=True, timeout=60)
        n = sum(len(c) for _, c in zip(range(40), resp.iter_content(1 << 16)))
        informe[nombre] = {"status": resp.status_code, "bytes_leidos": n}
    except Exception as e:
        informe[nombre] = {"error": type(e).__name__}


probar("original_UA_A", original, UA_A)
probar("original_UA_B", original, UA_B)
deriv_720 = next((d for d in derivados if "720p" in d), derivados[0] if derivados else None)
if deriv_720:
    probar("derivado_720_UA_B", deriv_720, UA_B)
probar("filepath_UA_B", "https://commons.wikimedia.org/wiki/Special:FilePath/" + p["title"].removeprefix("File:"), UA_B)
print(json.dumps(informe, indent=2, ensure_ascii=False))
