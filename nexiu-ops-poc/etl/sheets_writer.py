"""
Lectura y escritura del Google Sheet 'Nexiu Ops Warehouse'.

Estrategia de escritura: 'replace last N days'. Antes de insertar, borra todas
las filas cuyo `fecha` esté en el rango (today - lookback_days, today). Esto
evita duplicados y permite que correcciones retroactivas de Meta/Google se
reflejen.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
from typing import Iterable

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

logger = logging.getLogger("nexiu_etl.sheets")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _build_credentials() -> Credentials:
    """
    Construir credenciales de service account desde:
    - GOOGLE_SERVICE_ACCOUNT_JSON: contenido completo del JSON como string (prod)
    - SERVICE_ACCOUNT_JSON_PATH: ruta a archivo local (dev)
    """
    env_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if env_json:
        info = json.loads(env_json)
        return Credentials.from_service_account_info(info, scopes=SCOPES)

    path = os.environ.get("SERVICE_ACCOUNT_JSON_PATH")
    if path and os.path.exists(path):
        return Credentials.from_service_account_file(path, scopes=SCOPES)

    raise RuntimeError(
        "No encontré credenciales del service account. Definí "
        "GOOGLE_SERVICE_ACCOUNT_JSON (en prod) o SERVICE_ACCOUNT_JSON_PATH (en dev)."
    )


def open_sheet(sheet_id: str) -> gspread.Spreadsheet:
    """Abrir el Google Sheet por ID."""
    creds = _build_credentials()
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id)


def read_dim_clients(sheet: gspread.Spreadsheet) -> list[str]:
    """
    Lee la columna cliente_id del tab dim_clients (skipping la fila de nota).
    Devuelve solo los códigos activos (activo_si_no = 'si').
    """
    ws = sheet.worksheet("dim_clients")
    # row 1 = nota amarilla, row 2 = headers, row 3+ = data
    values = ws.get_all_values()
    if len(values) < 3:
        logger.warning("dim_clients vacío — no hay clientes para resolver naming")
        return []
    headers = values[1]
    try:
        col_id = headers.index("cliente_id")
        col_activo = headers.index("activo_si_no")
    except ValueError as e:
        raise RuntimeError(f"Headers de dim_clients no coinciden: {headers}") from e
    codes = []
    for row in values[2:]:
        if len(row) <= max(col_id, col_activo):
            continue
        if row[col_id] and row[col_activo].strip().lower() == "si":
            codes.append(row[col_id].strip())
    logger.info("dim_clients activos: %s", codes)
    return codes


def replace_last_n_days(
    sheet: gspread.Spreadsheet,
    tab_name: str,
    df: pd.DataFrame,
    date_col: str,
    lookback_days: int,
) -> tuple[int, int]:
    """
    Reemplaza en el tab las filas cuyo `date_col` esté en el rango
    [today - lookback_days, today]. Después agrega las filas nuevas del df.

    Returns:
        (filas_borradas, filas_insertadas)
    """
    ws = sheet.worksheet(tab_name)
    values = ws.get_all_values()

    # Filas 1 (nota) y 2 (headers) se mantienen siempre.
    if len(values) < 2:
        raise RuntimeError(f"Tab {tab_name} no tiene headers — revisar warehouse")
    headers = values[1]
    data_rows = values[2:]

    cutoff = dt.date.today() - dt.timedelta(days=lookback_days)
    try:
        date_idx = headers.index(date_col)
    except ValueError as e:
        raise RuntimeError(
            f"Columna {date_col!r} no existe en {tab_name}. Headers: {headers}"
        ) from e

    kept_rows = []
    deleted = 0
    for row in data_rows:
        if len(row) <= date_idx or not row[date_idx]:
            kept_rows.append(row)
            continue
        try:
            row_date = dt.date.fromisoformat(row[date_idx][:10])
        except ValueError:
            kept_rows.append(row)
            continue
        if row_date >= cutoff:
            deleted += 1
        else:
            kept_rows.append(row)

    # Asegurar que cada fila nueva tenga las columnas en el mismo orden que headers.
    df_aligned = df.reindex(columns=headers).fillna("")
    new_rows = df_aligned.astype(str).values.tolist()

    # Reescribir el rango de datos: filas existentes que sobreviven + filas nuevas.
    final_rows = kept_rows + new_rows
    # Limpiamos desde la fila 3 hacia abajo y escribimos todo.
    ws.batch_clear([f"A3:Z{ws.row_count}"])
    if final_rows:
        ws.update(
            range_name=f"A3",
            values=final_rows,
            value_input_option="USER_ENTERED",
        )
    logger.info(
        "Tab %s — borradas %d filas (últimos %d días), insertadas %d nuevas",
        tab_name, deleted, lookback_days, len(new_rows),
    )
    return deleted, len(new_rows)


def append_log(
    sheet: gspread.Spreadsheet,
    *,
    trigger: str,
    status: str,
    rows_meta: int = 0,
    rows_google: int = 0,
    rows_portales: int = 0,
    rows_leads: int = 0,
    rows_fact: int = 0,
    duration_sec: float = 0.0,
    error_message: str = "",
) -> None:
    """Append una línea al tab etl_logs."""
    ws = sheet.worksheet("etl_logs")
    ws.append_row(
        [
            dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            trigger,
            status,
            rows_meta,
            rows_google,
            rows_portales,
            rows_leads,
            rows_fact,
            round(duration_sec, 2),
            error_message[:500],
        ],
        value_input_option="USER_ENTERED",
    )
