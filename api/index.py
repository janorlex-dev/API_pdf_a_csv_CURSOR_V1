from __future__ import annotations

import csv
import io
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Asegura que `lib/` en la raíz del repo sea importable en Vercel.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from lib.csv_builder import construir_csv, parsear_cabecera
from lib.extractor_estructurado import extraer_preguntas_filtradas
from lib.models import ConvertResponse, HealthResponse, PreviewResponse
from lib.pdf_parser import es_pdf_sin_texto, extraer_paginas
from lib.plantilla import extraer_plantilla, fusionar_plantillas, parsear_respuestas_texto
from lib.storage import BlobError, subir_csv
from lib.validator import validar_csv


app = FastAPI(
    title="PDF a CSV API",
    version="1.1.0",
    description=(
        "API para convertir exámenes en PDF a CSV respetando la literalidad "
        "del texto. Detecta la plantilla de respuestas en la última hoja, "
        "permite override manual y nunca rellena la columna 'correcta' por "
        "conocimiento propio."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _max_bytes() -> int:
    try:
        return int(os.environ.get("MAX_PDF_BYTES", "10485760"))
    except ValueError:
        return 10 * 1024 * 1024


def _parse_respuestas(respuestas_raw: Optional[str]) -> Optional[dict[str, str]]:
    """Acepta JSON ``{"1":"b"}`` o plantilla en texto (``1.B``, ``1 B``, dos columnas)."""
    if not respuestas_raw or not respuestas_raw.strip():
        return None

    texto = respuestas_raw.strip()
    if texto.startswith("{"):
        try:
            data = json.loads(texto)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"El campo 'respuestas' no es JSON válido: {exc}",
            ) from exc
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=400,
                detail="El campo 'respuestas' debe ser un objeto {numero: letra}.",
            )
        return {
            str(k).lstrip("0") or str(k): str(v).lower() for k, v in data.items()
        }

    parejas = parsear_respuestas_texto(texto)
    if not parejas:
        raise HTTPException(
            status_code=400,
            detail=(
                "No se reconocieron respuestas en el texto. Use JSON {\"1\":\"b\"} "
                "o pegue la plantilla del examen (ej. 1.B, 1 B, 1.B    26.B)."
            ),
        )
    return parejas


def _parse_expected_rows(valor: Optional[str]) -> Optional[int]:
    if valor is None or str(valor).strip() == "":
        return None
    try:
        n = int(valor)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="filas_esperadas debe ser un entero (ej. 27 para 25+2 reservas).",
        ) from exc
    if n <= 0:
        raise HTTPException(
            status_code=400,
            detail="filas_esperadas debe ser mayor que 0.",
        )
    return n


async def _leer_pdf(file: UploadFile) -> bytes:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Se esperaba un archivo .pdf")

    contenido = await file.read()
    if not contenido:
        raise HTTPException(status_code=400, detail="El PDF está vacío.")

    limite = _max_bytes()
    if len(contenido) > limite:
        raise HTTPException(
            status_code=413,
            detail=f"PDF demasiado grande: {len(contenido)} bytes (máx {limite}).",
        )
    return contenido


