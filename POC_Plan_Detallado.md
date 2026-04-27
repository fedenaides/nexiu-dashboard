# POC Dashboard Nexiu — Plan Detallado

**Fecha de inicio:** 25 abril 2026
**Estimación total:** 1.5 a 2 semanas de trabajo (con tiempos muertos esperando aprobaciones de APIs)
**Costo:** $0/mes en operación

---

## 1. Arquitectura en una página

```
  ┌────────────────────────┐      ┌──────────────────────┐
  │  META Ads API          │      │  Google Ads API      │
  └────────────┬───────────┘      └──────────┬───────────┘
               │ cada 6h                     │ cada 6h
               ▼                             ▼
       ┌──────────────────────────────────────────┐
       │   GitHub Actions (cron)                  │
       │   Python script: ETL                     │
       └──────────────────┬───────────────────────┘
                          │ escribe
                          ▼
  ┌─────────────────────────────────────────────────────┐
  │          GOOGLE SHEETS — "Nexiu Warehouse"          │
  │  Tabs: ads_meta, ads_google, ads_indeed_manual,     │
  │        leads_manual, hires_manual, dim_clients,     │
  │        FACT_CONSOLIDADO                             │
  └──────────────────┬──────────────────────────────────┘
                     │ se conecta nativo
                     ▼
       ┌──────────────────────────────────────┐
       │  LOOKER STUDIO (dashboard web)       │
       │  Login Google → solo dominio nexiu   │
       └──────────────────────────────────────┘

  ↑ paralelo: tú subís Excels (Indeed + leads/hires)
  a una carpeta de Drive "Nexiu Manual Uploads/", y un
  Apps Script los normaliza dentro del Sheet.
```

**Por qué este stack:** todo es free tier, no hay servidores que mantener (GitHub Actions corre el cron gratis), Looker Studio se conecta a Sheets en un click, y el login con dominio @nexiu.ai sale de fábrica.

---

## 2. Pre-requisitos (cosas que vas a necesitar)

Antes de tocar código, conseguí estos accesos. Marcá cada uno cuando lo tengas:

- [ ] Cuenta de Google con tu mail @nexiu.ai (admin del Workspace si es posible).
- [ ] Acceso de admin a la cuenta de **Meta Business / Ad Account** que usan para captar talento.
- [ ] Acceso de admin a la cuenta de **Google Ads** (idealmente nivel MCC si manejan varias cuentas de cliente).
- [ ] Cuenta gratuita de **GitHub** (sirve la tuya personal).
- [ ] Tener instalado **Claude Code** en tu compu (lo vamos a usar para escribir el ETL).

---

## 3. Fase 0 — Setup base (estimado: 30–45 min)

### 3.1. Crear el "warehouse" en Google Sheets

Usá la plantilla `Nexiu_Ops_Warehouse.xlsx` que ya está en esta carpeta del proyecto (procedimiento detallado en `Fase0_Setup_Guia.md`). El warehouse tiene 8 tabs, todos a granularidad **semana ISO** (los KPIs son weekly cohort):

| Tab | Rol | Quién lo escribe |
|---|---|---|
| `dim_clients` | Lista maestra de clientes (cliente_id, nombre, activo) | Vos a mano, una vez |
| `inputs_semanales` | Open positions, avg price per hire, churn % por cliente × semana | Vos a mano, semanalmente |
| `ads_meta` | Costos y leads de META por día/campaña/cliente | ETL automático |
| `ads_google` | Costos y leads de Google Ads | ETL automático |
| `ads_portales_manual` | Costos de Indeed/Computrabajo/OCC | Apps Script desde Excels que vos subís |
| `leads_raw` | **Una fila por cada lead/candidato** (no agregado): nombre, fuente, status, etc. | Apps Script desde Excels de la plataforma de Nexiu |
| `FACT_CONSOLIDADO` | Tabla consolidada por cliente × semana — la única que lee Looker Studio | ETL automático |
| `etl_logs` | Log de cada corrida del ETL (debugging) | ETL automático |

