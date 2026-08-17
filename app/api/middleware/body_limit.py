from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_413_REQUEST_ENTITY_TOO_LARGE
from app.core.config import settings
from app.core.logger import logger

class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware de ciberseguridad que restringe el tamaño máximo del cuerpo de la petición (Payload Size Limit)
    para prevenir ataques de agotamiento de memoria (RAM Exhaustion DoS).
    """
    def __init__(self, app, max_bytes: int = settings.MAX_BODY_BYTES_LIMIT):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_bytes:
                    logger.warning(
                        f"Petición rechazada por exceso de tamaño de Payload: {length} bytes (Máx: {self.max_bytes} bytes). IP: {request.client.host}"
                    )
                    return JSONResponse(
                        status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"El cuerpo de la petición excede el tamaño máximo permitido de {self.max_bytes} bytes ({self.max_bytes // 1024 // 1024} MB).",
                                "path": request.url.path
                            }
                        }
                    )
            except ValueError:
                pass

        return await call_next(request)
