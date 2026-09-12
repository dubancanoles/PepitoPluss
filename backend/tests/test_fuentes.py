"""
Verifica RF2: Administracion de fuentes por pais.
Criterio de la rubrica (10 pts): administra correctamente nombre, URL,
pais, tipo y estado de las fuentes.
"""


def test_crear_fuente_con_atributos_minimos(client):
    payload = {
        "nombre": "El Tiempo",
        "url_inicial": "https://www.eltiempo.com",
        "pais": "Colombia",
        "tipo": "NOTICIAS",
        "activa": True,
    }
    resp = client.post("/fuentes", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    for campo in ["nombre", "url_inicial", "pais", "tipo", "activa"]:
        assert campo in data


def test_listar_fuentes_filtradas_por_pais(client):
    client.post("/fuentes", json={
        "nombre": "Fuente CO", "url_inicial": "https://co.example.com",
        "pais": "Colombia", "tipo": "NOTICIAS",
    })
    client.post("/fuentes", json={
        "nombre": "Fuente MX", "url_inicial": "https://mx.example.com",
        "pais": "Mexico", "tipo": "NOTICIAS",
    })

    resp = client.get("/fuentes", params={"pais": "Colombia"})
    assert resp.status_code == 200
    paises = {f["pais"] for f in resp.json()}
    assert paises == {"Colombia"}


def test_listar_solo_fuentes_activas(client):
    client.post("/fuentes", json={
        "nombre": "Activa", "url_inicial": "https://a.example.com",
        "pais": "Colombia", "tipo": "BLOG", "activa": True,
    })
    client.post("/fuentes", json={
        "nombre": "Inactiva", "url_inicial": "https://b.example.com",
        "pais": "Colombia", "tipo": "BLOG", "activa": False,
    })

    resp = client.get("/fuentes", params={"activa": True})
    nombres = [f["nombre"] for f in resp.json()]
    assert "Activa" in nombres
    assert "Inactiva" not in nombres


def test_cambiar_estado_de_fuente(client):
    creada = client.post("/fuentes", json={
        "nombre": "Fuente X", "url_inicial": "https://x.example.com",
        "pais": "Colombia", "tipo": "OTRO", "activa": True,
    }).json()

    resp = client.patch(f"/fuentes/{creada['id']}/estado", params={"activa": False})
    assert resp.status_code == 200
    assert resp.json()["activa"] is False