> **Decisiones clave del schema:**
> - **Lead-level, no agregado:** `leads_raw` guarda una fila por candidato. El ETL deriva las métricas Inbound / Under Qualification / Presented / Hired / Discarded filtrando por la columna `status`. Más rico, permite cualquier KPI ad-hoc después.
> - **cliente_id se infiere por filename** del Excel de la plataforma (ej: `LAFA_2026-W17.xlsx`). El ETL parsea el prefijo y lo matchea contra `dim_clients`.
> - **cliente_id en META se lee de la columna MKT***: el export de META ya incluye el cliente parseado, así que el ETL lo lee directo sin regex sobre `campaign_name`.
> - **Los inputs manuales (open positions, avg price, churn) viven en `inputs_semanales`** porque varían semana a semana — son los valores azules de tu sheet actual.

### 3.2. Crear carpeta de uploads manuales

En el mismo Drive, creá la carpeta **"Nexiu Manual Uploads"** con dos subcarpetas:
- `indeed/` → acá vas a tirar los Excels descargados de Indeed
- `clientes/` → acá vas a tirar los Excels descargados de tu plataforma, uno por cliente

### 3.3. Crear Service Account de Google Cloud (gratis)

Esto es lo que le da permiso al script Python para escribir en el Sheet sin que tengas que loguearte cada vez.

1. Ir a https://console.cloud.google.com/ → crear proyecto **"nexiu-ops-poc"**.
2. APIs & Services → Enable APIs → habilitar **Google Sheets API** y **Google Drive API**.
3. IAM & Admin → Service Accounts → "Create service account" → nombre `etl-writer`.
4. Crear key → JSON → descargar. Guardalo seguro (es la "contraseña" del bot).
5. Copiar el email del service account (algo como `etl-writer@nexiu-ops-poc.iam.gserviceaccount.com`) y compartir el Sheet "Nexiu Ops Warehouse" con ese mail, dándole permiso de **Editor**.

---

## 4. Fase 1 — Acceso a APIs de ads (estimado: 1–2 horas + tiempos de espera)

### 4.1. Meta Marketing API

1. Ir a https://developers.facebook.com/ → My Apps → Create App → tipo "Business".
2. En el dashboard de la app, agregar el producto **Marketing API**.
3. Generar **Access Token** con permiso `ads_read` y `business_management`.
4. Convertirlo a token de larga duración (60 días) con la herramienta "Access Token Debugger" → "Extend Access Token". Para POC alcanza; para producción se puede automatizar el refresh.
5. Anotar tu **Ad Account ID** (formato `act_1234567890`).

### 4.2. Google Ads API

Esta es la más fastidiosa porque pide aprobación humana de Google.

1. Ir a https://ads.google.com/aw/apicenter (con la cuenta MCC) → solicitar **Developer Token**. Ponen "Test Account" para empezar (ya alcanza para el POC).
2. En Google Cloud Console (mismo proyecto que el del Sheet), habilitar **Google Ads API**.
3. Crear OAuth 2.0 Client ID tipo "Desktop App" → descargar `client_secret.json`.
4. Generar refresh token corriendo localmente el flow de OAuth (Claude Code te ayuda con un script de 20 líneas).
5. Anotar tu **Customer ID** (formato `123-456-7890`, sin guiones para la API).

> **Heads up:** el Developer Token de Google Ads en modo "Test" solo lee cuentas de test. Para leer la cuenta real tenés que pedir nivel "Basic" → Google revisa en 1–3 días. Iniciá este trámite el día 1 del POC para que no te bloquee al final.

---

## 5. Fase 2 — Script ETL automático (estimado: 3–4 horas con Claude Code)

### 5.1. Estructura del repo

Crear un repo en GitHub llamado `nexiu-ops-poc` con esta estructura:

```
nexiu-ops-poc/
├── etl/
│   ├── __init__.py
│   ├── meta_ads.py
│   ├── google_ads.py
│   ├── sheets_writer.py
│   └── normalize.py
├── .github/workflows/etl.yml
├── requirements.txt
├── main.py
└── README.md
```

### 5.2. Lógica de cada módulo

