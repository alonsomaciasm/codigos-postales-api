import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Metadata del Proyecto
    PROJECT_NAME: str = "API Códigos Postales de México"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Servidor y Host
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 2
    
    # Base de Datos
    DB_PATH: str = "sepomex.db"
    DB_BUSY_TIMEOUT_MS: int = 5000
    DB_CACHE_SIZE_KB: int = -64000  # 64MB Cache
    
    # Ingesta de SEPOMEX y datos.gob.mx
    DATOS_GOB_MX_DATASET_URL: str = "https://datos.gob.mx/busca/dataset/codigo-postal-mexicano"
    SEPOMEX_EXPORT_URL: str = "https://www.correosdemexico.gob.mx/SSLServicios/ConsultaCP/CodigoPostal_Exportar.aspx"
    INGEST_MAX_RETRIES: int = 3
    INGEST_RETRY_BACKOFF_SEC: float = 3.0
    
    # Ciberseguridad, Autenticación (API Key / JWT)
    REQUIRE_AUTH: bool = False  # True para requerir API Key o JWT Bearer Token
    API_KEYS: str = "key-dev-12345,key-prod-67890"  # Lista de API Keys válidas separadas por coma
    JWT_SECRET_KEY: str = "super-secret-jwt-key-sepomex-api"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24  # Duración del token JWT en horas
    
    # Configuración CORS para Producción
    # Ej en producción: "https://midominio.com,https://app.midominio.com" o "*"
    CORS_ORIGINS: str = "*"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "*"      # Ej en prod: "GET,POST,OPTIONS"
    CORS_ALLOW_HEADERS: str = "*"      # Ej en prod: "Content-Type,Authorization,X-API-Key,X-Correlation-ID"
    
    # Performance, Caché LRU & Compresión
    CACHE_LRU_MAXSIZE: int = 1024    # Máximo número de CPs almacenados en caché LRU en RAM
    GZIP_MIN_SIZE: int = 1000        # Tamaño mínimo en bytes para comprimir respuestas HTTP con GZip
    MAX_BODY_BYTES_LIMIT: int = 1048576  # Límite máximo global del cuerpo de la petición HTTP (1 MB)
    
    # PDF & Exportación
    PDF_DEFAULT_TITLE: str = "Reporte Geográfico Ejecutivo - SEPOMEX"
    PDF_DEFAULT_SUBTITLE: str = "Ficha Técnica Oficial de Entidad Federativa"
    BATCH_MAX_ITEMS: int = 100

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 120
    
    # Logging & Auditoría
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_ROTATION: str = "00:00"      # Rotación diaria a las 00:00
    LOG_RETENTION: str = "30 days"  # Retención por 30 días
    
    # Atribución Legal CC BY 4.0
    ATTRIBUTION_TEXT: str = (
        "Esta API utiliza y procesa información geográfica y de códigos postales "
        "proveniente del catálogo oficial publicado por el Servicio Postal Mexicano (SEPOMEX) "
        "a través de datos.gob.mx bajo la licencia Creative Commons Attribution 4.0 International."
    )
    ATTRIBUTION_URL: str = "https://creativecommons.org/licenses/by/4.0/"
    SOURCE_URL: str = "https://datos.gob.mx"

    @property
    def api_keys_set(self) -> set:
        """Retorna un conjunto de API Keys válidas para autenticación rápida."""
        return {k.strip() for k in self.API_KEYS.split(",") if k.strip()}

    @property
    def cors_origins_list(self) -> List[str]:
        """Convierte la cadena de CORS_ORIGINS en una lista de cadenas válida para FastAPI."""
        v = self.CORS_ORIGINS.strip()
        if v.startswith("[") and v.endswith("]"):
            import json
            try:
                return json.loads(v)
            except Exception:
                pass
        return [i.strip() for i in v.split(",") if i.strip()]

    @property
    def cors_allow_methods_list(self) -> List[str]:
        """Convierte la cadena de CORS_ALLOW_METHODS en una lista para FastAPI."""
        v = self.CORS_ALLOW_METHODS.strip()
        if v == "*":
            return ["*"]
        return [i.strip() for i in v.split(",") if i.strip()]

    @property
    def cors_allow_headers_list(self) -> List[str]:
        """Convierte la cadena de CORS_ALLOW_HEADERS en una lista para FastAPI."""
        v = self.CORS_ALLOW_HEADERS.strip()
        if v == "*":
            return ["*"]
        return [i.strip() for i in v.split(",") if i.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
