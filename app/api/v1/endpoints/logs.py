import os
import json
import glob
from typing import Optional
from fastapi import APIRouter, Query, status
from app.core.config import settings
from app.models.schema import LogResponseSchema, LogEntrySchema

router = APIRouter()

@router.get(
    "/logs",
    response_model=LogResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Obtener Registros de Auditoría y Logs en Tiempo Real",
    description="Lee y parsea las últimas líneas del archivo de logs de auditoría diario."
)
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200, description="Cantidad de registros a obtener"),
    level: Optional[str] = Query(None, description="Filtrar por nivel (INFO, WARNING, ERROR)")
):
    """
    Retorna los registros de auditoría más recientes ordenados cronológicamente.
    """
    log_files = sorted(glob.glob(os.path.join(settings.LOG_DIR, "audit_*.log")), reverse=True)
    logs_entries = []

    if log_files:
        latest_file = log_files[0]
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Tomar las últimas líneas según el límite
                for line in reversed(lines):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        rec = data.get("record", {})
                        log_level = rec.get("level", {}).get("name", "INFO")
                        
                        if level and log_level.upper() != level.upper():
                            continue
                            
                        entry = LogEntrySchema(
                            timestamp=rec.get("time", {}).get("repr", ""),
                            level=log_level,
                            message=rec.get("message", data.get("text", "").strip()),
                            module=rec.get("module", "system")
                        )
                        logs_entries.append(entry)
                        if len(logs_entries) >= limit:
                            break
                    except Exception:
                        # Si es una línea de texto llana
                        logs_entries.append(LogEntrySchema(
                            timestamp="",
                            level="INFO",
                            message=line,
                            module="system"
                        ))
                        if len(logs_entries) >= limit:
                            break
        except Exception as e:
            logs_entries.append(LogEntrySchema(
                timestamp="",
                level="ERROR",
                message=f"Error leyendo archivo de logs: {e}",
                module="logger"
            ))

    # Invertir para retornar en orden cronológico (del más antiguo al más reciente dentro del set)
    logs_entries.reverse()

    return LogResponseSchema(
        total_entries=len(logs_entries),
        limit=limit,
        logs=logs_entries
    )
