# Cómo verificar que cada RF realmente cumple

Todos los RF ya están implementados y con tests automatizados (31/31 en
verde). Esta guía te dice qué prueba respalda cada uno y qué hacer antes
de entregar.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Mapa RF → test que lo respalda

| RF | Archivo de test | Qué demuestra |
|---|---|---|
| RF1 | `test_personas.py` | Datos completos se guardan, obligatorios se validan, persistencia real |
| RF2 | `test_fuentes.py` | Atributos mínimos, filtro por país, filtro por estado, cambio de estado |
| RF3 | `test_crawler_integration.py`, `test_medicion_concurrencia.py` | Crawling real de punta a punta; 8 workers más rápido que 1 bajo las mismas condiciones |
| RF4 | `test_queue_manager.py` | 20 hilos atacando la misma URL a la vez → solo uno la reclama; ningún `UrlEstado` queda en estado inconsistente tras el crawl |
| RF5 | `test_matching.py`, `test_crawler_integration.py` | Scoring por atributos; página sin relación queda `DESCARTADA` con motivo consultable |
| RF6 | `test_crawler_integration.py::test_crawling_evita_reprocesar_si_se_corre_dos_veces` | Mismo contenido no se duplica dentro de una búsqueda |
| RF7 | `test_identity.py` | Los 4 estados obligatorios, cada uno con su regla documentada |
| RF8 | `test_classification.py` | Caso crítico: misma palabra clave ("fraude"), contexto distinto (testigo vs. acusado) → resultado distinto. Prueba que es contextual, no por palabras sueltas |
| RF9 | Frontend manual (`frontend/index.html`) — no automatizado | Filtros combinables por clasificación, identidad y fecha |
| Medición de concurrencia | `test_medicion_concurrencia.py` | Corrida real con 1 vs. 8 workers, mismo servidor, mismas páginas, tiempos impresos |

## Un bug real que se encontró y corrigió corriendo estos tests

Al escribir `test_crawler_integration.py`, correrlo varias veces reveló
una condición de carrera intermitente (aprox. 1 de cada 3 corridas
fallaba con `UNIQUE constraint failed`): un worker podía tomar una URL
recién descubierta de la cola compartida y consultarla en la base de
datos **antes** de que el worker que la descubrió terminara de guardar su
fila — ambos terminaban intentando insertarla. Se corrigió separando
"reclamar" la URL (marca en memoria) de "encolarla" (visible para otros
workers): ahora la fila se persiste y se hace `commit` **antes** de que
la URL quede disponible para que otro worker la tome. Correr la suite 8
veces seguidas después del fix confirmó que ya no es intermitente.

Esta es exactamente la clase de evidencia que vale la pena mostrar en la
sustentación para RF4 — no solo "funciona", sino "encontramos esta
condición de carrera específica y así la resolvimos".

## Antes de entregar

- [ ] `pytest tests/ -v` — 31/31 en verde (corre la suite 3-4 veces, no solo una, para descartar problemas intermitentes)
- [ ] **Corre al menos una búsqueda contra 1-2 fuentes reales de Internet**, no solo contra el servidor simulado de los tests. El código es el mismo, pero sitios reales pueden tener: bloqueos por user-agent, contenido cargado con JavaScript (que `requests` no ejecuta), redirecciones, o `robots.txt` restrictivo. Si algún sitio bloquea el bot, cámbialo por otro para la demo — no vale la pena pelear con eso el día de la sustentación.
- [ ] Ten capturas de pantalla o logs de la comparación 1 vs. N workers con datos reales (no solo el test)
- [ ] Prueba el frontend manualmente: registra una persona, agrega una fuente, dispara una búsqueda, filtra resultados
- [ ] Revisa que el README refleje el estado real del proyecto (ya está actualizado)

