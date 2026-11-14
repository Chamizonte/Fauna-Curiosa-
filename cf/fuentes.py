"""Búsqueda de vídeo y fotos reales con licencia reutilizable.

Vídeo: Wikimedia Commons (dominio público, CC0 y CC BY), Pixabay y Pexels.
Fotos: Wikimedia Commons e iNaturalist (solo fotos CC BY o CC0; la licencia por
defecto de iNaturalist es NC y se descarta).
Se excluyen las licencias NC, ND y SA: SA obligaría a publicar nuestro vídeo
con esa misma licencia, y YouTube no lo permite.
"""
import re
from dataclasses import asdict, dataclass, field

from .util import env, get_json

ANCHO_MIN = 1280
DURACION_MIN = 6
FOTO_MIN = 1400   # lado mayor mínimo de una foto


@dataclass
class Candidato:
    fuente: str
    id: str
    url: str
    pagina: str
    titulo: str
    autor: str
    licencia: str
    duracion: float
    ancho: int
    alto: int
    tamano_mb: float = 0
    etiquetas: list = field(default_factory=list)
    url_escaneo: str = ""   # versión ligera para analizar (Wikimedia ofrece 480p/360p)
    tipo: str = "video"     # "video" o "foto"

    @property
    def clave(self):
        return f"{self.fuente}:{self.id}"

    @property
    def atribucion(self):
        if self.fuente == "inaturalist":
            lic = "dominio público" if "dominio" in self.licencia else self.licencia
            return f"Foto de {self.autor} ({lic}), vía iNaturalist ({self.pagina})"
        if self.fuente == "wikimedia" and "dominio" not in self.licencia:
            return f"«{self.titulo}» de {self.autor}, {self.licencia}, vía Wikimedia Commons ({self.pagina})"
        if self.fuente == "wikimedia":
            return f"«{self.titulo}», dominio público, vía Wikimedia Commons ({self.pagina})"
        return f"Vídeo de {self.autor} en {self.fuente.capitalize()} ({self.pagina})"

    def dict(self):
        d = asdict(self)
        d["clave"] = self.clave
        d["atribucion"] = self.atribucion
        return d


def _sin_html(t):
    return re.sub(r"<[^>]+>", "", t or "").strip()


def tipo_licencia(lic):
    """Devuelve 'dominio publico', 'CC BY x.y' o None si no se puede usar."""
    l = (lic or "").lower().replace("_", " ").replace("-", " ")
    if any(k in l.split() for k in ("nc", "nd", "sa")):
        return None
    if "cc0" in l or "public domain" in l or l.startswith("pd") or "pdm" in l:
        return "dominio publico"
    m = re.search(r"cc by (\d\.\d)", l)
    if m:
        return f"CC BY {m.group(1)}"
    return None


def _derivado(p, alturas):
    """URL del derivado transcodificado de Wikimedia con la primera altura disponible."""
    ders = (p.get("videoinfo") or [{}])[0].get("derivatives") or []
    for h in alturas:
        for d in ders:
            if d.get("height") == h and d.get("src"):
                return d["src"]
    return None


