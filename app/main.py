import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logger import logger
from app.core.limiter import limiter
from app.core.database import init_db_wal, get_db_connection
from app.api.v1.router import api_router
from app.api.middleware.correlation_id import CorrelationIDMiddleware
from app.api.middleware.audit_logging import AuditLoggingMiddleware
from app.api.middleware.rate_limit import SecurityHeadersMiddleware
from app.api.middleware.error_handler import (
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    rate_limit_exception_handler,
)

async def _schedule_monthly_update_check():
    """Tarea asíncrona en segundo plano que verifica actualizaciones del catálogo SEPOMEX cada 30 días."""
    from scripts.check_updates import run_update_check
    while True:
        try:
            # Esperar 30 días entre comprobaciones (30 días * 24 horas * 3600 segundos)
            await asyncio.sleep(2592000)
            logger.info("Ejecutando verificación automática mensual del catálogo SEPOMEX en segundo plano...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, run_update_check)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error en tarea en segundo plano de verificación SEPOMEX: {e}")
            await asyncio.sleep(86400) # Reintentar en 24h si ocurre una falla

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando servicio de API Códigos Postales de México...")
    init_db_wal()
    # Iniciar planificador asíncrono en segundo plano (0% impacto en latencia HTTP)
    update_task = asyncio.create_task(_schedule_monthly_update_check())
    yield
    update_task.cancel()
    logger.info("Deteniendo servicio de API Códigos Postales de México...")

# Inicializar aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=f"{settings.PROJECT_NAME}\n\n**Aviso Legal y Atribución:**\n{settings.ATTRIBUTION_TEXT}",
    default_response_class=JSONResponse,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Integración Prometheus Metrics Monitoreo
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", tags=["Monitoreo & Healthcheck"])
    logger.info("Prometheus Instrumentator configurado en /metrics.")
except ImportError:
    logger.warning("prometheus-fastapi-instrumentator no instalado. Omitiendo exposición de /metrics.")

# Asociar Limiter a la aplicación FastAPI
app.state.limiter = limiter

from app.api.middleware.body_limit import RequestBodyLimitMiddleware

# Registrar Middlewares Empresariales (el orden de ejecución es inverso al registro)
app.add_middleware(GZipMiddleware, minimum_size=settings.GZIP_MIN_SIZE)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestBodyLimitMiddleware)

@app.middleware("http")
async def add_cache_control_header(request, call_next):
    response = await call_next(request)
    if request.method == "GET" and response.status_code == 200:
        path = request.url.path
        if path.startswith("/api/v1/") and not path.endswith("/health"):
            response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=3600"
    return response

app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.cors_allow_methods_list,
    allow_headers=settings.cors_allow_headers_list,
)

# Registrar Manejadores Globales de Excepciones (RFC 7807)
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)

from fastapi.staticfiles import StaticFiles

# Montar archivos estáticos para widgets y utilidades de cliente
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Incluir Rutas V1
app.include_router(api_router, prefix=settings.API_V1_STR)

from fastapi.responses import JSONResponse, FileResponse

@app.get("/dashboard", tags=["Información General"], response_class=FileResponse)
def get_dashboard():
    """Sirve la interfaz gráfica ejecutiva de observabilidad y métricas del sistema."""
    return FileResponse("app/templates/dashboard.html")

@app.get("/", tags=["Información General"])
def root():
    """Endpoint raíz con información de la API y atribución legal CC BY 4.0."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "attribution": {
            "text": settings.ATTRIBUTION_TEXT,
            "license": settings.ATTRIBUTION_URL,
            "source": settings.SOURCE_URL
        }
    }

@app.get("/health", tags=["Monitoreo & Healthcheck"])
def health_check():
    """
    Healthcheck activo con verificación en tiempo real de la base de datos (SELECT 1).
    Utilizado por Docker / Kubernetes para determinar la salud y disponibilidad del servicio.
    """
    try:
        with get_db_connection(readonly=True) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            db_ok = cursor.fetchone()[0] == 1

        if db_ok:
            return {
                "status": "ok",
                "service": settings.PROJECT_NAME,
                "database": "connected",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        logger.error(f"Fallo de Healthcheck en verificación de base de datos: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "service": settings.PROJECT_NAME,
                "database": "disconnected",
                "detail": "Error de conexión a la base de datos",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
