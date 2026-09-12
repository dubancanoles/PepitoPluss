from app.analysis.classification import clasificar_documento
from app.models import ClasificacionContexto


def test_contexto_negativo_directo():
    texto = "Pepito Perez fue condenado por fraude tras un largo proceso judicial."
    resultado = clasificar_documento(texto, "Pepito Perez")
    assert resultado.resultado == ClasificacionContexto.NEGATIVO


def test_misma_palabra_clave_pero_como_testigo_no_es_negativo():
    """
    Caso critico para RF8: la palabra 'fraude' aparece en ambos textos,
    pero en este Pepito es testigo, no responsable -> NO debe dar NEGATIVO.
    Esto prueba que la clasificacion es por CONTEXTO, no por palabras sueltas.
    """
    texto = "Pepito Perez fue testigo clave en el caso de fraude y aporto pruebas."
    resultado = clasificar_documento(texto, "Pepito Perez")
    assert resultado.resultado != ClasificacionContexto.NEGATIVO


def test_contexto_positivo():
    texto = "Pepito Perez fue premiado y reconocido por su labor destacada en la empresa."
    resultado = clasificar_documento(texto, "Pepito Perez")
    assert resultado.resultado == ClasificacionContexto.POSITIVO


def test_sin_mencion_de_la_persona_es_no_determinado():
    texto = "El mercado bursatil tuvo un comportamiento estable esta semana."
    resultado = clasificar_documento(texto, "Pepito Perez")
    assert resultado.resultado == ClasificacionContexto.NO_DETERMINADO


def test_mencion_neutra_sin_senales_es_neutro():
    texto = "Pepito Perez asistio a la reunion programada para el jueves."
    resultado = clasificar_documento(texto, "Pepito Perez")
    assert resultado.resultado == ClasificacionContexto.NEUTRO


def test_justificacion_no_viene_vacia():
    texto = "Pepito Perez fue acusado de un delito menor segun fuentes cercanas."
    resultado = clasificar_documento(texto, "Pepito Perez")
    assert resultado.justificacion  # debe explicar el porque, no solo el resultado
