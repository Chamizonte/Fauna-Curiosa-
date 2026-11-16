"""¿Toca publicar un short ahora?

GitHub arranca los workflows programados con horas de retraso o se los salta cuando
va cargado. Por eso publicar-short.yml se lanza cada hora y este script decide:
toca publicar si hoy (UTC) se han publicado menos shorts que turnos ya pasados
(08, 12, 16 y 20 UTC) y han pasado al menos 2 h 30 min desde el último.
Así un turno perdido se recupera en la siguiente pasada, sin ráfagas.
Si no quedan guiones, no toca (aviso en el run) y se espera a la sala de redacción.

Uso:
  python -m cf.turno            escribe toca=si|no en $GITHUB_OUTPUT (y en pantalla)
"""
import datetime as dt
import json
import os

from .util import DATOS, log

TURNOS = [8, 12, 16, 20]
HUECO = dt.timedelta(hours=2, minutes=30)
PUBL = DATOS / "shorts" / "publicados"
PEND = DATOS / "shorts" / "pendientes"


def _fecha(txt):
    return dt.datetime.fromisoformat(txt.replace("Z", "+00:00")).replace(tzinfo=None)


def publicaciones():
    fechas = []
    for f in PUBL.glob("*.json"):
        p = json.loads(f.read_text(encoding="utf-8")).get("publicacion") or {}
        if p.get("fecha"):
            fechas.append(_fecha(p["fecha"]))
    return sorted(fechas)


def toca(ahora=None):
    ahora = ahora or dt.datetime.utcnow()
    hechas = publicaciones()
    hoy = [f for f in hechas if f.date() == ahora.date()]
    debidas = sum(1 for h in TURNOS if ahora.hour >= h)
    if len(hoy) >= debidas:
        return False, f"hoy van {len(hoy)} de {debidas} turnos pasados"
    if hechas and ahora - hechas[-1] < HUECO:
        return False, f"el último fue hace {ahora - hechas[-1]}; se espera a las 2 h 30 min"
    return True, f"hoy van {len(hoy)} de {debidas} turnos pasados"


def main():
    si, motivo = toca()
    if si and not any(not f.name.startswith("prueba-") for f in PEND.glob("*.json")):
        si, motivo = False, "no quedan guiones pendientes (la sala escribe más a las 02:30 UTC)"
        print(f"::warning::Turno sin short: {motivo}")
    log(("✅ Toca publicar: " if si else "⏸️ No toca: ") + motivo)
    salida = os.environ.get("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write(f"toca={'si' if si else 'no'}\n")


if __name__ == "__main__":
    main()