- **`meta_ads.py`**: usa la lib `facebook-business`. Endpoint `Insights` → pedís métricas `spend, impressions, clicks` con `time_increment=1` (granularidad diaria), `level=campaign`, `date_preset=last_7d`. Devuelve un DataFrame normalizado.
- **`google_ads.py`**: usa la lib `google-ads`. GAQL query a `campaign` + `metrics.cost_micros`, `metrics.impressions`, `metrics.clicks`, agrupado por día y campaña.
- **`sheets_writer.py`**: usa `gspread`. Función `upsert_rows(tab_name, df, key_cols)` que reescribe filas existentes y agrega nuevas (clave: `fecha + campaign_name`).
- **`normalize.py`**: función helper que de un nombre de campaña extrae el `cliente`. Convención sugerida: nombrar campañas con prefijo `[CLIENTE]-...` o `CLIENTE_...` para que un regex simple extraiga el nombre. Si la convención no existe hoy, vale la pena estandarizarla **antes** del POC.
- **`main.py`**: orquesta los tres pasos, loguea errores a un tab `etl_logs` del Sheet.

### 5.3. Cómo escribirlo con Claude Code

Abrí Claude Code en la carpeta del repo y prompteá algo como:

> "Necesito un módulo Python que use la librería `facebook-business` para descargar gasto, impresiones y clicks por día y campaña de los últimos 7 días desde el Ad Account `act_XXXX`. El token está en la variable de entorno `META_ACCESS_TOKEN`. Devolvé un DataFrame de pandas con columnas `fecha, campaign_name, spend, impressions, clicks`."

Y lo mismo para Google Ads y para `sheets_writer`. Iterá hasta que corra local.

### 5.4. Variables de entorno

Crear archivo `.env` (NO commitear) con:

```
META_ACCESS_TOKEN=...
META_AD_ACCOUNT_ID=act_...
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=...
GOOGLE_ADS_CUSTOMER_ID=...
GOOGLE_SERVICE_ACCOUNT_JSON=...   # contenido del JSON entero como string
SHEET_ID=1T-gM8VITjGxouZYPsc6HNsGLVs3dtAYszjAj0vUBxg4
```

---

## 6. Fase 3 — Cron cada 6 horas con GitHub Actions (estimado: 30 min)

GitHub Actions te da **2.000 minutos/mes gratis**. Una corrida del ETL tarda ~1–2 minutos. Cuatro corridas por día × 30 días = ~240 minutos/mes. Sobra muchísimo.

### 6.1. Workflow

Crear `.github/workflows/etl.yml`:

```yaml
name: nexiu-etl
on:
  schedule:
    - cron: '0 */6 * * *'   # cada 6 horas, en hora UTC
  workflow_dispatch:         # botón manual para correrlo a demanda

jobs:
  run-etl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          META_ACCESS_TOKEN: ${{ secrets.META_ACCESS_TOKEN }}
          META_AD_ACCOUNT_ID: ${{ secrets.META_AD_ACCOUNT_ID }}
          GOOGLE_ADS_DEVELOPER_TOKEN: ${{ secrets.GOOGLE_ADS_DEVELOPER_TOKEN }}
          GOOGLE_ADS_CLIENT_ID: ${{ secrets.GOOGLE_ADS_CLIENT_ID }}
          GOOGLE_ADS_CLIENT_SECRET: ${{ secrets.GOOGLE_ADS_CLIENT_SECRET }}
          GOOGLE_ADS_REFRESH_TOKEN: ${{ secrets.GOOGLE_ADS_REFRESH_TOKEN }}
          GOOGLE_ADS_CUSTOMER_ID: ${{ secrets.GOOGLE_ADS_CUSTOMER_ID }}
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
          SHEET_ID: ${{ secrets.SHEET_ID }}
```

### 6.2. Secrets

En GitHub → repo → Settings → Secrets and variables → Actions → New repository secret. Agregar cada una de las variables del `.env`.

### 6.3. Validación

- Ejecutá manualmente con "Run workflow" la primera vez.
- Confirmá que las filas aparecen en los tabs `ads_meta` y `ads_google` del Sheet.
- Esperá a que dispare la cron 6h después y revisá que los datos se actualicen sin duplicar.

