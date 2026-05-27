from __future__ import annotations

import re
from dataclasses import dataclass

from .pdf_parser import PaginaPDF, cortar_antes_plantilla, quitar_ruido_encabezado, texto_para_preguntas


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


# Separador tras el número: ``.-`` primero; luego ``. `` (no ``1.200``); guion suelto.
_SUFFIX_NUMERO = r"(?:\.-|\.(?!\d)\s+|[-–]\s+|\)\s+)"

_RE_CANDIDATO_LINEA = re.compile(
    rf"(?m)^\s*(?P<num>\d{{1,3}})\s*{_SUFFIX_NUMERO}"
)
_RE_CANDIDATO_INLINE = re.compile(
    r"(?<=\. )"
    r"(?P<num>\d{1,3})\s*"
    r"(?:"
    r"\.-"
    r"|\.(?!\d)\s+(?=[A-ZÁÉÍÓÚÑ¿""(])"
    r"|[-–]\s+"
    r")"
)

_RE_PREFIJO_NUMERO = re.compile(rf"^\s*(?P<num>\d{{1,3}})\s*{_SUFFIX_NUMERO}")

_RE_SPLIT_RESERVA = re.compile(r"(?i)\n\s*PREGUNTAS\s+DE\s+RESERVA\b")
_RE_BANNER_RESERVA = re.compile(r"(?i)\s*PREGUNTAS\s+DE\s+RESERVA\b.*", re.DOTALL)

# ChatGPT: a) / a.  — ampliado con a.- (Comun)
_RE_OPCION_NORMALIZADA = re.compile(
    r"(?m)^\s*([abcdABCD])\s*(?:\.\-|[\.\)]|\))\s*"
)
_RE_OPCION_BUSCAR = re.compile(r"\n\s*([abcd])\)\s*")
_RE_INICIO_OPCION_GUION = re.compile(r"^\s*-\s+(.*)$")
_RE_PALABRA_ANULADA = re.compile(r"(?i)pregunta\s+anulada")
_RE_ENUNCIADO_ANULADA = re.compile(r"(?i)^\s*ANULADA\.?\s*(?:$|\b)")
_RE_MARCADOR_PAGINA = re.compile(r"---\s*PAGE\s+\d+\s*---", re.I)


def _normalizar_opciones(texto: str) -> str:
    """Convierte etiquetas de opción a ``\\na) `` uniforme (script base + ``a.-``)."""
    return _RE_OPCION_NORMALIZADA.sub(
        lambda m: f"\n{m.group(1).lower()}) ",
        texto,
    )


