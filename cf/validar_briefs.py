"""Control de calidad automático de los guiones escritos por Claude.

Comprueba cada brief de datos/shorts/pendientes/ antes de que llegue al montaje.
Los que fallan se mueven a datos/shorts/rechazados/ con el motivo, para que la
siguiente sala de redacción los corrija o los sustituya.

Uso: python -m cf.validar_briefs
"""
import json
import re
import shutil
from pathlib import Path

from .util import DATOS, leer_jsonl, log

PEND = DATOS / "shorts" / "pendientes"
RECH = DATOS / "shorts" / "rechazados"
FORMATOS = {"por_que", "comparativa", "mito"}
CAMPOS = ["id", "formato", "animal", "gancho_pantalla", "guion", "datos", "planos", "titulo", "descripcion", "etiquetas"]


def errores(b, bib):
    e = [f"falta el campo {c}" for c in CAMPOS if not b.get(c)]
    if e:
        return e
    if b["formato"] not in FORMATOS:
        e.append(f"formato desconocido: {b['formato']}")
    n = len(b["guion"].split())
    if not 45 <= n <= 85:
        e.append(f"el guion tiene {n} palabras (45-85)")
    if len(b["gancho_pantalla"].split()) > 7:
        e.append("gancho en pantalla de más de 7 palabras")
    if len(b["titulo"]) > 100:
        e.append("título de más de 100 caracteres")
    for d in b["datos"]:
        urls = [u for u in d.get("fuentes", []) if re.match(r"https?://", u)]
        dominios = {u.split("/")[2].removeprefix("www.") for u in urls}
        if len(dominios) < 2:
            e.append(f"dato con menos de 2 fuentes independientes: {d.get('afirmacion', '')[:60]}")
    if not 3 <= len(b["planos"]) <= 8:
        e.append(f"{len(b['planos'])} planos (3-8)")
    for p in b["planos"]:
        m = bib.get(p.get("clave"))
        if not m:
            e.append(f"clip que no está en la biblioteca: {p.get('clave')}")
            continue
        if m["animal"] != b["animal"]:
            e.append(f"clip de otro animal ({m['animal']}): {p['clave']}")
        if not (0 <= p.get("desde", -1) < p.get("hasta", 0) <= m["duracion"] + 0.5):
            e.append(f"tramo fuera del clip {p['clave']}: {p.get('desde')}-{p.get('hasta')} (dura {m['duracion']})")
        elif p["hasta"] - p["desde"] < 1.5:
            e.append(f"tramo de menos de 1,5 s en {p['clave']}")
    return e


def main():
    bib = {r["clave"]: r for r in leer_jsonl(DATOS / "biblioteca" / "momentos.jsonl")}
    RECH.mkdir(parents=True, exist_ok=True)
    ok = mal = 0
    for f in sorted(PEND.glob("*.json")):
        if f.name.startswith("prueba-"):
            continue
        try:
            b = json.loads(f.read_text(encoding="utf-8"))
            err = errores(b, bib)
        except Exception as ex:
            err = [f"JSON no válido: {ex}"]
        if err:
            mal += 1
            shutil.move(str(f), RECH / f.name)
            (RECH / f"{f.stem}.motivo.txt").write_text("\n".join(err), encoding="utf-8")
            log(f"❌ {f.name}: " + "; ".join(err))
        else:
            ok += 1
            log(f"✅ {f.name}")
    log(f"Válidos: {ok} | rechazados: {mal}")


if __name__ == "__main__":
    main()
