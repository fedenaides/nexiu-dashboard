# Nexiu Ops POC — ETL

Script Python que jala datos de Meta Marketing API (y eventualmente Google Ads) y los escribe al Google Sheet warehouse "Nexiu Ops Warehouse" cada 6 horas.

Estado actual (Fase 2A):
- ✅ Meta Marketing API
- ⏸ Google Ads — esperando aprobación de Basic Access
- ⏸ Portales (Indeed) — manual upload a través de Apps Script (Fase 4)
- ⏸ Plataforma Nexiu (leads) — manual upload (Fase 4)
- ⏸ FACT_CONSOLIDADO — Fase 5

## Estructura

```
nexiu-ops-poc/
├── etl/
│   ├── __init__.py
│   ├── meta_ads.py       # Descarga insights de Meta Marketing API
│   ├── sheets_writer.py  # Lee/escribe Google Sheets via service account
│   └── utils.py          # Helpers (iso week, regex de cliente, logging)
├── main.py               # Orquestador
├── requirements.txt
├── .env.example          # Plantilla de variables de entorno
└── .gitignore
```

## Correr local

```bash
# 1. Crear entorno virtual (opcional pero recomendado)
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Crear .env desde la plantilla y rellenar valores
cp .env.example .env
# editar .env con tus tokens y SHEET_ID

# 4. Correr
python main.py
```

## Verificación post-run

Cuando termine sin errores deberías ver en el Sheet:
- `ads_meta` poblado con filas de los últimos 7 días.
- `etl_logs` con una nueva fila `status=success`.

Si algo falla, `etl_logs` tiene el `error_message` y la consola tiene el traceback completo.

## Próximos pasos

1. **Fase 3 — Cron en GitHub Actions:** workflow que corre `python main.py` cada 6h.
2. **Activar Google Ads** cuando aprueben Basic Access — agregar `etl/google_ads.py` y secrets correspondientes.
3. **Fase 4 — Manual uploads** vía Apps Script (Indeed + plataforma Nexiu).
4. **Fase 5 — FACT_CONSOLIDADO** + dashboard Looker Studio.
