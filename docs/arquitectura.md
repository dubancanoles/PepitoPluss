# Diagrama de arquitectura de software

Este diagrama se renderiza automáticamente en GitHub (formato Mermaid).

```mermaid
flowchart TB
    subgraph Cliente
        FE["Frontend web<br/>(HTML + JS)<br/>RF1, RF2, RF9"]
    end

    subgraph Backend["API Backend (FastAPI)"]
        API["Routers:<br/>personas · fuentes · busquedas · resultados"]
    end

    subgraph Crawling["Motor de crawling — RF3 / RF4"]
        COLA["Cola compartida<br/>queue.Queue + Lock"]
        POOL["Pool de workers<br/>ThreadPoolExecutor(N)"]
        FETCH["Fetcher<br/>requests + BeautifulSoup"]
    end

    subgraph Analisis["Pipeline de análisis"]
        MATCH["Matching — RF5<br/>contenido relacionado"]
        IDENT["Identidad — RF7<br/>4 estados obligatorios"]
        CLAS["Clasificación — RF8<br/>multiprocessing.Pool"]
    end

    DB[("Base de datos<br/>SQLite / PostgreSQL<br/>RF6")]
    MET["Métricas de ejecución<br/>1 vs N workers"]
    FUENTES[("Fuentes web externas<br/>(Internet)")]

    FE -->|HTTP/JSON| API
    API -->|dispara| POOL
    POOL --> COLA
    COLA --> POOL
    POOL --> FETCH
    FETCH -->|descarga| FUENTES
    FETCH --> MATCH
    MATCH -->|relacionado| IDENT
    MATCH -->|descartado + motivo| DB
    IDENT --> CLAS
    IDENT --> DB
    CLAS --> DB
    POOL --> MET
    MET --> DB
    API -->|consulta/filtra| DB
```

## Descripción de componentes

| Componente | Responsabilidad | RF relacionado |
|---|---|---|
| Frontend web | Registro de persona, administración de fuentes, disparo de búsquedas, consulta y filtrado de resultados | RF1, RF2, RF9 |
| API Backend (FastAPI) | Orquesta las solicitudes, valida datos, expone endpoints REST | Todos |
| Cola compartida | Estructura thread-safe que evita que una misma URL sea tomada por más de un worker a la vez | RF3, RF4 |
| Pool de workers | `ThreadPoolExecutor` configurable, procesa URLs concurrentemente | RF3 |
| Fetcher | Descarga HTML, extrae texto, enlaces y metadatos | RF3, RF6 |
| Matching | Determina si el contenido está relacionado con la persona consultada | RF5 |
| Identidad | Clasifica el nivel de correspondencia con la persona (4 estados) | RF7 |
| Clasificación contextual | Determina el tono del contenido relacionado con la persona (4 estados), paralelizado con `multiprocessing` | RF8 |
| Base de datos | Persistencia de personas, fuentes, búsquedas, URLs, documentos, verificaciones y métricas | RF6 |
| Métricas de ejecución | Registra tiempos por etapa para comparar 1 vs. N workers | Nota de medición |
