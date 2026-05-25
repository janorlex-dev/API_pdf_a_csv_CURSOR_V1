from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PaginaPDF:
    numero: int
    texto: str


def _limpiar(texto: str) -> str:
    """Limpieza mínima alineada con docs/base_pdf_a_csv.txt: no reformula
    ni resume, solo normaliza saltos y espacios."""
    texto = texto.replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def extraer_paginas(pdf_bytes: bytes) -> list[PaginaPDF]:
    """Extrae el texto literal de cada página del PDF con PyMuPDF (fitz).

    No hace OCR: si el PDF es una imagen escaneada, las páginas saldrán
    vacías y el extractor superior debe avisarlo. Esta v1 no incluye OCR.
    """
    import fitz  # PyMuPDF

    paginas: list[PaginaPDF] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for i, page in enumerate(doc, start=1):
            texto = page.get_text("text") or ""
            paginas.append(PaginaPDF(numero=i, texto=_limpiar(texto)))
    return paginas


def texto_completo(paginas: list[PaginaPDF]) -> str:
    """Une todas las páginas separadas por marcador, útil para regex globales."""
    partes: list[str] = []
    for p in paginas:
        if p.texto:
            partes.append(f"\n--- PAGE {p.numero} ---\n{p.texto}")
    return "\n".join(partes)


def es_pdf_sin_texto(paginas: list[PaginaPDF]) -> bool:
    return all(not p.texto.strip() for p in paginas)
