"""Resumen compacto de la biblioteca de momentos, pensado para que Claude la lea
gastando pocos tokens (una línea por clip, sin URLs ni metadatos largos).

Uso:
  python -m cf.biblioteca --resumen                 # recuento por animal
  python -m cf.biblioteca --animal pulpo            # clips de un animal
"""
import argparse
from collections import Counter

from .util import DATOS, leer_jsonl

MOMENTOS = DATOS / "biblioteca" / "momentos.jsonl"


def linea(r):
    v = r.get("vision") or {}
    escenas = " ".join(f"{e['ini']:.0f}-{e['fin']:.0f}s" for e in (r.get("tecnico") or {}).get("escenas", [])[:6])
    probl = ",".join(v.get("problemas") or []) or "-"
    return (f"{r['clave']} | {r['duracion']:.0f}s {r['ancho']}x{r['alto']} | cal={v.get('calidad_visual')} "
            f"mov={(r.get('tecnico') or {}).get('movimiento')} | escenas {escenas} | "
            f"{v.get('descripcion', '')} | destacado: {v.get('momento_destacado', '')} | problemas: {probl}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resumen", action="store_true")
    ap.add_argument("--animal")
    a = ap.parse_args()
    regs = leer_jsonl(MOMENTOS)
    if a.animal:
        for r in regs:
            if r["animal"] == a.animal:
                print(linea(r))
    else:
        for animal, n in Counter(r["animal"] for r in regs).most_common():
            print(f"{animal}: {n} clips")


if __name__ == "__main__":
    main()
