"""
Punto de entrada del ETL.

Flujo:
  1. Cargar variables de entorno (.env en local; secrets en GitHub Actions)
  2. Abrir el Google Sheet warehouse
  3. Leer dim_clients para conocer los códigos de cliente válidos
  4. [META] Descargar insights de los últimos N días y reemplazar en ads_meta
  5. [Google Ads] Si hay credenciales, hacer lo mismo. Sino, skip.
  6. Loguear el resultado a etl_logs
  7. (Por venir) Reconstruir FACT_CONSOLIDADO
"""

from __future__ import annotations

import logging
import os
import sys
import time
import traceback

from dotenv import load_dotenv

from etl.meta_ads import fetch_meta_insights
from etl.sheets_writer import (
    append_log,
    open_sheet,
    read_dim_clients,
    replace_last_n_days,
)
from etl.utils import setup_logging


def get_env(name: str, *, required: bool = True, default: str | None = None) -> str:
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"Variable de entorno {name} no está definida")
    return val or ""


def run_meta(sheet, lookback_days: int, client_codes: list[str]) -> int:
    """Descargar META y reemplazar en ads_meta. Devuelve filas insertadas."""
    token = get_env("META_ACCESS_TOKEN")
    account = get_env("META_AD_ACCOUNT_ID")
    df = fetch_meta_insights(
        access_token=token,
        ad_account_id=account,
        lookback_days=lookback_days,
        known_client_codes=client_codes,
    )
    if df.empty:
        logging.getLogger("nexiu_etl").warning("META no devolvió filas")
        return 0
    _, inserted = replace_last_n_days(
        sheet=sheet,
        tab_name="ads_meta",
        df=df,
        date_col="fecha",
        lookback_days=lookback_days,
    )
    return inserted


def run_google_ads(sheet, lookback_days: int, client_codes: list[str]) -> int:
    """Stub — se activa cuando aprueben Basic Access. Por ahora devuelve 0."""
    if not os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"):
        logging.getLogger("nexiu_etl").info(
            "Google Ads desactivado (sin GOOGLE_ADS_DEVELOPER_TOKEN). Skip."
        )
        return 0
    # TODO Fase 2D: importar etl.google_ads y correr fetch + replace_last_n_days
    logging.getLogger("nexiu_etl").info(
        "Google Ads developer token presente pero módulo aún no implementado. Skip."
    )
    return 0


def main() -> int:
    load_dotenv()
    log = setup_logging()
    started = time.monotonic()
    trigger = os.environ.get("ETL_TRIGGER", "manual")
    lookback = int(os.environ.get("ETL_LOOKBACK_DAYS", "7"))

    rows_meta = 0
    rows_google = 0
    error_message = ""

    try:
        sheet_id = get_env("SHEET_ID")
        sheet = open_sheet(sheet_id)
        log.info("Sheet abierto: %s", sheet.title)

        client_codes = read_dim_clients(sheet)
        if not client_codes:
            log.warning(
                "dim_clients no devolvió códigos activos; las campañas se "
                "marcarán como UNKNOWN."
            )

        rows_meta = run_meta(sheet, lookback, client_codes)
        rows_google = run_google_ads(sheet, lookback, client_codes)

        duration = time.monotonic() - started
        append_log(
            sheet,
            trigger=trigger,
            status="success",
            rows_meta=rows_meta,
            rows_google=rows_google,
            duration_sec=duration,
        )
        log.info(
            "ETL OK en %.1fs — META: %d filas, Google: %d filas",
            duration, rows_meta, rows_google,
        )
        return 0

    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        log.error("ETL falló: %s\n%s", error_message, traceback.format_exc())
        try:
            sheet = open_sheet(get_env("SHEET_ID"))
            append_log(
                sheet,
                trigger=trigger,
                status="error",
                rows_meta=rows_meta,
                rows_google=rows_google,
                duration_sec=time.monotonic() - started,
                error_message=error_message,
            )
        except Exception as log_exc:
            log.error("No pude escribir el log de error: %s", log_exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
