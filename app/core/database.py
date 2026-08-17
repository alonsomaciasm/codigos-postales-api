import sqlite3
import os
from contextlib import contextmanager
from typing import Generator
from app.core.config import settings
from app.core.logger import logger


def init_db_wal():
    """Asegura que la base de datos utilice SQLite WAL (Write-Ahead Logging) para lecturas concurrentes sin deadlocks."""
    if os.path.exists(settings.DB_PATH):
        try:
            conn = sqlite3.connect(settings.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA temp_store=MEMORY;")
            cursor.execute(f"PRAGMA cache_size={settings.DB_CACHE_SIZE_KB};")
            conn.commit()
            conn.close()
            logger.info("Base de datos SQLite verificada en modo WAL con cache optimizado.")
        except sqlite3.OperationalError as oe:
            if "readonly" in str(oe).lower():
                logger.warning("La base de datos SQLite se encuentra en modo Solo Lectura (Read-Only). Omitiendo configuración de pragma WAL.")
            else:
                logger.error(f"Error operacional al inicializar modo WAL en la BD: {oe}")
        except Exception as e:
            logger.error(f"Error al inicializar modo WAL en la BD: {e}")


@contextmanager
def get_db_connection(readonly: bool = True) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager para obtener conexiones a SQLite.
    Por defecto abre las conexiones en modo lectura pura (URI readonly=1) con busy_timeout para prevenir bloqueos.
    """
    db_uri = f"file:{settings.DB_PATH}?mode=ro" if readonly else settings.DB_PATH
    conn = sqlite3.connect(db_uri, uri=readonly, timeout=10.0)
    conn.row_factory = sqlite3.Row  # Retorna filas como diccionarios
    
    # Registrar función geográfica Haversine para consultas nativas en SQL
    from app.core.geo import haversine_distance
    conn.create_function("haversine", 4, haversine_distance)
    
    # Previene deadlocks esperando hasta DB_BUSY_TIMEOUT_MS si hay un bloqueo temporal de escritura
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA busy_timeout={settings.DB_BUSY_TIMEOUT_MS};")
    
    try:
        yield conn
    finally:
        conn.close()
