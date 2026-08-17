from typing import List, Optional, Dict, Union, Any
from pydantic import BaseModel, Field


class AsentamientoSchema(BaseModel):
    id: int
    nombre: str = Field(..., description="Nombre oficial de la colonia o asentamiento")
    nombre_sat: Optional[str] = Field(None, description="Nombre normalizado sin acentos en mayúsculas compatible con SAT/CFDI 4.0")
    tipo_asentamiento: str = Field(..., description="Tipo (ej. Colonia, Barrio, Ejido, Fraccionamiento)")
    zona: str = Field(..., description="Urbano o Rural")
    codigo_postal: str = Field(..., description="Código postal de 5 dígitos")
    ciudad: Optional[str] = Field(None, description="Nombre de la ciudad si aplica")
    clave_estado: Optional[str] = Field(None, description="Clave de 2 dígitos del estado")
    clave_municipio: Optional[str] = Field(None, description="Clave del municipio")
    latitud: Optional[float] = Field(None, description="Latitud en grados decimales")
    longitud: Optional[float] = Field(None, description="Longitud en grados decimales")


class AsentamientoCercanoSchema(AsentamientoSchema):
    distancia_km: float = Field(..., description="Distancia ortodrómica estimada en kilómetros (Haversine)")


class PaginatedAsentamientosSchema(BaseModel):
    total_records: int = Field(..., description="Total de registros encontrados")
    total_pages: int = Field(..., description="Total de páginas disponibles")
    current_page: int = Field(..., description="Página actual")
    limit: int = Field(..., description="Registros por página")
    data: List[AsentamientoSchema] = Field(..., description="Lista de asentamientos de la página actual")


class MunicipioSchema(BaseModel):
    clave_municipio: str = Field(..., description="Clave del municipio dentro del estado (c_mnpio)")
    nombre: str = Field(..., description="Nombre del municipio o alcaldía")
    nombre_sat: Optional[str] = Field(None, description="Nombre normalizado compatible con SAT/CFDI 4.0")


class EstadoSchema(BaseModel):
    clave_estado: str = Field(..., description="Clave del estado (c_estado, 2 dígitos)")
    nombre: str = Field(..., description="Nombre del estado o entidad federativa")
    nombre_sat: Optional[str] = Field(None, description="Nombre normalizado compatible con SAT/CFDI 4.0")


class ValidacionCoincidenciaSchema(BaseModel):
    """Esquema de resultado para validación cruzada opcional de formulario (CP, Colonia, Estado)."""
    es_valido: bool = Field(..., description="Indica si el CP existe en el catálogo SEPOMEX")
    match_colonia: Optional[bool] = Field(None, description="Indica si la colonia enviada pertenece a este CP")
    match_estado: Optional[bool] = Field(None, description="Indica si el estado enviado coincide con este CP")
    match_municipio: Optional[bool] = Field(None, description="Indica si el municipio enviado coincide con este CP")
    coincidencia_exacta: bool = Field(..., description="Verdadero si todos los parámetros enviados coinciden al 100%")
    mensaje: str = Field(..., description="Detalle o diagnóstico explicativo de la validación")


class CodigoPostalDetalleSchema(BaseModel):
    codigo_postal: str = Field(..., description="Código postal de 5 dígitos")
    estado: EstadoSchema
    municipio: MunicipioSchema
    ciudad: Optional[str] = Field(None, description="Nombre de la ciudad si aplica")
    asentamientos: List[AsentamientoSchema]
    validacion: Optional[ValidacionCoincidenciaSchema] = Field(None, description="Resultado de validación cruzada si se enviaron parámetros de coincidencia")


class AttributionSchema(BaseModel):
    mensaje: str
    licencia: str
    url_licencia: str
    fuente_oficial: str


class AutocompleteItemSchema(BaseModel):
    codigo_postal: str = Field(..., description="Código postal de 5 dígitos")
    estado_nombre: str = Field(..., description="Nombre del estado")
    municipio_nombre: str = Field(..., description="Nombre del municipio o alcaldía")
    total_asentamientos: int = Field(..., description="Cantidad de asentamientos o colonias asociadas")


