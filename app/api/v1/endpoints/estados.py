from fastapi import APIRouter, HTTPException, status
from typing import List
from app.core.config import settings
from app.core.database import get_db_connection
from app.core.logger import logger
from app.models.schema import (
    EstadoSchema,
    MunicipioSchema,
    AsentamientoSchema,
    MunicipioDetalleCodigosPostalesSchema,
    GeoJSONFeatureCollectionSchema,
    GeoJSONFeatureSchema,
    GeoJSONGeometrySchema
)

router = APIRouter()

from app.api.v1.endpoints.codigos_postales import normalize_search_text

@router.get("/estados", response_model=List[EstadoSchema], summary="Listado de Estados de México")
def get_estados():
    """Retorna la lista completa de las 32 entidades federativas de México."""
    logger.info("Consulta de catálogo completo de Estados.")
    with get_db_connection(readonly=True) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT clave_estado, nombre FROM estados ORDER BY clave_estado ASC;")
        rows = cursor.fetchall()
        return [
            EstadoSchema(
                clave_estado=r["clave_estado"],
                nombre=r["nombre"],
                nombre_sat=normalize_search_text(r["nombre"])
            )
            for r in rows
        ]


@router.get("/estados/{c_estado}/municipios", response_model=List[MunicipioSchema], summary="Municipios por Estado")
def get_municipios_by_estado(c_estado: str):
    """Retorna la lista de municipios o alcaldías correspondientes a una clave de estado (ej. 09 para CDMX, 19 para NL)."""
    clave_est = c_estado.zfill(2)
    logger.info(f"Consulta de municipios para estado clave: {clave_est}")
    with get_db_connection(readonly=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT clave_municipio, nombre FROM municipios WHERE clave_estado = ? ORDER BY clave_municipio ASC;",
            (clave_est,)
        )
        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontraron municipios para el estado con clave {c_estado}."
            )
        return [
            MunicipioSchema(
                clave_municipio=r["clave_municipio"],
                nombre=r["nombre"],
                nombre_sat=normalize_search_text(r["nombre"])
            )
            for r in rows
        ]


@router.get(
    "/estados/{c_estado}/municipios/{c_municipio}",
    response_model=MunicipioDetalleCodigosPostalesSchema,
    summary="Detalle de Municipio con CPs y Asentamientos"
)
def get_municipio_detalle_y_codigos_postales(c_estado: str, c_municipio: str):
    """
    Retorna el detalle completo de un Municipio incluyendo todos sus Códigos Postales y Colonias/Asentamientos.
    """
    clave_est = c_estado.zfill(2)
    clave_mun = c_municipio.zfill(3)
    logger.info(f"Consulta detallada de municipio: Estado {clave_est}, Municipio {clave_mun}")

    with get_db_connection(readonly=True) as conn:
        cursor = conn.cursor()

        # Verificar existencia del municipio
        cursor.execute(
            """SELECT m.nombre as municipio_nombre, e.nombre as estado_nombre
               FROM municipios m
               JOIN estados e ON m.clave_estado = e.clave_estado
               WHERE m.clave_estado = ? AND m.clave_municipio = ?""",
            (clave_est, clave_mun)
        )
        mun_row = cursor.fetchone()
        if not mun_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El municipio {c_municipio} en el estado {c_estado} no fue encontrado."
            )

        # Obtener asentamientos del municipio
        cursor.execute(
            """SELECT id, codigo_postal, nombre, tipo_asentamiento, zona, ciudad, latitud, longitud
               FROM asentamientos
               WHERE clave_estado = ? AND clave_municipio = ?
               ORDER BY codigo_postal ASC, nombre ASC""",
            (clave_est, clave_mun)
        )
        rows = cursor.fetchall()

        asentamientos = [
            AsentamientoSchema(
                id=r["id"],
                nombre=r["nombre"],
                tipo_asentamiento=r["tipo_asentamiento"],
                zona=r["zona"],
                codigo_postal=r["codigo_postal"],
                ciudad=r["ciudad"],
                clave_estado=clave_est,
                clave_municipio=clave_mun,
                latitud=r["latitud"],
                longitud=r["longitud"]
            )
            for r in rows
        ]

        cps_unicos = sorted(list({r["codigo_postal"] for r in rows}))

        return MunicipioDetalleCodigosPostalesSchema(
            clave_estado=clave_est,
            estado_nombre=mun_row["estado_nombre"],
            clave_municipio=clave_mun,
            municipio_nombre=mun_row["municipio_nombre"],
            total_codigos_postales=len(cps_unicos),
            codigos_postales=cps_unicos,
            total_asentamientos=len(asentamientos),
            asentamientos=asentamientos
        )


