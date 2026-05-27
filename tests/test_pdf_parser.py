from __future__ import annotations

from lib.extractor_estructurado import _parsear_texto_preguntas
from lib.pdf_parser import cortar_antes_plantilla, limpiar_textos_pagina, quitar_ruido_encabezado


def test_cortar_antes_plantilla_laboral_guion_bajo() -> None:
    texto = (
        "d)- Opción final de la pregunta. laboral_2018_1\n"
        "1.B          2.C\n"
    )
    assert cortar_antes_plantilla(texto) == "d)- Opción final de la pregunta."


def test_limpia_membrete_repetido_entre_paginas() -> None:
    paginas = [
        "MINISTERIO DE JUSTICIA\n35.- Pregunta treinta y cinco:\na) op a\n12",
        "MINISTERIO DE JUSTICIA\n36.- Pregunta treinta y seis:\na) op a\n13",
    ]
    limpias = limpiar_textos_pagina(paginas)
    assert all("MINISTERIO DE JUSTICIA" not in p for p in limpias)
    assert "35.- Pregunta treinta y cinco:" in limpias[0]
    assert "12" not in limpias[0]
    assert "13" not in limpias[1]


def test_quita_numero_pagina_con_etiqueta() -> None:
    paginas = [
        "MINISTERIO DE JUSTICIA\nPágina 5\n1.- Primera:\na) a",
        "MINISTERIO DE JUSTICIA\nPágina 6\n2.- Segunda:\na) a",
    ]
    limpias = limpiar_textos_pagina(paginas)
    assert all("Página" not in p for p in limpias)


def test_encabezado_inline_no_contamina_opcion() -> None:
    texto = """
35.- Tras agotar los recursos de derecho interno:
a) No, la demanda individual debe ser examinada siempre por un comité de tres jueces.
b) Sí, cuando dicha decisión no requiera un examen más detenido, siendo definitiva.
c) Sí, cuando dicha decisión no requiera un examen más detenido, siendo recurrible ante la Gran Sala.
d) No, para que el Juez único declare una demanda inadmisible debe ser de la misma nacionalidad que la del Estado demandado. MINISTERIO DE JUSTICIA
"""
    out = _parsear_texto_preguntas(texto)
    assert len(out) == 1
    assert out[0].numero == "35"
    assert out[0].d.endswith("Estado demandado.")
    assert "MINISTERIO" not in out[0].d


def test_quitar_ruido_encabezado_en_fragmento() -> None:
    assert (
        quitar_ruido_encabezado("Texto de opción. MINISTERIO DE JUSTICIA")
        == "Texto de opción."
    )


def test_no_borra_marcador_pregunta_guion_solo_linea() -> None:
    """``30 -`` en línea propia es inicio de pregunta (Común), no número de página."""
    paginas = [
        "MINISTERIO DE JUSTICIA\n29 -\nEnunciado veintinueve\n- op a\n- 5 -",
        "MINISTERIO DE JUSTICIA\n30 -\nEnunciado treinta\n- op a\n- 6 -",
    ]
    limpias = limpiar_textos_pagina(paginas)
    assert "29 -" in limpias[0]
    assert "30 -" in limpias[1]
    assert "- 5 -" not in limpias[0]
    assert "- 6 -" not in limpias[1]


def test_preguntas_guion_tras_limpieza_paginas() -> None:
    paginas = [
        "MINISTERIO DE JUSTICIA\n1 -\n¿Primera?\n- op a\n- op b\n- op c\n- op d\n- 1 -",
        "MINISTERIO DE JUSTICIA\n2 -\n¿Segunda?\n- ra\n- rb\n- rc\n- rd\n- 2 -",
    ]
    texto = "\n\n".join(limpiar_textos_pagina(paginas))
    out = _parsear_texto_preguntas(texto)
    assert [p.numero for p in out] == ["1", "2"]
    assert out[0].parse_ok is True
    assert out[1].parse_ok is True
