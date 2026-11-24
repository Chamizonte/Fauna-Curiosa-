"""Reparto de formatos según las visitas (prueba A/B de los Shorts).

Lee las visitas de los shorts publicados (datos/shorts/publicados/*.json) en YouTube y
decide cuántos guiones de cada formato escribe la sala esta noche:
- Solo cuentan los shorts con al menos una semana (antes las visitas aún no dicen nada).
- Mientras algún formato tenga menos de 3 shorts medidos, reparto a partes iguales.
- Después, cada formato recibe al menos 1 guion (para seguir aprendiendo) y el resto
  se reparte en proporción a la mediana de visitas de cada formato.
Si no se pueden leer las visitas, reparto a partes iguales: nunca hace fallar la sala.

Uso: python -m cf.rendimiento N   (N = guiones a escribir; imprime el reparto)
"""
import datetime as dt
import json
import os
import re
import statistics
import sys

import requests

from .util import DATOS

FORMATOS = ["momento", "por_que", "comparativa", "mito"]   # «tarjeta» se retiró: la sustituye «momento»
PUBL = DATOS / "shorts" / "publicados"
EDAD = dt.timedelta(days=7)
MIN_MEDIDOS = 3
NUEVO_MITO = dt.datetime(2026, 11, 18)
API = "https://www.googleapis.com/youtube/v3/videos"


def _id(url):
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", url or "")
    return m.group(1) if m else None


def _token():
    """Token de acceso con la cuenta del canal (si sus permisos dejan leer)."""
    try:
        from .google import credenciales
        return credenciales("YOUTUBE_REFRESH_TOKEN", ["https://www.googleapis.com/auth/youtube.readonly"]).token
    except Exception:
        return None


def visitas(ids):
    """{id: visitas}. Prueba con la cuenta del canal y, si no, con la clave de API."""
    if not ids:
        return {}
    intentos = []
    tok = _token()
    if tok:
        intentos.append({"headers": {"Authorization": f"Bearer {tok}"}, "params": {}})
    if os.environ.get("GEMINI_API_KEY"):
        intentos.append({"headers": {}, "params": {"key": os.environ["GEMINI_API_KEY"]}})
    for it in intentos:
        out = {}
        try:
            for i in range(0, len(ids), 50):
                r = requests.get(API, headers=it["headers"], timeout=30, params={
                    "part": "statistics", "id": ",".join(ids[i:i + 50]), **it["params"]})
                r.raise_for_status()
                for v in r.json().get("items", []):
                    out[v["id"]] = int(v["statistics"].get("viewCount", 0))
            return out
        except Exception as ex:
            print(f"(no se pudieron leer las visitas por esta vía: {ex})", file=sys.stderr)
    return None


def medidos(ahora=None):
    """{formato: [visitas de cada short con más de una semana]}"""
    ahora = ahora or dt.datetime.utcnow()
    shorts = []
    for f in PUBL.glob("*.json"):
        b = json.loads(f.read_text(encoding="utf-8"))
        p = b.get("publicacion") or {}
        vid = _id(p.get("url"))
        if not vid or not p.get("fecha") or b.get("formato") not in FORMATOS:
            continue
        fecha = dt.datetime.fromisoformat(p["fecha"].replace("Z", ""))
        if b["formato"] == "mito" and fecha < NUEVO_MITO:
            continue   # el formato mito cambió (pregunta abierta): no se mezclan los antiguos
        if ahora - fecha >= EDAD:
            shorts.append((b["formato"], vid))
    v = visitas([vid for _, vid in shorts])
    if v is None:
        return None
    res = {f: [] for f in FORMATOS}
    for fmt, vid in shorts:
        if vid in v:
            res[fmt].append(v[vid])
    return res


def reparto(n, datos):
    iguales = {f: n // len(FORMATOS) + (1 if i < n % len(FORMATOS) else 0) for i, f in enumerate(FORMATOS)}
    if datos is None:
        return iguales, "no se pudieron leer las visitas: reparto a partes iguales"
    if any(len(datos[f]) < MIN_MEDIDOS for f in FORMATOS):
        cuenta = ", ".join(f"{f} {len(datos[f])}" for f in FORMATOS)
        return iguales, f"aún pocos datos (shorts medidos: {cuenta}; hacen falta {MIN_MEDIDOS} de cada): partes iguales"
    med = {f: statistics.median(datos[f]) for f in FORMATOS}
    base = 1 if n >= len(FORMATOS) else 0
    out = {f: base for f in FORMATOS}
    resto = n - base * len(FORMATOS)
    total = sum(med.values()) or 1
    cuotas = {f: resto * med[f] / total for f in FORMATOS}
    for f in FORMATOS:
        out[f] += int(cuotas[f])
    for f in sorted(FORMATOS, key=lambda f: cuotas[f] - int(cuotas[f]), reverse=True)[:n - sum(out.values())]:
        out[f] += 1
    det = ", ".join(f"{f} {int(med[f])}" for f in sorted(FORMATOS, key=med.get, reverse=True))
    return out, f"mediana de visitas a la semana o más: {det}"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    r, motivo = reparto(n, medidos())
    print(f"Reparto de formatos para {n} guiones ({motivo}):")
    for f in FORMATOS:
        print(f"- {f}: {r[f]}")


if __name__ == "__main__":
    main()