def wikimedia(consulta, maximo=40):
    out, cont = [], {}
    while len(out) < maximo:
        r = get_json("https://commons.wikimedia.org/w/api.php", params={
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": f"{consulta} filetype:video", "gsrnamespace": 6, "gsrlimit": 50,
            "prop": "imageinfo|videoinfo", "iiprop": "url|size|mime|extmetadata",
            "viprop": "derivatives", **cont})
        for p in r.get("query", {}).get("pages", {}).values():
            ii = (p.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata") or {}
            lic = tipo_licencia(meta.get("LicenseShortName", {}).get("value"))
            if not lic or (ii.get("width") or 0) < ANCHO_MIN or (ii.get("duration") or 0) < DURACION_MIN:
                continue
            titulo = p.get("title", "").removeprefix("File:")
            out.append(Candidato(
                fuente="wikimedia", id=str(p.get("pageid")),
                # para montar: 1080p transcodificado (pesa menos que el original)
                url=_derivado(p, (1080, 1440, 2160)) or ii.get("url"),
                url_escaneo=_derivado(p, (480, 360, 720)) or "",
                pagina=ii.get("descriptionurl") or "", titulo=titulo,
                autor=_sin_html(meta.get("Artist", {}).get("value")) or "autor desconocido",
                licencia=lic, duracion=float(ii.get("duration") or 0),
                ancho=int(ii.get("width") or 0), alto=int(ii.get("height") or 0),
                tamano_mb=round((ii.get("size") or 0) / 1e6, 1),
                etiquetas=[_sin_html(meta.get("ImageDescription", {}).get("value"))[:300]],
            ))
        if "continue" not in r:
            break
        cont = r["continue"]
    return out[:maximo]


def wikimedia_fotos(consulta, maximo=20):
    r = get_json("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "format": "json", "generator": "search",
        # solo imágenes de calidad o destacadas: sin esto salen ejemplares de museo y láminas
        "gsrsearch": f"{consulta} filetype:bitmap incategory:Quality_images|Featured_pictures_on_Wikimedia_Commons", "gsrnamespace": 6, "gsrlimit": 50,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 2048})
    out = []
    for p in r.get("query", {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata") or {}
        lic = tipo_licencia(meta.get("LicenseShortName", {}).get("value"))
        w, h = int(ii.get("width") or 0), int(ii.get("height") or 0)
        if not lic or max(w, h) < FOTO_MIN or ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        grande = ii.get("thumburl") or ii.get("url")
        out.append(Candidato(
            fuente="wikimedia", id=str(p.get("pageid")), url=grande,
            url_escaneo=grande.replace("/2048px-", "/640px-") if "/2048px-" in grande else grande,
            pagina=ii.get("descriptionurl") or "", titulo=p.get("title", "").removeprefix("File:"),
            autor=_sin_html(meta.get("Artist", {}).get("value")) or "autor desconocido",
            licencia=lic, duracion=0, ancho=w, alto=h, tipo="foto",
            etiquetas=[_sin_html(meta.get("ImageDescription", {}).get("value"))[:300]],
        ))
    return out[:maximo]


def inaturalist(cientifico, maximo=20):
    """Fotos de observaciones de grado de investigación (especie confirmada por la comunidad)."""
    # taxon_id incluye las especies descendientes (taxon_name no: "Octopoda" daría 0)
    t = get_json("https://api.inaturalist.org/v1/taxa", params={"q": cientifico, "per_page": 1})
    taxones = [x for x in t.get("results", []) if x.get("name", "").lower() == cientifico.lower()]
    if not taxones:
        return []
    r = get_json("https://api.inaturalist.org/v1/observations", params={
        "taxon_id": taxones[0]["id"], "quality_grade": "research", "photo_license": "cc-by,cc0",
        "photos": "true", "order_by": "votes", "per_page": 50})
    out = []
    for o in r.get("results", []):
        for f in o.get("photos", [])[:2]:
            lic_code = (f.get("license_code") or "").lower()
            if lic_code not in ("cc-by", "cc0"):
                continue
            dim = f.get("original_dimensions") or {}
            w, h = int(dim.get("width") or 0), int(dim.get("height") or 0)
            if max(w, h) < FOTO_MIN or not f.get("url"):
                continue
            autor = re.sub(r"^\(c\)\s*", "", (f.get("attribution") or "").split(",")[0]).strip()
            out.append(Candidato(
                fuente="inaturalist", id=str(f["id"]), tipo="foto",
                url=f["url"].replace("/square.", "/original."),
                url_escaneo=f["url"].replace("/square.", "/medium."),
                pagina=f"https://www.inaturalist.org/photos/{f['id']}",
                titulo=(o.get("taxon") or {}).get("name", cientifico),
                autor=autor or (o.get("user") or {}).get("login", "autor desconocido"),
                licencia="dominio publico" if lic_code == "cc0" else "CC BY 4.0",
                duracion=0, ancho=w, alto=h,
                etiquetas=[(o.get("place_guess") or "")[:120]],
            ))
            if len(out) >= maximo:
                return out
    return out


def pixabay(consulta, maximo=30):
    key = env("PIXABAY_API_KEY")
    if not key:
        return []
    r = get_json("https://pixabay.com/api/videos/", params={
        "key": key, "q": consulta, "per_page": min(200, maximo), "video_type": "film"})
    out = []
    for h in r.get("hits", []):
        v = h.get("videos", {})
        mejor = next((v[k] for k in ("large", "medium") if v.get(k, {}).get("width", 0) >= ANCHO_MIN), None)
        if not mejor or h.get("duration", 0) < DURACION_MIN:
            continue
        out.append(Candidato(
            fuente="pixabay", id=str(h["id"]), url=mejor["url"], pagina=h.get("pageURL", ""),
            titulo=h.get("tags", ""), autor=h.get("user", ""), licencia="Pixabay Content License",
            duracion=float(h.get("duration", 0)), ancho=mejor["width"], alto=mejor["height"],
            tamano_mb=round(mejor.get("size", 0) / 1e6, 1), etiquetas=h.get("tags", "").split(", "),
        ))
    return out


def pexels(consulta, maximo=30):
    key = env("PEXELS_API_KEY")
    if not key:
        return []
    r = get_json("https://api.pexels.com/videos/search", headers={"Authorization": key},
                 params={"query": consulta, "per_page": min(80, maximo)})
    out = []
    for v in r.get("videos", []):
        archivos = [f for f in v.get("video_files", [])
                    if f.get("file_type") == "video/mp4" and ANCHO_MIN <= max(f.get("width") or 0, f.get("height") or 0) <= 2160]
        if not archivos or v.get("duration", 0) < DURACION_MIN:
            continue
        f = max(archivos, key=lambda x: x.get("width") or 0)
        out.append(Candidato(
            fuente="pexels", id=str(v["id"]), url=f["link"], pagina=v.get("url", ""),
            titulo=v.get("url", "").rstrip("/").split("/")[-1].replace("-", " "),
            autor=(v.get("user") or {}).get("name", ""), licencia="Pexels License",
            duracion=float(v.get("duration", 0)), ancho=f.get("width") or 0, alto=f.get("height") or 0,
        ))
    return out


def _intercalar(listas):
    out = []
    for i in range(max((len(l) for l in listas), default=0)):
        out += [l[i] for l in listas if i < len(l)]
    return out


def buscar(animal, por_fuente=20, fotos=True):
    """Candidatos de todas las fuentes, intercalados (vídeos primero, luego fotos).

    En Wikimedia e iNaturalist se busca por nombre científico: el nombre común en
    inglés trae ruido ("wolf" devuelve vídeos del gobernador Tom Wolf)."""
    listas = []
    cient = animal.get("cientifico")
    q_wm = f'"{cient}"' if cient else animal["en"]
    consultas = {wikimedia: q_wm, pixabay: animal["en"], pexels: animal["en"]}
    if fotos:
        consultas[wikimedia_fotos] = q_wm
        if cient:
            consultas[inaturalist] = cient
    vistos = set()
    for fn, q in consultas.items():
        try:
            res = [c for c in fn(q, por_fuente) if c.clave not in vistos]
            vistos.update(c.clave for c in res)
            listas.append(res)
        except Exception as e:  # una fuente caída no debe parar el resto
            print(f"  [{fn.__name__}] no disponible: {e}", flush=True)
    return _intercalar(listas)
