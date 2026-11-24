"""Busca material para las escenas del próximo vídeo largo.

Para cada escena sin planos: busca con su `visual.busqueda` en Pexels, Pixabay,
Wikimedia (y fotos en iNaturalist/Wikimedia si la escena pide foto), descarga una
versión ligera y pide al juez de visión que diga si muestra lo que pide la escena.
Guarda en la escena los planos aceptados. Se ejecuta varias noches seguidas hasta
cubrir todas las escenas (el progreso se guarda en el propio brief).

Uso: python -m cf.material_largo [--max-total 100]
"""
import argparse
import json
import shutil
import tempfile
from pathlib import Path

from . import analisis, fuentes, vision
from .explorador import MOV_MINIMO, _proxy
from .util import DATOS, descargar, log, run

PEND = DATOS / "largos" / "pendientes"
POR_ESCENA = 3  # candidatos a examinar por escena como máximo
ENCAJA_MIN = 7  # un clip solo entra si muestra lo que cuenta la escena (si no, va su animación)


def candidatos(visual, cache):
    q = visual.get("busqueda", "")
    clave_cache = (q, visual.get("tipo", "video"), visual.get("cientifico"))
    if clave_cache in cache:
        return cache[clave_cache]
    listas = []
    funcs = [(fuentes.pexels, q), (fuentes.pixabay, q)]
    if visual.get("cientifico"):
        funcs.append((fuentes.wikimedia, f'"{visual["cientifico"]}"'))
    if visual.get("tipo") == "foto":
        funcs = [(fuentes.wikimedia_fotos, f'"{visual["cientifico"]}"' if visual.get("cientifico") else q)]
        if visual.get("cientifico"):
            funcs.append((fuentes.inaturalist, visual["cientifico"]))
    for fn, consulta in funcs:
        try:
            listas.append(fn(consulta, 15))
        except Exception as e:
            log(f"  [{fn.__name__}] no disponible: {type(e).__name__}")
    # horizontales primero: el vídeo largo es 16:9
    res = [c for c in fuentes._intercalar(listas) if c.tipo == "foto" or c.ancho >= c.alto]
    cache[clave_cache] = res
    return res


def juzgar(c, visual, tmp):
    """Devuelve (plano, motivo_rechazo)."""
    describe = visual.get("describe") or visual.get("busqueda")
    especie = f"{visual.get('animal') or 'cualquier animal o paisaje'}. La escena pide: {describe}"
    contexto = f"{c.titulo}. {' '.join(c.etiquetas)[:200]}"
    if c.tipo == "foto":
        img = tmp / "f"
        descargar(c.url_escaneo or c.url, img, max_mb=30)
        run(["ffmpeg", "-y", "-v", "error", "-i", str(img), "-vf", "scale='min(640,iw)':-2", str(tmp / "v.jpg")])
        v = vision.juzgar((tmp / "v.jpg").read_bytes(), 1, especie, visual.get("cientifico", ""), contexto, foto=True,
                          pedido=describe)
        escenas = []
    else:
        original, proxy = tmp / "o", tmp / "p.mp4"
        descargar(c.url_escaneo or c.url, original, max_mb=350)
        _proxy(original, proxy)
        tec = analisis.analizar(proxy)
        if tec["movimiento"] < MOV_MINIMO:
            return None, "casi estático"
        d = tec["duracion"]
        tiempos = [d * f for f in (0.06, 0.22, 0.38, 0.54, 0.70, 0.88)]
        hoja = analisis.hoja_contacto(analisis.fotogramas(proxy, tiempos))
        v = vision.juzgar(hoja, 6, especie, visual.get("cientifico", ""), contexto, pedido=describe)
        escenas = tec["escenas"]
    ok = v.get("es_la_especie_buscada") and v.get("confianza", 0) >= 0.6 and v.get("calidad_visual", 0) >= 3
    if c.tipo == "foto":  # en fotos, nada de ilustraciones, láminas ni ejemplares de museo
        ok = ok and v.get("apto_para_short") and v.get("calidad_visual", 0) >= 4
    if ok and v.get("encaja", 10) < ENCAJA_MIN:
        return None, f"no muestra lo que pide la escena (encaja {v.get('encaja')}): {v.get('descripcion', '')[:70]}"
    if not ok:
        return None, (", ".join(v.get("problemas") or []) or v.get("descripcion", ""))[:100]
    # el tramo más largo y con más movimiento
    mejor = max(escenas, key=lambda e: (e["fin"] - e["ini"]) * (1 + e["movimiento"]), default=None)
    return {
        "clave": c.clave, "url": c.url, "tipo": c.tipo, "atribucion": c.atribucion,
        "desde": round(mejor["ini"], 2) if mejor else 0.0,
        "hasta": round(mejor["fin"], 2) if mejor else 0.0,
        "duracion_clip": c.duracion, "posicion_x": v.get("posicion_x", 0.5),
        "descripcion": v.get("descripcion", ""), "encaja": v.get("encaja"),
    }, None


