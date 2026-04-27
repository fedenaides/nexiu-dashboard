"""
Smoke test que verifica que las credenciales funcionan, SIN escribir nada al Sheet.

Hace 3 chequeos:
  1. Service account puede leer dim_clients del Sheet.
  2. META access token funciona y devuelve insights del último día.
  3. Imprime un sample de filas para que vos validés visualmente.

Útil ANTES de correr `python main.py` por primera vez para descartar errores
de credenciales y de naming de campañas.

Uso:
  python validate.py
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

from etl.meta_ads import fetch_meta_insights
from etl.sheets_writer import open_sheet, read_dim_clients
from etl.utils import setup_logging


def main() -> int:
    load_dotenv()
    log = setup_logging()
    import os

    # ---- 1. Sheet ----
    log.info("=" * 60)
    log.info("TEST 1/2 — Acceso al Google Sheet")
    log.info("=" * 60)
    try:
        sheet = open_sheet(os.environ["SHEET_ID"])
        log.info("✓ Sheet abierto: %r", sheet.title)
        codes = read_dim_clients(sheet)
        log.info("✓ Códigos de cliente activos en dim_clients: %s", codes or "(vacío)")
        if not codes:
            log.warning("dim_clients vacío — el ETL marcará todas las campañas como UNKNOWN")
    except Exception as e:
        log.error("✗ Falló acceso al Sheet: %s", e)
        log.error(
            "Posibles causas: SHEET_ID incorrecto, service account no tiene "
            "permiso de Editor en el sheet, JSON de credenciales malformado."
        )
        return 1

    # ---- 2. META ----
    log.info("")
    log.info("=" * 60)
    log.info("TEST 2/2 — Meta Marketing API")
    log.info("=" * 60)
    try:
        df = fetch_meta_insights(
            access_token=os.environ["META_ACCESS_TOKEN"],
            ad_account_id=os.environ["META_AD_ACCOUNT_ID"],
            lookback_days=2,
            known_client_codes=codes,
        )
        log.info("✓ META devolvió %d filas", len(df))
        if df.empty:
            log.warning("Sin datos en los últimos 2 días — probá con ETL_LOOKBACK_DAYS=14")
        else:
            log.info("Sample (primeras 5 filas):")
            print(df.head(5).to_string(index=False))
            unknown = df[df["cliente_id"] == "UNKNOWN"]
            if not unknown.empty:
                log.warning(
                    "%d filas tienen cliente_id=UNKNOWN. Nombres de campaña afectados:",
                    len(unknown),
                )
                for n in unknown["campaign_name"].unique()[:10]:
                    log.warning("  - %s", n)
                log.warning(
                    "Solución: o renombrar las campañas para que incluyan un "
                    "código de dim_clients, o agregar el código a dim_clients."
                )
    except Exception as e:
        log.error("✗ Falló META: %s", e)
        log.error(
            "Posibles causas: META_ACCESS_TOKEN expirado o inválido, "
            "META_AD_ACCOUNT_ID con formato incorrecto (debe ser 'act_NUMERO')."
        )
        return 1

    log.info("")
    log.info("=" * 60)
    log.info("✓ Todo OK. Ya podés correr `python main.py` para escribir al Sheet.")
    log.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
