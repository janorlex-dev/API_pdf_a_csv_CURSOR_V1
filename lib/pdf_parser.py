from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


@dataclass
class PaginaPDF:
    numero: int
    texto: str


_RE_MARCADOR_PAGINA = re.compile(r"---\s*PAGE\s+\d+\s*---", re.I)

_TEXTOS_ENCABEZADO_FIJO: tuple[str, ...] = (
    "MINISTERIO DE JUSTICIA",
    "MINISTERIO DE LA PRESIDENCIA, JUSTICIA Y RELACIONES CON LAS CORTES",
    "PRUEBA DE EVALUACIÓN DE APTITUD PROFESIONAL",
    "ACCESO A LA PROFESIÓN DE ABOGADO",
    "ACCESO A LA ABOGACÍA",
    "CONVOCATORIA",
)

_RE_NUM_PAGINA = (
    re.compile(r"^\d{1,3}$"),
    # Pie de página con guiones a ambos lados (- 12 -). No confundir con preguntas ``30 -``.
    re.compile(r"^-\s*\d{1,3}\s*-$"),
    re.compile(r"(?i)^p[aá]gina\s+\d{1,3}$"),
    re.compile(r"(?i)^page\s+\d{1,3}$"),
)

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


def _normalizar_linea_comparacion(linea: str) -> str:
    return re.sub(r"\s+", " ", linea.strip())


def _es_numero_pagina(linea: str) -> bool:
    s = linea.strip()
    return any(p.fullmatch(s) for p in _RE_NUM_PAGINA)


def _es_encabezado_fijo(linea: str) -> bool:
    comp = _normalizar_linea_comparacion(linea).upper()
    return comp in {texto.upper() for texto in _TEXTOS_ENCABEZADO_FIJO}


def _detectar_lineas_repetidas(
    paginas: list[str],
    min_repeticiones: int = 2,
) -> set[str]:
    """Líneas idénticas en ≥2 páginas (membrete, pie, título del examen…)."""
    contador: Counter[str] = Counter()
    for pagina in paginas:
        unicas = {
            _normalizar_linea_comparacion(linea)
            for linea in pagina.splitlines()
            if _normalizar_linea_comparacion(linea)
        }
        contador.update(unicas)
    return {
        linea for linea, veces in contador.items() if veces >= min_repeticiones
    }


def _quitar_encabezado_de_linea(linea: str) -> str:
    """Quita membrete fijo pegado al final de una línea (p. ej. opción d + ministerio)."""
    resultado = linea.strip()
    for texto in _TEXTOS_ENCABEZADO_FIJO:
        resultado = re.sub(
            rf"(?i)\s*{re.escape(texto)}\s*$",
            "",
            resultado,
        )
    return resultado.strip()


def _limpiar_paginas_pdf(paginas: list[str]) -> list[str]:
    """Elimina encabezados/pies repetidos y números de página antes de unir hojas."""
    repetidas = _detectar_lineas_repetidas(paginas)
    limpias: list[str] = []

    for pagina in paginas:
        nuevas_lineas: list[str] = []
        for linea in pagina.splitlines():
            original = linea.strip()
            if not original:
                continue
            comparacion = _normalizar_linea_comparacion(original)
            if _es_numero_pagina(original):
                continue
            if _es_encabezado_fijo(original):
                continue
            if comparacion in repetidas and len(comparacion) < 90:
                continue
            limpia = _quitar_encabezado_de_linea(original)
            if limpia:
                nuevas_lineas.append(limpia)
        limpias.append(_limpiar("\n".join(nuevas_lineas)))

    return limpias


def quitar_ruido_encabezado(texto: str) -> str:
    """Limpieza de seguridad en fragmentos (enunciado u opción)."""
    if not texto or not texto.strip():
        return texto

    lineas: list[str] = []
    for linea in texto.splitlines():
        original = linea.strip()
        if not original:
            continue
        if _es_numero_pagina(original):
            continue
        if _es_encabezado_fijo(original):
            continue
        limpia = _quitar_encabezado_de_linea(original)
        if limpia:
            lineas.append(limpia)

    if lineas:
        return _limpiar("\n".join(lineas))
    return _limpiar(_quitar_encabezado_de_linea(texto))


def _limpiar(texto: str) -> str:
    """Limpieza mínima: no reformula ni resume, solo normaliza saltos y espacios."""
    texto = texto.replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _quitar_ruido_pagina(texto: str) -> str:
    """Normaliza marcadores internos; la limpieza de membrete va en ``_limpiar_paginas_pdf``."""
    texto = _RE_MARCADOR_PAGINA.sub("\n", texto)
    return texto.replace("\r", "\n")


def _extraer_texto_pagina(page: object) -> str:
    """Extrae texto en orden de lectura (sort=True) para PDFs de dos columnas."""
    import fitz  # PyMuPDF

    if not isinstance(page, fitz.Page):
        return ""

    texto = page.get_text("text", sort=True) or ""
    if not texto.strip():
        return ""

    return _quitar_ruido_pagina(texto)


def limpiar_textos_pagina(paginas: list[str]) -> list[str]:
    """API pública para tests: limpia membrete/pie repetido entre hojas."""
    return _limpiar_paginas_pdf(paginas)


def extraer_paginas(pdf_bytes: bytes) -> list[PaginaPDF]:
    """Extrae el texto literal de cada página del PDF con PyMuPDF (fitz)."""
    import fitz  # PyMuPDF

    textos_crudos: list[str] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            if not isinstance(page, fitz.Page):
                textos_crudos.append("")
                continue
            texto = page.get_text("text", sort=True) or ""
            textos_crudos.append(_quitar_ruido_pagina(texto))

    textos_limpios = _limpiar_paginas_pdf(textos_crudos)
    paginas: list[PaginaPDF] = []
    for i, texto in enumerate(textos_limpios, start=1):
        paginas.append(PaginaPDF(numero=i, texto=texto))
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
