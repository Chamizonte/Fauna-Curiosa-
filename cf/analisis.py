"""Análisis técnico de un clip sin IA: cortes de escena, movimiento y nitidez.

Sirve para descartar clips estáticos o borrosos antes de gastar llamadas de
visión, y para proponer los tramos (escenas) de los que cortar planos.
"""
import cv2
import numpy as np

PASO_S = 0.25          # analiza 4 fotogramas por segundo
UMBRAL_CORTE = 38.0    # diferencia media (0-255) que se considera cambio de plano
ESCENA_MIN_S = 2.0


def analizar(path):
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    paso = max(1, int(round(fps * PASO_S)))
    prev = None
    tiempos, difs, nitidez = [], [], []
    i = 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % paso == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            peq = cv2.resize(frame, (192, 108))
            gris = cv2.cvtColor(peq, cv2.COLOR_BGR2GRAY)
            if prev is not None:
                difs.append(float(np.mean(cv2.absdiff(gris, prev))))
                tiempos.append(i / fps)
            nitidez.append(float(cv2.Laplacian(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()))
            prev = gris
        i += 1
    cap.release()
    duracion = (total or i) / fps

    # Escenas: cortar donde la diferencia supera el umbral.
    cortes = [0.0] + [t for t, d in zip(tiempos, difs) if d > UMBRAL_CORTE] + [duracion]
    escenas = []
    for a, b in zip(cortes, cortes[1:]):
        if b - a < ESCENA_MIN_S:
            continue
        mov = [d for t, d in zip(tiempos, difs) if a < t < b and d <= UMBRAL_CORTE]
        escenas.append({
            "ini": round(a, 2), "fin": round(b, 2),
            # movimiento medio dentro de la escena (sin contar los cortes)
            "movimiento": round(float(np.mean(mov)) if mov else 0.0, 2),
        })
    mov_global = [d for d in difs if d <= UMBRAL_CORTE]
    return {
        "duracion": round(duracion, 2),
        "movimiento": round(float(np.mean(mov_global)) if mov_global else 0.0, 2),
        "nitidez": round(float(np.median(nitidez)) if nitidez else 0.0, 1),
        "escenas": escenas,
    }


def fotogramas(path, tiempos, ancho=640):
    """Extrae fotogramas en los segundos indicados (para la hoja de contacto)."""
    cap = cv2.VideoCapture(str(path))
    out = []
    for t in tiempos:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if ok:
            h, w = frame.shape[:2]
            frame = cv2.resize(frame, (ancho, int(h * ancho / w)))
            out.append((t, frame))
    cap.release()
    return out


def hoja_contacto(frames, columnas=3):
    """Une los fotogramas en una cuadrícula numerada con su segundo (una sola imagen
    = una sola llamada de visión)."""
    if not frames:
        return None
    h, w = frames[0][1].shape[:2]
    filas = (len(frames) + columnas - 1) // columnas
    lienzo = np.zeros((filas * h, columnas * w, 3), dtype=np.uint8)
    for k, (t, f) in enumerate(frames):
        f = cv2.resize(f, (w, h))
        r, c = divmod(k, columnas)
        lienzo[r * h:(r + 1) * h, c * w:(c + 1) * w] = f
        etiqueta = f"#{k + 1}  {t:.1f}s"
        cv2.rectangle(lienzo, (c * w, r * h), (c * w + 190, r * h + 40), (0, 0, 0), -1)
        cv2.putText(lienzo, etiqueta, (c * w + 8, r * h + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    ok, buf = cv2.imencode(".jpg", lienzo, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buf.tobytes() if ok else None
