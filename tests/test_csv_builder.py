from __future__ import annotations

from lib.csv_builder import construir_csv, limpiar_campo
from lib.extractor_estructurado import Pregunta


def test_limpiar_campo_quita_saltos() -> None:
    assert limpiar_campo("línea uno\nlínea dos") == "línea uno línea dos"
    assert limpiar_campo("a\n\nb") == "a b"


def test_csv_anulada() -> None:
    preguntas = [
        Pregunta(
            numero="11",
            enunciado="ANULADA.",
            a=" ",
            b=" ",
            c=" ",
            d=" ",
            anulada=True,
        )
    ]
    cabecera = ["numero", "pregunta", "a", "b", "c", "d", "correcta", "materia"]
    data, filas, cols = construir_csv(preguntas, cabecera, {"11": "a"}, None)
    texto = data.decode("utf-8-sig")
    assert '"11","ANULADA."," "," "," "," ","ANULADA",""' in texto
    assert filas == 1
    assert cols == 8