def procesar(path, max_total):
    b = json.loads(path.read_text(encoding="utf-8"))
    cache, usados, examinados = {}, set(), 0
    for s in b["escenas"]:
        for p in s.get("planos", []):
            usados.add(p["clave"])
    objetivos = [("miniatura", b["miniatura"])] if not b["miniatura"].get("plano") else []
    objetivos += [(i, s["visual"]) for i, s in enumerate(b["escenas"])
                  if s.get("visual", {}).get("tipo", "video") in ("video", "foto")
                  and not s.get("planos") and not s.get("sin_material")]
    # los esquemas animados solo necesitan material de respaldo: se buscan al final
    objetivos += [(i, {**s["visual"], "tipo": "video"}) for i, s in enumerate(b["escenas"])
                  if s.get("visual", {}).get("tipo") == "esquema" and s["visual"].get("busqueda")
                  and not s.get("planos") and not s.get("sin_material")]
    log(f"{path.name}: {len(objetivos)} escenas sin material")
    for i, visual in objetivos:
        if examinados >= max_total:
            break
        if i == "miniatura":
            visual = {**visual, "tipo": "foto", "describe": f"retrato de {visual.get('animal', '')} de cerca, nítido"}
        cands = [c for c in candidatos(visual, cache) if c.clave not in usados][:POR_ESCENA]
        elegido, probados = None, 0
        for c in cands:
            tmp = Path(tempfile.mkdtemp())
            try:
                plano, motivo = juzgar(c, visual, tmp)
                examinados += 1
                probados += 1
            except Exception as e:
                log(f"  ⚠️ escena {i}: {c.fuente} {type(e).__name__}")
                continue
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            if plano:
                elegido = plano
                break
            log(f"  ❌ escena {i}: {c.fuente} {c.titulo[:40]} | {motivo}")
        if i == "miniatura":
            if elegido:
                b["miniatura"]["plano"] = elegido
            continue
        if elegido:
            usados.add(elegido["clave"])
            b["escenas"][i]["planos"] = [elegido]
            log(f"  ✅ escena {i}: {elegido['descripcion'][:90]}")
        elif probados or not cands:  # si solo hubo errores de red, se reintenta otra noche
            # sin candidatos válidos: el montaje pone la animación de respaldo de la escena
            b["escenas"][i]["sin_material"] = True
            log(f"  ➖ escena {i}: sin material ({visual.get('busqueda')})")
        path.write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")
    faltan = sum(1 for s in b["escenas"] if s.get("visual", {}).get("tipo", "video") in ("video", "foto")
                 and not s.get("planos") and not s.get("sin_material"))
    path.write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Quedan {faltan} escenas por cubrir | llamadas de visión: {examinados}")
    return examinados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-total", type=int, default=100)
    a = ap.parse_args()
    restante = a.max_total
    for f in sorted(PEND.glob("*.json")):
        if restante <= 0:
            break
        restante -= procesar(f, restante)


if __name__ == "__main__":
    main()
