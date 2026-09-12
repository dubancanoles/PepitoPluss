"""
RF8: Clasificacion contextual del contenido.

Enfoque (heuristico basado en reglas, documentado para sustentacion):
No basta con contar palabras "negativas" o "positivas" en todo el
documento -- eso clasificaria mal una noticia donde la persona solo es
citada como testigo de algo negativo que le paso a alguien mas. Por eso:

1. Se identifican las ORACIONES donde aparece el nombre/alias de la
   persona (ventana de contexto), no el documento completo.
2. Dentro de esas oraciones se buscan:
   a. Palabras de "rol neutro/positivo cercano al hecho": testigo,
      denunciante, victima, declaro, informo, gano, recibio, lidero.
   b. Palabras que indican que la persona es sujeto activo de algo
      negativo: condenado, acusado, arrestado, investigado, sancionado,
      señalado, implicado.
   c. Palabras claramente positivas: premiado, reconocido, galardonado,
      destaco, logro, exito, nombrado (en sentido de cargo/honor).
3. Si el rol detectado es "victima/testigo/denunciante" se descarta la
   carga negativa de palabras que describen el hecho (no la culpa de la
   persona) y se clasifica como NEUTRO (o POSITIVO si ademas hay
   reconocimiento).
4. Sin oraciones que mencionen a la persona -> NO_DETERMINADO.
5. Empate entre señales positivas y negativas -> NEUTRO.

Este enfoque es deliberadamente explicable (cada resultado trae la
oracion y las palabras que lo motivaron) para poder defenderlo en la
sustentacion. Si se dispone de mas tiempo/recursos, este modulo puede
reemplazarse por un modelo de NLP entrenado o una llamada a un LLM,
manteniendo la misma firma de funcion.
"""
import json
import os
import re
from dataclasses import dataclass
from multiprocessing import Pool
from typing import List, Optional

import requests

from app.crawler.fetcher import normalizar
from app.models import ClasificacionContexto

ROL_NEUTRALIZADOR = ["testigo", "victima", "denunciante", "declaro", "informo", "reporto"]
NEGATIVAS = [
    "condenado", "acusado", "arrestado", "detenido", "investigado",
    "sancionado", "senalado", "implicado", "estafa", "fraude", "corrupcion",
    "demandado", "capturado",
]
POSITIVAS = [
    "premiado", "reconocido", "galardonado", "destaco", "logro", "exito",
    "nombrado", "lidero", "gano", "recibio el premio", "exitosa", "innovador",
]


def _dividir_en_oraciones(texto: str) -> List[str]:
    return [o.strip() for o in re.split(r"(?<=[.!?])\s+", texto) if o.strip()]


def _oraciones_con_persona(texto: str, nombre: str, alias: Optional[str] = None) -> List[str]:
    nombre_norm = normalizar(nombre)
    alias_norms = [normalizar(a.strip()) for a in (alias or "").split(",") if a.strip()]
    encontradas = []
    for oracion in _dividir_en_oraciones(texto):
        oracion_norm = normalizar(oracion)
        if nombre_norm in oracion_norm or any(a in oracion_norm for a in alias_norms):
            encontradas.append(oracion)
    return encontradas


@dataclass
class ResultadoClasificacion:
    resultado: ClasificacionContexto
    score: float
    justificacion: Optional[str] = None


