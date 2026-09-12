from app.analysis.identity import verificar_identidad
from app.models import Persona, ResultadoIdentidad


def _persona(**kwargs):
    base = dict(
        id="p1", nombre_completo="Pepito Perez Gomez", pais="Colombia",
        ciudad="Barranquilla", profesion_cargo="Ingeniero de Software",
        empresa_organizacion="Pepito Plus SAS", alias="Pepito",
        palabras_relacionadas="python, backend",
    )
    base.update(kwargs)
    return Persona(**base)


def test_nombre_mas_dos_atributos_es_misma_persona():
    texto = (
        "Pepito Perez Gomez, ingeniero de software radicado en Barranquilla, "
        "presento su nuevo proyecto."
    )
    resultado = verificar_identidad(texto, _persona())
    assert resultado.resultado == ResultadoIdentidad.MISMA_PERSONA


def test_nombre_mas_un_atributo_es_posible_coincidencia():
    texto = "Pepito Perez Gomez vive en Barranquilla."
    resultado = verificar_identidad(texto, _persona())
    assert resultado.resultado == ResultadoIdentidad.POSIBLE_COINCIDENCIA


def test_nombre_solo_sin_senales_es_no_determinado():
    texto = "Pepito Perez Gomez aparecio mencionado brevemente en un articulo."
    resultado = verificar_identidad(texto, _persona())
    assert resultado.resultado == ResultadoIdentidad.NO_DETERMINADO


def test_nombre_con_senal_de_homonimia_es_persona_diferente():
    texto = "Hay un tocayo de Pepito Perez Gomez que trabaja en otra ciudad."
    resultado = verificar_identidad(texto, _persona())
    assert resultado.resultado == ResultadoIdentidad.PERSONA_DIFERENTE


def test_texto_sin_relacion_es_no_determinado():
    texto = "Noticias del clima para mañana en la region caribe."
    resultado = verificar_identidad(texto, _persona())
    assert resultado.resultado == ResultadoIdentidad.NO_DETERMINADO
