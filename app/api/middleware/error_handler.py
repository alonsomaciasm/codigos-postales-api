from datetime import datetime, timezone
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.logger import logger

async def global_exception_handler(request: Request, exc: Exception):
    """Manejador global para excepciones no controladas."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.error(f"Error 500 no controlado en {request.url.path}: {exc} [CID: {correlation_id}]")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Ha ocurrido un error interno en el servidor. Por favor intente más tarde.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "correlation_id": correlation_id,
                "path": request.url.path
            }
        }
    )

from slowapi.errors import RateLimitExceeded

async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    """Manejador para exceso de límite de peticiones (429 Too Many Requests)."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.warning(f"Rate limit superado en {request.url.path} por IP {request.client.host if request.client else 'unknown'}")
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Ha superado el límite permitido de peticiones ({exc.detail}). Por favor intente más tarde.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "correlation_id": correlation_id,
                "path": request.url.path
            }
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Manejador estandarizado para excepciones HTTP (404, 403, 401, etc.)."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    code_map = {
        404: "NOT_FOUND",
        400: "BAD_REQUEST",
        429: "TOO_MANY_REQUESTS",
        403: "FORBIDDEN"
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code_map.get(exc.status_code, "HTTP_ERROR"),
                "message": str(exc.detail),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "correlation_id": correlation_id,
                "path": request.url.path
            }
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Manejador para errores de validación de entrada (Pydantic / Regex)."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Parámetros de entrada inválidos.",
                "details": exc.errors(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "correlation_id": correlation_id,
                "path": request.url.path
            }
        }
    )
