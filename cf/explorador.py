"""Explorador de material: llena la biblioteca de momentos.

Para cada animal: busca clips con licencia válida, los descarga, mide
movimiento y escenas, y pide al juez de visión que describa qué se ve.
- Los clips aptos van a datos/biblioteca/momentos.jsonl
- Los descartados van a datos/biblioteca/descartes.jsonl (para no repetirlos)
El vídeo no se guarda: el día del montaje se vuelve a descargar desde su URL.

Uso: python -m cf.explorador [--animales pulpo,lobo] [--nuevos 4] [--max-total 20]
"""
import argparse
import json
import shutil
import tempfile
import time
from collections import Counter
from pathlib import Path

from . import analisis, fuentes, vision
from .util import DATOS, anadir_jsonl, descargar, leer_jsonl, log, run

BIB = DATOS / "biblioteca"
MOMENTOS = BIB / "momentos.jsonl"
DESCARTES = BIB / "descartes.jsonl"
MOV_MINIMO = 0.6      # por debajo, el clip es prácticamente una foto
MAX_MB = 350


def _proxy(origen, destino):
    """Copia ligera en MP4 (640 px, sin audio) para analizar cualquier formato."""
    run(["ffmpeg", "-y", "-v", "error", "-i", str(origen), "-vf", "scale=640:-2", "-an",
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", str(destino)])


def examinar(c, animal, tmp):
    """Devuelve (registro, apto)."""
    reg = {**c.dict(), "animal": animal["es"], "fecha": time.strftime("%Y-%m-%d")}
    if c.tamano_mb and c.tamano_mb > MAX_MB:
        return {**reg, "motivo": "archivo demasiado grande"}, False
    original = tmp / "original"
    proxy = tmp / "proxy.mp4"
    descargar(c.url_escaneo or c.url, original, max_mb=MAX_MB)
    _proxy(original, proxy)
    tec = analisis.analizar(proxy)
    reg["tecnico"] = tec
    if tec["movimiento"] < MOV_MINIMO:
        return {**reg, "motivo": f"casi estático (movimiento {tec['movimiento']})"}, False

    d = tec["duracion"]
    tiempos = [d * f for f in (0.06, 0.22, 0.38, 0.54, 0.70, 0.88)]
    hoja = analisis.hoja_contacto(analisis.fotogramas(proxy, tiempos))
    contexto = f"{c.titulo}. {' '.join(c.etiquetas)[:250]}"
    v = vision.juzgar(hoja, 6, animal["es"], animal.get("cientifico", ""), contexto)
    v["tiempos_fotogramas"] = [round(t, 2) for t in tiempos]
    reg["vision"] = v
    apto = bool(v.get("apto_para_short") and v.get("es_la_especie_buscada") and v.get("confianza", 0) >= 0.6)
    if not apto:
        reg["motivo"] = "visión: " + (", ".join(v.get("problemas") or []) or
                                      f"especie={v.get('especie_vista')} conf={v.get('confianza')}")
    return reg, apto


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--animales", default="")
    ap.add_argument("--nuevos", type=int, default=4, help="candidatos nuevos a examinar por animal")
    ap.add_argument("--max-total", type=int, default=20, help="tope de llamadas de visión por ejecución")
    a = ap.parse_args()

    catalogo = json.loads((DATOS / "animales.json").read_text(encoding="utf-8"))
    vistos = {r["clave"] for r in leer_jsonl(MOMENTOS) + leer_jsonl(DESCARTES)}
    aptos = Counter(r["animal"] for r in leer_jsonl(MOMENTOS))
    if a.animales:
        nombres = [n.strip() for n in a.animales.split(",")]
        objetivo = [x for x in catalogo if x["es"] in nombres]
    else:  # primero los animales con menos material
        objetivo = sorted(catalogo, key=lambda x: aptos[x["es"]])

    examinados = 0
    resumen = Counter()
    for animal in objetivo:
        if examinados >= a.max_total:
            break
        log(f"== {animal['es']} ({aptos[animal['es']]} momentos en biblioteca)")
        cands = [c for c in fuentes.buscar(animal) if c.clave not in vistos]
        for c in cands[: a.nuevos]:
            if examinados >= a.max_total:
                break
            tmp = Path(tempfile.mkdtemp())
            try:
                reg, apto = examinar(c, animal, tmp)
                if "vision" in reg:
                    examinados += 1
            except Exception as e:
                # Error transitorio (red, cuota): no se registra, se reintentará otro día.
                log(f"  ⚠️ {c.fuente} {c.titulo[:60]} | {type(e).__name__}: {str(e)[:140]}")
                continue
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            anadir_jsonl(MOMENTOS if apto else DESCARTES, reg)
            vistos.add(c.clave)
            resumen["aptos" if apto else "descartados"] += 1
            v = reg.get("vision", {})
            log(f"  {'✅' if apto else '❌'} {c.fuente} {c.titulo[:60]} | "
                f"mov={reg.get('tecnico', {}).get('movimiento')} | {v.get('descripcion', reg.get('motivo', ''))[:110]}")
    log(f"\nResumen: {dict(resumen)} | llamadas de visión: {examinados}")


if __name__ == "__main__":
    main()