def _procesar(
    pdf_bytes: bytes,
    cabecera_raw: Optional[str],
    materia: Optional[str],
    respuestas_manual: Optional[dict[str, str]],
    filas_esperadas: Optional[int],
) -> tuple[bytes, int, int, list[str], bool, list[str], list[str]]:
    paginas = extraer_paginas(pdf_bytes)
    advertencias: list[str] = []

    if es_pdf_sin_texto(paginas):
        raise HTTPException(
            status_code=422,
            detail=(
                "El PDF no contiene texto seleccionable (probablemente escaneado). "
                "Esta v1 no incluye OCR."
            ),
        )

    cabecera = parsear_cabecera(cabecera_raw)

    preguntas = extraer_preguntas_filtradas(paginas, filas_esperadas)
    if not preguntas:
        raise HTTPException(
            status_code=422,
            detail=(
                "No se detectaron preguntas numeradas en el PDF. Revisa que tenga "
                "el formato '1.- enunciado / a) ... / b) ... / c) ... / d) ...'."
            ),
        )

    no_parseadas = [p.numero for p in preguntas if not p.parse_ok]
    if no_parseadas:
        advertencias.append(
            "Preguntas sin 4 opciones detectadas (revisión manual): "
            + ", ".join(no_parseadas)
        )

    plantilla_auto = extraer_plantilla(paginas)
    plantilla = fusionar_plantillas(plantilla_auto, respuestas_manual)
    plantilla_detectada = bool(plantilla_auto)

    if not plantilla:
        advertencias.append(
            "No se ha detectado plantilla de respuestas en el PDF ni se ha "
            "aportado manualmente. La columna 'correcta' irá vacía."
        )
    else:
        faltan = [p.numero for p in preguntas if p.numero not in plantilla]
        if faltan:
            advertencias.append(
                "Faltan respuestas en la plantilla para las preguntas: "
                + ", ".join(faltan)
            )

    data, filas, columnas = construir_csv(
        preguntas=preguntas,
        cabecera=cabecera,
        respuestas=plantilla,
        materia=materia,
    )

    errores_validacion = validar_csv(
        data,
        columnas_esperadas=columnas,
        filas_esperadas=filas_esperadas,
    )
    if errores_validacion:
        advertencias.extend(errores_validacion)

    return data, filas, columnas, cabecera, plantilla_detectada, no_parseadas, advertencias


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    """Vercel sirve la web en /index.html; FastAPI intercepta / si no hay rewrite."""
    return RedirectResponse("/index.html", status_code=307)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/api/convert", response_model=ConvertResponse)
async def convert(
    file: UploadFile = File(...),
    cabecera: Optional[str] = Form(None),
    materia: Optional[str] = Form(None),
    respuestas: Optional[str] = Form(None),
    filas_esperadas: Optional[str] = Form(None),
) -> JSONResponse:
    pdf_bytes = await _leer_pdf(file)
    respuestas_manual = _parse_respuestas(respuestas)
    esperadas = _parse_expected_rows(filas_esperadas)

    data, filas, columnas, cab, plantilla_detectada, no_parseadas, advertencias = (
        _procesar(
            pdf_bytes=pdf_bytes,
            cabecera_raw=cabecera,
            materia=materia,
            respuestas_manual=respuestas_manual,
            filas_esperadas=esperadas,
        )
    )

    nombre_base = (file.filename or "salida.pdf").rsplit(".", 1)[0] + ".csv"
    try:
        url = subir_csv(data, nombre_sugerido=nombre_base)
    except BlobError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return JSONResponse(
        ConvertResponse(
            ok=True,
            csv_url=url,
            filas=filas,
            columnas=columnas,
            cabecera=cab,
            plantilla_detectada=plantilla_detectada,
            preguntas_no_parseadas=no_parseadas,
            advertencias=advertencias,
        ).model_dump()
    )


@app.post("/api/preview", response_model=PreviewResponse)
async def preview(
    file: UploadFile = File(...),
    cabecera: Optional[str] = Form(None),
    materia: Optional[str] = Form(None),
    respuestas: Optional[str] = Form(None),
    filas_esperadas: Optional[str] = Form(None),
    n: int = Form(5),
) -> JSONResponse:
    """Como /api/convert pero NO sube el CSV: devuelve las primeras N filas."""
    n = max(1, min(n, 50))
    pdf_bytes = await _leer_pdf(file)
    respuestas_manual = _parse_respuestas(respuestas)
    esperadas = _parse_expected_rows(filas_esperadas)

    data, filas_totales, _, cab, plantilla_detectada, no_parseadas, advertencias = (
        _procesar(
            pdf_bytes=pdf_bytes,
            cabecera_raw=cabecera,
            materia=materia,
            respuestas_manual=respuestas_manual,
            filas_esperadas=esperadas,
        )
    )

    texto = data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(texto))
    filas_csv = list(reader)
    muestra: list[dict[str, str]] = []
    for fila in filas_csv[1 : 1 + n]:
        muestra.append(
            {cab[i]: (fila[i] if i < len(fila) else "") for i in range(len(cab))}
        )

    return JSONResponse(
        PreviewResponse(
            ok=True,
            cabecera=cab,
            filas_totales=filas_totales,
            muestra=muestra,
            plantilla_detectada=plantilla_detectada,
            preguntas_no_parseadas=no_parseadas,
            advertencias=advertencias,
        ).model_dump()
    )
