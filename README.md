# Pepito Plus

Plataforma para localizar, clasificar y verificar informacion publica de
Internet relacionada con una persona, usando crawling concurrente
(threads/procesos en Python).

Taller Practico #1 — Programacion Concurrente, Crawling, Indexacion y
Procesamiento de Informacion.

## Estado del proyecto

Todos los RF estan implementados y probados (31/31 tests en verde,
incluyendo un test de integracion end-to-end contra un servidor HTTP
local simulado):

- [x] RF1 Registro de persona — CRUD completo con validaciones
- [x] RF2 Administracion de fuentes por pais — CRUD completo con filtros
- [x] RF3 Crawler concurrente — `ThreadPoolExecutor` configurable + cola compartida
- [x] RF4 Control concurrente de URLs — lock + `UniqueConstraint` en BD (con test de 20 hilos simultaneos)
- [x] RF5 Contenido relacionado — scoring por atributos, descartados consultables con motivo
- [x] RF6 Extraccion/persistencia — sin duplicados (hash de contenido)
- [x] RF7 Verificacion de identidad — 4 estados obligatorios
- [x] RF8 Clasificacion contextual — heuristica basada en oraciones + rol (no solo palabras sueltas), paralelizable con `multiprocessing`
- [x] RF9 Frontend de consulta y filtrado — `frontend/index.html`
- [x] Medicion de concurrencia — `app/metrics.py` + test comparando 1 vs 8 workers

**Importante — se probo con un servidor simulado, no con internet real**:
en el entorno donde se desarrollo esto no habia acceso a internet general,
asi que toda la logica (crawling, matching, identidad, clasificacion,
concurrencia) se probo contra un servidor HTTP local que sirve paginas de
prueba. La logica es identica a la que correria contra sitios reales, pero
**antes de entregar, corre al menos una busqueda real contra 1-2 fuentes
verdaderas de Internet** para confirmar que no hay sorpresas (headers
distintos, JavaScript-rendered content, bloqueos, etc.) — ver la seccion
"Antes de entregar" en `TESTING.md`.


## Cómo correr el frontend

Es un archivo estático simple, sin build. Ábrelo directamente:

```bash
open frontend/index.html   # macOS
# o simplemente doble clic en el archivo, con el backend corriendo en :8000
```

## Como correr el backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000` y la documentacion interactiva
(Swagger) en `http://localhost:8000/docs`. Con eso puedes probar RF1 y RF2
de una vez, sin necesidad del frontend.

Por defecto usa SQLite (`backend/pepito.db`, se crea solo). Para usar
PostgreSQL, define la variable de entorno `DATABASE_URL` antes de levantar
el servidor:

```bash
export DATABASE_URL="postgresql://usuario:password@localhost:5432/pepito_plus"
```

## Estructura

```
pepito-plus/
├── backend/
│   └── app/
│       ├── main.py           # arranque de FastAPI
│       ├── db.py             # conexion a la BD
│       ├── models.py         # modelo de datos (SQLAlchemy)
│       ├── schemas.py        # esquemas Pydantic
│       ├── routers/          # endpoints de la API (RF1, RF2, busquedas, RF9)
│       ├── crawler/          # RF3-RF4: cola compartida, workers, fetcher
│       ├── analysis/         # RF5, RF7, RF8: matching, identidad, clasificacion
│       └── metrics.py        # medicion de tiempos por etapa
├── frontend/                 # interfaz web (por construir)
├── frontend/                 # interfaz web estática para RF1, RF2, RF3 y RF9
├── docs/                     # diagramas y modelo de datos para entrega
└── README.md
```

## Siguiente paso

El código funcional ya cubre todos los RF. Ideas para profundizar si
tienes tiempo antes de la sustentación:
- La clasificación contextual (RF8) puede usar una IA compatible con
  OpenAI. Configura `AI_API_KEY` (o `OPENAI_API_KEY`) antes de iniciar
  el backend. Opcionalmente define `AI_API_URL`, `AI_MODEL` y
  `AI_TIMEOUT_SECONDS`. Sin clave, el sistema usa el clasificador local
  como respaldo. En ambos casos el resultado es `POSITIVO`, `NEUTRO`,
  `NEGATIVO` o `NO_DETERMINADO`.
- Correr una búsqueda real contra 1-2 fuentes verdaderas de Colombia
  para tener capturas reales en la sustentación (ver `TESTING.md`).
- Agregar `robots.txt` parsing real y rate-limiting por dominio en
  `fetcher.py` antes de crawlear sitios de producción.
