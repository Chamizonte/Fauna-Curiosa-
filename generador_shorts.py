#!/usr/bin/env python3
"""
Generador automático de SHORTS para el canal (historia de animales).

Pensado para ejecutarse SOLO, sin que nadie lo mire, disparado por GitHub
Actions varias veces al día. Cada ejecución:

  1. Lee el "banco de temas" (una Google Sheet en Drive) y coge el primer
     dato/curiosidad que todavía no se ha usado.
  2. Descarga una foto/vídeo real (Wikimedia/Pexels/Pixabay) para el fondo.
  3. Pone encima la tarjeta de texto (mismo formato "SABIAS QUE...?").
  4. Le pone la pista fija de piano chill (o el sonido real del clip si lo
     detecta y tiene sentido conservarlo).
  5. Sube el short a YouTube.
  6. Marca esa fila del banco de temas como "usada" para no repetirla.

No requiere Colab ni que nadie abra el navegador: toda la autenticación con
Google (YouTube + Drive + Sheets) se hace con un refresh_token guardado como
secreto, sin interacción humana.

Variables de entorno necesarias (se configuran como Secrets en GitHub, ver
GITHUB-SETUP.md):
  PEXELS_API_KEY, PIXABAY_API_KEY
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN, YOUTUBE_REFRESH_TOKEN
Opcionales:
  TOPICS_SHEET_NAME      (por defecto "Banco de temas - Shorts")
  MUSICA_DRIVE_NOMBRE    (por defecto "shorts_musica_piano_chill.mp3")
  MARCA_TEXTO            (por defecto "SABIAS QUE...?")
  PRIVACIDAD_YOUTUBE     (por defecto "public"; "private"/"unlisted"/"public")
"""

import os
import re
import io
import json
import random
import subprocess
from datetime import date
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# ---------------------------------------------------------------------------
# 0) Configuración
# ---------------------------------------------------------------------------

def _env_limpio(nombre, requerido=True):
    v = os.environ.get(nombre)
    if v is None:
        if requerido:
            raise RuntimeError(f"Falta la variable de entorno {nombre}")
        return None
    return v.strip()  # quita espacios/saltos de línea colados al pegar el Secret


PEXELS_API_KEY = _env_limpio("PEXELS_API_KEY", requerido=False)
PIXABAY_API_KEY = _env_limpio("PIXABAY_API_KEY", requerido=False)

GOOGLE_CLIENT_ID = _env_limpio("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = _env_limpio("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = _env_limpio("GOOGLE_REFRESH_TOKEN")
YOUTUBE_REFRESH_TOKEN = _env_limpio("YOUTUBE_REFRESH_TOKEN")

TOPICS_SHEET_NAME = os.environ.get("TOPICS_SHEET_NAME", "Banco de temas - Shorts")
MUSICA_DRIVE_NOMBRE = os.environ.get("MUSICA_DRIVE_NOMBRE", "shorts_musica_piano_chill.mp3")
MARCA_TEXTO = os.environ.get("MARCA_TEXTO", "SABIAS QUE...?")
PRIVACIDAD_YOUTUBE = os.environ.get("PRIVACIDAD_YOUTUBE") or "public"

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
]
TOKEN_URI = "https://oauth2.googleapis.com/token"

COLOR_HEADER_BG = (56, 189, 248)
COLOR_HEADER_TXT = (10, 15, 25)
COLOR_TEXTO = (255, 255, 255)
COLOR_VERDE = (74, 222, 128)
COLOR_AZUL = (56, 189, 248)
CARD_BG = (10, 12, 18, 190)

ANCHO, ALTO = 1080, 1920
FPS = 30
FONT_PATH = "Poppins-Bold.ttf"

OUT_BASE = Path("shorts_output")
OUT_BASE.mkdir(exist_ok=True)

# Columnas del banco de temas (Google Sheet), en este orden exacto:
#   A=tema  B=texto  C=resaltados (separados por " | ")  D=busqueda_visual
#   E=fuente_visual  F=modo_visual  G=usado  H=fecha_usado  I=video_url
COL_USADO = "G"
COL_FECHA = "H"
COL_URL = "I"


def log(*args):
    print(*args, flush=True)


# ---------------------------------------------------------------------------
# 1) Autenticación con Google (sin navegador, con refresh_token guardado)
# ---------------------------------------------------------------------------

def get_google_credentials(refresh_token, scopes):
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=scopes,
    )
    creds.refresh(GoogleAuthRequest())
    return creds


