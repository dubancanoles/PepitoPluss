# Modelo de datos

Corresponde 1:1 con `backend/app/models.py`.

```mermaid
erDiagram
    PERSONA ||--o{ BUSQUEDA : "es consultada en"
    BUSQUEDA ||--o{ URL_ESTADO : "contiene"
    BUSQUEDA ||--o{ DOCUMENTO : "contiene"
    BUSQUEDA ||--o{ METRICA_EJECUCION : "registra"
    FUENTE ||--o{ URL_ESTADO : "origina"
    URL_ESTADO ||--o| DESCARTE : "puede tener"
    URL_ESTADO ||--o| DOCUMENTO : "produce"
    DOCUMENTO ||--o| VERIFICACION_IDENTIDAD : "tiene"
    DOCUMENTO ||--o| CLASIFICACION_CONTEXTUAL : "tiene"
    PERSONA ||--o{ DOCUMENTO : "referenciada en"

    PERSONA {
        string id PK
        string nombre_completo "obligatorio"
        string pais "obligatorio"
        string ciudad
        string profesion_cargo
        string empresa_organizacion
        string alias
        string palabras_relacionadas
        datetime creado_en
    }

    FUENTE {
        string id PK
        string nombre
        string url_inicial
        string pais
        enum tipo "NOTICIAS|RED_SOCIAL|BLOG|DIRECTORIO_PUBLICO|OTRO"
        bool activa
        datetime creado_en
    }

    BUSQUEDA {
        string id PK
        string persona_id FK
        string pais
        datetime fecha_inicio
        datetime fecha_fin
        int num_workers_usado
        string estado "EN_EJECUCION|FINALIZADA|ERROR"
    }

    URL_ESTADO {
        string id PK
        string busqueda_id FK
        string fuente_id FK
        string url
        enum estado "PENDIENTE|EN_PROCESAMIENTO|PROCESADA|DESCARTADA|ERROR"
        string worker_id
        int intentos
        datetime descubierta_en
    }

    DESCARTE {
        string id PK
        string url_estado_id FK
        string motivo
        datetime creado_en
    }

    DOCUMENTO {
        string id PK
        string busqueda_id FK
        string url_estado_id FK
        string fuente_id FK
        string persona_id FK
        string titulo
        string url
        string pais
        datetime fecha_publicacion
        datetime fecha_consulta
        text contenido_texto
        string hash_contenido "UNIQUE junto con busqueda_id"
    }

    VERIFICACION_IDENTIDAD {
        string id PK
        string documento_id FK
        enum resultado "MISMA_PERSONA|POSIBLE_COINCIDENCIA|PERSONA_DIFERENTE|NO_DETERMINADO"
        float score
        text evidencia
    }

    CLASIFICACION_CONTEXTUAL {
        string id PK
        string documento_id FK
        enum resultado "POSITIVO|NEUTRO|NEGATIVO|NO_DETERMINADO"
        float score
        text justificacion
    }

    METRICA_EJECUCION {
        string id PK
        string busqueda_id FK
        string etapa
        int num_workers
        float tiempo_total_seg
        int num_items_procesados
    }
```

## Notas de diseño

- `UrlEstado` tiene una restricción `UNIQUE(busqueda_id, url)` — es la garantía a nivel de base de datos de que no se procesa la misma URL dos veces dentro de una búsqueda (RF4).
- `Documento` tiene una restricción `UNIQUE(busqueda_id, hash_contenido)` — evita persistir contenido duplicado dentro de la misma búsqueda (RF6), incluso si dos URLs distintas devuelven el mismo texto.
- `VerificacionIdentidad` y `ClasificacionContextual` usan tipos `Enum` a nivel de base de datos, por lo que es imposible insertar un valor fuera de los 4 estados obligatorios definidos por RF7 y RF8.
