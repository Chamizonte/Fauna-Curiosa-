"""Programa los shorts en YouTube con antelación.

GitHub lanza los workflows programados con horas de retraso o se los salta, así que no
publicamos "a la hora": en cuanto el workflow arranca (de noche, normalmente), monta los
shorts de los próximos turnos y los sube a YouTube como PROGRAMADOS. YouTube los
publica a su hora exacta: 09:00, 13:00, 17:00 y 21:00 hora de España.

Reglas:
- Turnos que se programan: los que caen entre ahora + 20 min y ahora + 28 h y aún no
  tienen short (se ve en datos/shorts/publicados/, campo publicacion.fecha).
- Máximo 4 subidas por ejecución y 5 por día de cuota de YouTube (cada subida gasta
  1.600 de 10.000 unidades; se deja hueco para el vídeo largo).
- Si un guion no se puede montar, pasa a datos/shorts/rechazados/ con el motivo y se
  prueba con el siguiente: un guion roto no deja el turno vacío.

Uso:
  python -m cf.programar_shorts --comprobar   escribe falta=si|no en $GITHUB_OUTPUT
  python -m cf.programar_shorts --uno         programa el siguiente turno libre
      (código 0 = programado, 4 = nada que hacer). El workflow hace commit tras cada uno.
"""
import argparse
import datetime as dt
import json
import os
import shutil
import sys
import traceback
from zoneinfo import ZoneInfo

from .util import DATOS, log

HORAS = [9, 13, 17, 21]                 # hora de España
ES = ZoneInfo("Europe/Madrid")
PACIFICO = ZoneInfo("America/Los_Angeles")  # la cuota de YouTube se reinicia a medianoche de allí
MARGEN = dt.timedelta(minutes=20)
HORIZONTE = dt.timedelta(hours=28)
MAX_DIA_CUOTA = 5
PEND = DATOS / "shorts" / "pendientes"
PUBL = DATOS / "shorts" / "publicados"
RECH = DATOS / "shorts" / "rechazados"
UTC = dt.timezone.utc


def _utc(txt):
    return dt.datetime.fromisoformat(txt.replace("Z", "+00:00")).astimezone(UTC)


def _publicaciones():
    out = []
    for f in PUBL.glob("*.json"):
        p = json.loads(f.read_text(encoding="utf-8")).get("publicacion") or {}
        if p.get("fecha"):
            out.append(p)
    return out


def turnos_libres(ahora):
    ocupados = {_utc(p["fecha"]).replace(second=0, microsecond=0) for p in _publicaciones()}
    libres = []
    dia = ahora.astimezone(ES).date()
    for d in range(3):
        for h in HORAS:
            t = dt.datetime.combine(dia + dt.timedelta(days=d), dt.time(h), ES).astimezone(UTC)
            if ahora + MARGEN < t <= ahora + HORIZONTE and t not in ocupados:
                libres.append(t)
    return sorted(libres)


def subidas_hoy(ahora):
    hoy = ahora.astimezone(PACIFICO).date()
    return sum(1 for p in _publicaciones()
               if _utc(p.get("subido") or p["fecha"]).astimezone(PACIFICO).date() == hoy)


def briefs():
    return [f for f in sorted(PEND.glob("*.json")) if not f.name.startswith("prueba-")]


def cupo(ahora):
    return min(MAX_DIA_CUOTA - subidas_hoy(ahora), len(turnos_libres(ahora)), len(briefs()))


def programar_uno(ahora):
    from .montaje_short import biblioteca, montar
    from .publicar_short import descripcion, subir

    libres = turnos_libres(ahora)
    if not libres or subidas_hoy(ahora) >= MAX_DIA_CUOTA:
        return False
    turno = libres[0]
    for f in briefs():
        brief = json.loads(f.read_text(encoding="utf-8"))
        log(f"Turno {turno.astimezone(ES):%d/%m %H:%M} (España) → {f.name} ({brief['formato']}, {brief['animal']})")
        try:
            mp4, con_voz = montar(f)
        except Exception:
            motivo = traceback.format_exc()[-1500:]
            log(f"⚠️ No se pudo montar {f.name}; se aparta y se prueba con el siguiente:\n{motivo}")
            RECH.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), RECH / f.name)
            (RECH / f"{f.stem}.motivo.txt").write_text("montaje: " + motivo, encoding="utf-8")
            continue
        url = subir(mp4, brief["titulo"], descripcion(brief, biblioteca()), brief.get("etiquetas", []),
                    publicar_en=turno)
        log(f"✅ Programado para {turno.astimezone(ES):%d/%m %H:%M}: {url}")
        brief["publicacion"] = {"url": url, "fecha": turno.strftime("%Y-%m-%dT%H:%MZ"),
                                "subido": dt.datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
                                "programado": True, "con_voz": con_voz, "privacidad": "public"}
        PUBL.mkdir(parents=True, exist_ok=True)
        (PUBL / f.name).write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
        f.unlink()
        return True
    log("❌ No queda ningún guion que se pueda montar.")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comprobar", action="store_true")
    ap.add_argument("--uno", action="store_true")
    a = ap.parse_args()
    ahora = dt.datetime.now(UTC)
    libres = turnos_libres(ahora)
    log("Turnos libres: " + (", ".join(f"{t.astimezone(ES):%d/%m %H:%M}" for t in libres) or "ninguno")
        + f" | guiones: {len(briefs())} | subidas hoy (cuota): {subidas_hoy(ahora)}/{MAX_DIA_CUOTA}")
    if a.comprobar:
        n = cupo(ahora)
        if libres and not briefs():
            print("::warning::Hay turnos sin short y no quedan guiones (la sala escribe más de noche)")
        log(f"Shorts a programar ahora: {max(n, 0)}")
        salida = os.environ.get("GITHUB_OUTPUT")
        if salida:
            with open(salida, "a", encoding="utf-8") as fh:
                fh.write(f"falta={'si' if n > 0 else 'no'}\n")
        return
    if a.uno:
        sys.exit(0 if programar_uno(ahora) else 4)


if __name__ == "__main__":
    main()
