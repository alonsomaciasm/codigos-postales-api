from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

# Limiter global con clave por IP remota o API Key
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"]
)
