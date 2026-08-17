import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Genera o mantiene un Header X-Correlation-ID para trazabilidad de peticiones de auditoría."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", f"req-{uuid.uuid4().hex[:12]}")
        request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