def _buscar_archivo_drive(drive, nombre):
    r = drive.files().list(
        q=f"name = '{nombre}' and trashed = false",
        fields="files(id, name, mimeType)",
        pageSize=5,
    ).execute()
    archivos = r.get("files", [])
    if not archivos:
        raise RuntimeError(
            f"No encuentro en Drive ningún archivo llamado '{nombre}'. "
            "Revisa el nombre exacto (mayúsculas/minúsculas incluidas)."
        )
    return archivos[0]


# ---------------------------------------------------------------------------
# 2) Banco de temas (Google Sheet en Drive)
# ---------------------------------------------------------------------------

def _primera_hoja(sheets, spreadsheet_id):
    meta = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return meta["sheets"][0]["properties"]["title"]


def obtener_siguiente_tema(creds):
    """Lee el banco de temas y devuelve (fila_numero, dict_con_los_datos)
    de la primera fila sin usar. Lanza un error claro si no queda ninguna."""
    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)

    archivo = _buscar_archivo_drive(drive, TOPICS_SHEET_NAME)
    spreadsheet_id = archivo["id"]
    hoja = _primera_hoja(sheets, spreadsheet_id)

    rango = f"{hoja}!A2:I"
    valores = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=rango
    ).execute().get("values", [])

    for i, fila in enumerate(valores):
        fila = fila + [""] * (9 - len(fila))  # rellena columnas que falten
        usado = (fila[6] or "").strip().upper()
        if usado in ("TRUE", "SI", "SÍ", "X", "1"):
            continue
        fila_numero = i + 2  # +2 porque A2 es la fila 1 de datos y Sheets es 1-indexado
        datos = {
            "tema": fila[0].strip(),
            "texto": fila[1].strip(),
            "resaltados": [r.strip() for r in fila[2].split("|") if r.strip()],
            "busqueda_visual": fila[3].strip(),
            "fuente_visual": (fila[4].strip() or "wikimedia").lower(),
            "modo_visual": (fila[5].strip() or "pan").lower(),
        }
        if not datos["tema"] or not datos["texto"]:
            continue
        return spreadsheet_id, hoja, fila_numero, datos

    raise RuntimeError(
        "SE HA ACABADO EL BANCO DE TEMAS: no queda ninguna fila sin usar en "
        f"'{TOPICS_SHEET_NAME}'. Hay que sentarse con Martín a escribir más "
        "filas (ver GITHUB-SETUP.md, sección 'Banco de temas')."
    )


def marcar_tema_usado(creds, spreadsheet_id, hoja, fila_numero, video_url):
    sheets = build("sheets", "v4", credentials=creds)
    rango = f"{hoja}!{COL_USADO}{fila_numero}:{COL_URL}{fila_numero}"
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=rango,
        valueInputOption="RAW",
        body={"values": [["TRUE", date.today().isoformat(), video_url or ""]]},
    ).execute()


def siguiente_numero_para_tema(creds, spreadsheet_id, hoja, tema):
    """Cuenta cuántos shorts ya usados hay de este mismo tema, para numerar
    el nuevo (#01, #02, ...) sin que nadie tenga que llevar la cuenta a mano."""
    sheets = build("sheets", "v4", credentials=creds)
    rango = f"{hoja}!A2:G"
    valores = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=rango
    ).execute().get("values", [])
    contador = 0
    for fila in valores:
        fila = fila + [""] * (7 - len(fila))
        usado = (fila[6] or "").strip().upper()
        if fila[0].strip() == tema and usado in ("TRUE", "SI", "SÍ", "X", "1"):
            contador += 1
    return contador + 1


# ---------------------------------------------------------------------------
# 3) Música: pista fija de piano chill desde Drive (o sonido real del clip)
# ---------------------------------------------------------------------------

def descargar_musica_drive(creds, destino="bg_music.mp3"):
    drive = build("drive", "v3", credentials=creds)
    archivo = _buscar_archivo_drive(drive, MUSICA_DRIVE_NOMBRE)
    request = drive.files().get_media(fileId=archivo["id"])
    with io.FileIO(destino, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return destino


def _tiene_audio_real(path, umbral_db=-50.0):
    """True si el clip de vídeo tiene una pista de audio con sonido real
    (no silencio ni ausencia de pista), midiendo el volumen medio con ffmpeg."""
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", path, "-af", "volumedetect", "-vn", "-f", "null", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60,
        )
        m = re.search(r"mean_volume:\s*(-?\d+(\.\d+)?)\s*dB", r.stdout)
        if not m:
            return False
        return float(m.group(1)) > umbral_db
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 4) Visual de fondo (foto o vídeo REAL; nada de IA salvo que no haya nada)
# ---------------------------------------------------------------------------

