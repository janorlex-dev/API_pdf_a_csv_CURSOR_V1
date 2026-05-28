from __future__ import annotations

from lib.extractor_estructurado import (
    Pregunta,
    _parsear_texto_preguntas,
    _renumerar_reservas,
    extraer_preguntas,
    quitar_prefijo_numero,
)
from lib.pdf_parser import PaginaPDF


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


def test_anulada_con_texto_sustituto() -> None:
    texto = """
28.- ANULADA Se sustituye por la primera de reserva.
a) op a
b) op b
c) op c
d) op d
"""
    out = _parsear_texto_preguntas(texto)
    assert len(out) == 1
    assert out[0].anulada is True
    assert out[0].enunciado == "ANULADA."


def test_corte_comprobada_no_contamina_opcion() -> None:
    texto = """
51.- Pregunta reserva:
a) op a
b) op b
c) op c
d) op d final COMPROBADA 1.b 2.c 28.anulada
"""
    out = _parsear_texto_preguntas(texto)
    assert len(out) == 1
    assert out[0].d == "op d final"
    assert "COMPROBADA" not in out[0].d


def test_reserva_dos_laboral_2018_2_no_contamina_opcion_d() -> None:
    """Reserva 2 renumerada a 27; cabecera ``laboral_2018_2`` no debe entrar en opción d."""
    texto = """
25.- Ultima principal:
a)- op a
b)- op b
c)- op c
d)- op d

PREGUNTAS DE RESERVA
1.- Reserva uno:
a)- ra
b)- rb
c)- rc
d)- rd
2.- El Juzgado de lo Social de Cartagena dicta Sentencia declarando un despido como improcedente. La parte demandada decide interponer recurso de suplicación contra la Sentencia al entender que los hechos probados de la Resolución no son ciertos. En qué situación se encuentra la demandada:
a)- No podrá recurrir por ese motivo porque no se permite la revisión de hechos probados en la Sentencia.
b)- Podrá recurrir y alegar como motivo la revisión de hechos declarados probados a la vista de todas las pruebas practicadas.
c)- Podrá recurrir y alegar como motivo la revisión de hechos declarados probados a la vista de las pruebas documentales y periciales practicadas.
d)- Podrá recurrir y alegar como motivo la revisión de hechos probados a la vista exclusivamente de las pruebas documentales practicadas. laboral_2018_2
1.A          15.B
2.B          16.B
27.C
"""
    out = extraer_preguntas([PaginaPDF(numero=1, texto=texto)])
    q27 = next(p for p in out if p.numero == "27")
    assert q27.d.endswith("pruebas documentales practicadas.")
    assert "laboral_2018_2" not in q27.d
    assert "1.A" not in q27.d


def test_corte_cabecera_laboral_guion_bajo_no_contamina_opcion() -> None:
    """Cabecera ``laboral_2018_1`` pegada a la opción d (examen laboral)."""
    texto = """
2.- Has recibido una sentencia en un asunto de modificación sustancial individual de las condiciones de trabajo contraria a tus intereses. Además, es muy discutible y consideras que el juzgador se ha equivocado y mezclado las pruebas que se desarrollaron en la vista. En definitiva, tienes razones para recurrir en suplicación la misma y así se lo dices a tu cliente.
a)- Es un error porque las sentencias que se dictan en materia de modificación sustancial de las condiciones de trabajo de carácter individual no tienen ulterior recurso.
b)- Es un buen consejo, aunque también debes advertir a tu cliente que estos recursos son muy difíciles y es probable que no os den la razón.
c)- Es un error porque el recurso que procede es el de casación para la unificación de doctrina.
d)- No está mal pero sería mejor que le aconsejaras hablar con la otra parte e intentar llegar a un acuerdo a cambio de no recurrir. laboral_2018_1
1.B          26.B
"""
    out = _parsear_texto_preguntas(texto)
    assert len(out) == 1
    assert out[0].d.endswith("a cambio de no recurrir.")
    assert "laboral_2018_1" not in out[0].d


def test_corte_plantilla_inline_sin_cabecera_no_contamina_opcion() -> None:
    """Plantilla pegada a la opción d sin COMUN/COMPROBADA (examen común)."""
    texto = """
51.- Marta, Abogada en el turno de oficio:
a) Sí, siempre que el cliente muestre su conformidad.
b) No, dado que en el ejercicio de su cargo está obligada a asistir.
c) Sí, es posible la excusa en el orden penal, apreciada por el Juzgado.
d) Sí, es posible la excusa en el orden penal, apreciada por el Decano de su Colegio profesional. 1.b 26.d 51.d 2.d 27.d 3.a 28.anulada 4.d 29.a 25.d 50.c
"""
    out = _parsear_texto_preguntas(texto)
    assert len(out) == 1
    assert out[0].d.endswith("Colegio profesional.")
    assert "1.b" not in out[0].d
    assert "26.d" not in out[0].d
    assert "51.d" not in out[0].d


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
    assert "99" not in out[0].d


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
    """1.200 euros no debe cortar la pregunta 5 (secuencial ignora el falso 1.)."""
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
    assert "obedeciendo" in q5.a


