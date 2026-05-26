from __future__ import annotations

from lib.plantilla import parsear_respuestas_texto

PLANTILLA_COMUN = """COMUN 2019_2
1.B          26.B
2.C          27.B
3.D          28.D
4.C          29.C
5.D          30.D
6.A          31.A
7.D          32.A
8.D          33.C
9.D          34.B
10.A         35.D
11.D         36.D
12.C         37.B
13.A         38.C
14.C         39.D
15.B         40.D
16.B         41.B
17.A         42.A
18.C         43.C
19.A         44.C
20.C         45.D
21.A         46.B
22.C         47.B
23.C         48.D
24.D         49.B
25.B         50.C
"""


def test_plantilla_dos_columnas_comun() -> None:
    parejas = parsear_respuestas_texto(PLANTILLA_COMUN)
    assert len(parejas) == 50
    assert parejas["1"] == "b"
    assert parejas["26"] == "b"
    assert parejas["50"] == "c"


def test_plantilla_una_por_linea() -> None:
    texto = "1 B\n2 D\n3 A\n"
    parejas = parsear_respuestas_texto(texto)
    assert parejas == {"1": "b", "2": "d", "3": "a"}


def test_plantilla_formato_punto() -> None:
    texto = "1.B\n2.C\n3.D\n"
    parejas = parsear_respuestas_texto(texto)
    assert parejas == {"1": "b", "2": "c", "3": "d"}
