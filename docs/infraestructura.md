# Diagrama de infraestructura

```mermaid
flowchart TB
    subgraph Cliente["Máquina del usuario"]
        Browser["Navegador web<br/>abre frontend/index.html"]
    end

    subgraph Servidor["Servidor de aplicación (1 host / contenedor)"]
        direction TB
        Uvicorn["Uvicorn (ASGI server)<br/>puerto 8000"]
        FastAPI["Proceso FastAPI<br/>(app.main:app)"]
        subgraph ThreadPool["Threads del proceso FastAPI"]
            W1["Worker thread 1"]
            W2["Worker thread 2"]
            WN["Worker thread N"]
        end
        Uvicorn --> FastAPI
        FastAPI --> ThreadPool
    end

    subgraph Datos["Capa de datos"]
        DB[("PostgreSQL / SQLite<br/>puerto 5432")]
    end

    subgraph Externo["Internet — fuentes públicas"]
        S1["Fuente 1 (noticias)"]
        S2["Fuente 2 (blog)"]
        S3["Fuente N (directorio)"]
    end

    Browser <-->|HTTP :8000<br/>REST/JSON| Uvicorn
    ThreadPool -->|SQL| DB
    W1 -->|HTTPS| S1
    W2 -->|HTTPS| S2
    WN -->|HTTPS| S3
```

## Notas de despliegue

- **Desarrollo local**: un solo proceso (`uvicorn app.main:app --reload`) con SQLite en un archivo local (`pepito.db`). Suficiente para el taller.
- **Despliegue con más carga**: separar la base de datos a PostgreSQL (variable `DATABASE_URL`), y considerar mover el crawling a un worker process independiente (ej. vía `multiprocessing` o una cola externa tipo Redis/Celery) si el volumen de búsquedas crece, para no bloquear el proceso web con crawls largos.
- **Escalado horizontal del crawler**: el número de threads del pool (`num_workers`) es configurable por búsqueda; en un entorno con más núcleos se puede subir sin cambiar código.
- **Frontend**: archivo estático (`frontend/index.html`), se puede servir con cualquier servidor HTTP simple o abrir directamente en el navegador, ya que consume la API vía `fetch` a `http://localhost:8000`.
