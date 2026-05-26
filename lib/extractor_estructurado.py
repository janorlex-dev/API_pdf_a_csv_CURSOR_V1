from __future__ import annotations

import re
from dataclasses import dataclass

from .pdf_parser import PaginaPDF, texto_para_preguntas


@dataclass
class Pregunta:
    numero: str
    enunciado: str
    a: str
    b: str
    c: str
    d: str
    anulada: bool = False
    parse_ok: bool = True


_RE_INICIO_PREGUNTA = re.compile(
    r"(?m)^\s*(?P<num>\d{1,3})\s*(?:\.-|[\.\-\u2013:]|\))\s*"
)

_RE_PREFIJO_NUMERO = re.compile(
    r"^\s*(?P<num>\d{1,3})\s*(?:\.-|[\.\-\u2013:]|\))\s*"
)

_RE_SPLIT_RESERVA = re.compile(r"(?i)\n\s*PREGUNTAS\s+DE\s+RESERVA\b")

_RE_BANNER_RESERVA = re.compile(r"(?i)\s*PREGUNTAS\s+DE\s+RESERVA\b.*", re.DOTALL)

# a) / a. / a.- (exámenes UNED común)
_RE_OPCION_NORMALIZADA = re.compile(
    r"(?m)^\s*([abcdABCD])\s*(?:\.\-|[\.\)]|\))\s*"
)
_RE_OPCION_BUSCAR = re.compile(r"\n\s*([abcd])\)\s+")
_RE_PALABRA_ANULADA = re.compile(r"(?i)pregunta\s+anulada")
_RE_ENUNCIADO_ANULADA = re.compile(r"(?i)^\s*ANULADA\.?\s*$")
_RE_MARCADOR_PAGINA = re.compile(r"---\s*PAGE\s+\d+\s*---", re.I)
_RE_CORTE_PLANTILLA = re.compile(
    r"(?i)\n\s*("
    r"JUNIO|SEPT|SEPTIEMBRE|SOLUCION|PLANTILLA|RESPUESTAS|"
    r"COMUN\s+\d{4}(?:[_\-][A-Za-z0-9]+)?|"
    r"PENAL\s+\d{4}(?:[_\-][A-Za-z0-9]+)?|"
    r"PENITENCIARIO\s+\d{4}(?:[_\-][A-Za-z0-9]+)?|"
    r"LABORAL\s+\d{4}(?:[_\-][A-Za-z0-9]+)?"
    r")\b"
)


def _normalizar_opciones(texto: str) -> str:
    """Convierte 'a)', 'a.', 'a.-', etc., a '\\na) ' uniforme."""
    return _RE_OPCION_NORMALIZADA.sub(
        lambda m: f"\n{m.group(1).lower()}) ",
        texto,
    )