---

## 7. Fase 4 — Ingesta de Excels manuales (estimado: 2–3 horas)

Esta es la pata que **no se puede automatizar** porque la descarga la hacés vos. Pero podemos automatizar el **pegado** dentro del Sheet con un Apps Script.

### 7.1. Formato esperado del Excel de la plataforma

El Excel que descargás hoy ya viene lead-level (una fila por candidato) con columnas como `MOI`, `WEE`, `MKT***`, `O_id`, `Job order`, `Work Location`, `Name`, `Phone`, `Email`. Para el POC necesitamos que también tenga una columna **`status`** con uno de: `inbound`, `under_qualification`, `presented`, `hired`, `discarded`. Sin la columna status, el ETL no puede calcular el funnel Inbound → Hired.

**Naming del archivo (regla rígida):** debe empezar con `cliente_id` en MAYÚSCULAS seguido de guión bajo. Ejemplos válidos:
- `LAFA_2026-W17.xlsx` ✅
- `KAVAK_abril_2026.xlsx` ✅
- `lafa_W17.xlsx` ❌ (minúsculas)
- `GRUPALIA-leads.xlsx` ❌ (guión en vez de underscore)

### 7.2. Apps Script de ingesta

En el Sheet "Nexiu Ops Warehouse" → Extensions → Apps Script. Pegar un script que:
1. Cada 10 minutos chequea la carpeta `Nexiu Manual Uploads/clientes/`.
2. Por cada Excel nuevo, lo abre, lee las columnas, y agrega filas a `leads_manual` y `hires_manual` con `uploaded_at = now()`.
3. Mueve el archivo procesado a una subcarpeta `archivo/` para no procesarlo dos veces.

Lo mismo para Indeed (`Nexiu Manual Uploads/indeed/`) → tab `ads_indeed_manual`.

> Claude Code o Claude.ai te puede escribir este Apps Script en 10 min. Prompt sugerido: "Necesito un Google Apps Script que lea archivos .xlsx nuevos en la carpeta de Drive con ID XXX, parsee las columnas A-F asumiendo headers en fila 1, y agregue las filas al tab `leads_manual` del Sheet con ID YYY, agregando una columna `uploaded_at` con la fecha y hora actuales."

### 7.3. Alternativa más simple si te cuesta el Apps Script

Si el Apps Script se complica, hay un plan B sin código: tener tabs `MANUAL_PASTE_INDEED` y `MANUAL_PASTE_LEADS` donde literalmente pegás los datos del Excel con Ctrl+V. El resto del pipeline lo lee de ahí. Menos elegante pero funciona.

---

## 8. Fase 5 — Tabla consolidada (estimado: 1 hora)

En el tab `FACT_CONSOLIDADO` armás una sola tabla por **fecha + cliente** que combine todo:

| fecha | cliente | spend_meta | spend_google | spend_indeed | spend_total | leads_ingresados | leads_presentados | contratados | revenue | costo_por_lead | costo_por_contratacion | conversion | margen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Esto se construye con `QUERY()` o una macro de Apps Script que recorre todos los tabs fuente y escribe el consolidado. Es el equivalente a una "fact table" — el dashboard se conecta solo a este tab.

**Recomendación:** que esto lo refresque el mismo workflow de GitHub Actions al final del ETL, así el consolidado siempre está sincronizado.

---

## 9. Fase 6 — Dashboard en Looker Studio (estimado: 2–3 horas)

### 9.1. Crear el reporte

1. Ir a https://lookerstudio.google.com/ → Create → Report.
2. Add data → Google Sheets connector → seleccionar "Nexiu Ops Warehouse" → tab `FACT_CONSOLIDADO`.
3. Importante: marcar "Use first row as headers".

### 9.2. Páginas y widgets sugeridos

**Página 1 — Resumen ejecutivo**
- Scorecards arriba: Spend total, Leads ingresados, Leads presentados, Contratados, CPL, CPH, Tasa de conversión, Margen.
- Gráfico de líneas: Spend por plataforma a lo largo del tiempo.
- Gráfico de barras: Contrataciones por cliente.

