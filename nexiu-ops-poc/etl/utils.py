"""Helpers compartidos por todos los módulos del ETL."""

from __future__ import annotations

import datetime as dt
import logging
import re
from typing import Iterable

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configurar logging unificado para todos los módulos."""
    logging.basicConfig(level=level, format=LOG_FORMAT, force=True)
    return logging.getLogger("nexiu_etl")


def iso_year_week(date_value: dt.date | dt.datetime | str) -> tuple[int, int]:
    """Devuelve (iso_year, iso_week) para una fecha."""
    if isinstance(date_value, str):
        date_value = dt.date.fromisoformat(date_value[:10])
    if isinstance(date_value, dt.datetime):
        date_value = date_value.date()
    iso = date_value.isocalendar()
    return iso.year, iso.week


def extract_cliente_id(text: str | None, known_codes: Iterable[str]) -> str:
    """
    Encuentra el primer código de cliente conocido dentro de un texto.

    Hace match case-insensitive contra cada código de `known_codes`. Si encuentra
    múltiples, devuelve el primero según el orden de `known_codes`. Si no hay
    match, devuelve "UNKNOWN" (queda registrado en logs para que Fede revise
    el naming de campañas).

    Ejemplos asumiendo known_codes=["LAFA", "KAVAK", "GRUPALIA"]:
      "042026-1026-LAFA-CDMX"      -> "LAFA"
      "[KAVAK]-search-mty"         -> "KAVAK"
      "1804- Grupalia Conv Whats"  -> "GRUPALIA"
      "campaña-genérica"            -> "UNKNOWN"
    """
    if not text:
        return "UNKNOWN"
    upper = text.upper()
    # Boundary-aware regex para evitar matches parciales (ej: "PLATA" dentro de "PLATAFORMA").
    for code in known_codes:
        pattern = rf"(?<![A-Z]){re.escape(code.upper())}(?![A-Z])"
        if re.search(pattern, upper):
            return code.upper()
    return "UNKNOWN"


def utc_now_iso() -> str:
    """Timestamp ISO en UTC para columnas tipo `pulled_at`."""
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def daterange(start: dt.date, end: dt.date) -> list[dt.date]:
    """Lista de fechas entre start y end (inclusive)."""
    return [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
