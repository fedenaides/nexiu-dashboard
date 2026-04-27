# Fase 2 — Probar el ETL local

**Tiempo estimado:** 15–20 minutos
**Objetivo:** Confirmar que el código que escribí funciona contra tus credenciales reales y escribe filas correctas a `ads_meta`.

---

## Paso 1 — Setup del entorno (una sola vez)

Abrí Terminal y andá a la carpeta del repo:

```bash
cd "/Users/federiconaides/Documents/Claude/Projects/DASHBOARD FULLSTACK/nexiu-ops-poc"
```

Crear un entorno virtual de Python (aísla las dependencias del POC del resto de tu sistema):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Vas a ver descargas de `requests`, `gspread`, `pandas`, etc. Tarda 1–2 min.

---

## Paso 2 — Crear tu archivo `.env`

```bash
cp .env.example .env
```

Editá `.env` con tu editor favorito (o `nano .env`) y rellená:

```
SHEET_ID=el_id_de_tu_sheet
SERVICE_ACCOUNT_JSON_PATH=/Users/federiconaides/ruta/a/etl-service-account.json
META_ACCESS_TOKEN=EAA...el_token_extendido_de_60_dias...
META_AD_ACCOUNT_ID=act_1234567890123456
```

> Las dos variables de Google Ads las dejás vacías por ahora — el código las detecta y las saltea.

---

## Paso 3 — Validar credenciales (smoke test)

Antes de escribir nada al Sheet, corré el smoke test:

```bash
python validate.py
```

**Output esperado:**

```
TEST 1/2 — Acceso al Google Sheet
✓ Sheet abierto: 'Nexiu Ops Warehouse'
✓ Códigos de cliente activos en dim_clients: ['LAFA', 'KAVAK', 'GRUPALIA', 'PODEMOS', 'PLATA']

TEST 2/2 — Meta Marketing API
✓ META devolvió 47 filas
Sample (primeras 5 filas):
  fecha       iso_year  iso_week  cliente_id  campaign_name              campaign_type  ...
  2026-04-23  2026      17        LAFA        042026-1026-LAFA-CDMX      Conv Whats     ...
  ...

✓ Todo OK. Ya podés correr `python main.py` para escribir al Sheet.
```

**Si te dice que algunas filas tienen `cliente_id=UNKNOWN`:** te lista los nombres de campaña afectados. Para arreglar:
- O renombrás esas campañas en META para que incluyan un código de `dim_clients` (ej: agregar `[LAFA]-` adelante).
- O agregás un nuevo cliente a `dim_clients` si es uno que faltaba.

**Si falla TEST 1:** revisá que el service account tenga permiso de Editor en el Sheet (Paso 3.5 de Fase 0).

**Si falla TEST 2:** lo más probable es que el access token haya expirado. Volvé a https://developers.facebook.com/tools/debug/accesstoken/ y extendelo de nuevo.

---

## Paso 4 — Primera corrida real

Solo cuando `validate.py` te dé verde:

```bash
python main.py
```

**Lo que va a pasar:**

1. Abre el Sheet.
2. Lee `dim_clients`.
3. Pide a META los insights de los últimos 7 días.
4. Borra del tab `ads_meta` cualquier fila con fecha en los últimos 7 días.
5. Inserta las filas nuevas.
6. Loguea una línea en `etl_logs` con `status=success`.

**Output esperado:**

```
2026-04-25 19:30:01 [INFO] nexiu_etl: Sheet abierto: Nexiu Ops Warehouse
2026-04-25 19:30:02 [INFO] nexiu_etl.sheets: dim_clients activos: ['LAFA', 'KAVAK', ...]
2026-04-25 19:30:03 [INFO] nexiu_etl.meta: Pidiendo insights de META: account=act_..., 2026-04-18 -> 2026-04-25
2026-04-25 19:30:04 [INFO] nexiu_etl.meta: Meta devolvió 47 filas crudas
2026-04-25 19:30:04 [INFO] nexiu_etl.meta: Meta normalizado: 47 filas
2026-04-25 19:30:05 [INFO] nexiu_etl.sheets: Tab ads_meta — borradas 0 filas (últimos 7 días), insertadas 47 nuevas
2026-04-25 19:30:05 [INFO] nexiu_etl: ETL OK en 4.2s — META: 47 filas, Google: 0 filas
```

---

## Paso 5 — Verificación visual en el Sheet

1. Abrí el Sheet en el navegador.
2. Andá al tab `ads_meta`.
3. Tendría que tener filas a partir de la fila 3 con datos reales:
   - `fecha` con fechas de los últimos 7 días.
   - `cliente_id` con códigos de tu `dim_clients` (LAFA, KAVAK, etc.).
   - `spend`, `impressions`, `clicks`, `leads_meta` con valores numéricos.
4. Andá al tab `etl_logs` — debería haber una línea con `status=success`, `rows_meta=47` (o lo que sea), `duration_sec=4.2`.

---

## Paso 6 — Reconciliar con tu sheet manual

Para validar que los números son correctos, tomá una semana cerrada y compará:

| Métrica | Sheet manual | Sheet POC | ¿Empata? |
|---|---|---|---|
| Spend META — LAFA — Week 17 | ej: $2.345 | ej: $2.343 | ✓ (centavos por timezone) |
| Spend META — KAVAK — Week 17 | | | |

Si hay diferencias **grandes** (más del 5%) avisame con el detalle y vemos. Diferencias chicas suelen ser por timezone (META reporta en zona horaria de la cuenta de ads, tu sheet quizá en otra).

---

## Próximo paso

Cuando este test local funcione completo, pasamos a **Fase 3**: subir el código a GitHub y configurar el cron para que corra cada 6h en GitHub Actions automáticamente.

---

## Errores comunes

**"ModuleNotFoundError: No module named 'etl'"** — Estás corriendo desde otra carpeta. Asegurate de hacer `cd nexiu-ops-poc` antes de ejecutar.

**"google.auth.exceptions.RefreshError: invalid_grant"** — El service account JSON está corrupto o el archivo se renombró. Volvé a descargarlo desde Google Cloud Console.

**"requests.exceptions.HTTPError: 400 ... (#100) The parameter access_token is required"** — `META_ACCESS_TOKEN` no está cargado en `.env`. Confirmá con `cat .env | grep META`.

**"PERMISSION_DENIED: The caller does not have permission"** — El service account no fue compartido como Editor en el Sheet. Volvé a Fase 0, Paso 3.5.

**"meta devolvió 0 filas"** — O bien no hubo gasto en los últimos 7 días, o el Ad Account ID es incorrecto. Probá con `ETL_LOOKBACK_DAYS=30 python validate.py` para ampliar la ventana.