**Página 2 — Cohortes (lo que hoy son tus 4 sheets)**
- Tabla pivot con filtros de fecha (semanal/mensual) y cliente, mostrando todas las métricas.
- Reemplaza tus 4 sheets con un solo tablero filtrable.

**Página 3 — P&L por cliente**
- Tabla con costos, revenue, margen por cliente, ordenable.

### 9.3. Filtros globales

Agregar tres filtros en la barra superior que apliquen a todas las páginas: **Cliente** (dropdown multi-select), **Plataforma** (chips), **Rango de fechas**.

### 9.4. Compartir solo con dominio Nexiu

1. Share → "Restricted to nexiu.ai".
2. Copiá la URL del reporte y mandala a tu equipo. Cuando entren con su mail @nexiu.ai van a tener acceso; cualquier otro mail rebota.

---

## 10. Fase 7 — Validación (estimado: 1–2 horas)

Antes de declarar el POC "vivo", reconciliá contra tu Sheet actual:

1. Tomá una semana cerrada (ej: la última completa).
2. Comparativa lado a lado:
   - Spend META en POC vs. Spend META en sheet actual → debería empatar al centavo.
   - Spend Google → empatar.
   - Leads ingresados → empatar (si subiste el Excel del cliente correspondiente).
   - CPL, CPH, conversión, margen → mismas fórmulas, mismos números.
3. Si hay diferencias, casi siempre son: (a) zona horaria distinta, (b) campaña con cliente mal nombrado, (c) un Excel manual que falta subir.
4. Recién con esa reconciliación al 100% podés mostrarlo al resto del equipo.

---

## 11. Roadmap post-POC (cuando este POC funcione)

Cosas que podés sumar después, no en el POC:
- Integrar Indeed via API (existe, requiere developer access).
- Reemplazar Google Sheets por **BigQuery** (gratis hasta 10GB) cuando los datos crezcan.
- Reemplazar Looker Studio por **Metabase** o **Streamlit** si necesitás interactividad más fina.
- Exponer la API de tu plataforma propia para eliminar el paso manual de Excels — esto es lo que más palanca te da a mediano plazo.
- Alertas en Slack cuando el ETL falla o cuando un KPI sale de banda.

---

## 12. Checklist final (para imprimir)

- [ ] Sheet "Nexiu Ops Warehouse" creado con todos los tabs
- [ ] Carpeta "Nexiu Manual Uploads" creada
- [ ] Service account creado y compartido con el sheet
- [ ] Token de META obtenido (60 días)
- [ ] Developer token de Google Ads aprobado a "Basic"
- [ ] Refresh token de Google Ads generado
- [ ] Repo `nexiu-ops-poc` creado en GitHub
- [ ] Script ETL corre exitoso en local
- [ ] Secrets cargados en GitHub Actions
- [ ] Workflow scheduled corre cada 6h sin errores
- [ ] Apps Script (o paste manual) procesa Excels manuales
- [ ] Tab `FACT_CONSOLIDADO` se actualiza al final del ETL
- [ ] Dashboard Looker Studio publicado
- [ ] Permiso restringido a dominio @nexiu.ai
- [ ] Validación lado a lado con sheet actual al 100%

---

## 13. Riesgos y cosas a tener en cuenta

1. **Convenciones de naming de campañas:** si los nombres de campaña no incluyen el cliente de forma estructurada, es imposible cruzarlos. **Esto es lo primero a resolver.**
2. **Token de Meta caduca cada 60 días:** anotá un recordatorio. Para producción, automatizar el refresh.
3. **Quotas de Google Sheets API:** con 4 corridas/día estás muy lejos del límite, pero si algún día crece, mover a BigQuery.
4. **Cambios en formato del Excel de la plataforma:** si el equipo de producto cambia las columnas del export, el Apps Script se rompe. Avisar al equipo.
5. **Datos sensibles:** Looker Studio compartido por dominio es seguro, pero si alguien hace un export y lo manda fuera, no hay control. Política interna clara.
