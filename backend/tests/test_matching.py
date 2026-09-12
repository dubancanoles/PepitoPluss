from app.analysis.matching import es_contenido_relacionado
from app.models import Persona


def _persona(**kwargs):
    base = dict(
        id="p1", nombre_completo="Pepito Perez Gomez", pais="Colombia",
        ciudad="Barranquilla", profesion_cargo="Ingeniero de Software",
        empresa_organizacion="Pepito Plus SAS", alias="Pepito, PP",
        palabras_relacionadas="python, backend",
    )
    base.update(kwargs)
    return Persona(**base)


def test_texto_con_nombre_completo_y_ciudad_es_relacionado():
    texto = "Pepito Perez Gomez, residente de Barranquilla, participo en un evento tecnologico."
    resultado = es_contenido_relacionado(texto, _persona())
    assert resultado.relacionado is True
    assert resultado.score >= 1.0


def test_texto_sin_ninguna_coincidencia_es_descartado():
    texto = "El precio del dolar subio esta semana en los mercados internacionales."
    resultado = es_contenido_relacionado(texto, _persona())
    assert resultado.relacionado is False
    assert resultado.motivo_descarte is not None
    assert "no se encontro" in resultado.motivo_descarte.lower()


def test_solo_ciudad_sin_nombre_no_alcanza_el_umbral():
    texto = "Barranquilla celebro su carnaval con gran exito este año."
    resultado = es_contenido_relacionado(texto, _persona())
    assert resultado.relacionado is False


def test_alias_solo_tambien_activa_relacion():
    texto = "PP fue reconocido por su trabajo en Pepito Plus SAS este mes."
    resultado = es_contenido_relacionado(texto, _persona())
    assert resultado.relacionado is True