def clasificar_documento(texto: str, nombre_persona: str, alias: Optional[str] = None) -> ResultadoClasificacion:
    oraciones = _oraciones_con_persona(texto, nombre_persona, alias)

    if not oraciones:
        return ResultadoClasificacion(
            resultado=ClasificacionContexto.NO_DETERMINADO,
            score=0.0,
            justificacion="No se encontraron oraciones que mencionen a la persona.",
        )

    puntos_positivos = 0
    puntos_negativos = 0
    evidencia = []

    for oracion in oraciones:
        oracion_norm = normalizar(oracion)
        es_rol_neutralizador = any(rol in oracion_norm for rol in ROL_NEUTRALIZADOR)

        negativas_encontradas = [p for p in NEGATIVAS if p in oracion_norm]
        positivas_encontradas = [p for p in POSITIVAS if p in oracion_norm]

        if negativas_encontradas:
            if es_rol_neutralizador:
                # La persona es testigo/victima/denunciante del hecho negativo,
                # no la responsable -> no se le atribuye carga negativa.
                evidencia.append(
                    f"'{oracion.strip()}' -> negativo neutralizado por rol "
                    f"(testigo/victima/denunciante)"
                )
            else:
                puntos_negativos += len(negativas_encontradas)
                evidencia.append(f"'{oracion.strip()}' -> señales negativas: {negativas_encontradas}")

        if positivas_encontradas:
            puntos_positivos += len(positivas_encontradas)
            evidencia.append(f"'{oracion.strip()}' -> señales positivas: {positivas_encontradas}")

    if puntos_positivos == 0 and puntos_negativos == 0:
        resultado = ClasificacionContexto.NEUTRO
    elif puntos_positivos > puntos_negativos:
        resultado = ClasificacionContexto.POSITIVO
    elif puntos_negativos > puntos_positivos:
        resultado = ClasificacionContexto.NEGATIVO
    else:
        resultado = ClasificacionContexto.NEUTRO  # empate

    return ResultadoClasificacion(
        resultado=resultado,
        score=puntos_positivos - puntos_negativos,
        justificacion=" | ".join(evidencia) if evidencia else "Se menciona a la persona sin señales positivas/negativas claras.",
    )


def clasificar_documento_con_ia(
    texto: str, nombre_persona: str, alias: Optional[str] = None
) -> ResultadoClasificacion:
    """Clasifica con un endpoint compatible con OpenAI y conserva un fallback local."""
    api_key = os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return clasificar_documento(texto, nombre_persona, alias)

    endpoint = os.getenv("AI_API_URL", "https://api.openai.com/v1/chat/completions")
    model = os.getenv("AI_MODEL", "gpt-4o-mini")
    prompt = (
        "Clasifica el contenido respecto a la persona indicada. Devuelve solo JSON valido con "
        'las claves "resultado", "score" y "justificacion". "resultado" debe ser exactamente '
        "POSITIVO, NEUTRO, NEGATIVO o NO_DETERMINADO. Usa NO_DETERMINADO si no hay evidencia "
        "suficiente o no se menciona a la persona. score debe estar entre -1 y 1.\n\n"
        f"Persona: {nombre_persona}\nAlias: {alias or 'ninguno'}\nContenido:\n{texto}"
    )

    try:
        respuesta = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "Eres un clasificador de contexto preciso y objetivo."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=float(os.getenv("AI_TIMEOUT_SECONDS", "20")),
        )
        respuesta.raise_for_status()
        contenido = respuesta.json()["choices"][0]["message"]["content"]
        datos = json.loads(contenido)
        resultado = ClasificacionContexto(datos["resultado"])
        score = max(-1.0, min(1.0, float(datos.get("score", 0))))
        justificacion = str(datos.get("justificacion", "Clasificacion generada por IA."))
        return ResultadoClasificacion(resultado, score, justificacion)
    except (requests.RequestException, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return clasificar_documento(texto, nombre_persona, alias)


def _clasificar_worker(args):
    texto, nombre_persona, alias = args
    return clasificar_documento_con_ia(texto, nombre_persona, alias)


def clasificar_documentos_en_paralelo(
    documentos: List[str], nombre_persona: str, alias: Optional[str] = None, num_procesos: int = 4
) -> List[ResultadoClasificacion]:
    """
    Paraleliza la clasificacion con multiprocessing.Pool (CPU-bound:
    tokenizacion + comparacion de listas de palabras por oracion).
    """
    args = [(texto, nombre_persona, alias) for texto in documentos]
    with Pool(processes=num_procesos) as pool:
        return pool.map(_clasificar_worker, args)
