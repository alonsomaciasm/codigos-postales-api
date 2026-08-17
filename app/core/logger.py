import os
import sys
import json
from loguru import logger
from app.core.config import settings

# Crear directorio de logs si no existe
os.makedirs(settings.LOG_DIR, exist_ok=True)

# Formateador JSON personalizado para auditoría empresarial
def json_formatter(record):
    log_record = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
        "extra": record["extra"]
    }
    return json.dumps(log_record) + "\n"

# Eliminar handlers por defecto
logger.remove()

# Handler para Consola (StdOut)
logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:8}</level> | <cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True
)

# Handler para Archivos de Log con Rotación Diaria en formato JSON
try:
    logger.add(
        os.path.join(settings.LOG_DIR, "audit_{time:YYYY-MM-DD}.log"),
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
        serialize=True,
        enqueue=True
    )
except (PermissionError, OSError) as e:
    logger.warning(f"No se pudo inicializar la escritura de archivo de logs en {settings.LOG_DIR}: {e}. Operando únicamente con stdout.")

__all__ = ["logger"]
