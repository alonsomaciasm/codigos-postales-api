import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader

from app.core.config import settings
from app.core.logger import logger

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Genera un Token JWT firmado."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=settings.JWT_EXPIRE_HOURS))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> Dict[str, Any]:
    """Verifica y decodifica un Token JWT."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token JWT ha expirado."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT inválido."
        )


async def get_current_user_or_api_key(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Dict[str, Any]:
    """
    Dependencia de seguridad que permite la autenticación mediante:
    1. Header X-API-Key: key-dev-12345
    2. Header Authorization: Bearer <jwt_token>
    Si REQUIRE_AUTH está en False en .env, permite el acceso libre (Modo API Pública).
    """
    if not settings.REQUIRE_AUTH:
        return {"auth": "public", "user": "anonymous"}

    # 1. Validar por X-API-Key Header
    if api_key:
        if api_key in settings.api_keys_set:
            return {"auth": "api_key", "client_id": api_key[:10]}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-API-Key proporcionada es inválida o ha sido revocada."
            )

    # 2. Validar por Authorization: Bearer JWT Header
    if credentials and credentials.credentials:
        payload = verify_token(credentials.credentials)
        return {"auth": "jwt", "payload": payload}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticación requerida. Proporcione un header 'X-API-Key' o 'Authorization: Bearer <token>'."
    )
