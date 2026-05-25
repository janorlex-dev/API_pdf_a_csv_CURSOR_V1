from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ConvertResponse(BaseModel):
    ok: bool
    csv_url: Optional[str] = None
    filas: int = 0
    columnas: int = 0
    cabecera: list[str]
    plantilla_detectada: bool = False
    preguntas_no_parseadas: list[str] = Field(
        default_factory=list,
        description=(
            "Lista de números de pregunta con parse_ok=False. Se incluyen "
            "en el CSV con opciones vacías para no inventar contenido."
        ),
    )
    advertencias: list[str] = []


class PreviewResponse(BaseModel):
    ok: bool
    cabecera: list[str]
    filas_totales: int
    muestra: list[dict[str, str]]
    plantilla_detectada: bool = False
    preguntas_no_parseadas: list[str] = Field(default_factory=list)
    advertencias: list[str] = []


class HealthResponse(BaseModel):
    ok: bool = True
    servicio: str = "pdf-a-csv"
    version: str = "1.1.0"