def _limpiar_fragmento(texto: str) -> str:
    """Quita restos de salto de página, números sueltos y letras huérfanas."""
    texto = _RE_MARCADOR_PAGINA.sub("", texto)
    texto = _RE_BANNER_RESERVA.sub("", texto)
    texto = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", texto)
    texto = re.sub(r"(?m)\n\s*[abcdABCD]\s*$", "", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def quitar_prefijo_numero(numero: str, enunciado: str) -> str:
    """Quita ``N.-`` / ``N.`` del enunciado si la columna ``numero`` va aparte."""
    if not enunciado:
        return enunciado
    m = _RE_PREFIJO_NUMERO.match(enunciado)
    if m and (m.group("num").lstrip("0") or m.group("num")) == (
        numero.lstrip("0") or numero
    ):
        return enunciado[m.end() :].strip()
    return enunciado.strip()


def _es_anulada(texto: str) -> bool:
    """Detecta pregunta anulada (solo ``ANULADA`` o ``PREGUNTA ANULADA``)."""
    if not texto or not texto.strip():
        return False
    if _RE_PALABRA_ANULADA.search(texto):
        return True
    t = texto.strip()
    if _RE_ENUNCIADO_ANULADA.match(t):
        return True
    sin_num = re.sub(
        r"^\d{1,3}\s*(?:\.-|[\.\-\u2013:]|\))\s*",
        "",
        t,
        flags=re.IGNORECASE,
    ).strip()
    return bool(_RE_ENUNCIADO_ANULADA.match(sin_num))


def _pregunta_anulada(numero: str, bloque: str, enunciado: str) -> Pregunta:
    """Fila de pregunta anulada: enunciado corto y opciones con un espacio."""
    return Pregunta(
        numero=numero,
        enunciado="ANULADA.",
        a=" ",
        b=" ",
        c=" ",
        d=" ",
        anulada=True,
        parse_ok=True,
    )


def _puntuar(p: Pregunta) -> tuple[int, int, int]:
    """Mayor puntuación = pregunta más completa (para deduplicar)."""
    opts = sum(1 for o in (p.a, p.b, p.c, p.d) if o.strip())
    return (
        1 if p.parse_ok else 0,
        len(p.enunciado.strip()),
        opts,
    )


def _deduplicar(preguntas: list[Pregunta]) -> list[Pregunta]:
    """Si el PDF de dos columnas genera el mismo número dos veces, queda la mejor."""
    mejores: dict[str, Pregunta] = {}
    for p in preguntas:
        if p.numero not in mejores:
            mejores[p.numero] = p
            continue
        if _puntuar(p) > _puntuar(mejores[p.numero]):
            mejores[p.numero] = p
    return sorted(mejores.values(), key=lambda p: int(p.numero))


def filtrar_preguntas_numeradas(
    preguntas: list[Pregunta],
    filas_esperadas: int | None = None,
) -> list[Pregunta]:
    """Conserva solo preguntas con número entero >= 1 (1, 2, 3…).

    Si se indica ``filas_esperadas``, limita al rango 1..N (como el script base).
    """
    filtradas: list[Pregunta] = []
    for p in preguntas:
        if not p.numero.isdigit():
            continue
        n = int(p.numero)
        if n < 1:
            continue
        if filas_esperadas is not None and n > filas_esperadas:
            continue
        filtradas.append(p)
    return filtradas


def _renumerar_reservas(
    reservas: list[Pregunta],
    max_principal: int,
) -> list[Pregunta]:
    """Si el bloque de reserva vuelve a numerar desde 1, continúa tras la última principal."""
    renumeradas: list[Pregunta] = []
    for p in reservas:
        n = int(p.numero)
        if max_principal > 0 and n <= max_principal:
            p.numero = str(max_principal + n)
        renumeradas.append(p)
    return renumeradas


def _parsear_texto_preguntas(texto: str) -> list[Pregunta]:
    """Parsea un bloque de texto (sin banner de reserva mezclado)."""
    texto = _normalizar_opciones(texto)
    inicios = list(_RE_INICIO_PREGUNTA.finditer(texto))
    if not inicios:
        return []

    preguntas: list[Pregunta] = []
    for i, m in enumerate(inicios):
        numero = m.group("num").lstrip("0") or m.group("num")
        bloque_inicio = m.end()
        bloque_fin = inicios[i + 1].start() if i + 1 < len(inicios) else len(texto)
        bloque = texto[bloque_inicio:bloque_fin].strip()
        bloque = _RE_CORTE_PLANTILLA.split(bloque)[0].strip()

        if _es_anulada(bloque):
            preguntas.append(_pregunta_anulada(numero, bloque, bloque))
            continue

        opt_iter = list(_RE_OPCION_BUSCAR.finditer("\n" + bloque))
        if len(opt_iter) < 4:
            enunciado_crudo = _limpiar_fragmento(bloque)
            if not enunciado_crudo.strip():
                continue
            if _es_anulada(enunciado_crudo):
                preguntas.append(_pregunta_anulada(numero, bloque, enunciado_crudo))
                continue
            preguntas.append(
                Pregunta(
                    numero=numero,
                    enunciado=quitar_prefijo_numero(numero, enunciado_crudo),
                    a="",
                    b="",
                    c="",
                    d="",
                    anulada=False,
                    parse_ok=False,
                )
            )
            continue

        bloque2 = "\n" + bloque
        enunciado = _limpiar_fragmento(bloque2[: opt_iter[0].start()].strip())
        enunciado = quitar_prefijo_numero(numero, enunciado)

        if _es_anulada(enunciado) or _es_anulada(bloque):
            preguntas.append(_pregunta_anulada(numero, bloque, enunciado))
            continue

        opciones: dict[str, str] = {}
        for j, om in enumerate(opt_iter[:4]):
            letra = om.group(1)
            inicio = om.end()
            fin = opt_iter[j + 1].start() if j + 1 < 4 else len(bloque2)
            opciones[letra] = _limpiar_fragmento(bloque2[inicio:fin])

        anulada = _es_anulada(enunciado)
        if anulada:
            preguntas.append(_pregunta_anulada(numero, bloque, enunciado))
            continue

        preguntas.append(
            Pregunta(
                numero=numero,
                enunciado=enunciado,
                a=opciones.get("a", ""),
                b=opciones.get("b", ""),
                c=opciones.get("c", ""),
                d=opciones.get("d", ""),
                anulada=False,
                parse_ok=bool(enunciado.strip()),
            )
        )

    return preguntas


def extraer_preguntas(paginas: list[PaginaPDF]) -> list[Pregunta]:
    """Detecta y parsea preguntas tipo test del PDF."""
    if not paginas:
        return []

    texto = texto_para_preguntas(paginas)
    if not texto:
        return []

    texto = _RE_MARCADOR_PAGINA.sub("\n", texto)
    texto = _normalizar_opciones(texto)
    texto = re.sub(
        r"(?i)(\bPREGUNTAS\s+DE\s+RESERVA\b)",
        r"\n\1\n",
        texto,
    )

    partes = _RE_SPLIT_RESERVA.split(texto, maxsplit=1)
    principales = _parsear_texto_preguntas(partes[0])
    if len(partes) == 1:
        return _deduplicar(principales)

    max_principal = max((int(p.numero) for p in principales), default=0)
    reservas = _parsear_texto_preguntas(partes[1])
    reservas = _renumerar_reservas(reservas, max_principal)
    return _deduplicar(principales + reservas)


def extraer_preguntas_filtradas(
    paginas: list[PaginaPDF],
    filas_esperadas: int | None = None,
) -> list[Pregunta]:
    """Extrae preguntas numeradas y descarta ruido fuera del rango esperado."""
    return filtrar_preguntas_numeradas(extraer_preguntas(paginas), filas_esperadas)
