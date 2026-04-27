"""
Descarga de insights de Meta Marketing API.

Endpoint: GET /v19.0/{ad-account-id}/insights
Docs: https://developers.facebook.com/docs/marketing-api/insights/

Devuelve un DataFrame con las columnas que espera el tab `ads_meta` del warehouse:
    fecha, iso_year, iso_week, cliente_id, campaign_name, campaign_type, status,
    spend, impressions, clicks, leads_meta, pulled_at
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Iterable

import pandas as pd
import requests

from .utils import extract_cliente_id, iso_year_week, utc_now_iso

logger = logging.getLogger("nexiu_etl.meta")

GRAPH_API_VERSION = "v19.0"
INSIGHTS_FIELDS = [
    "campaign_id",
    "campaign_name",
    "objective",
    "spend",
    "impressions",
    "clicks",
    "actions",
    "date_start",
]


def _detect_campaign_type(objective: str | None, campaign_name: str | None) -> str:
    """
    Inferir el tipo de campaña ('Conv Landing', 'Conv Whats', 'Interacción', etc.)
    desde el `objective` de la API o del nombre de campaña como fallback.

    En el sheet manual de Fede esto viene en una columna separada — acá hacemos
    nuestro mejor esfuerzo desde lo que la API expone.
    """
    obj = (objective or "").upper()
    name = (campaign_name or "").lower()
    if "MESSAGES" in obj or "whats" in name or "wapp" in name:
        return "Conv Whats"
    if "LEAD_GENERATION" in obj:
        return "Lead Gen"
    if "OUTCOME_LEADS" in obj or "LEADS" in obj:
        return "Lead Gen"
    if "CONVERSIONS" in obj or "OUTCOME_SALES" in obj or "landing" in name:
        return "Conv Landing"
    if "ENGAGEMENT" in obj or "OUTCOME_ENGAGEMENT" in obj or "interacc" in name:
        return "Interacción"
    if "TRAFFIC" in obj or "OUTCOME_TRAFFIC" in obj:
        return "Tráfico"
    return obj.title() if obj else "Otros"


def _extract_leads_count(actions: list[dict] | None) -> int:
    """
    Sumar todas las acciones que cuentan como 'lead' (lead, onsite_conversion.lead_grouped, etc.).
    """
    if not actions:
        return 0
    total = 0
    for a in actions:
        action_type = (a.get("action_type") or "").lower()
        if "lead" in action_type:
            try:
                total += int(float(a.get("value", 0)))
            except (TypeError, ValueError):
                pass
    return total


def _paginate(url: str, params: dict) -> list[dict]:
    """Recorrer paginación de la Graph API y devolver todos los registros."""
    rows: list[dict] = []
    next_url: str | None = url
    next_params: dict | None = params
    while next_url:
        resp = requests.get(next_url, params=next_params, timeout=60)
        if resp.status_code >= 400:
            logger.error("Meta API error %s: %s", resp.status_code, resp.text[:500])
            resp.raise_for_status()
        data = resp.json()
        rows.extend(data.get("data", []))
        # paging.next ya viene como URL completa con params; no le pasamos params extra.
        next_url = data.get("paging", {}).get("next")
        next_params = None
    return rows


def fetch_meta_insights(
    access_token: str,
    ad_account_id: str,
    lookback_days: int,
    known_client_codes: Iterable[str],
) -> pd.DataFrame:
    """
    Descarga insights diarios por campaña de los últimos `lookback_days` días.

    Args:
        access_token: long-lived token con scope ads_read + business_management.
        ad_account_id: con prefijo 'act_'.
        lookback_days: cuántos días hacia atrás traer.
        known_client_codes: códigos de dim_clients (ej: ['LAFA', 'KAVAK', ...]).

    Returns:
        DataFrame con el schema del tab ads_meta.
    """
    end = dt.date.today()
    start = end - dt.timedelta(days=lookback_days)
    logger.info(
        "Pidiendo insights de META: account=%s, %s -> %s",
        ad_account_id, start, end,
    )

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ad_account_id}/insights"
    params = {
        "access_token": access_token,
        "fields": ",".join(INSIGHTS_FIELDS),
        "level": "campaign",
        "time_increment": 1,                                    # granularidad diaria
        "time_range": f'{{"since":"{start}","until":"{end}"}}',
        "limit": 500,
    }

    raw = _paginate(url, params)
    logger.info("Meta devolvió %d filas crudas", len(raw))

    pulled_at = utc_now_iso()
    rows: list[dict] = []
    for r in raw:
        date_str = r.get("date_start")
        if not date_str:
            continue
        year, week = iso_year_week(date_str)
        campaign_name = r.get("campaign_name")
        cliente_id = extract_cliente_id(campaign_name, known_client_codes)
        if cliente_id == "UNKNOWN":
            logger.warning(
                "Campaña sin cliente identificado: %r — revisar naming",
                campaign_name,
            )
        rows.append({
            "fecha": date_str,
            "iso_year": year,
            "iso_week": week,
            "cliente_id": cliente_id,
            "campaign_name": campaign_name,
            "campaign_type": _detect_campaign_type(r.get("objective"), campaign_name),
            "status": "active",   # Insights endpoint no devuelve status; lo dejamos por default
            "spend": float(r.get("spend") or 0),
            "impressions": int(r.get("impressions") or 0),
            "clicks": int(r.get("clicks") or 0),
            "leads_meta": _extract_leads_count(r.get("actions")),
            "pulled_at": pulled_at,
        })

    df = pd.DataFrame(rows, columns=[
        "fecha", "iso_year", "iso_week", "cliente_id",
        "campaign_name", "campaign_type", "status",
        "spend", "impressions", "clicks", "leads_meta", "pulled_at",
    ])
    logger.info("Meta normalizado: %d filas", len(df))
    return df
