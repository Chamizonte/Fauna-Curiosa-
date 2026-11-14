"""Acceso a Google (Drive y YouTube) con los refresh tokens guardados como secretos."""
import io

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .util import env

TOKEN_URI = "https://oauth2.googleapis.com/token"


def credenciales(token_env, scopes):
    c = Credentials(token=None, refresh_token=env(token_env, requerido=True), token_uri=TOKEN_URI,
                    client_id=env("GOOGLE_CLIENT_ID", requerido=True),
                    client_secret=env("GOOGLE_CLIENT_SECRET", requerido=True), scopes=scopes)
    c.refresh(Request())
    return c


def drive():
    return build("drive", "v3", cache_discovery=False, credentials=credenciales(
        "GOOGLE_REFRESH_TOKEN",
        ["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/spreadsheets"]))


def descargar_de_drive(nombre, destino):
    d = drive()
    r = d.files().list(q=f"name = '{nombre}' and trashed = false", fields="files(id)", pageSize=1).execute()
    archivos = r.get("files", [])
    if not archivos:
        raise RuntimeError(f"No está en Drive: {nombre}")
    req = d.files().get_media(fileId=archivos[0]["id"])
    with io.FileIO(str(destino), "wb") as fh:
        dl = MediaIoBaseDownload(fh, req)
        hecho = False
        while not hecho:
            _, hecho = dl.next_chunk()
    return destino