def _limpiar_fragmento(texto: str) -> str:
    texto = _RE_MARCADOR_PAGINA.sub("", texto)
    texto = _RE_BANNER_RESERVA.sub("", texto)
    texto = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", texto)
    texto = re.sub(r"(?m)\n\s*[abcdABCD]\s*$", "", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return quitar_ruido_encabezado(texto.strip())


def quitar_prefijo_numero(numero: str, enunciado: str) -> str:
    if not enunciado:
        return enunciado
    m = _RE_PREFIJO_NUMERO.match(enunciado)
    if m and (m.group("num").lstrip("0") or m.group("num")) == (
        numero.lstrip("0") or numero
    ):
        return enunciado[m.end() :].strip()
    return enunciado.strip()


def _es_anulada(texto: str) -> bool:
    if not texto or not texto.strip():
        return False
    if _RE_PALABRA_ANULADA.search(texto):
        return True
    t = texto.strip()
    if _RE_ENUNCIADO_ANULADA.match(t):
        return True
    sin_num = re.sub(
        rf"^\d{{1,3}}\s*{_SUFFIX_NUMERO}",
        "",
        t,
        flags=re.IGNORECASE,
    ).strip()
    return bool(_RE_ENUNCIADO_ANULADA.match(sin_num))


def _pregunta_anulada(numero: str, bloque: str, enunciado: str) -> Pregunta:
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
    opts = sum(1 for o in (p.a, p.b, p.c, p.d) if o.strip())
    return (1 if p.parse_ok else 0, len(p.enunciado.strip()), opts)


def _deduplicar(preguntas: list[Pregunta]) -> list[Pregunta]:
    mejores: dict[str, Pregunta] = {}
    for p in preguntas:
        if p.numero not in mejores or _puntuar(p) > _puntuar(mejores[p.numero]):
            mejores[p.numero] = p
    return sorted(mejores.values(), key=lambda p: int(p.numero))


def filtrar_preguntas_numeradas(
    preguntas: list[Pregunta],
    filas_esperadas: int | None = None,
) -> list[Pregunta]:
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
    renumeradas: list[Pregunta] = []
    for p in reservas:
        n = int(p.numero)
        if max_principal > 0 and n <= max_principal:
            p.numero = str(max_principal + n)
        renumeradas.append(p)
    return renumeradas


def _candidatos_pregunta(texto: str) -> list[re.Match[str]]:
    """Marcas de inicio: inicio de línea (ChatGPT) + tras ``. `` en la misma línea."""
    vistos: set[tuple[int, str]] = set()
    candidatos: list[re.Match[str]] = []
    for pat in (_RE_CANDIDATO_LINEA, _RE_CANDIDATO_INLINE):
        for m in pat.finditer(texto):
            clave = (m.start(), m.group("num"))
            if clave in vistos:
                continue
            vistos.add(clave)
            candidatos.append(m)
    candidatos.sort(key=lambda m: m.start())
    return candidatos


def _bloques_secuenciales(texto: str) -> list[tuple[str, int, int]]:
    """Delimita 1, 2, 3… solo aceptando el número que toca (ignora ruido)."""
    candidatos = _candidatos_pregunta(texto)
    if not candidatos:
        return []

    esperado = int(candidatos[0].group("num").lstrip("0") or candidatos[0].group("num"))
    aceptados: list[re.Match[str]] = []
    buscar_desde = 0

    while buscar_desde < len(candidatos):
        encontrado: re.Match[str] | None = None
        for j in range(buscar_desde, len(candidatos)):
            n = int(
                candidatos[j].group("num").lstrip("0") or candidatos[j].group("num")
            )
            if n < esperado:
                continue
            if n > esperado:
                continue
            encontrado = candidatos[j]
            buscar_desde = j + 1
            break
        if encontrado is None:
            break
        aceptados.append(encontrado)
        esperado += 1

    bloques: list[tuple[str, int, int]] = []
    for i, m in enumerate(aceptados):
        numero = m.group("num").lstrip("0") or m.group("num")
        inicio = m.end()
        fin = aceptados[i + 1].start() if i + 1 < len(aceptados) else len(texto)
        bloques.append((numero, inicio, fin))
    return bloques


def _truncar_antes_siguiente(bloque: str, numero: str) -> str:
    """Quita ruido tipo ``99.-`` dentro del bloque antes de la pregunta que toca."""
    n_min = int(numero) + 1
    for m in _candidatos_pregunta(bloque):
        if m.start() == 0:
            continue
        n = int(m.group("num").lstrip("0") or m.group("num"))
        if n >= n_min:
            return bloque[: m.start()].strip()
    return bloque


def _parsear_opciones_letra(bloque: str) -> tuple[str, dict[str, str]] | None:
    """Opciones con etiqueta a/b/c/d (``a)``, ``a.-``, etc.)."""
    opt_iter = list(_RE_OPCION_BUSCAR.finditer("\n" + bloque))
    if len(opt_iter) < 4:
        return None

    bloque2 = "\n" + bloque
    enunciado = _limpiar_fragmento(bloque2[: opt_iter[0].start()].strip())
    opciones: dict[str, str] = {}
    for j, om in enumerate(opt_iter[:4]):
        letra = om.group(1)
        inicio = om.end()
        fin = opt_iter[j + 1].start() if j + 1 < 4 else len(bloque2)
        opciones[letra] = _limpiar_fragmento(bloque2[inicio:fin])
    return enunciado, opciones


def _parsear_opciones_guion(bloque: str) -> tuple[str, list[str]] | None:
    """Opciones con guion al inicio de línea (3 o 4); texto multilínea hasta el siguiente ``-``."""
    enunciado_partes: list[str] = []
    opciones_partes: list[list[str]] = []
    actual: list[str] | None = None

    for linea in bloque.splitlines():
        m = _RE_INICIO_OPCION_GUION.match(linea)
        if m:
            if actual is not None:
                opciones_partes.append(actual)
            actual = [m.group(1).strip()]
        elif actual is not None:
            if linea.strip():
                actual.append(linea.strip())
        elif linea.strip():
            enunciado_partes.append(linea.strip())

    if actual is not None:
        opciones_partes.append(actual)

    if len(opciones_partes) not in (3, 4):
        return None

    enunciado = _limpiar_fragmento("\n".join(enunciado_partes))
    textos = [_limpiar_fragmento(" ".join(partes)) for partes in opciones_partes]
    return enunciado, textos


def _pregunta_desde_opciones(
    numero: str,
    enunciado: str,
    a: str,
    b: str,
    c: str,
    d: str,
) -> Pregunta:
    enunciado = quitar_prefijo_numero(numero, enunciado)
    return Pregunta(
        numero=numero,
        enunciado=enunciado,
        a=a,
        b=b,
        c=c,
        d=d,
        anulada=False,
        parse_ok=bool(enunciado.strip()),
    )


def _parsear_bloque(numero: str, bloque: str) -> Pregunta | None:
    """Parsea un bloque (script base ``parse_questions_basic`` + opciones con guion)."""
    bloque = _truncar_antes_siguiente(bloque, numero)
    bloque = cortar_antes_plantilla(bloque)
    if not bloque.strip():
        return None

    if _es_anulada(bloque):
        return _pregunta_anulada(numero, bloque, bloque)

    letras = _parsear_opciones_letra(bloque)
    if letras is not None:
        enunciado, opciones = letras
        if _es_anulada(enunciado) or _es_anulada(bloque):
            return _pregunta_anulada(numero, bloque, enunciado)
        return _pregunta_desde_opciones(
            numero,
            enunciado,
            opciones.get("a", ""),
            opciones.get("b", ""),
            opciones.get("c", ""),
            opciones.get("d", ""),
        )

    guiones = _parsear_opciones_guion(bloque)
    if guiones is not None:
        enunciado, opts = guiones
        if _es_anulada(enunciado) or _es_anulada(bloque):
            return _pregunta_anulada(numero, bloque, enunciado)
        d = opts[3] if len(opts) == 4 else ""
        return _pregunta_desde_opciones(numero, enunciado, opts[0], opts[1], opts[2], d)

    enunciado_crudo = _limpiar_fragmento(bloque)
    if not enunciado_crudo.strip():
        return None
    if _es_anulada(enunciado_crudo):
        return _pregunta_anulada(numero, bloque, enunciado_crudo)
    return Pregunta(
        numero=numero,
        enunciado=quitar_prefijo_numero(numero, enunciado_crudo),
        a="",
        b="",
        c="",
        d="",
        anulada=False,
        parse_ok=False,
    )


def _parsear_texto_preguntas(texto: str) -> list[Pregunta]:
    texto = _normalizar_opciones(texto)
    preguntas: list[Pregunta] = []
    for numero, inicio, fin in _bloques_secuenciales(texto):
        parsed = _parsear_bloque(numero, texto[inicio:fin].strip())
        if parsed is not None:
            preguntas.append(parsed)
    return preguntas


def extraer_preguntas(paginas: list[PaginaPDF]) -> list[Pregunta]:
    if not paginas:
        return []

    texto = texto_para_preguntas(paginas)
    if not texto:
        return []

    texto = _RE_MARCADOR_PAGINA.sub("\n", texto)
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
    return filtrar_preguntas_numeradas(extraer_preguntas(paginas), filas_esperadas)