WIKIMEDIA_HEADERS = {
    "User-Agent": "MundoCuriosoShortsBot/1.0 (+https://github.com/Chamizonte/Fauna-Curiosa-; contacto: marchatov@gmail.com)"
}


def _pick_best_wikimedia(query, min_width=1000):
    api = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query", "format": "json", "list": "search",
        "srsearch": query, "srnamespace": 6, "srlimit": 10,
    }
    r = requests.get(api, params=params, headers=WIKIMEDIA_HEADERS, timeout=30).json()
    titles = [x["title"] for x in r.get("query", {}).get("search", [])]
    for title in titles:
        info = requests.get(api, params={
            "action": "query", "format": "json", "prop": "imageinfo",
            "titles": title, "iiprop": "url|size|mime",
        }, headers=WIKIMEDIA_HEADERS, timeout=30).json()
        pages = info.get("query", {}).get("pages", {})
        for p in pages.values():
            ii = p.get("imageinfo")
            if not ii:
                continue
            info0 = ii[0]
            mime = info0.get("mime", "")
            # Solo formatos de foto de verdad: nada de SVG/PDF/TIFF raros que
            # luego Pillow no puede abrir.
            if mime in ("image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp") \
                    and info0.get("width", 0) >= min_width:
                return info0["url"], "image"
    return None, None


def _pick_pexels(query, want="video"):
    headers = {"Authorization": PEXELS_API_KEY}
    if want == "video":
        r = requests.get("https://api.pexels.com/videos/search",
                          params={"query": query, "per_page": 5, "orientation": "portrait"},
                          headers=headers, timeout=30).json()
        for v in r.get("videos", []):
            files = sorted(v.get("video_files", []), key=lambda f: -f.get("width", 0))
            for f in files:
                if f.get("width", 0) >= 720:
                    return f["link"], "video"
    else:
        r = requests.get("https://api.pexels.com/v1/search",
                          params={"query": query, "per_page": 5, "orientation": "portrait"},
                          headers=headers, timeout=30).json()
        for p in r.get("photos", []):
            return p["src"]["large2x"], "image"
    return None, None


def _pick_pixabay(query, want="video"):
    ep = "https://pixabay.com/api/videos/" if want == "video" else "https://pixabay.com/api/"
    r = requests.get(ep, params={"key": PIXABAY_API_KEY, "q": query, "per_page": 5}, timeout=30).json()
    hits = r.get("hits", [])
    if not hits:
        return None, None
    if want == "video":
        v = hits[0]["videos"]
        best = v.get("large") or v.get("medium") or v.get("small")
        return best["url"] if best else None, "video"
    return hits[0]["largeImageURL"], "image"


def fetch_visual(query, fuente, modo, outfile="bg_source"):
    url, kind = None, None
    if fuente == "wikimedia":
        url, kind = _pick_best_wikimedia(query)
    elif fuente == "pexels" and PEXELS_API_KEY:
        url, kind = _pick_pexels(query, "video" if modo == "video" else "image")
    elif fuente == "pixabay" and PIXABAY_API_KEY:
        url, kind = _pick_pixabay(query, "video" if modo == "video" else "image")

    if not url:
        for f in ["wikimedia", "pexels", "pixabay"]:
            if f == fuente:
                continue
            if f == "wikimedia":
                url, kind = _pick_best_wikimedia(query)
            elif f == "pexels" and PEXELS_API_KEY:
                url, kind = _pick_pexels(query, "image")
            elif f == "pixabay" and PIXABAY_API_KEY:
                url, kind = _pick_pixabay(query, "image")
            if url:
                break

    if not url:
        raise RuntimeError(
            "No se encontró ningún clip/foto real para: " + query +
            " -- revisa la búsqueda en el banco de temas."
        )

    ext = ".mp4" if kind == "video" else ".jpg"
    path = outfile + ext
    r = requests.get(url, headers=WIKIMEDIA_HEADERS, timeout=60)
    r.raise_for_status()
    open(path, "wb").write(r.content)
    log("Visual descargado:", path, "(", kind, "de", fuente, ")")
    return path, kind