class MunicipioDetalleCodigosPostalesSchema(BaseModel):
    clave_estado: str = Field(..., description="Clave de 2 dígitos del estado")
    estado_nombre: str = Field(..., description="Nombre del estado")
    clave_municipio: str = Field(..., description="Clave de 3 dígitos del municipio")
    municipio_nombre: str = Field(..., description="Nombre del municipio o alcaldía")
    total_codigos_postales: int = Field(..., description="Total de CPs distintos en el municipio")
    codigos_postales: List[str] = Field(..., description="Lista de códigos postales pertenecientes al municipio")
    total_asentamientos: int = Field(..., description="Total de colonias/asentamientos registrados en el municipio")
    asentamientos: List[AsentamientoSchema] = Field(..., description="Lista de asentamientos del municipio")


class CatalogStatsSchema(BaseModel):
    total_codigos_postales: int = Field(..., description="Total de códigos postales únicos")
    total_asentamientos: int = Field(..., description="Total de asentamientos / colonias registradas")
    total_estados: int = Field(..., description="Total de estados o entidades federativas (32)")
    total_municipios: int = Field(..., description="Total de municipios o alcaldías registradas")
    tipos_asentamiento_conteo: Dict[str, int] = Field(..., description="Desglose de conteo por tipo de asentamiento (Colonia, Barrio, etc.)")
    zonas_conteo: Dict[str, int] = Field(..., description="Desglose por zona (Urbano vs Rural)")


class GeoJSONGeometrySchema(BaseModel):
    type: str = Field("Point", description="Tipo de geometría GeoJSON")
    coordinates: List[float] = Field(..., description="[Longitud, Latitud]")


class GeoJSONFeatureSchema(BaseModel):
    type: str = Field("Feature", description="Objeto Feature de GeoJSON")
    geometry: GeoJSONGeometrySchema
    properties: Dict[str, Optional[Union[str, int, float]]] = Field(..., description="Propiedades y atributos del punto")


class GeoJSONFeatureCollectionSchema(BaseModel):
    type: str = Field("FeatureCollection", description="Colección de características GeoJSON")
    codigo_postal: str = Field(..., description="Código Postal")
    features: List[GeoJSONFeatureSchema] = Field(..., description="Lista de características geográficas GeoJSON")


class LogEntrySchema(BaseModel):
    """Esquema para una entrada individual de auditoría en los logs."""
    timestamp: str = Field(..., description="Fecha y hora de emisión del log en ISO 8601")
    level: str = Field(..., description="Nivel del log (INFO, WARNING, ERROR)")
    message: str = Field(..., description="Mensaje del registro de auditoría")
    module: Optional[str] = Field(None, description="Módulo de origen del log")

class LogResponseSchema(BaseModel):
    """Esquema de respuesta para la lista de registros de logs de auditoría."""
    total_entries: int = Field(..., description="Cantidad total de registros leídos")
    limit: int = Field(..., description="Límite máximo solicitado")
    logs: List[LogEntrySchema] = Field(..., description="Lista de registros de auditoría")


class BatchValidateItemSchema(BaseModel):
    """Esquema de entrada para un ítem individual en la validación en lote."""
    id_externo: Optional[str] = Field(None, description="Identificador único del registro de cliente (ej. USR-001)")
    codigo_postal: str = Field(..., pattern="^[0-9]{5}$", description="Código Postal de 5 dígitos")
    colonia: Optional[str] = Field(None, description="Nombre de colonia a validar")
    estado: Optional[str] = Field(None, description="Nombre o clave de estado a validar")
    municipio: Optional[str] = Field(None, description="Nombre o clave de municipio a validar")


class BatchValidateResultSchema(BaseModel):
    """Esquema de respuesta para el resultado de validación en lote."""
    id_externo: Optional[str] = Field(None, description="Identificador externo de referencia")
    codigo_postal: str = Field(..., description="Código Postal de 5 dígitos consultado")
    existe_cp: bool = Field(..., description="Indica si el Código Postal existe en SEPOMEX")
    validacion: Optional[ValidacionCoincidenciaSchema] = Field(None, description="Diagnóstico de coincidencia de formulario")
    oficial: Optional[Dict[str, Any]] = Field(None, description="Datos oficiales del CP (Estado SAT, Municipio, Colonias)")

