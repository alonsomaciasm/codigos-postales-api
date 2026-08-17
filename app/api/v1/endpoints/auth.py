from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from app.core.auth import create_access_token

router = APIRouter()

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_hours: int = settings.JWT_EXPIRE_HOURS

@router.post("/auth/token", response_model=TokenResponse, summary="Genera un Token JWT con X-API-Key")
def generate_jwt_token(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """
    Genera un Token JWT de acceso proporcionando una X-API-Key válida.
    """
    if not x_api_key or x_api_key not in settings.api_keys_set:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key no proporcionada o inválida."
        )
    
    token = create_access_token(data={"sub": x_api_key[:10], "role": "api_client"})
    return TokenResponse(access_token=token, expires_in_hours=settings.JWT_EXPIRE_HOURS)
