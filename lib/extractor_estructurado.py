from __future__ import annotations

import re
from dataclasses import dataclass

from .pdf_parser import PaginaPDF, texto_completo


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
    r"(?m)^\s*(?P<num>\d{1,3})\s*(?:[\.\-–]|\.-|\))\s+(?P<resto>.+)$"
)

_RE_OPCION_NORMALIZADA = re.compile(r"(?m)^\s*([abcdABCD])\s*[\.\)]\s*")
_RE_OPCION_BUSCAR = re.compile(r"\n\s*([abcd])\)\s*")
_RE_PALABRA_ANULADA = re.compile(r"(?i)pregunta\s+anulada")


def _normalizar_opciones(texto: str) -> str:
    """Convierte 'a)', 'A.', 'b )', etc., a un formato uniforme '\\na) '.

    Replica `parse_questions_basic` del script base: cualquier letra
    a/b/c/d al inicio de línea seguida de '.' o ')' pasa a 'a) '.
    """
    return _RE_OPCION_NORMALIZADA.sub(
        lambda m: f"\n{m.group(1).lower()}) ",
        texto,
    )


def extraer_preguntas(paginas: list[PaginaPDF]) -> list[Pregunta]:
    """Detecta y parsea preguntas tipo test del PDF.

    Reglas (alineadas con docs/base_pdf_a_csv.txt):
    - Detecta inicios de pregunta: ``1.``, ``1.-``, ``1 -``, ``1)``, ``1–``.
    - Normaliza opciones a/b/c/d.
    - Si una pregunta no separa limpiamente 4 opciones, NO se descarta:
      se incluye con ``parse_ok=False`` y opciones vacías, y se reflejará en
      las advertencias. Así no se inventa contenido y el cliente puede
      revisar manualmente la fila.
    - Se ignora la última página si el resto tiene contenido (suele ser la
      plantilla; la trata `plantilla.py`).
    """
    if not paginas:
        return []

    if len(paginas) > 1:
        texto = texto_completo(paginas[:-1])
    else:
        texto = paginas[0].texto

    if not texto:
        return []

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

        opt_iter = list(_RE_OPCION_BUSCAR.finditer("\n" + bloque))
        if len(opt_iter) < 4:
            preguntas.append(
                Pregunta(
                    numero=numero,
                    enunciado=bloque,
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
        enunciado = bloque2[: opt_iter[0].start()].strip()
        opciones: dict[str, str] = {}
        for j, om in enumerate(opt_iter[:4]):
            letra = om.group(1)
            inicio = om.end()
            fin = opt_iter[j + 1].start() if j + 1 < 4 else len(bloque2)
            opciones[letra] = bloque2[inicio:fin].strip()

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
                parse_ok=True,
            )
        )

    return preguntas
