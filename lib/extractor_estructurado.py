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
    r"(?m)^\s*(?P<num>\d{1,3})\s*(?:\.-|[\.\-\u2013]|\))\s*"
)

_RE_OPCION_NORMALIZADA = re.compile(r"(?m)^\s*([abcdABCD])\s*[\.\)]\s*")
_RE_OPCION_BUSCAR = re.compile(r"\n\s*([abcd])\)\s+")
_RE_PALABRA_ANULADA = re.compile(r"(?i)pregunta\s+anulada")
_RE_MARCADOR_PAGINA = re.compile(r"---\s*PAGE\s+\d+\s*---", re.I)
_RE_CORTE_PLANTILLA = re.compile(
    r"(?i)\n\s*(JUNIO|SEPT|SEPTIEMBRE|SOLUCION|PLANTILLA|RESPUESTAS)\b"
)


def _normalizar_opciones(texto: str) -> str:
    """Convierte 'a)', 'A.', etc., a '\\na) ' uniforme."""
    return _RE_OPCION_NORMALIZADA.sub(
        lambda m: f"\n{m.group(1).lower()}) ",
        texto,
    )


def _limpiar_fragmento(texto: str) -> str:
    """Quita restos de salto de página, números sueltos y letras huérfanas."""
    texto = _RE_MARCADOR_PAGINA.sub("", texto)
    texto = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", texto)
    texto = re.sub(r"(?m)\n\s*[abcdABCD]\s*$", "", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _prefijo_enunciado(numero: str, enunciado: str) -> str:
    """Mantiene el prefijo literal ``N.-`` como en el PDF cuando falta."""
    if not enunciado:
        return enunciado
    prefijo = f"{numero}.-"
    if enunciado.startswith(prefijo) or enunciado.startswith(f"{numero}."):
        return enunciado
    resto = re.sub(r"^[\-\u2013\.\)\s]+", "", enunciado)
    return f"{prefijo} {resto}"


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
    orden: list[str] = []
    for p in preguntas:
        if p.numero not in mejores:
            mejores[p.numero] = p
            orden.append(p.numero)
            continue
        if _puntuar(p) > _puntuar(mejores[p.numero]):
            mejores[p.numero] = p
    return [mejores[n] for n in orden]


def extraer_preguntas(paginas: list[PaginaPDF]) -> list[Pregunta]:
    """Detecta y parsea preguntas tipo test del PDF."""
    if not paginas:
        return []

    texto = texto_para_preguntas(paginas)
    if not texto:
        return []

    texto = _RE_MARCADOR_PAGINA.sub("\n", texto)
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

        opt_iter = list(_RE_OPCION_BUSCAR.finditer("\n" + bloque))
        if len(opt_iter) < 4:
            enunciado_crudo = _limpiar_fragmento(bloque)
            preguntas.append(
                Pregunta(
                    numero=numero,
                    enunciado=_prefijo_enunciado(numero, enunciado_crudo),
                    a="",
                    b="",
                    c="",
                    d="",
                    anulada=bool(_RE_PALABRA_ANULADA.search(bloque)),
                    parse_ok=False,
                )
            )
            continue

        bloque2 = "\n" + bloque
        enunciado = _limpiar_fragmento(bloque2[: opt_iter[0].start()].strip())
        enunciado = _prefijo_enunciado(numero, enunciado)

        opciones: dict[str, str] = {}
        for j, om in enumerate(opt_iter[:4]):
            letra = om.group(1)
            inicio = om.end()
            fin = opt_iter[j + 1].start() if j + 1 < 4 else len(bloque2)
            opciones[letra] = _limpiar_fragmento(bloque2[inicio:fin])

        anulada = bool(_RE_PALABRA_ANULADA.search(enunciado))
        if anulada and not enunciado.upper().startswith("PREGUNTA ANULADA"):
            enunciado = f"PREGUNTA ANULADA. {enunciado}"

        preguntas.append(
            Pregunta(
                numero=numero,
                enunciado=enunciado,
                a=opciones.get("a", ""),
                b=opciones.get("b", ""),
                c=opciones.get("c", ""),
                d=opciones.get("d", ""),
                anulada=anulada,
                parse_ok=bool(enunciado.strip()),
            )
        )

    return _deduplicar(preguntas)
