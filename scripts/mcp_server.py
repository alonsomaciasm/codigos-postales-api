#!/usr/bin/env python3
"""
Servidor MCP (Model Context Protocol) para la API de Códigos Postales de México
===============================================================================
Permite a Agentes de IA (Claude, ChatGPT, Antigravity, LangChain) consultar e interactuar 
con la base de datos geográfica oficial de México en lenguaje natural.

Uso:
    python3 scripts/mcp_server.py
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from mcp.server.mcpserver import MCPServer
from app.api.v1.endpoints.codigos_postales import fetch_cp_data_from_db, normalize_search_text
from app.core.database import get_db_connection

# Inicializar Servidor MCP
mcp = MCPServer("MX Postal Codes AI Server")


@mcp.tool()
def consultar_codigo_postal(cp: str) -> str:
    """
    Busca la información geográfica oficial de un Código Postal de México de 5 dígitos (ej. '01000', '64000').
    Retorna el estado, municipio, ciudad y la lista de colonias/asentamientos asociadas.
    """
    rows = fetch_cp_data_from_db(cp)
    if not rows:
        return f"El código postal '{cp}' no existe en el catálogo oficial de SEPOMEX."

    r0 = rows[0]
    colonias = [f"{r['asentamiento_nombre']} ({r['tipo_asentamiento']}, {r['zona']})" for r in rows]
    colonias_str = "; ".join(colonias)

    return (
        f"Código Postal: {cp}\n"
        f"Estado: {r0['estado_nombre']} (Clave: {r0['clave_estado']})\n"
        f"Municipio/Alcaldía: {r0['municipio_nombre']} (Clave: {r0['clave_municipio']})\n"
        f"Ciudad: {r0.get('ciudad') or 'N/A'}\n"
        f"Total Colonias: {len(rows)}\n"
        f"Colonias: {colonias_str}"
    )


@mcp.tool()
def validar_direccion_postal(codigo_postal: str, colonia: str = "", estado: str = "", municipio: str = "") -> str:
    """
    Valida si una colonia, municipio o estado ingresados en un formulario o texto coinciden exactamente
    con el Código Postal registrado oficialmente en SEPOMEX.
    """
    rows = fetch_cp_data_from_db(codigo_postal)
    if not rows:
        return f"No se pudo validar. El código postal '{codigo_postal}' no existe en SEPOMEX."

    r0 = rows[0]
    evaluaciones = []
    
    if colonia:
        col_norm = normalize_search_text(colonia)
        match_col = any(normalize_search_text(r["asentamiento_nombre"]) == col_norm or col_norm in normalize_search_text(r["asentamiento_nombre"]) for r in rows)
        evaluaciones.append(f"Colonia '{colonia}': {'COINCIDE' if match_col else 'NO COINCIDE'}")

    if estado:
        est_norm = normalize_search_text(estado)
        est_row_norm = normalize_search_text(r0["estado_nombre"])
        is_cdmx = (est_norm == "CDMX" and ("CIUDAD DE MEXICO" in est_row_norm or r0["clave_estado"] == "09"))
        match_est = (is_cdmx or est_norm == est_row_norm or est_norm == r0["clave_estado"] or est_norm in est_row_norm)
        evaluaciones.append(f"Estado '{estado}': {'COINCIDE' if match_est else 'NO COINCIDE'}")

    if municipio:
        mun_norm = normalize_search_text(municipio)
        mun_row_norm = normalize_search_text(r0["municipio_nombre"])
        match_mun = (mun_norm == mun_row_norm or mun_norm == r0["clave_municipio"] or mun_norm in mun_row_norm)
        evaluaciones.append(f"Municipio '{municipio}': {'COINCIDE' if match_mun else 'NO COINCIDE'}")

    res_str = "\n".join(evaluaciones) if evaluaciones else "No se proporcionaron campos para comparar."
    return (
        f"Resultado de Validación para CP {codigo_postal}:\n"
        f"Estado Oficial: {r0['estado_nombre']}\n"
        f"Municipio Oficial: {r0['municipio_nombre']}\n"
        f"Diagnóstico:\n{res_str}"
    )


@mcp.tool()
def buscar_asentamientos_por_nombre(nombre_colonia: str, limite: int = 10) -> str:
    """
    Busca colonias o asentamientos en todo México por nombre o palabra clave (insensible a acentos o mayúsculas).
    Retorna el código postal, tipo de asentamiento, municipio y estado.
    """
    norm_query = normalize_search_text(nombre_colonia)
    with get_db_connection(readonly=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT a.codigo_postal, a.nombre, a.tipo_asentamiento, e.nombre as estado_nombre, m.nombre as municipio_nombre
               FROM asentamientos a
               JOIN estados e ON a.clave_estado = e.clave_estado
               JOIN municipios m ON a.clave_estado = m.clave_estado AND a.clave_municipio = m.clave_municipio
               WHERE a.nombre_normalizado LIKE ? OR a.nombre LIKE ?
               LIMIT ?""",
            (f"%{norm_query}%", f"%{nombre_colonia.strip()}%", limite)
        )
        rows = cursor.fetchall()
        if not rows:
            return f"No se encontraron colonias con el nombre '{nombre_colonia}'."

        res = [f"• {r['nombre']} ({r['tipo_asentamiento']}) - CP: {r['codigo_postal']} - {r['municipio_nombre']}, {r['estado_nombre']}" for r in rows]
        return f"Resultados para '{nombre_colonia}':\n" + "\n".join(res)


if __name__ == "__main__":
    mcp.run(transport='stdio')
