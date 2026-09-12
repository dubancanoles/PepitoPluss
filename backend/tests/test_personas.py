"""
Verifica RF1: Registro de persona a consultar.
Criterio de la rubrica (10 pts): registra los datos requeridos, valida
los obligatorios y persiste correctamente.
"""


def test_crear_persona_con_datos_completos(client):
    payload = {
        "nombre_completo": "Pepito Perez",
        "pais": "Colombia",
        "ciudad": "Barranquilla",
        "profesion_cargo": "Ingeniero",
        "empresa_organizacion": "Pepito Plus SAS",
        "alias": "Pepito, PP",
        "palabras_relacionadas": "software, tecnologia",
    }
    resp = client.post("/personas", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre_completo"] == payload["nombre_completo"]
    assert "id" in data and data["id"]
    assert "creado_en" in data


def test_nombre_completo_es_obligatorio(client):
    resp = client.post("/personas", json={"pais": "Colombia"})
    # Pydantic ya rechaza esto porque falta un campo requerido en el schema
    assert resp.status_code == 422


def test_pais_es_obligatorio(client):
    resp = client.post("/personas", json={"nombre_completo": "Pepito"})
    assert resp.status_code == 422


def test_nombre_vacio_es_rechazado(client):
    """El schema permite string vacio, pero la logica de negocio debe rechazarlo."""
    resp = client.post("/personas", json={"nombre_completo": "   ", "pais": "Colombia"})
    assert resp.status_code == 400


def test_persona_persiste_y_se_puede_listar(client):
    client.post("/personas", json={"nombre_completo": "Ana Gomez", "pais": "Colombia"})
    client.post("/personas", json={"nombre_completo": "Luis Diaz", "pais": "Mexico"})

    resp = client.get("/personas")
    assert resp.status_code == 200
    nombres = [p["nombre_completo"] for p in resp.json()]
    assert "Ana Gomez" in nombres
    assert "Luis Diaz" in nombres


def test_obtener_persona_por_id(client):
    creada = client.post("/personas", json={"nombre_completo": "Maria Lopez", "pais": "Colombia"}).json()
    resp = client.get(f"/personas/{creada['id']}")
    assert resp.status_code == 200
    assert resp.json()["nombre_completo"] == "Maria Lopez"


def test_persona_inexistente_devuelve_404(client):
    resp = client.get("/personas/no-existe")
    assert resp.status_code == 404
