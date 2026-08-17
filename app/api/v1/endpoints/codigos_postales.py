import math
import unicodedata
from fastapi import APIRouter, HTTPException, Path, Query, Body, status
from typing import List, Optional
from functools import lru_cache

from app.core.config import settings
from app.core.logger import logger
from app.core.database import get_db_connection
from app.core.geo import haversine_distance, calculate_bounding_box
from app.models.schema import (
    CodigoPostalDetalleSchema,
    EstadoSchema,
    MunicipioSchema,
    AsentamientoSchema,
    AsentamientoCercanoSchema,
    PaginatedAsentamientosSchema,
    AutocompleteItemSchema,
    CatalogStatsSchema,
    GeoJSONFeatureCollectionSchema,
    GeoJSONFeatureSchema,
    GeoJSONGeometrySchema,
    ValidacionCoincidenciaSchema,
    BatchValidateItemSchema,
    BatchValidateResultSchema,
)

router = APIRouter()


def normalize_search_text(text: str) -> str:
    """Remueve diacríticos/acentos, prefijos coloquiales de tipo de asentamiento y convierte a mayúsculas."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    stripped = "".join([c for c in nfkd if not unicodedata.combining(c)]).upper().strip()
    
    # Remover prefijos de tipo de asentamiento coloquiales
    prefixes = ["FRACCIONAMIENTO ", "FRACC ", "FRACC. ", "COLONIA ", "COL. ", "COL ", "BARRIO ", "BO. ", "CONJUNTO "]
    for p in prefixes:
        if stripped.startswith(p):
            stripped = stripped[len(p):].strip()
            break
            
    return stripped


@lru_cache(maxsize=settings.CACHE_LRU_MAXSIZE)
def fetch_cp_data_from_db(cp: str) -> Optional[List[dict]]:
    """Consulta la BD y almacena el resultado en caché LRU en memoria RAM para CPs de alta frecuencia."""
    with get_db_connection(readonly=True) as conn:
        cursor = conn.cursor()
        query = """
            SELECT 
                a.id, a.codigo_postal, a.nombre as asentamiento_nombre, a.tipo_asentamiento, a.zona, a.ciudad,
                a.latitud, a.longitud,
                e.clave_estado, e.nombre as estado_nombre,
                m.clave_municipio, m.nombre as municipio_nombre
            FROM asentamientos a
            JOIN estados e ON a.clave_estado = e.clave_estado
            JOIN municipios m ON a.clave_estado = m.clave_estado AND a.clave_municipio = m.clave_municipio
            WHERE a.codigo_postal = ?
        """
        cursor.execute(query, (cp,))
        rows = cursor.fetchall()
        if not rows:
            return None
        return [dict(r) for r in rows]


@router.get("/codigo-postal/cercanos", response_model=List[AsentamientoCercanoSchema], summary="Búsqueda por proximidad geográfica por coordenadas (Lat/Lng)")
def get_asentamientos_cercanos(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitud en grados decimales (ej. 19.4326)"),
    lng: float = Query(..., ge=-180.0, le=180.0, description="Longitud en grados decimales (ej. -99.1332)"),
    radio_km: float = Query(5.0, ge=0.1, le=50.0, description="Radio de búsqueda en kilómetros"),
    limit: int = Query(10, ge=1, le=50, description="Límite máximo de asentamientos a retornar")
):
    """
    Busca los asentamientos y códigos postales más cercanos a un punto geográfico (Latitud, Longitud)
    dentro de un radio en kilómetros utilizando filtrado por Bounding Box e índices B-Tree en SQLite + Fórmula de Haversine.
    """
    min_lat, max_lat, min_lon, max_lon = calculate_bounding_box(lat, lng, radio_km)
    
    with get_db_connection(readonly=True) as conn:
        cursor = conn.cursor()
        query = """
            SELECT id, codigo_postal, nombre, tipo_asentamiento, zona, ciudad, clave_estado, clave_municipio, latitud, longitud
            FROM asentamientos
            WHERE latitud BETWEEN ? AND ? AND longitud BETWEEN ? AND ?
        """
        cursor.execute(query, (min_lat, max_lat, min_lon, max_lon))
        rows = cursor.fetchall()
        
        candidatos = []
        for r in rows:
            r_lat = r["latitud"]
            r_lng = r["longitud"]
            if r_lat is not None and r_lng is not None:
                dist = haversine_distance(lat, lng, r_lat, r_lng)
                if dist <= radio_km:
                    item = AsentamientoCercanoSchema(
                        id=r["id"],
                        nombre=r["nombre"],
                        tipo_asentamiento=r["tipo_asentamiento"],
                        zona=r["zona"],
                        codigo_postal=r["codigo_postal"],
                        ciudad=r["ciudad"],
                        clave_estado=r["clave_estado"],
                        clave_municipio=r["clave_municipio"],
                        latitud=r_lat,
                        longitud=r_lng,
                        distancia_km=dist
                    )
                    candidatos.append(item)
                    
        # Ordenar por distancia ortodrómica ascendente
        candidatos.sort(key=lambda x: x.distancia_km)
        return candidatos[:limit]


@router.get("/codigo-postal/autocomplete", response_model=List[AutocompleteItemSchema], summary="Autocompletado de Código Postal por prefijo (2 a 5 dígitos)")
def autocomplete_codigo_postal(
    prefix: str = Query(..., min_length=2, max_length=5, pattern="^[0-9]{2,5}$", description="Prefijo numérico del CP (ej. 01, 010, 0100)"),
    limit: int = Query(10, ge=1, le=50, description="Cantidad máxima de sugerencias a retornar")
):
    """
    Endpoint de autocompletado en tiempo real para formularios dinámicos.
    Recibe un prefijo de 2 a 5 dígitos y retorna las sugerencias correspondientes.
    """
    logger.info(f"Petición de autocompletado para prefijo: {prefix}")
    with get_db_connection(readonly=True) as conn:
        cursor = conn.cursor()
        query = """
            SELECT a.codigo_postal, e.nombre as estado_nombre, m.nombre as municipio_nombre, COUNT(a.id) as total_asentamientos
            FROM asentamientos a
            JOIN estados e ON a.clave_estado = e.clave_estado
            JOIN municipios m ON a.clave_estado = m.clave_estado AND a.clave_municipio = m.clave_municipio
            WHERE a.codigo_postal LIKE ?
            GROUP BY a.codigo_postal
            ORDER BY a.codigo_postal ASC
            LIMIT ?
        """
        cursor.execute(query, (f"{prefix}%", limit))
        rows = cursor.fetchall()
        
        return [
            AutocompleteItemSchema(
                codigo_postal=r["codigo_postal"],
                estado_nombre=r["estado_nombre"],
                municipio_nombre=r["municipio_nombre"],
                total_asentamientos=r["total_asentamientos"]
            )
            for r in rows
        ]


@router.get("/stats", response_model=CatalogStatsSchema, summary="Estadísticas y resumen métrico del catálogo SEPOMEX")
def get_catalog_stats():
    """
    Retorna métricas globales del catálogo cargado en la base de datos (conteo de CPs, asentamientos, estados y desgloses).
    """
    logger.info("Generando reporte de estadísticas del catálogo SEPOMEX...")
    with get_db_connection(readonly=True) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(DISTINCT codigo_postal) FROM asentamientos;")
        total_cps = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM asentamientos;")
        total_asentamientos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM estados;")
        total_estados = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM municipios;")
        total_municipios = cursor.fetchone()[0]

        cursor.execute("SELECT tipo_asentamiento, COUNT(*) as count FROM asentamientos GROUP BY tipo_asentamiento ORDER BY count DESC LIMIT 15;")
        tipo_rows = cursor.fetchall()
        tipos_conteo = {r["tipo_asentamiento"]: r["count"] for r in tipo_rows}

        cursor.execute("SELECT zona, COUNT(*) as count FROM asentamientos GROUP BY zona;")
        zona_rows = cursor.fetchall()
        zonas_conteo = {r["zona"]: r["count"] for r in zona_rows}

        return CatalogStatsSchema(
            total_codigos_postales=total_cps,
            total_asentamientos=total_asentamientos,
            total_estados=total_estados,
            total_municipios=total_municipios,
            tipos_asentamiento_conteo=tipos_conteo,
            zonas_conteo=zonas_conteo
        )


@router.get("/codigo-postal/{cp}/geojson", response_model=GeoJSONFeatureCollectionSchema, summary="Exportación de Código Postal en estándar GeoJSON")
def get_codigo_postal_geojson(
    cp: str = Path(..., pattern="^[0-9]{5}$", description="Código Postal de 5 dígitos (ej. 01000)")
):
    """
    Retorna la ubicación y colonias pertenecientes a un Código Postal en formato estándar GeoJSON (FeatureCollection)
    ideal para integración con Mapbox, Leaflet, Google Maps y GIS.
    """
    logger.info(f"Exportando GeoJSON para Código Postal: {cp}")
    rows = fetch_cp_data_from_db(cp)
    
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El código postal {cp} no fue encontrado en el catálogo de SEPOMEX."
        )

    features = []
    for r in rows:
        lat = r["latitud"]
        lng = r["longitud"]
        if lat is not None and lng is not None:
            feature = GeoJSONFeatureSchema(
                geometry=GeoJSONGeometrySchema(coordinates=[lng, lat]),
                properties={
                    "id": r["id"],
                    "codigo_postal": r["codigo_postal"],
                    "nombre": r["asentamiento_nombre"],
                    "nombre_sat": normalize_search_text(r["asentamiento_nombre"]),
                    "tipo_asentamiento": r["tipo_asentamiento"],
                    "zona": r["zona"],
                    "ciudad": r["ciudad"],
                    "estado": r["estado_nombre"],
                    "municipio": r["municipio_nombre"]
                }
            )
            features.append(feature)

    return GeoJSONFeatureCollectionSchema(
        codigo_postal=cp,
        features=features
    )


def perform_cross_validation(rows: List[dict], input_colonia: Optional[str], input_estado: Optional[str], input_municipio: Optional[str]) -> Optional[ValidacionCoincidenciaSchema]:
    """Helper para realizar validación cruzada de coincidencia de formulario sobre un conjunto de filas de un CP."""
    if not (input_colonia or input_estado or input_municipio):
        return None

    first_row = rows[0]
    match_col = None
    match_est = None
    match_mun = None

    if input_colonia:
        col_norm = normalize_search_text(input_colonia)
        match_col = any(normalize_search_text(r["asentamiento_nombre"]) == col_norm or col_norm in normalize_search_text(r["asentamiento_nombre"]) for r in rows)

    if input_estado:
        est_norm = normalize_search_text(input_estado).replace(".", "").replace(" ", "")
        est_row_norm = normalize_search_text(first_row["estado_nombre"]).replace(".", "").replace(" ", "")
        
        # Mapa de alias de estados
        state_aliases = {
            "CDMX": ["CIUDADDEMEXICO", "09", "DF", "DISTRITOFEDERAL"],
            "EDOMEX": ["ESTADODEMEXICO", "MEXICO", "15"],
            "EDOMEXICO": ["ESTADODEMEXICO", "MEXICO", "15"],
            "NL": ["NUEVOLEON", "19"],
            "NUEVOLEON": ["NL", "19"]
        }
        
        is_alias_match = False
        if est_norm in state_aliases and any(alias in est_row_norm or alias == first_row["clave_estado"] for alias in state_aliases[est_norm]):
            is_alias_match = True

        match_est = (is_alias_match or est_norm == est_row_norm or est_norm == first_row["clave_estado"] or est_norm in est_row_norm or est_row_norm in est_norm)

    if input_municipio:
        mun_norm = normalize_search_text(input_municipio)
        mun_row_norm = normalize_search_text(first_row["municipio_nombre"])
        match_mun = (mun_norm == mun_row_norm or mun_norm == first_row["clave_municipio"] or mun_norm in mun_row_norm)

    evals = [m for m in (match_col, match_est, match_mun) if m is not None]
    es_valido = all(evals) if evals else True
    coincidencia_exacta = es_valido and (match_col is not False) and (match_est is not False)

    if coincidencia_exacta:
        msg = "Coincidencia exacta de formulario válida."
    elif es_valido:
        msg = "Coincidencia parcial válida."
    else:
        msg = "Disconformidad detectada: Los datos del formulario no coinciden con el registro de SEPOMEX."

    return ValidacionCoincidenciaSchema(
        es_valido=es_valido,
        match_colonia=match_col,
        match_estado=match_est,
        match_municipio=match_mun,
        coincidencia_exacta=coincidencia_exacta,
        mensaje=msg
    )


@router.get("/codigo-postal/{cp}", response_model=CodigoPostalDetalleSchema, summary="Consulta un Código Postal de México (incluye campos SAT CFDI 4.0 y validación opcional)")
def get_codigo_postal(
    cp: str = Path(..., pattern="^[0-9]{5}$", description="Código Postal de 5 dígitos (ej. 01000, 64000)"),
    colonia: Optional[str] = Query(None, description="Nombre opcional de colonia para validación cruzada"),
    estado: Optional[str] = Query(None, description="Nombre u opción de estado para validación cruzada"),
    municipio: Optional[str] = Query(None, description="Nombre u opción de municipio para validación cruzada")
):
    """
    Busca la información completa de un Código Postal incluyendo nombres normalizados en mayúsculas sin acentos compatibles con SAT CFDI 4.0.
    Opcionalmente, si se envían los parámetros `colonia`, `estado` o `municipio`, realiza una validación cruzada para verificar la coincidencia del formulario.
    """
    rows = fetch_cp_data_from_db(cp)
    
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El código postal {cp} no fue encontrado en el catálogo de SEPOMEX."
        )
    
    first_row = rows[0]
    
    asentamientos = [
        AsentamientoSchema(
            id=r["id"],
            nombre=r["asentamiento_nombre"],
            nombre_sat=normalize_search_text(r["asentamiento_nombre"]),
            tipo_asentamiento=r["tipo_asentamiento"],
            zona=r["zona"],
            codigo_postal=r["codigo_postal"],
            ciudad=r["ciudad"],
            clave_estado=first_row["clave_estado"],
            clave_municipio=first_row["clave_municipio"],
            latitud=r["latitud"],
            longitud=r["longitud"]
        )
        for r in rows
    ]

    # Lógica de validación cruzada opcional si se enviaron parámetros de coincidencia
    validacion_obj = perform_cross_validation(rows, colonia, estado, municipio)
    
    return CodigoPostalDetalleSchema(
        codigo_postal=cp,
        estado=EstadoSchema(
            clave_estado=first_row["clave_estado"],
            nombre=first_row["estado_nombre"],
            nombre_sat=normalize_search_text(first_row["estado_nombre"])
        ),
        municipio=MunicipioSchema(
            clave_municipio=first_row["clave_municipio"],
            nombre=first_row["municipio_nombre"],
            nombre_sat=normalize_search_text(first_row["municipio_nombre"])
        ),
        ciudad=first_row["ciudad"],
        asentamientos=asentamientos,
        validacion=validacion_obj
    )


@router.get("/asentamientos", summary="Búsqueda avanzada, filtros, paginación con FTS5 y exportación CSV/Excel")
def get_asentamientos(
    query: Optional[str] = Query(None, min_length=2, max_length=100, description="Búsqueda por texto (insensible a acentos/mayúsculas)"),
    clave_estado: Optional[str] = Query(None, max_length=10, description="Filtrar por clave de estado (ej. 09)"),
    clave_municipio: Optional[str] = Query(None, max_length=10, description="Filtrar por clave de municipio (ej. 010)"),
    tipo_asentamiento: Optional[str] = Query(None, max_length=50, description="Filtrar por tipo (ej. Colonia, Barrio, Fraccionamiento)"),
    zona: Optional[str] = Query(None, max_length=20, description="Filtrar por zona (Urbano o Rural)"),
    page: int = Query(1, ge=1, description="Número de página (1-based)"),
    limit: int = Query(20, ge=1, le=1000, description="Cantidad de registros por página (máx 1000 para exportación)"),
    format: Optional[str] = Query(None, description="Formato opcional de exportación directa ('csv' o 'excel')")
):
    """
    Endpoint de Búsqueda Avanzada FTS5 (Full-Text Search) con tolerancia a acentos,
    filtros combinados, paginación estructurada y exportación directa en formato CSV/Excel si se especifica `format=csv`.
    """
    offset = (page - 1) * limit
    where_clauses = []
    params = []

    with get_db_connection(readonly=True) as conn:
        cursor = conn.cursor()

        fts_ids = None
        if query:
            norm_query = normalize_search_text(query)
            try:
                fts_query = f'"{norm_query}"*'
                cursor.execute(
                    "SELECT asentamiento_id FROM asentamientos_fts WHERE asentamientos_fts MATCH ? LIMIT 1000",
                    (fts_query,)
                )
                rows_fts = cursor.fetchall()
                if rows_fts:
                    fts_ids = [r["asentamiento_id"] for r in rows_fts]
            except Exception:
                fts_ids = None

            if fts_ids is not None and len(fts_ids) > 0:
                placeholders = ",".join(["?"] * len(fts_ids))
                where_clauses.append(f"a.id IN ({placeholders})")
                params.extend(fts_ids)
            else:
                where_clauses.append("(a.nombre_normalizado LIKE ? OR a.nombre LIKE ?)")
                search_term = f"%{norm_query}%"
                search_term_orig = f"%{query.strip()}%"
                params.extend([search_term, search_term_orig])

        if clave_estado:
            where_clauses.append("a.clave_estado = ?")
            params.append(clave_estado.zfill(2))

        if clave_municipio:
            where_clauses.append("a.clave_municipio = ?")
            params.append(clave_municipio.zfill(3))

        if tipo_asentamiento:
            where_clauses.append("a.tipo_asentamiento LIKE ?")
            params.append(f"%{tipo_asentamiento.strip()}%")

        if zona:
            where_clauses.append("a.zona = ?")
            params.append(zona.strip().capitalize())

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        count_query = f"SELECT COUNT(*) FROM asentamientos a {where_sql}"
        cursor.execute(count_query, params)
        total_records = cursor.fetchone()[0]

        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0

        data_query = f"""
            SELECT a.id, a.codigo_postal, a.nombre, a.tipo_asentamiento, a.zona, a.ciudad, a.clave_estado, a.clave_municipio, a.latitud, a.longitud
            FROM asentamientos a
            {where_sql}
            ORDER BY a.codigo_postal ASC, a.nombre ASC
            LIMIT ? OFFSET ?
        """
        cursor.execute(data_query, params + [limit, offset])
        rows = cursor.fetchall()

        # Si se solicita exportación en CSV o Excel
        if format and format.lower() in ["csv", "excel", "xlsx"]:
            import io
            import csv
            from fastapi.responses import StreamingResponse

            output = io.StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["ID", "CodigoPostal", "Nombre", "NombreSAT", "TipoAsentamiento", "Zona", "Ciudad", "ClaveEstado", "ClaveMunicipio", "Latitud", "Longitud"])
            
            for r in rows:
                writer.writerow([
                    r["id"], r["codigo_postal"], r["nombre"], normalize_search_text(r["nombre"]),
                    r["tipo_asentamiento"], r["zona"], r["ciudad"] or "", r["clave_estado"],
                    r["clave_municipio"], r["latitud"] or "", r["longitud"] or ""
                ])
            
            output.seek(0)
            filename = f"asentamientos_export.{'csv' if format.lower() == 'csv' else 'csv'}"
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode("utf-8-sig")),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

        items = [
            AsentamientoSchema(
                id=r["id"],
                nombre=r["nombre"],
                nombre_sat=normalize_search_text(r["nombre"]),
                tipo_asentamiento=r["tipo_asentamiento"],
                zona=r["zona"],
                codigo_postal=r["codigo_postal"],
                ciudad=r["ciudad"],
                clave_estado=r["clave_estado"],
                clave_municipio=r["clave_municipio"],
                latitud=r["latitud"],
                longitud=r["longitud"]
            )
            for r in rows
        ]

        return PaginatedAsentamientosSchema(
            total_records=total_records,
            total_pages=total_pages,
            current_page=page,
            limit=limit,
            data=items
        )


@router.get("/asentamientos/search", response_model=List[AsentamientoSchema], summary="Búsqueda rápida de asentamientos por nombre con FTS5")
def search_asentamientos(
    query: str = Query(..., min_length=2, description="Nombre o parte del nombre de la colonia/asentamiento"),
    limit: int = Query(20, ge=1, le=100, description="Límite de resultados")
):
    """
    Búsqueda rápida de asentamientos optimizada con FTS5 (Full-Text Search) e insensibilidad a acentos.
    """
    norm_query = normalize_search_text(query)
    with get_db_connection(readonly=True) as conn:
        cursor = conn.cursor()

        try:
            fts_query = f'"{norm_query}"*'
            cursor.execute(
                """SELECT a.id, a.nombre, a.tipo_asentamiento, a.zona, a.codigo_postal, a.ciudad, a.clave_estado, a.clave_municipio, a.latitud, a.longitud
                   FROM asentamientos a
                   JOIN asentamientos_fts f ON a.id = f.asentamiento_id
                   WHERE asentamientos_fts MATCH ?
                   LIMIT ?""",
                (fts_query, limit)
            )
            rows = cursor.fetchall()
            if rows:
                return [
                    AsentamientoSchema(
                        id=r["id"],
                        nombre=r["nombre"],
                        tipo_asentamiento=r["tipo_asentamiento"],
                        zona=r["zona"],
                        codigo_postal=r["codigo_postal"],
                        ciudad=r["ciudad"],
                        clave_estado=r["clave_estado"],
                        clave_municipio=r["clave_municipio"],
                        latitud=r["latitud"],
                        longitud=r["longitud"]
                    )
                    for r in rows
                ]
        except Exception:
            pass
        # Fallback si FTS5 no arroja resultados directos
        search_term = f"%{norm_query}%"
        cursor.execute(
            """SELECT id, nombre, tipo_asentamiento, zona, codigo_postal, ciudad, clave_estado, clave_municipio, latitud, longitud
               FROM asentamientos 
               WHERE nombre_normalizado LIKE ? OR nombre LIKE ?
               LIMIT ?""",
            (search_term, f"%{query.strip()}%", limit)
        )
        rows = cursor.fetchall()
        
        return [
            AsentamientoSchema(
                id=r["id"],
                nombre=r["nombre"],
                tipo_asentamiento=r["tipo_asentamiento"],
                zona=r["zona"],
                codigo_postal=r["codigo_postal"],
                ciudad=r["ciudad"],
                clave_estado=r["clave_estado"],
                clave_municipio=r["clave_municipio"],
                latitud=r["latitud"],
                longitud=r["longitud"]
            )
            for r in rows
        ]


@router.post(
    "/codigo-postal/batch-validate",
    response_model=List[BatchValidateResultSchema],
    summary="Validación y Normalización Masiva en Lote (Batch Validate)"
)
def batch_validate_codigos_postales(items: List[BatchValidateItemSchema] = Body(...)):
    """
    Recibe un listado (JSON Array) de hasta 100 direcciones/formularios con Código Postal, Colonia y Estado.
    Valida y normaliza en lote en una sola transacción ultrarrápida, retornando la lista corregida con el estándar del SAT.
    """
    if len(items) > settings.BATCH_MAX_ITEMS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Exceso de capacidad en lote: La solicitud contiene {len(items)} ítems. El límite máximo permitido es de {settings.BATCH_MAX_ITEMS} solicitudes por petición."
        )

    logger.info(f"Procesando solicitud de validación masiva en lote para {len(items)} ítems...")
    results = []

    for item in items:
        rows = fetch_cp_data_from_db(item.codigo_postal)
        if not rows:
            results.append(
                BatchValidateResultSchema(
                    id_externo=item.id_externo,
                    codigo_postal=item.codigo_postal,
                    existe_cp=False,
                    validacion=ValidacionCoincidenciaSchema(
                        es_valido=False,
                        match_colonia=False,
                        match_estado=False,
                        match_municipio=False,
                        coincidencia_exacta=False,
                        mensaje=f"El código postal {item.codigo_postal} no existe en el catálogo SEPOMEX."
                    ),
                    oficial=None
                )
            )
            continue

        diag = perform_cross_validation(
            rows=rows,
            input_colonia=item.colonia,
            input_estado=item.estado,
            input_municipio=item.municipio
        )

        r0 = rows[0]
        asentamientos_nombres = [r["asentamiento_nombre"] for r in rows]

        oficial_data = {
            "estado": r0["estado_nombre"],
            "estado_sat": normalize_search_text(r0["estado_nombre"]),
            "municipio": r0["municipio_nombre"],
            "municipio_sat": normalize_search_text(r0["municipio_nombre"]),
            "asentamientos": asentamientos_nombres
        }

        results.append(
            BatchValidateResultSchema(
                id_externo=item.id_externo,
                codigo_postal=item.codigo_postal,
                existe_cp=True,
                validacion=diag,
                oficial=oficial_data
            )
        )

    return results