@router.get(
    "/estados/{c_estado}/pdf",
    summary="Generar Reporte PDF Ejecutivo de Estado",
    description="Genera y descarga un informe ejecutivo en formato PDF con la ficha técnica geográfica completa del Estado."
)
def export_estado_pdf(
    c_estado: str,
    titulo: str = settings.PDF_DEFAULT_TITLE,
    subtitulo: str = settings.PDF_DEFAULT_SUBTITLE,
    logo_url: str = None
):
    """
    Genera un archivo PDF con la ficha técnica y desglose de municipios y asentamientos de una Entidad Federativa.
    Permite personalizar el título, subtítulo e imagen de logotipo (con fallback automático a mapa por defecto).
    """
    import io
    import httpx
    from fastapi.responses import StreamingResponse
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    clave_est = c_estado.zfill(2)

    with get_db_connection(readonly=True) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT nombre FROM estados WHERE clave_estado = ?;", (clave_est,))
        est_row = cursor.fetchone()
        if not est_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El estado con clave {c_estado} no existe."
            )

        estado_nombre = est_row["nombre"]

        cursor.execute(
            "SELECT COUNT(DISTINCT clave_municipio) as total_mun, COUNT(*) as total_asen, COUNT(DISTINCT codigo_postal) as total_cp FROM asentamientos WHERE clave_estado = ?;",
            (clave_est,)
        )
        stats = cursor.fetchone()

        cursor.execute(
            "SELECT clave_municipio, nombre FROM municipios WHERE clave_estado = ? ORDER BY clave_municipio ASC LIMIT 40;",
            (clave_est,)
        )
        mun_rows = cursor.fetchall()

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'CustomSubTitle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )
    normal_style = styles['Normal']

    story = []

    # Cargar Logotipo (URL personalizada o Isotipo Vectorial por defecto)
    logo_element = None
    if logo_url:
        try:
            resp = httpx.get(logo_url, timeout=4.0)
            if resp.status_code == 200:
                img_data = io.BytesIO(resp.content)
                logo_element = Image(img_data, width=45, height=45)
        except Exception:
            logo_element = None

    if not logo_element:
        # Isotipo vectorial ejecutivo por defecto (Pin de Ubicación + Escudo Geográfico)
        from reportlab.graphics.shapes import Drawing, Rect, Circle, Polygon, String, Group
        d = Drawing(48, 48)
        # Fondo redondeado azul oscuro
        d.add(Rect(0, 0, 48, 48, rx=8, ry=8, fillColor=colors.HexColor('#0f172a'), strokeColor=None))
        # Anillos concéntricos de mapa
        d.add(Circle(24, 24, 18, fillColor=None, strokeColor=colors.HexColor('#1e293b'), strokeWidth=1.5))
        d.add(Circle(24, 24, 11, fillColor=None, strokeColor=colors.HexColor('#334155'), strokeWidth=1.5))
        # Marca de mapa verde de México
        d.add(Circle(24, 24, 6, fillColor=colors.HexColor('#10b981'), strokeColor=colors.white, strokeWidth=1.5))
        logo_element = d

    header_data = [
        [logo_element, Paragraph(f"<b>{titulo}</b><br/>{subtitulo}", title_style)]
    ]
    header_table = Table(header_data, colWidths=[58, 482])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10)
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # Ficha Resumen de Estado
    resumen_data = [
        ["Entidad Federativa:", estado_nombre, "Clave Estado:", clave_est],
        ["Total Municipios:", str(stats["total_mun"]), "Códigos Postales:", str(stats["total_cp"])],
        ["Asentamientos Totales:", str(stats["total_asen"]), "Licencia:", "CC BY 4.0 International"]
    ]
    resumen_table = Table(resumen_data, colWidths=[130, 140, 130, 140])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#1e293b')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('PADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0'))
    ]))
    story.append(resumen_table)
    story.append(Spacer(1, 15))

    # Muestra de Municipios
    story.append(Paragraph("<b>Resumen de Municipios / Alcaldías</b>", styles['Heading2']))
    story.append(Spacer(1, 6))

    table_data = [["Clave", "Nombre del Municipio"]]
    for m in mun_rows:
        table_data.append([m["clave_municipio"], m["nombre"]])

    mun_table = Table(table_data, colWidths=[80, 460])
    mun_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f1f5f9')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1'))
    ]))
    story.append(mun_table)
    story.append(Spacer(1, 15))

    # Pie de Página Legal CC BY 4.0
    story.append(Paragraph(
        "<i>Atribución Legal: Esta información proviene del catálogo oficial de SEPOMEX (datos.gob.mx) bajo la licencia Creative Commons Attribution 4.0 International (CC BY 4.0).</i>",
        ParagraphStyle('Legal', fontSize=7.5, textColor=colors.HexColor('#64748b'))
    ))

    doc.build(story)
    pdf_buffer.seek(0)

    filename = f"reporte_estado_{clave_est}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get(
    "/estados/{c_estado}/geojson",
    response_model=GeoJSONFeatureCollectionSchema,
    summary="Exportación de Estado Completo en Estándar GeoJSON"
)
def export_estado_geojson(c_estado: str):
    """
    Retorna la colección completa de capas geográficas (`FeatureCollection`) de todos los asentamientos con coordenadas de un Estado.
    Ideal para importar en software GIS (QGIS, ArcGIS, Mapbox, Google Earth).
    """
    clave_est = c_estado.zfill(2)
    logger.info(f"Exportando GeoJSON completo para Estado clave: {clave_est}")

    with get_db_connection(readonly=True) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT nombre FROM estados WHERE clave_estado = ?;", (clave_est,))
        est_row = cursor.fetchone()
        if not est_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El estado con clave {c_estado} no existe."
            )

        cursor.execute(
            """SELECT a.id, a.codigo_postal, a.nombre, a.tipo_asentamiento, a.zona, a.ciudad, a.latitud, a.longitud, m.nombre as municipio_nombre
               FROM asentamientos a
               JOIN municipios m ON a.clave_estado = m.clave_estado AND a.clave_municipio = m.clave_municipio
               WHERE a.clave_estado = ? AND a.latitud IS NOT NULL AND a.longitud IS NOT NULL
               ORDER BY a.codigo_postal ASC;""",
            (clave_est,)
        )
        rows = cursor.fetchall()

        features = []
        for r in rows:
            features.append(
                GeoJSONFeatureSchema(
                    geometry=GeoJSONGeometrySchema(coordinates=[r["longitud"], r["latitud"]]),
                    properties={
                        "id": r["id"],
                        "codigo_postal": r["codigo_postal"],
                        "nombre": r["nombre"],
                        "nombre_sat": normalize_search_text(r["nombre"]),
                        "tipo_asentamiento": r["tipo_asentamiento"],
                        "zona": r["zona"],
                        "ciudad": r["ciudad"],
                        "estado": est_row["nombre"],
                        "municipio": r["municipio_nombre"]
                    }
                )
            )

        return GeoJSONFeatureCollectionSchema(
            codigo_postal=f"ESTADO-{clave_est}",
            features=features
        )
