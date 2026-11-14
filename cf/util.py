"""Utilidades comunes: entorno, HTTP con reintentos, FFmpeg y descargas."""
import json
import os
import subprocess
import time
from pathlib import Path

# Formato que exige la política de User-Agent de Wikimedia:
# nombre/versión (contacto público) librería/versión
UA = {"User-Agent": "CuriosaFaunaBot/2.0 (https://www.youtube.com/@CuriosaFauna-y3s; canal educativo de fauna) "
                    "python-requests/2"}
_bloqueados = {}  # dominio -> nº de descargas rechazadas seguidas en esta ejecución
RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"


def env(nombre, defecto=None, requerido=False):
    """Lee una variable de entorno sin espacios ni saltos de línea colados."""
    v = os.environ.get(nombre)
    v = v.strip() if v else None
    if not v:
        if requerido:
            raise RuntimeError(f"Falta la variable de entorno {nombre}")
        return defecto
    return v


def log(*a):
    print(*a, flush=True)


def get_json(url, params=None, headers=None, intentos=5, timeout=60):
    """GET que tolera límites de uso (429/5xx o respuesta no JSON) con espera creciente.
    Nunca incluye cabeceras en los errores, para no filtrar claves."""
    import requests  # import diferido: los scripts de solo lectura no lo necesitan
    h = {**UA, **(headers or {})}
    ultimo = None
    for i in range(intentos):
        try:
            r = requests.get(url, params=params, headers=h, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                ultimo = f"HTTP {r.status_code}"
            else:
                r.raise_for_status()
                return r.json()
        except (requests.RequestException, ValueError) as e:
            ultimo = type(e).__name__
        time.sleep(4 * (i + 1))
    raise RuntimeError(f"Fallo al consultar {url.split('?')[0]}: {ultimo}")


_ultima_descarga = {}


def descargar(url, destino, max_mb=400, intentos=5):
    """Descarga respetando a los servidores: pausa entre descargas del mismo
    dominio y espera creciente si responden 429 (Wikimedia lo hace)."""
    import requests
    destino = Path(destino)
    dominio = url.split("/")[2]
    # Si un servidor ya nos rechazó dos veces seguidas, no se insiste en esta ejecución
    # (cada intento fallido cuesta minutos de espera y minutos de Actions).
    if _bloqueados.get(dominio, 0) >= 2:
        raise RuntimeError(f"{dominio} nos está limitando; se reintentará otro día")
    for i in range(intentos):
        espera = 4 - (time.time() - _ultima_descarga.get(dominio, 0))
        if espera > 0:
            time.sleep(espera)
        _ultima_descarga[dominio] = time.time()
        with requests.get(url, headers=UA, stream=True, timeout=120) as r:
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(15 * (i + 1))
                continue
            r.raise_for_status()
            total = 0
            with open(destino, "wb") as f:
                for trozo in r.iter_content(1 << 16):
                    total += len(trozo)
                    if total > max_mb * 1024 * 1024:
                        raise RuntimeError(f"Archivo demasiado grande (> {max_mb} MB)")
                    f.write(trozo)
            _bloqueados[dominio] = 0
            return destino
    _bloqueados[dominio] = _bloqueados.get(dominio, 0) + 1
    raise RuntimeError(f"Descarga rechazada repetidamente por {dominio}")


def run(cmd, timeout=1800):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"Error ejecutando {cmd[0]}: {p.stderr[-800:]}")
    return p.stdout


def sondear(path):
    """Duración, ancho, alto y fps de un vídeo con ffprobe."""
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)])
    d = json.loads(out)
    s = (d.get("streams") or [{}])[0]
    num, den = (s.get("r_frame_rate") or "30/1").split("/")
    return {
        "duracion": float(d.get("format", {}).get("duration") or 0),
        "ancho": int(s.get("width") or 0),
        "alto": int(s.get("height") or 0),
        "fps": float(num) / float(den or 1),
    }


def leer_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def anadir_jsonl(path, registro):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
