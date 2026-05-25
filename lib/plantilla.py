from __future__ import annotations

import re
from typing import Optional

from .pdf_parser import PaginaPDF, _RE_CORTE_PLANTILLA


_RE_PAREJA_LINEA = re.compile(
    r"(?m)^\s*(\d{1,3})\s*[\.\-:\)]?\s*([A-Da-d](?:\?)?|ANULADA|anulada|/)\s*$"
)

_RE_PAREJA_INLINE = re.compile(
    r"\b(\d{1,3})\s*[\.\-:\)]\s*([A-Da-d](?:\?)?|ANULADA|anulada|/)\b"
)


def _normalizar(letra: str) -> str:
    """Mantiene 'd?' literal y normaliza 'ANULADA' a una marca corta."""
    bruta = letra.strip()
    if bruta.lower() == "anulada":
        return "anulada"
    if bruta == "/":
        return ""
    return bruta.lower()


def _parejas_en_texto(texto: str) -> dict[str, str]:
    """Extrae todas las parejas numero->letra de un bloque de texto.

    Prioriza coincidencias por línea (más fiables) y luego rellena con
    coincidencias inline para plantillas en formato '1 B  2 D  3 A'.
    """
    parejas: dict[str, str] = {}
    for numero, letra in _RE_PAREJA_LINEA.findall(texto):
        clave = numero.lstrip("0") or numero
        parejas.setdefault(clave, _normalizar(letra))
    for numero, letra in _RE_PAREJA_INLINE.findall(texto):
        clave = numero.lstrip("0") or numero
        parejas.setdefault(clave, _normalizar(letra))
    return parejas


def extraer_plantilla(paginas: list[PaginaPDF]) -> dict[str, str]:
    """Busca la plantilla de respuestas en las últimas páginas del PDF.

    Recorre desde la última hacia atrás y devuelve el mapa {numero: letra}
    de la primera página que tenga al menos 5 parejas. Conserva sufijo '?'
    y marca 'anulada' literal cuando la plantilla lo indica.
    """
    if not paginas:
        return {}

    candidatas = (
        list(reversed(paginas[-3:])) if len(paginas) >= 3 else list(reversed(paginas))
    )

    for pagina in candidatas:
        if not pagina.texto:
            continue
        partes = _RE_CORTE_PLANTILLA.split(pagina.texto, maxsplit=1)
        texto_plantilla = partes[-1] if len(partes) > 1 else pagina.texto
        parejas = _parejas_en_texto(texto_plantilla)
        if len(parejas) >= 5:
            return parejas

    return {}


def fusionar_plantillas(
    auto: dict[str, str],
    manual: Optional[dict[str, str]],
) -> dict[str, str]:
    """El override manual tiene prioridad sobre la plantilla extraída del PDF."""
    if not manual:
        return dict(auto)
    fusion = dict(auto)
    for k, v in manual.items():
        clave = str(k).lstrip("0") or str(k)
        fusion[clave] = str(v).lower()
    return fusion
