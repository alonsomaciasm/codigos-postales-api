import pytest
from scripts.mcp_server import (
    consultar_codigo_postal,
    validar_direccion_postal,
    buscar_asentamientos_por_nombre,
)


def test_consultar_codigo_postal():
    # CP existente
    res = consultar_codigo_postal("01000")
    assert "Código Postal: 01000" in res
    assert "Estado:" in res
    assert "Colonias:" in res

    # CP inexistente
    res_invalid = consultar_codigo_postal("999999")
    assert "no existe" in res_invalid


def test_validar_direccion_postal():
    # Validación correcta
    res = validar_direccion_postal(
        codigo_postal="01000",
        colonia="San Ángel",
        estado="CDMX",
        municipio="Álvaro Obregón",
    )
    assert "Resultado de Validación" in res
    assert "COINCIDE" in res

    # CP no existente
    res_invalid = validar_direccion_postal(codigo_postal="00000", colonia="Inexistente")
    assert "No se pudo validar" in res_invalid


def test_buscar_asentamientos_por_nombre():
    # Búsqueda por nombre
    res = buscar_asentamientos_por_nombre(nombre_colonia="Polanco", limite=5)
    assert "Resultados para 'Polanco':" in res
    assert "CP:" in res

    # Búsqueda sin resultados
    res_empty = buscar_asentamientos_por_nombre(nombre_colonia="NombreTotalmenteInexistente123")
    assert "No se encontraron colonias" in res_empty
