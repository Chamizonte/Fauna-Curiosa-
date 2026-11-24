"""Control de calidad del guion de un vídeo largo.

Uso: python -m cf.validar_largo [ruta.json ...]   (sin rutas: todos los pendientes)
Sale con código 1 si alguno falla (el workflow lo marca en rojo y no se guarda).
"""
import json
import re
import sys
from pathlib import Path

from . import esquemas
from .util import DATOS, log

PEND = DATOS / "largos" / "pendientes"
CAMPOS = ["id", "fecha_publicacion", "tema", "titulo", "descripcion", "etiquetas",
          "miniatura", "capitulos", "escenas", "datos"]
TIPOS = {"video", "foto", "grafico", "mapa", "texto", "esquema"}
# animaciones propias (remotion/src/Graficos.tsx): campos obligatorios de cada una
GRAFICOS = {
    "cifra": ["valor", "texto"], "comparativa": ["titulo", "items"], "linea_tiempo": ["titulo", "eventos"],
    "mapa": ["puntos"], "lista": ["titulo", "puntos"], "proceso": ["titulo", "pasos"],
    "cita": ["texto", "autor"], "titular": ["texto"],
}
MIN_GRAFICOS = 0.3   # al menos el 30 % de las escenas son animaciones (el resto, clips que encajen)


def errores_grafico(g, donde):
    if not isinstance(g, dict) or g.get("tipo") not in GRAFICOS:
        return [f"{donde}: animación desconocida (tipos: {', '.join(GRAFICOS)})"]
    e = [f"{donde}: a la animación {g['tipo']} le falta {c}" for c in GRAFICOS[g["tipo"]] if not g.get(c)]
    if e:
        return e
    t = g["tipo"]
    if t == "cifra" and not isinstance(g["valor"], (int, float)):
        e.append(f"{donde}: cifra.valor tiene que ser un número")
    if t == "comparativa" and (not 2 <= len(g["items"]) <= 6 or
                               any(not isinstance(i.get("valor"), (int, float)) or not i.get("nombre") for i in g["items"])):
        e.append(f"{donde}: comparativa con 2-6 items, cada uno con nombre y valor numérico")
    if t == "linea_tiempo" and not 2 <= len(g["eventos"]) <= 6:
        e.append(f"{donde}: línea de tiempo con 2-6 eventos")
    if t == "mapa" and any(not (-90 <= p.get("lat", 999) <= 90 and -180 <= p.get("lon", 999) <= 180) or not p.get("nombre")
                           for p in g["puntos"]):
        e.append(f"{donde}: cada punto del mapa necesita nombre, lat y lon")
    if t in ("lista", "proceso") and not 2 <= len(g.get("puntos") or g.get("pasos")) <= 5:
        e.append(f"{donde}: {t} con 2-5 elementos")
    return e


def errores(b):
    e = [f"falta el campo {c}" for c in CAMPOS if not b.get(c)]
    if e:
        return e
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", b["fecha_publicacion"]):
        e.append("fecha_publicacion no es AAAA-MM-DD")
    if len(b["titulo"]) > 100:
        e.append("título de más de 100 caracteres")
    esc = b["escenas"]
    palabras = sum(len(s.get("narracion", "").split()) for s in esc)
    if not 1000 <= palabras <= 1700:
        e.append(f"{palabras} palabras de locución (1.000-1.700)")
    if not 40 <= len(esc) <= 100:
        e.append(f"{len(esc)} escenas (40-100)")
    for i, s in enumerate(esc):
        n = len(s.get("narracion", "").split())
        if not 4 <= n <= 70:
            e.append(f"escena {i}: {n} palabras (4-70)")
        v = s.get("visual") or {}
        if v.get("tipo", "video") not in TIPOS:
            e.append(f"escena {i}: tipo visual desconocido {v.get('tipo')}")
        if v.get("tipo", "video") in ("video", "foto", "esquema") and not v.get("busqueda"):
            e.append(f"escena {i}: falta visual.busqueda (en un esquema, es el material de respaldo)")
        if v.get("tipo") == "grafico":
            e += errores_grafico(v.get("grafico"), f"escena {i}")
        if v.get("tipo", "video") in ("video", "foto"):
            if not s.get("respaldo"):
                e.append(f"escena {i}: falta «respaldo» (la animación que sale si no hay un clip que muestre esto)")
            else:
                e += errores_grafico(s["respaldo"], f"escena {i} (respaldo)")
    n_graf = sum(1 for s in esc if (s.get("visual") or {}).get("tipo") == "grafico")
    if n_graf < MIN_GRAFICOS * len(esc):
        e.append(f"solo {n_graf} de {len(esc)} escenas son animaciones (mínimo {MIN_GRAFICOS:.0%})")
    caps = b["capitulos"]
    if not 3 <= len(caps) <= 8 or caps[0].get("escena") != 0:
        e.append("capítulos: entre 3 y 8 y el primero en la escena 0")
    if any(not 0 <= c.get("escena", -1) < len(esc) for c in caps):
        e.append("capítulo que apunta a una escena inexistente")
    for d in b["datos"]:
        dominios = {u.split("/")[2].removeprefix("www.") for u in d.get("fuentes", []) if re.match(r"https?://", u)}
        if len(dominios) < 2:
            e.append(f"dato con menos de 2 fuentes independientes: {d.get('afirmacion', '')[:60]}")
    e += esquemas.errores(b)
    if not (b["miniatura"].get("texto") and b["miniatura"].get("busqueda")):
        e.append("miniatura sin texto o sin busqueda")
    return e


def main():
    rutas = [Path(p) for p in sys.argv[1:]] or sorted(PEND.glob("*.json"))
    fallos = 0
    for f in rutas:
        try:
            err = errores(json.loads(f.read_text(encoding="utf-8")))
        except Exception as ex:
            err = [f"JSON no válido: {ex}"]
        if err:
            fallos += 1
            log(f"❌ {f.name}:\n  - " + "\n  - ".join(err))
        else:
            log(f"✅ {f.name}")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
