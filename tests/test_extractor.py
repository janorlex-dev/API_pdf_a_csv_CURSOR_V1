from __future__ import annotations

from lib.extractor_estructurado import (
    Pregunta,
    _parsear_texto_preguntas,
    _renumerar_reservas,
    quitar_prefijo_numero,
)


def test_quitar_prefijo_numero() -> None:
    assert quitar_prefijo_numero("1", "1.- Jorge es abogado") == "Jorge es abogado"
    assert quitar_prefijo_numero("3", "3. ¿Quién fue?") == "¿Quién fue?"
    assert quitar_prefijo_numero("1", "Jorge es abogado") == "Jorge es abogado"


def test_renumerar_reservas_desde_uno() -> None:
    reservas = [
        Pregunta(numero="1", enunciado="R1", a="a", b="b", c="c", d="d"),
        Pregunta(numero="2", enunciado="R2", a="a", b="b", c="c", d="d"),
    ]
    out = _renumerar_reservas(reservas, max_principal=20)
    assert [p.numero for p in out] == ["21", "22"]


def test_renumerar_reservas_ya_continuadas() -> None:
    reservas = [Pregunta(numero="21", enunciado="R1", a="a", b="b", c="c", d="d")]
    out = _renumerar_reservas(reservas, max_principal=20)
    assert out[0].numero == "21"


def test_pregunta_anulada() -> None:
    texto = """
11.- ANULADA.
12.- Pregunta normal:
a) op a
b) op b
c) op c
d) op d
"""
    out = _parsear_texto_preguntas(texto)
    assert out[0].numero == "11"
    assert out[0].anulada is True
    assert out[0].enunciado == "ANULADA."
    assert out[0].a == " "
    assert out[1].numero == "12"
    assert out[1].anulada is False


def test_anulada_sin_punto() -> None:
    texto = """
49.- ANULADA
"""
    out = _parsear_texto_preguntas(texto)
    assert len(out) == 1
    assert out[0].anulada is True


def test_bloque_reserva_no_contamina_opcion() -> None:
    texto = """
1.- Pregunta principal:
a) op a
b) op b
c) op c
d) op d con texto

PREGUNTAS DE RESERVA
1.- Reserva uno:
a) ra
b) rb
c) rc
d) rd
"""
    principales = _parsear_texto_preguntas(texto.split("PREGUNTAS DE RESERVA")[0])
    assert "RESERVA" not in principales[0].d
    reservas = _renumerar_reservas(
        _parsear_texto_preguntas(texto.split("PREGUNTAS DE RESERVA", 1)[1]),
        1,
    )
    assert reservas[0].numero == "2"
    assert reservas[0].enunciado == "Reserva uno:"


def test_secuencial_ignora_numeros_fuera_de_orden() -> None:
    """Solo acepta 1, 2, 3…; ignora marcas fuera de secuencia."""
    texto = """
1.- Primera:
a) a
b) b
c) c
d) d
99.- Falso positivo
2.- Segunda:
a) a
b) b
c) c
d) d
"""
    out = _parsear_texto_preguntas(texto)
    assert [p.numero for p in out] == ["1", "2"]
    assert out[0].enunciado.startswith("Primera")
    assert out[1].enunciado.startswith("Segunda")


def test_opciones_formato_guion() -> None:
    """Formato habitual en Comun: a.- b.- c.- d.-"""
    texto = """
5.- Montaña, abogada, está negociando con su compañero Simón:
a.- Sí, porque está obedeciendo las indicaciones de su cliente.
b.- Sí, porque está próxima la posible prescripción de la acción.
c.- No, porque debe comunicarse el cese de las negociaciones al letrado contrario antes de demandar.
d.- No, porque en este caso la intervención del Letrado no es preceptiva.
6.- Otra pregunta:
a) op a
b) op b
c) op c
d) op d
"""
    out = _parsear_texto_preguntas(texto)
    assert out[0].numero == "5"
    assert out[0].parse_ok is True
    assert "Montaña" in out[0].enunciado
    assert "obedeciendo" in out[0].a
    assert "prescripción" in out[0].b
    assert "cese de las negociaciones" in out[0].c
    assert "Letrado no es preceptiva" in out[0].d


def test_no_confunde_importe_con_pregunta() -> None:
    """1.200 euros no debe cortar la pregunta 5."""
    texto = """
5.- Montaña, abogada, está negociando con su compañero Simón el cumplimiento de un
contrato de compraventa entre clientes de ambos y en concreto el pago de la cantidad de
1.200 euros. Las negociaciones se prolongan intentando evitar el juicio, pero Montaña
sospecha que el ánimo de su compañero es dilatorio. El ejercicio de la acción de
reclamación prescribe en breve por lo que el cliente de Montaña le ordena presentar la
demanda, y ella así lo hace sin previo aviso a Simón ¿es correcta la actuación de
Montaña?:
a.- Sí, porque está obedeciendo las indicaciones de su cliente.
b.- Sí, porque está próxima la posible prescripción de la acción.
c.- No, porque debe comunicarse el cese de las negociaciones al letrado contrario antes de demandar.
d.- No, porque en este caso la intervención del Letrado no es preceptiva y la demanda la presenta el
cliente a su nombre.
6.- Siguiente pregunta:
a.- op a
b.- op b
c.- op c
d.- op d
"""
    out = _parsear_texto_preguntas(texto)
    q5 = next(p for p in out if p.numero == "5")
    assert q5.parse_ok is True
    assert "1.200 euros" in q5.enunciado
    assert "Montaña?:" in q5.enunciado.replace("\n", " ")
    assert "obedeciendo" in q5.a


def test_no_confunde_fecha_con_pregunta() -> None:
    """15 de septiembre / 1 de diciembre no deben cortar la pregunta 22."""
    texto = """
22.- Iker, incorporado como abogado al colegio de abogados de Zaragoza el 15 de
septiembre de 2018, quiere votar para elegir al nuevo Decano de su colegio en las
elecciones convocadas el 1 de diciembre de 2018. ¿Puede Iker votar en las elecciones al
Decanato conforme a lo que dispone el Estatuto General de la Abogacía?:
a.- No, porque los colegiados no pueden participar en las primeras elecciones a Decanato que se
convoquen tras su incorporación al Colegio.
b.- No, porque no lleva tres meses aún colegiado al convocarse las elecciones.
c.- Sí, puede participar como elector desde el mismo día de la colegiación.
d.- Sí, puede participar como elector porque lleva más de un mes colegiado al convocarse las
elecciones.
23.- Otra:
a.- op a
b.- op b
c.- op c
d.- op d
"""
    out = _parsear_texto_preguntas(texto)
    q22 = next(p for p in out if p.numero == "22")
    assert q22.parse_ok is True
    assert "septiembre de 2018" in q22.enunciado
    assert "diciembre de 2018" in q22.enunciado
    assert "tres meses" in q22.b
