from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PaginaPDF:
    numero: int
    texto: str


_RE_SOLO_NUM_PAGINA = re.compile(r"^\d{1,3}$")
_RE_MARCADOR_PAGINA = re.compile(r"---\s*PAGE\s+\d+\s*---", re.I)
_RE_CORTE_PLANTILLA = re.compile(
    r"(?i)(?:\n\s*|\s+)"
    r"("
    r"COMPROBADA\b|"
    r"(?:JUNIO|SEPTIEMBRE|SEPT)\s+\d{4}|"
    r"SOLUCION|PLANTILLA|RESPUESTAS|"
    r"COMUN\s+\d{4}(?:[_\-][A-Za-z0-9]+)?|"
    r"PENAL\s+\d{4}(?:[_\-][A-Za-z0-9]+)?|"
    r"PENITENCIARIO\s+\d{4}(?:[_\-][A-Za-z0-9]+)?|"
    r"LABORAL\s+\d{4}(?:[_\-][A-Za-z0-9]+)?"
    r")\b"
)

# Plantilla sin cabecera: ``1.b 26.d`` (dos parejas seguidas) o línea solo ``1.b``.
_RE_LETRA_PLANTILLA = r"(?:[A-Da-d](?:\?)?|ANULADA|anulada|/)"
_RE_INICIO_PLANTILLA_LINEA = re.compile(
    rf"(?m)^\s*1\s*[\.\-:]\s*{_RE_LETRA_PLANTILLA}\s*$"
)
_RE_INICIO_PLANTILLA_INLINE = re.compile(
    rf"(?<!\d)"
    rf"(\d{{1,3}})\s*[\.\-:]\s*{_RE_LETRA_PLANTILLA}"
    rf"\s+"
    rf"(?<!\d)(\d{{1,3}})\s*[\.\-:]\s*{_RE_LETRA_PLANTILLA}"
)
_RE_COLA_CABECERA_PLANTILLA = re.compile(
    r"(?is)\b("
    r"COMUN\s+\d{4}(?:[_\-][A-Za-z0-9]+)?|"
    r"JUNIO\s+\d{4}|"
    r"SEPT(?:IEMBRE)?\s+\d{4}"
    r").*$"
)


def cortar_antes_plantilla(texto: str) -> str:
    """Elimina la zona de plantilla final pegada al bloque de preguntas.

    Corta en la primera aparición de cabecera (COMUN, JUNIO, COMPROBADA…),
    de una línea solo ``1.b``, o de dos parejas número-letra seguidas (``1.b 26.d``).
    """
    if not texto or not texto.strip():
        return texto

    cortes: list[int] = []
    for patron in (
        _RE_CORTE_PLANTILLA,
        _RE_INICIO_PLANTILLA_LINEA,
        _RE_INICIO_PLANTILLA_INLINE,
    ):
        m = patron.search(texto)
        if m:
            cortes.append(m.start())

    recortado = texto[: min(cortes)].strip() if cortes else texto.strip()
    return _RE_COLA_CABECERA_PLANTILLA.sub("", recortado).strip()


def _limpiar(texto: str) -> str:
    """Limpieza mínima: no reformula ni resume, solo normaliza saltos y espacios."""
    texto = texto.replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _quitar_ruido_pagina(texto: str) -> str:
    """Elimina números de página sueltos y marcadores internos."""
    texto = _RE_MARCADOR_PAGINA.sub("\n", texto)
    lineas: list[str] = []
    for linea in texto.splitlines():
        s = linea.strip()
        if _RE_SOLO_NUM_PAGINA.fullmatch(s):
            continue
        lineas.append(linea)
    return _limpiar("\n".join(lineas))


def _extraer_texto_pagina(page: object) -> str:
    """Extrae texto en orden de lectura (sort=True) para PDFs de dos columnas."""
    import fitz  # PyMuPDF

    if not isinstance(page, fitz.Page):
        return ""

    texto = page.get_text("text", sort=True) or ""
    if not texto.strip():
        return ""

    return _quitar_ruido_pagina(texto)


def extraer_paginas(pdf_bytes: bytes) -> list[PaginaPDF]:
    """Extrae el texto literal de cada página del PDF con PyMuPDF (fitz)."""
    import fitz  # PyMuPDF

    paginas: list[PaginaPDF] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for i, page in enumerate(doc, start=1):
            paginas.append(PaginaPDF(numero=i, texto=_extraer_texto_pagina(page)))
    return paginas


def texto_para_preguntas(paginas: list[PaginaPDF]) -> str:
    """Une todas las páginas de preguntas, cortando la plantilla en la última hoja."""
    if not paginas:
        return ""
    partes: list[str] = []
    for i, pagina in enumerate(paginas):
        if not pagina.texto:
            continue
        texto = pagina.texto
        if i == len(paginas) - 1:
            texto = cortar_antes_plantilla(texto)
        partes.append(texto)
    return "\n\n".join(partes)


def texto_completo(paginas: list[PaginaPDF]) -> str:
    """Alias de ``texto_para_preguntas`` (sin marcadores PAGE)."""
    return texto_para_preguntas(paginas)


def es_pdf_sin_texto(paginas: list[PaginaPDF]) -> bool:
    return all(not p.texto.strip() for p in paginas)
