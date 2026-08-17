import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_root_attribution():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "attribution" in data
    assert "Creative Commons" in data["attribution"]["text"]

def test_attribution_endpoint():
    response = client.get("/api/v1/attribution")
    assert response.status_code == 200
    data = response.json()
    assert "mensaje" in data
    assert "Creative Commons" in data["mensaje"]

def test_health_check_active_db():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert "timestamp" in data

def test_invalid_cp_format():
    response = client.get("/api/v1/codigo-postal/invalid")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"

def test_valid_cp_query_lru_cache():
    resp1 = client.get("/api/v1/codigo-postal/01000")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["codigo_postal"] == "01000"

    resp2 = client.get("/api/v1/codigo-postal/01000")
    assert resp2.status_code == 200
    assert resp2.json() == data1

def test_proximity_search_by_coordinates():
    # Petición por proximidad en CDMX (Lat=19.4326, Lng=-99.1332, Radio=5 km)
    response = client.get("/api/v1/codigo-postal/cercanos?lat=19.4326&lng=-99.1332&radio_km=5.0&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "distancia_km" in data[0]
    assert data[0]["distancia_km"] <= 5.0
    # Comprobar que los resultados vienen ordenados por distancia ascendente
    distances = [item["distancia_km"] for item in data]
    assert distances == sorted(distances)

def test_gzip_compression_middleware():
    headers = {"Accept-Encoding": "gzip"}
    response = client.get("/api/v1/asentamientos?limit=50", headers=headers)
    assert response.status_code == 200
    assert "content-encoding" in response.headers
    assert response.headers["content-encoding"] == "gzip"

def test_accent_insensitive_search():
    response = client.get("/api/v1/asentamientos/search?query=juarez")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

def test_paginated_asentamientos_with_filters():
    response = client.get("/api/v1/asentamientos?clave_estado=09&tipo_asentamiento=Colonia&page=1&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "total_records" in data
    assert data["current_page"] == 1
    assert len(data["data"]) <= 5

def test_generate_jwt_token():
    response = client.post("/api/v1/auth/token", headers={"X-API-Key": "key-dev-12345"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

def test_protected_mode_access(monkeypatch):
    monkeypatch.setattr(settings, "REQUIRE_AUTH", True)

    resp_no_auth = client.get("/api/v1/codigo-postal/01000")
    assert resp_no_auth.status_code == 401

    resp_api_key = client.get("/api/v1/codigo-postal/01000", headers={"X-API-Key": "key-dev-12345"})
    assert resp_api_key.status_code == 200

def test_security_headers():
    response = client.get("/health")
    assert "x-content-type-options" in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "x-correlation-id" in response.headers

def test_cache_control_headers():
    response = client.get("/api/v1/codigo-postal/01000")
    assert response.status_code == 200
    assert "cache-control" in response.headers
    assert "public, max-age=86400" in response.headers["cache-control"]

def test_estados_and_municipios_endpoints():
    resp_estados = client.get("/api/v1/estados")
    assert resp_estados.status_code == 200
    estados = resp_estados.json()
    assert len(estados) > 0
    assert any(e["clave_estado"] == "09" for e in estados)

    resp_mun = client.get("/api/v1/estados/09/municipios")
    assert resp_mun.status_code == 200
    municipios = resp_mun.json()
    assert len(municipios) > 0

def test_cp_not_found_returns_404():
    response = client.get("/api/v1/codigo-postal/99999")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"
    assert "timestamp" in data["error"]
    assert "correlation_id" in data["error"]

def test_invalid_coordinates_out_of_bounds():
    # Latitud > 90
    resp_lat = client.get("/api/v1/codigo-postal/cercanos?lat=95.0&lng=-99.13")
    assert resp_lat.status_code == 422
    assert resp_lat.json()["error"]["code"] == "VALIDATION_ERROR"

    # Longitud < -180
    resp_lng = client.get("/api/v1/codigo-postal/cercanos?lat=19.43&lng=-190.0")
    assert resp_lng.status_code == 422
    assert resp_lng.json()["error"]["code"] == "VALIDATION_ERROR"

    # Radio negativo o 0
    resp_radio = client.get("/api/v1/codigo-postal/cercanos?lat=19.43&lng=-99.13&radio_km=0")
    assert resp_radio.status_code == 422
    assert resp_radio.json()["error"]["code"] == "VALIDATION_ERROR"

def test_auth_errors_invalid_api_key_and_jwt(monkeypatch):
    monkeypatch.setattr(settings, "REQUIRE_AUTH", True)

    # API Key incorrecta al solicitar token
    resp_bad_key = client.post("/api/v1/auth/token", headers={"X-API-Key": "key-invalida"})
    assert resp_bad_key.status_code == 401

    # Token Bearer malformado/inválido
    resp_bad_bearer = client.get("/api/v1/codigo-postal/01000", headers={"Authorization": "Bearer token_falso_123"})
    assert resp_bad_bearer.status_code == 401

def test_asentamientos_short_query_validation():
    # Parámetro query menor a 2 caracteres
    response = client.get("/api/v1/asentamientos?query=a")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

def test_health_check_database_failure_simulation(monkeypatch):
    def mock_db_error(readonly=True):
        raise Exception("Simulated DB Connection Error")

    monkeypatch.setattr("app.main.get_db_connection", mock_db_error)
    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["database"] == "disconnected"

def test_autocomplete_codigo_postal():
    response = client.get("/api/v1/codigo-postal/autocomplete?prefix=01")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["codigo_postal"].startswith("01")
    assert "estado_nombre" in data[0]

def test_catalog_stats_endpoint():
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_codigos_postales"] > 0
    assert data["total_asentamientos"] > 0
    assert data["total_estados"] == 32
    assert "tipos_asentamiento_conteo" in data

def test_municipio_detalle_and_not_found():
    # Caso Exitoso: CDMX Álvaro Obregón (09 / 010)
    response = client.get("/api/v1/estados/09/municipios/010")
    assert response.status_code == 200
    data = response.json()
    assert data["municipio_nombre"] == "Álvaro Obregón"
    assert len(data["codigos_postales"]) > 0

    # Caso Error 404: Municipio Inexistente (09 / 999)
    resp_404 = client.get("/api/v1/estados/09/municipios/999")
    assert resp_404.status_code == 404
    assert resp_404.json()["error"]["code"] == "NOT_FOUND"

def test_geojson_export_endpoint():
    response = client.get("/api/v1/codigo-postal/01000/geojson")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert data["codigo_postal"] == "01000"
    assert len(data["features"]) > 0
    assert data["features"][0]["type"] == "Feature"
    assert "coordinates" in data["features"][0]["geometry"]

def test_sat_cfdi_fields():
    response = client.get("/api/v1/codigo-postal/01000")
    assert response.status_code == 200
    data = response.json()
    assert "nombre_sat" in data["estado"]
    assert data["estado"]["nombre_sat"] == "CIUDAD DE MEXICO"
    assert "nombre_sat" in data["asentamientos"][0]

def test_dashboard_endpoint():
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "API Códigos Postales 🇲🇽" in response.text

def test_extended_cp_validation():
    # Prueba de validación cruzada exitosa
    response = client.get("/api/v1/codigo-postal/01000?colonia=San%20Ángel&estado=Ciudad%20de%20México")
    assert response.status_code == 200
    data = response.json()
    assert "validacion" in data
    assert data["validacion"]["es_valido"] is True
    assert data["validacion"]["match_colonia"] is True
    assert data["validacion"]["match_estado"] is True
    assert data["validacion"]["coincidencia_exacta"] is True

    # Prueba de validación cruzada con disconformidad
    response_invalid = client.get("/api/v1/codigo-postal/01000?colonia=Polanco")
    assert response_invalid.status_code == 200
    data_inv = response_invalid.json()
    assert data_inv["validacion"]["match_colonia"] is False
    assert data_inv["validacion"]["coincidencia_exacta"] is False

def test_asentamientos_csv_export():
    response = client.get("/api/v1/asentamientos?clave_estado=09&limit=5&format=csv")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
def test_export_estado_pdf():
    response = client.get("/api/v1/estados/09/pdf?titulo=Reporte%20Prueba&subtitulo=Ficha%20Tecnica")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
def test_batch_validate_endpoint():
    payload = [
        {"id_externo": "CUST-001", "codigo_postal": "01000", "colonia": "San Ángel", "estado": "CDMX"},
        {"id_externo": "CUST-002", "codigo_postal": "99999", "colonia": "Desconocida"}
    ]
    response = client.post("/api/v1/codigo-postal/batch-validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id_externo"] == "CUST-001"
    assert data[0]["existe_cp"] is True
    assert data[0]["validacion"]["coincidencia_exacta"] is True

    assert data[1]["id_externo"] == "CUST-002"
    assert data[1]["existe_cp"] is False
    assert data[1]["validacion"]["es_valido"] is False

    # Prueba de Exceso de Límite (105 ítems > 100)
    over_limit_payload = [{"codigo_postal": "01000"}] * 105
    resp_over = client.post("/api/v1/codigo-postal/batch-validate", json=over_limit_payload)
    assert resp_over.status_code == 422
    err_msg = resp_over.json().get("error", {}).get("message", "") or resp_over.json().get("detail", "")
def test_body_limit_exceeded():
    # Enviar payload con Content-Length mayor a 1 MB
    large_payload = "a" * (1024 * 1024 + 100)
    response = client.post(
        "/api/v1/codigo-postal/batch-validate",
        content=large_payload,
        headers={"Content-Type": "application/json", "Content-Length": str(len(large_payload))}
    )
    assert response.status_code == 413
def test_estado_geojson_export():
    response = client.get("/api/v1/estados/09/geojson")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert data["codigo_postal"] == "ESTADO-09"
    assert len(data["features"]) > 0

def test_static_widget_file():
    response = client.get("/static/mx-postal-widget.js")
    assert response.status_code == 200
    assert "data-mx-postal" in response.text





