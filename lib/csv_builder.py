from __future__ import annotations

import csv
import io
import os
from typing import Iterable, Optional

from .extractor_estructurado import Pregunta


CABECERA_DEFAULT = ("numero", "pregunta", "a", "b", "c", "d", "correcta", "materia")

_ALIAS_NUMERO = {"numero", "número", "nº", "n", "num", "no"}
_ALIAS_MATERIA = {"materia", "bloque", "tema", "asignatura"}


def cabecera_por_defecto() -> list[str]:
    """Lee la cabecera por defecto desde el entorno o usa CABECERA_DEFAULT.

    Variable `DEFAULT_HEADER` con columnas separadas por comas, sin espacios.
    """
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


def _valor_para_columna(
    columna: str,
    pregunta: Pregunta,
    respuestas: dict[str, str],
    materia: Optional[str],
) -> str:
    c = columna.strip().lower()
    if c in _ALIAS_NUMERO:
        return pregunta.numero
    if c == "pregunta":
        return pregunta.enunciado
    if c == "a":
        return pregunta.a
    if c == "b":
        return pregunta.b
    if c == "c":
        return pregunta.c
    if c == "d":
        return pregunta.d
    if c == "correcta":
        return respuestas.get(pregunta.numero, "")
    if c in _ALIAS_MATERIA:
        return materia or ""
    return ""


def construir_csv(
    preguntas: Iterable[Pregunta],
    cabecera: list[str],
    respuestas: dict[str, str],
    materia: Optional[str],
) -> tuple[bytes, int, int]:
    """Construye el CSV en memoria.

    Convenciones (alineadas con docs/base_pdf_a_csv.txt y proyecto.mdc):
    - ``csv.QUOTE_ALL`` con `delimiter=","` y `lineterminator="\\n"`.
    - Encoding ``utf-8-sig`` (UTF-8 con BOM) para abrir bien en Excel.
    - Cabecera explícita en la primera fila.

    Devuelve ``(bytes_csv, filas_de_datos, numero_columnas)``.
    """
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
            _valor_para_columna(col, pregunta, respuestas, materia) for col in cabecera
        ]
        writer.writerow(fila)
        filas += 1

    data = buffer.getvalue().encode("utf-8-sig")
    return data, filas, len(cabecera)
