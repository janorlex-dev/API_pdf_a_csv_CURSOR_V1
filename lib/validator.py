from __future__ import annotations

import csv
import io
from typing import Optional


def validar_csv(
    data: bytes,
    columnas_esperadas: int,
    filas_esperadas: Optional[int] = None,
) -> list[str]:
    """Replica las comprobaciones del script base (docs/base_pdf_a_csv.txt).

    Devuelve lista de advertencias (vacía si todo correcto).

    Comprobaciones:
    1. CSV no vacío y decodificable como UTF-8.
    2. Cabecera con el número de columnas esperado.
    3. Si se aporta ``filas_esperadas`` (ej. 27 = 25 + 2 reservas), avisar.
    4. Todas las filas tienen el mismo número de columnas que la cabecera.
    5. Sin filas vacías.
    6. Sin cabeceras repetidas dentro del archivo.
    """
    errores: list[str] = []
    try:
        texto = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ["CSV no decodificable como UTF-8"]

    reader = list(csv.reader(io.StringIO(texto)))
    if not reader:
        return ["CSV vacío"]

    cabecera = reader[0]
    if len(cabecera) != columnas_esperadas:
        errores.append(
            f"Cabecera con {len(cabecera)} columnas, esperadas {columnas_esperadas}"
        )

    filas_datos = reader[1:]
    if filas_esperadas is not None and len(filas_datos) != filas_esperadas:
        errores.append(
            f"Filas útiles: {len(filas_datos)}; esperadas {filas_esperadas}"
        )

    for i, fila in enumerate(filas_datos, start=2):
        if not any(celda.strip() for celda in fila):
            errores.append(f"Fila vacía en línea {i}")
        if len(fila) != columnas_esperadas:
            errores.append(
                f"Fila {i} tiene {len(fila)} columnas, esperadas {columnas_esperadas}"
            )

    repetidas = [
        i for i, fila in enumerate(filas_datos, start=2) if fila == cabecera
    ]
    if repetidas:
        errores.append(f"Cabecera repetida en líneas: {repetidas}")

    return errores
