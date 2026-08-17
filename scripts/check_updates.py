#!/usr/bin/env python3
"""
Script Utilitario de Verificación de Actualizaciones SEPOMEX (Check Updates)
=============================================================================
Práctica recomendada empresarial:
- Verifica por Checksum / Last-Modified / ETag si el archivo remoto en datos.gob.mx ha cambiado.
- Si detecta cambios, descarga la nueva versión, ejecuta la ingesta en una BD temporal y realiza un reemplazo atómico.
- Si no hay cambios, termina limpiamente con código 0 sin alterar nada.

¿Quién lo ejecuta?
- En Linux / Servidores: Un cron job del sistema ejecutándose 1 vez al mes (ej. el día 1 de cada mes a las 03:00 AM).
- En Docker / K8s: Un CronJob independiente o script de mantenimiento.

Comando de ejecución:
    python3 scripts/check_updates.py [--force]
"""

import os
import sys
import json
import argparse
import httpx
from pathlib import Path

# Agregar directorio raíz del proyecto al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from app.core.logger import logger
from scripts.ingest_sepomex import download_with_retry, parse_and_ingest_atomic

STATE_FILE = ROOT_DIR / "logs" / "sepomex_update_state.json"
REMOTE_URL = settings.SEPOMEX_EXPORT_URL


def get_remote_metadata() -> dict:
    """Realiza una petición HEAD / GET parcial para obtener ETag, Last-Modified o MD5."""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "*/*"
    }
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.head(REMOTE_URL, headers=headers)
            if resp.status_code != 200:
                resp = client.get(REMOTE_URL, headers={"Range": "bytes=0-1024", **headers})
            
            last_modified = resp.headers.get("Last-Modified", "")
            etag = resp.headers.get("ETag", "")
            content_length = resp.headers.get("Content-Length", "")
            
            return {
                "url": REMOTE_URL,
                "last_modified": last_modified,
                "etag": etag,
                "content_length": content_length
            }
    except Exception as e:
        logger.warning(f"No se pudo consultar metadata remota en {REMOTE_URL}: {e}")
        return {}


def load_local_state() -> dict:
    """Carga el estado de la última actualización exitosa."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_local_state(state: dict):
    """Guarda el estado actualizado."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def run_update_check(force: bool = False) -> bool:
    """Ejecuta la verificación de actualización del catálogo SEPOMEX."""
    logger.info("Verificando si existen actualizaciones del catálogo oficial de SEPOMEX...")

    remote_meta = get_remote_metadata()
    local_state = load_local_state()

    has_changes = False
    if force:
        logger.info("Forzando actualización de catálogo...")
        has_changes = True
    elif not local_state:
        logger.info("No se encontró estado previo de actualización. Guardando metadata inicial...")
        save_local_state({
            "last_check": str(Path(__file__).stat().st_mtime),
            "etag": remote_meta.get("etag", ""),
            "last_modified": remote_meta.get("last_modified", "")
        })
        return False
    else:
        remote_etag = remote_meta.get("etag")
        local_etag = local_state.get("etag")
        remote_lm = remote_meta.get("last_modified")
        local_lm = local_state.get("last_modified")

        if remote_etag and local_etag and remote_etag != local_etag:
            logger.info(f"ETag remoto cambió ({local_etag} -> {remote_etag}). Novedad detectada.")
            has_changes = True
        elif remote_lm and local_lm and remote_lm != local_lm:
            logger.info(f"Fecha Last-Modified cambió ({local_lm} -> {remote_lm}). Novedad detectada.")
            has_changes = True
        else:
            logger.info("El catálogo oficial remoto de SEPOMEX no presenta cambios.")

    if not has_changes:
        return False

    try:
        txt_file = download_with_retry(str(ROOT_DIR / "CPdescarga.txt"))
        target_db = str(ROOT_DIR / "sepomex.db")

        parse_and_ingest_atomic(txt_file, target_db)

        save_local_state({
            "last_check": str(Path(__file__).stat().st_mtime),
            "etag": remote_meta.get("etag", ""),
            "last_modified": remote_meta.get("last_modified", "")
        })
        logger.info("Verificación y actualización del catálogo finalizadas exitosamente.")
        return True

    except Exception as e:
        logger.error(f"Error procesando la actualización automática: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Verificador de actualizaciones del catálogo SEPOMEX")
    parser.add_argument("--force", action="store_true", help="Forzar la actualización aunque no se detecten cambios")
    args = parser.parse_args()

    success = run_update_check(force=args.force)
    sys.exit(0 if success or not args.force else 1)


if __name__ == "__main__":
    main()