def test_comun_2019_pregunta_inline_tras_punto() -> None:
    """Comun_2019: la 15 empieza en la misma línea: 'instancia. 15. Federico'."""
    texto = """
14.- María, abogada de oficio de Juan en un proceso matrimonial:
a) No, Juan debe solicitar una nueva designación.
b) Si, ya que la designación del turno de oficio comporta incidentes.
c) No, ya que transcurrido un año se extingue la designación.
d) Sí, ya que la asistencia jurídica gratuita comprende el trámite de ejecución, si se produce dentro de los dos años de la sentencia de la instancia. 15. Federico es designado abogado de Juana, quien quiere entablar una demanda:
a) Federico tendrá que asumir la asistencia jurídica que reclama Juana.
b) La comisión designará un nuevo abogado.
c) Se solicitará un informe adicional al Ministerio Fiscal.
d) Federico puede renunciar a la designación.
16.- Joana, Pere y Joan Francesc quieren ejercer colectivamente la abogacía:
a) Sí, independientemente de la forma social.
b) No, ya que pueden acogerse a cualquier forma mercantil.
c) Sí, siempre que vayan a tener colaboradores.
d) No, ya que los abogados están exentos.
"""
    out = _parsear_texto_preguntas(texto)
    assert [p.numero for p in out] == ["14", "15", "16"]
    q14 = next(p for p in out if p.numero == "14")
    q15 = next(p for p in out if p.numero == "15")
    assert q14.parse_ok is True
    assert "instancia" in q14.d
    assert "Federico" not in q14.d
    assert q15.parse_ok is True
    assert "Federico" in q15.enunciado
    assert "Juana" in q15.enunciado


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


def test_opciones_formato_guion_pregunta() -> None:
    """Examen tipo ``1 -`` pregunta y ``-`` opción (multilínea hasta el siguiente ``-``)."""
    texto = """
1 - La Abogada Helena asiste a un cliente, Hernán, en una causa penal.
¿Podría Helena desatender las instrucciones de su cliente?
- Sí, puede rechazar las instrucciones de Hernán
  y no recusar al Juez.
- No, debe seguir las instrucciones del cliente pues es quien decide.
- No, debe atender a las instrucciones haciendo constar este extremo.
- Sí, pero renunciando de inmediato a la defensa.
2 - Rafael y Antonia están intentando llegar a una solución extrajudicial.
¿Qué debe hacer Rafael?
- Puede o no comunicar a Antonia que da por concluido el intento.
- Debe comunicar a Antonia la finalización solo si es preceptiva la intervención.
- Tiene que comunicar a Antonia que han concluido las gestiones extrajudiciales.
- No tiene que comunicar nada a Antonia.
"""
    out = _parsear_texto_preguntas(texto)
    assert [p.numero for p in out] == ["1", "2"]
    q1 = out[0]
    assert q1.parse_ok is True
    assert "Helena" in q1.enunciado
    assert "no recusar al Juez" in q1.a
    assert "renunciando" in q1.d
    assert q1.b.startswith("No, debe seguir")


def test_opciones_guion_tres_respuestas() -> None:
    texto = """
1 - Enunciado de prueba con tres opciones:
- Primera opción
- Segunda opción
- Tercera opción
2 - Otra pregunta:
- A
- B
- C
- D
"""
    out = _parsear_texto_preguntas(texto)
    q1 = out[0]
    assert q1.parse_ok is True
    assert q1.a == "Primera opción"
    assert q1.c == "Tercera opción"
    assert q1.d == ""


def test_enunciado_con_palabra_plantilla_no_corta_opciones() -> None:
    """«su plantilla» en el enunciado no debe activar corte de solucionario."""
    texto = """
6 - Fernando ha trabajado en el despacho de Saturnino durante 13 años. Laura le ha
propuesto a Fernando que se incorpore a su plantilla, siempre y cuando revele datos:
- Primera opción de respuesta.
- Segunda opción de respuesta.
- Tercera opción de respuesta.
- Cuarta opción de respuesta.
"""
    out = _parsear_texto_preguntas(texto)
    assert len(out) == 1
    assert out[0].parse_ok is True
    assert "plantilla" in out[0].enunciado
    assert out[0].a.startswith("Primera")


def test_reserva_guion_sin_espacio_tras_guion() -> None:
    """Reservas del Común: ``1 -José`` (sin espacio) → renumerar a 51."""
    texto = """
50 - Última pregunta principal:
- op a
- op b
- op c
- op d

PREGUNTAS DE RESERVA
1 -José Luis, Abogado de Patricia, tiene un depósito del cliente:
- Sí, siempre que lleve la contabilidad.
- Sí, si hace gestión diligente.
- No, debe usar cuenta específica.
- No, nunca debe ser depositario.
"""
    principales = _parsear_texto_preguntas(texto.split("PREGUNTAS DE RESERVA")[0])
    reservas = _renumerar_reservas(
        _parsear_texto_preguntas(texto.split("PREGUNTAS DE RESERVA", 1)[1]),
        50,
    )
    assert len(principales) == 1
    assert len(reservas) == 1
    assert reservas[0].numero == "51"
    assert reservas[0].parse_ok is True
    assert "José Luis" in reservas[0].enunciado