# ---------------------------------------------------------------------------
# 5) Tarjeta de texto (overlay PNG)
# ---------------------------------------------------------------------------

def _build_spans(texto, resaltados):
    spans, cursor, colores = [], 0, [COLOR_VERDE, COLOR_AZUL]
    for i, frase in enumerate(resaltados):
        idx = texto.find(frase, cursor)
        if idx == -1:
            idx = texto.lower().find(frase.lower(), 0)
        if idx == -1:
            continue
        spans.append((idx, idx + len(frase), colores[i % 2]))
        cursor = idx + len(frase)
    return spans


def _color_for(pos, spans):
    for s, e, c in spans:
        if s <= pos < e:
            return c
    return COLOR_TEXTO


def build_text_overlay(texto, resaltados, marca, numero, ancho=ANCHO, alto=ALTO):
    spans = _build_spans(texto, resaltados)
    words = []
    for m in re.finditer(r"\S+", texto):
        w = m.group(0)
        color = _color_for(m.start(), spans)
        words.append((w, color))

    margen = 70
    max_w = ancho - 2 * margen
    header_h = 130
    card_top = 160

    # La tarjeta NUNCA tapa más de ~44% del short: con texto largo se reduce
    # la letra automáticamente hasta que quepa en ese hueco.
    card_bottom_max = round(alto * 0.44)
    text_budget_h = card_bottom_max - card_top - header_h - 60

    font_body = None
    lines = []
    for font_size in range(54, 23, -1):
        font_body = ImageFont.truetype(FONT_PATH, font_size)
        line_h = round(font_size * 1.26)
        lines, current, current_w = [], [], 0
        space_w = font_body.getlength(" ")
        for w, color in words:
            ww = font_body.getlength(w)
            if current and current_w + space_w + ww > max_w:
                lines.append(current)
                current, current_w = [], 0
            current.append((w, color))
            current_w += (space_w if current_w else 0) + ww
        if current:
            lines.append(current)
        if len(lines) * line_h <= text_budget_h or font_size <= 24:
            break

    img = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_header = ImageFont.truetype(FONT_PATH, 46)

    text_block_h = len(lines) * line_h + 60
    card_h = header_h + text_block_h + 60
    card_bottom = card_top + card_h

    draw.rounded_rectangle([50, card_top, ancho - 50, card_bottom], radius=36, fill=CARD_BG)
    draw.rounded_rectangle([50, card_top, ancho - 50, card_top + header_h], radius=36, fill=COLOR_HEADER_BG)
    header_txt = f"{marca}  #{numero:02d}"
    tw = draw.textlength(header_txt, font=font_header)
    draw.text(((ancho - tw) / 2, card_top + (header_h - 46) / 2 - 6), header_txt,
               font=font_header, fill=COLOR_HEADER_TXT)

    y = card_top + header_h + 40
    for line in lines:
        line_text = " ".join(w for w, _ in line)
        line_w = draw.textlength(line_text + " ", font=font_body)
        x = (ancho - line_w) / 2
        for w, color in line:
            draw.text((x, y), w, font=font_body, fill=color)
            x += font_body.getlength(w + " ")
        y += line_h

    return img, card_bottom


# ---------------------------------------------------------------------------
# 6) Subida a YouTube
# ---------------------------------------------------------------------------

