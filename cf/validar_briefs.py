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
FORMATOS = {"por_que", "comparativa", "mito", "tarjeta", "momento"}
ESP_MINIMA = 6   # nota de espectacularidad mínima del plano que abre el short (vídeo primero)
CAMPOS = ["id", "formato", "animal", "gancho_pantalla", "datos", "planos", "titulo", "descripcion", "etiquetas"]


def texto_plano(t):
    """Texto de la tarjeta sin las marcas de resaltado **…**."""
    return re.sub(r"\*\*", "", t or "")


# La voz no puede señalar algo que no sale en la imagen («Mira cómo come…» sobre un
# cocodrilo tumbado). En las frases que señalan la imagen, cada acción nombrada tiene que
# estar en lo que la visión describió de los planos del short.
SENALA = re.compile(r"\b(mira|mirad|fíjate|fijaos|observa|observad|ves|veis|aquí|ahí)\b|en (pantalla|la imagen|este vídeo)")
ACCIONES = {  # acción: (cómo la dice el guion, raíces aceptadas en la descripción de la visión)
    "comer": (r"\b(come|comen|comiendo|devora\w*|engull\w*|mastica\w*|se zampa\w*)\b",
              ["come", "comer", "comiendo", "alimenta", "devor", "engull", "mastic"]),
    "cazar": (r"\b(caza|cazan|cazando|ataca\w*|atrapa\w*|captura\w*)\b", ["caz", "atac", "atrap", "captur", "presa"]),
    "saltar": (r"\bsalt(a|an|ando|o)\b", ["salt"]),
    "volar": (r"\b(vuela|vuelan|volando|planea\w*)\b", ["vuel", "volar", "volando", "plane"]),
    "nadar": (r"\b(nadan|nadando|bucea\w*)\b", ["nad", "bucea", "sumerg"]),
    "correr": (r"\b(corre|corren|corriendo)\b", ["corr", "carrera"]),
    "dormir": (r"\b(duerme|duermen|durmiendo)\b", ["duerm", "dorm"]),
    "pelear": (r"\b(pelea\w*|lucha\w*)\b", ["pele", "luch", "combat"]),
    "llorar": (r"\b(llora\w*|lágrima\w*)\b", ["llor", "lágrim"]),
    "beber": (r"\b(bebe|beben|bebiendo)\b", ["beb"]),
    "cambiar de color": (r"cambia\w* de color", ["color"]),
}


def senala_lo_que_no_se_ve(b, bib):
    vision = " ".join(
        " ".join([v.get("descripcion", ""), v.get("momento_destacado", ""), " ".join(v.get("acciones", []))])
        for v in ((bib.get(p.get("clave")) or {}).get("vision") or {} for p in b.get("planos", []))
    ).lower()
    texto = " ".join(texto_plano(b.get(c, "")) for c in ("guion", "texto_tarjeta", "gancho_pantalla"))
    e = []
    for frase in re.split(r"(?<=[.!?¿¡…])\s+", texto):
        f = frase.lower()
        if not SENALA.search(f):
            continue
        for accion, (dice, raices) in ACCIONES.items():
            if re.search(dice, f) and not any(r in vision for r in raices):
                e.append(f"la voz señala la imagen («{frase.strip()[:70]}») pero en los planos no se ve "
                         f"{accion}: o se elige un plano donde se vea, o se cuenta el dato sin señalar")
    return e


def errores(b, bib):
    tarjeta = b.get("formato") in ("tarjeta", "momento")   # sin voz: texto que se lee
    campos = CAMPOS + (["texto_tarjeta"] if tarjeta else ["guion"])
    e = [f"falta el campo {c}" for c in campos if not b.get(c)]
    if e:
        return e
    if b["formato"] not in FORMATOS:
        e.append(f"formato desconocido: {b['formato']}")
    if tarjeta:
        n = len(texto_plano(b["texto_tarjeta"]).split())
        lo, hi = (12, 30) if b["formato"] == "momento" else (30, 70)
        if not lo <= n <= hi:
            e.append(f"el texto de la {b['formato']} tiene {n} palabras ({lo}-{hi})")
        if b["texto_tarjeta"].count("**") % 2:
            e.append("resaltado ** sin cerrar")
    else:
        n = len(b["guion"].split())
        if not 45 <= n <= 85:
            e.append(f"el guion tiene {n} palabras (45-85)")
    if b["formato"] == "mito":
        # pregunta abierta: el vídeo no responde; la respuesta va en la descripción
        if "respuesta" not in b["descripcion"].lower():
            e.append("mito: la descripción debe incluir «Respuesta: …»")
        if "comentario" not in b["guion"].lower():
            e.append("mito: el guion debe cerrar pidiendo el voto en comentarios")
        delata = re.search(r"\b(falso|mito|en realidad|la verdad es)\b", b["guion"].lower())
        if delata:
            e.append(f"mito: el guion delata la respuesta («{delata.group(1)}»)")
    if len(b["gancho_pantalla"].split()) > 7:
        e.append("gancho en pantalla de más de 7 palabras")
    if len(b["titulo"]) > 100:
        e.append("título de más de 100 caracteres")
    for d in b["datos"]:
        urls = [u for u in d.get("fuentes", []) if re.match(r"https?://", u)]
        dominios = {u.split("/")[2].removeprefix("www.") for u in urls}
        if len(dominios) < 2:
            e.append(f"dato con menos de 2 fuentes independientes: {d.get('afirmacion', '')[:60]}")
    lo, hi = {"momento": (1, 2), "tarjeta": (1, 4)}.get(b["formato"], (3, 8))
    if not lo <= len(b["planos"]) <= hi:
        e.append(f"{len(b['planos'])} planos ({lo}-{hi})")
    if b["formato"] == "momento":
        tramo = sum(p.get("hasta", 0) - p.get("desde", 0) for p in b["planos"])
        if not 5 <= tramo <= 12.5:
            e.append(f"momento: el clip dura {tramo:.1f} s en pantalla (6-12)")
    # vídeo primero: el short abre con un vídeo en el que pasa algo, nunca con una foto
    primero = bib.get((b["planos"] or [{}])[0].get("clave"))
    if primero:
        if primero.get("tipo") == "foto":
            e.append("el primer plano es una foto: el short tiene que abrir con un vídeo en el que pase algo")
        nota = (primero.get("vision") or {}).get("espectacularidad")
        if nota is not None and nota < ESP_MINIMA:
            e.append(f"el primer plano es poco llamativo (espectacularidad {nota}, mínimo {ESP_MINIMA}): "
                     f"abre con el momento más espectacular del animal")
    e += senala_lo_que_no_se_ve(b, bib)
    for p in b["planos"]:
        m = bib.get(p.get("clave"))
        if not m:
            e.append(f"clip que no está en la biblioteca: {p.get('clave')}")
            continue
        if m["animal"] != b["animal"]:
            e.append(f"clip de otro animal ({m['animal']}): {p['clave']}")
        if m.get("tipo") == "foto":
            # en una foto, desde/hasta solo indican cuántos segundos se ve
            if not 1.5 <= p.get("hasta", 0) - p.get("desde", 0) <= 12:
                e.append(f"foto {p['clave']}: duración en pantalla fuera de 1,5-12 s")
            continue
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
