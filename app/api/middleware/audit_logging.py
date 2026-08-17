import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.logger import logger

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Registra entradas de auditoría estructuradas para cada petición HTTP."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        
        response = await call_next(request)
        
        process_time_ms = round((time.time() - start_time) * 1000, 2)
        
        # Log estructurado de auditoría
        logger.info(
            f"HTTP {request.method} {request.url.path} - Status: {response.status_code} - "
            f"Latency: {process_time_ms}ms - IP: {client_ip} - CID: {correlation_id}"
        )
        
        response.headers["X-Response-Time-MS"] = str(process_time_ms)
        return response
