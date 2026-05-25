from __future__ import annotations

import os
import secrets
from typing import Optional

import httpx


_BLOB_API = "https://blob.vercel-storage.com"


class BlobError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token:
        raise BlobError(
            "Falta BLOB_READ_WRITE_TOKEN. Configúralo en Vercel (Storage > Blob) o en .env"
        )
    return token


def _nombre_aleatorio(base: str) -> str:
    """Construye una ruta con token aleatorio largo, no adivinable."""
    token = secrets.token_urlsafe(24)
    return f"csv/{token}/{base}"


def subir_csv(data: bytes, nombre_sugerido: str = "salida.csv") -> str:
    """Sube el CSV a Vercel Blob y devuelve la URL pública (con token en la ruta).

    Si BLOB_READ_WRITE_TOKEN no está configurado lanza BlobError; el endpoint
    superior debe capturarlo y responder 503 explicando cómo configurarlo.
    """
    ruta = _nombre_aleatorio(nombre_sugerido)
    url = f"{_BLOB_API}/{ruta}"
    headers = {
        "authorization": f"Bearer {_token()}",
        "x-content-type": "text/csv; charset=utf-8",
        "x-add-random-suffix": "0",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.put(url, content=data, headers=headers)
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPError as exc:
        raise BlobError(f"Error subiendo a Vercel Blob: {exc}") from exc

    url_publica: Optional[str] = payload.get("url")
    if not url_publica:
        raise BlobError(f"Respuesta inesperada de Vercel Blob: {payload}")
    return url_publica
