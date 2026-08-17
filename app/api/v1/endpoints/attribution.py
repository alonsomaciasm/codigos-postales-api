from fastapi import APIRouter
from app.core.config import settings
from app.models.schema import AttributionSchema

router = APIRouter()

@router.get("/attribution", response_model=AttributionSchema, summary="Cláusula de Atribución Legal (CC BY 4.0)")
def get_attribution():
    """
    Retorna los créditos y atribución legal de la fuente de datos oficial (SEPOMEX / datos.gob.mx)
    bajo la licencia Creative Commons Attribution 4.0 International.
    """
    return AttributionSchema(
        mensaje=settings.ATTRIBUTION_TEXT,
        licencia="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        url_licencia=settings.ATTRIBUTION_URL,
        fuente_oficial=settings.SOURCE_URL
    )