def subir_a_youtube(creds, video_path, titulo, descripcion, tags=None, privacidad="public"):
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": titulo[:100],
            "description": descripcion + "\n\n#Shorts",
            "tags": tags or [],
            "categoryId": "27",  # Educación
        },
        "status": {"privacyStatus": privacidad, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            log(f"Subiendo... {int(status.progress() * 100)}%")
    url = "https://youtube.com/watch?v=" + response["id"]
    log("Subido a YouTube:", url)
    return url


# ---------------------------------------------------------------------------
# 7) Programa principal
# ---------------------------------------------------------------------------

def main():
    log("== Generador de shorts automático ==")

    if not os.path.exists(FONT_PATH):
        r = requests.get(
            "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Bold.ttf",
            timeout=30,
        )
        r.raise_for_status()
        open(FONT_PATH, "wb").write(r.content)

    creds_drive = get_google_credentials(GOOGLE_REFRESH_TOKEN, DRIVE_SCOPES)
    creds_youtube = get_google_credentials(YOUTUBE_REFRESH_TOKEN, YOUTUBE_SCOPES)

    spreadsheet_id, hoja, fila_numero, datos = obtener_siguiente_tema(creds_drive)
    numero = siguiente_numero_para_tema(creds_drive, spreadsheet_id, hoja, datos["tema"])
    log(f"Tema elegido: {datos['tema']} #{numero:02d} (fila {fila_numero} del banco)")

    bg_path, bg_kind = fetch_visual(
        datos["busqueda_visual"], datos["fuente_visual"], datos["modo_visual"]
    )

    usar_sonido_original = False
    if bg_kind == "video":
        usar_sonido_original = _tiene_audio_real(bg_path)
        log("Sonido real detectado en el clip:", "SI" if usar_sonido_original else "NO -> se usará la música")

    if usar_sonido_original:
        music_path = None
        log("Se conserva el sonido ambiente original del vídeo.")
    else:
        music_path = descargar_musica_drive(creds_drive)
        log("Música (piano chill, pista fija) descargada desde Drive.")

    overlay_img, _ = build_text_overlay(datos["texto"], datos["resaltados"], MARCA_TEXTO, numero)
    overlay_img.save("overlay.png")

    n_palabras = len(datos["texto"].split())
    duracion = max(16, min(35, round(n_palabras / 2.3) + 4))
    log("Duración estimada:", duracion, "s (", n_palabras, "palabras )")

    tema = datos["tema"]
    out_dir = OUT_BASE / tema
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{numero:02d}_{tema}_SHORT.mp4"

    if bg_kind == "image":
        im = Image.open(bg_path)
        iw, ih = im.size
        scale_h = ALTO
        scale_w = max(ANCHO, round(iw * (ALTO / ih)))
        if datos["modo_visual"] == "pan" and scale_w > ANCHO * 1.15:
            vf_bg = (
                f"scale={scale_w}:{scale_h},"
                f"crop={ANCHO}:{ALTO}:x='min({scale_w}-{ANCHO}, ({scale_w}-{ANCHO})*t/{duracion})':y=0"
            )
        else:
            vf_bg = (
                f"scale={int(ANCHO * 1.15)}:-1,"
                f"zoompan=z='min(zoom+0.0007,1.15)':d={duracion * FPS}:s={ANCHO}x{ALTO}:fps={FPS}"
            )
        bg_cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", bg_path, "-t", str(duracion),
            "-vf", vf_bg, "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "bg_video.mp4",
        ]
    else:
        bg_cmd = [
            "ffmpeg", "-y", "-i", bg_path, "-t", str(duracion),
            "-vf", f"scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,crop={ANCHO}:{ALTO}",
            "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p",
        ]
        if usar_sonido_original:
            bg_cmd += ["-c:a", "aac", "-b:a", "192k"]
        else:
            bg_cmd += ["-an"]
        bg_cmd += ["bg_video.mp4"]

    subprocess.run(bg_cmd, check=True)
    log("Fondo listo: bg_video.mp4")

    if music_path is not None:
        audio_cmd = [
            "ffmpeg", "-y", "-i", music_path, "-t", str(duracion),
            "-af", f"afade=t=in:st=0:d=1.5,afade=t=out:st={duracion - 2}:d=2,volume=0.9",
            "-c:a", "aac", "-b:a", "192k",
            "audio_trimmed.aac",
        ]
    else:
        audio_cmd = [
            "ffmpeg", "-y", "-i", "bg_video.mp4", "-vn", "-t", str(duracion),
            "-af", f"afade=t=in:st=0:d=1.5,afade=t=out:st={duracion - 2}:d=2,volume=1.6",
            "-c:a", "aac", "-b:a", "192k",
            "audio_trimmed.aac",
        ]
    subprocess.run(audio_cmd, check=True)

    final_cmd = [
        "ffmpeg", "-y",
        "-i", "bg_video.mp4",
        "-i", "overlay.png",
        "-i", "audio_trimmed.aac",
        "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-shortest", str(out_path),
    ]
    subprocess.run(final_cmd, check=True)
    log("Short generado:", out_path)

    titulo = f"{MARCA_TEXTO} #{numero:02d}"
    descripcion = datos["texto"]
    video_url = subir_a_youtube(
        creds_youtube, str(out_path), titulo=titulo, descripcion=descripcion,
        privacidad=PRIVACIDAD_YOUTUBE,
    )

    marcar_tema_usado(creds_drive, spreadsheet_id, hoja, fila_numero, video_url)
    log("Fila", fila_numero, "marcada como usada en el banco de temas.")
    log("== Terminado OK ==")


if __name__ == "__main__":
    main()
