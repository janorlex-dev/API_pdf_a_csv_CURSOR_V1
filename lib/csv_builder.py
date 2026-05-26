from __future__ import annotations

import csv
import io
import os
import re
from typing import Iterable, Optional

from .extractor_estructurado import Pregunta, quitar_prefijo_numero


CABECERA_DEFAULT = ("numero", "pregunta", "a", "b", "c", "d", "correcta", "materia")

_ALIAS_NUMERO = {"numero", "número", "nº", "n", "num", "no"}
_ALIAS_MATERIA = {"materia", "bloque", "tema", "asignatura"}

_OPCION_VACIA_ANULADA = " "


def limpiar_campo(texto: str | None) -> str:
    """Una sola línea por celda: quita saltos del PDF sin reformular (estilo ChatGPT)."""
    if texto is None:
        return ""
    bruto = str(texto)
    if bruto == _OPCION_VACIA_ANULADA:
        return _OPCION_VACIA_ANULADA
    bruto = bruto.replace("\r\n", "\n").replace("\r", "\n")
    bruto = re.sub(r"\s*\n\s*", " ", bruto)
    bruto = re.sub(r"[ \t]{2,}", " ", bruto)
    return bruto.strip()


def cabecera_por_defecto() -> list[str]:
    """Lee la cabecera por defecto desde el entorno o usa CABECERA_DEFAULT."""
    bruta = os.environ.get("DEFAULT_HEADER", "")
    if not bruta.strip():
        return list(CABECERA_DEFAULT)
    cols = [c.strip() for c in bruta.split(",") if c.strip()]
    return cols or list(CABECERA_DEFAULT)


def parsear_cabecera(cabecera: Optional[str]) -> list[str]:
    if not cabecera:
        return cabecera_por_defecto()
    cols = [c.strip() for c in cabecera.split(",") if c.strip()]
    return cols or cabecera_por_defecto()


def _cabecera_tiene_numero(cabecera: list[str]) -> bool:
    return any(col.strip().lower() in _ALIAS_NUMERO for col in cabecera)


def _valor_para_columna(
    columna: str,
    pregunta: Pregunta,
    respuestas: dict[str, str],
    materia: Optional[str],
    cabecera: list[str],
) -> str:
    c = columna.strip().lower()
    if c in _ALIAS_NUMERO:
        return pregunta.numero
    if c == "pregunta":
        if pregunta.anulada:
            return "ANULADA."
        enunciado = pregunta.enunciado
        if _cabecera_tiene_numero(cabecera):
            enunciado = quitar_prefijo_numero(pregunta.numero, enunciado)
        return enunciado
    if c in ("a", "b", "c", "d"):
        if pregunta.anulada:
            return _OPCION_VACIA_ANULADA
        return getattr(pregunta, c)
    if c == "correcta":
        if pregunta.anulada:
            return "ANULADA"
        resp = respuestas.get(pregunta.numero, "")
        if resp.strip().lower() == "anulada":
            return "ANULADA"
        return resp
    if c in _ALIAS_MATERIA:
        return materia or ""
    return ""


def construir_csv(
    preguntas: Iterable[Pregunta],
    cabecera: list[str],
    respuestas: dict[str, str],
    materia: Optional[str],
) -> tuple[bytes, int, int]:
    """Construye el CSV en memoria con QUOTE_ALL y UTF-8 BOM."""
    buffer = io.StringIO()
    writer = csv.writer(
        buffer,
        quoting=csv.QUOTE_ALL,
        delimiter=",",
        lineterminator="\n",
    )
    writer.writerow(cabecera)

    filas = 0
    for pregunta in preguntas:
        fila = [
            limpiar_campo(
                _valor_para_columna(col, pregunta, respuestas, materia, cabecera)
            )
            for col in cabecera
        ]
        writer.writerow(fila)
        filas += 1

    data = buffer.getvalue().encode("utf-8-sig")
    return data, filas, len(cabecera)
