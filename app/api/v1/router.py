from fastapi import APIRouter, Depends
from app.core.auth import get_current_user_or_api_key
from app.api.v1.endpoints import codigos_postales, estados, attribution, auth, logs

api_router = APIRouter()

# Endpoint de autenticación y logs de observabilidad
api_router.include_router(auth.router, tags=["Autenticación & JWT"])
api_router.include_router(logs.router, tags=["Monitoreo & Healthcheck"])

# Endpoints protegidos con Auth híbrida (API Key o JWT si REQUIRE_AUTH=True)
api_router.include_router(
    codigos_postales.router,
    tags=["Códigos Postales & Asentamientos"],
    dependencies=[Depends(get_current_user_or_api_key)]
)
api_router.include_router(
    estados.router,
    tags=["Estados & Municipios"],
    dependencies=[Depends(get_current_user_or_api_key)]
)
api_router.include_router(
    attribution.router,
    tags=["Atribución Legal & Licencia"]
)
