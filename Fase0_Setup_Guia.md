# Fase 0 — Setup base del POC

**Tiempo total estimado:** 30–45 minutos

Esta guía te lleva paso a paso por las tres tareas que dejan el terreno listo para el ETL:

1. Subir y convertir el warehouse a Google Sheets
2. Crear el proyecto en Google Cloud y la cuenta de servicio
3. Crear las carpetas de Drive para los uploads manuales

Al terminar vas a tener: un Google Sheet "Nexiu Ops Warehouse" listo, un archivo JSON con las credenciales del bot, y dos carpetas en Drive donde después subirás los Excels manuales.

---

## Paso 1 — Subir el warehouse a Google Sheets (5 min)

Ya generé el archivo `Nexiu_Ops_Warehouse.xlsx` en esta carpeta del proyecto. Ese archivo tiene los 7 tabs con los headers correctos y unas filas de ejemplo en `dim_clients` para que veas el patrón. **Es solo una plantilla** — el archivo "vivo" donde el ETL va a escribir tiene que ser un Google Sheet, no un .xlsx.

1. Abrí https://drive.google.com con tu cuenta @nexiu.ai.
2. Creá (o entrá a) un Drive compartido del equipo donde vas a vivir este POC. Sugerencia: una carpeta llamada **"Nexiu Ops POC"**.
3. Arrastrá `Nexiu_Ops_Warehouse.xlsx` adentro de esa carpeta.
4. Click derecho en el archivo subido → **Open with** → **Google Sheets**.
5. Una vez abierto en Sheets, **File → Save as Google Sheets**. Esto crea una copia nativa de Sheets (que es la que sirve; el .xlsx original podés borrarlo o archivarlo).
6. Renombrá la copia nativa exactamente a **`Nexiu Ops Warehouse`** (sin extensión, sin "Copia de").
7. Anotá el **ID del Sheet**. Lo encontrás en la URL:
   ```
   https://docs.google.com/spreadsheets/d/   ESTE_ID_LARGO   /edit
   ```
   Lo vas a usar en varios lugares — guardalo en un archivo de notas con el nombre `SHEET_ID`.

> **Verificación:** abrí el Sheet nuevo y revisá que los 8 tabs estén en este orden: `dim_clients`, `inputs_semanales`, `ads_meta`, `ads_google`, `ads_portales_manual`, `leads_raw`, `FACT_CONSOLIDADO`, `etl_logs`. Cada tab debe tener una fila amarilla arriba con una nota explicativa, y los headers en negro abajo.

---

## Paso 2 — Llenar `dim_clients` y `inputs_semanales` (10–15 min)

### 2.1 `dim_clients` (lista maestra de clientes)

Es la tabla que vas a llenar **vos a mano una sola vez** (después la mantenés cuando entran/salen clientes). Es la que conecta todas las otras tablas.

1. Abrí el tab `dim_clients`.
2. Las 5 filas de ejemplo ya tienen tus códigos reales (LAFA, KAVAK, GRUPALIA, PODEMOS, PLATA). Revisá que estén bien y agregá / sacá los que falten.
3. Columnas:

| Columna | Qué va | Ejemplo |
|---|---|---|
| `cliente_id` | Código corto en MAYÚSCULAS, sin espacios. Tiene que coincidir EXACTO con la columna MKT*** de tus exports de META. | `LAFA`, `KAVAK`, `GRUPALIA` |
| `cliente_nombre` | Nombre legible para el dashboard | `LAFA`, `Kavak`, `Grupalia` |
| `activo_si_no` | `si` si está activo hoy, `no` si pausado | `si` |

> **Crítico:** el `cliente_id` debe coincidir letra por letra con: (a) la columna MKT*** del export de META, y (b) el prefijo del nombre del Excel que descargás de la plataforma de Nexiu (ej: `LAFA_2026-W17.xlsx` → cliente_id = `LAFA`). Si hoy en META aparece "Lafa" o "LAFA-MX", hay que estandarizar a un solo código antes de arrancar el ETL.

### 2.2 `inputs_semanales` (open positions, avg price, churn)

Estos son los inputs manuales que cambian semana a semana — los que en tu sheet actual están en azul.

1. Abrí el tab `inputs_semanales`.
2. Borrá las dos filas de ejemplo (LAFA y KAVAK con `comentario = "ejemplo — borrar"`).
3. Cargá una fila por cada combinación cliente × semana que querés trackear. Mínimo: la semana corriente y las anteriores que quieras rellenar para tener historia comparable. Columnas:

| Columna | Qué va | Ejemplo |
|---|---|---|
| `cliente_id` | El mismo código que está en `dim_clients` | `LAFA` |
| `iso_year` | Año ISO (ej: 2026) | `2026` |
| `iso_week` | Número de semana ISO (1–53). En tu sheet actual son las "Week 11", "Week 12"... | `17` |
| `open_positions` | Cuántas vacantes abiertas tiene el cliente esa semana | `40` |
| `avg_price_per_hire` | Lo que cobrás por contratación esa semana (en MXN o moneda local) | `160` |
| `churn_pct` | Tasa de churn esperada, entre 0 y 1 | `0` o `0.05` |
| `comentario` | Texto libre opcional para anotar cambios | `"Subida de fee acordada con cliente"` |

> **Tip:** podés cargar los inputs de toda una semana de golpe los lunes — abrís el tab, agregás 5 filas (una por cliente activo) con `iso_week` = la semana que arranca, y listo. El dashboard usa esos valores para calcular Revenue, CM1, CPL, CPH.

---

## Paso 3 — Crear proyecto en Google Cloud y Service Account (15–20 min)

La cuenta de servicio (service account) es un "usuario robot" que el script ETL va a usar para escribir al Sheet sin que vos tengas que loguearte cada vez. Es 100% gratis y solo se hace una vez.

### 3.1 Crear el proyecto

1. Ir a https://console.cloud.google.com con tu cuenta @nexiu.ai.
2. Si nunca usaste Google Cloud, va a pedir que aceptes términos y elijas país. **No te pide tarjeta** para lo que vamos a hacer.
3. Arriba a la izquierda, al lado del logo de Google Cloud, hay un selector de proyectos (dice "Select a project" o similar). Hacé click → **New Project**.
4. Nombre del proyecto: **`nexiu-ops-poc`**. Dejá la organización por defecto. Click **Create**.
5. Esperá ~30 seg a que se cree, después seleccionalo en el mismo dropdown.

### 3.2 Habilitar las APIs que necesita el ETL

1. Menú hamburguesa (☰) → **APIs & Services** → **Library**.
2. Buscá y habilitá las siguientes una por una (click en el resultado → botón azul "Enable"):
   - **Google Sheets API**
   - **Google Drive API**
   - **Google Ads API** (esta la usa el ETL en Fase 2; mejor habilitarla ahora)

### 3.3 Crear la Service Account

1. Menú (☰) → **IAM & Admin** → **Service Accounts**.
2. Botón **+ Create Service Account** arriba.
3. Llenar:
   - **Service account name:** `etl-writer`
   - **Service account ID:** se autocompleta a `etl-writer`
   - **Description:** `Bot que escribe datos del ETL al Google Sheet del warehouse`
4. Click **Create and Continue**.
5. En "Grant this service account access to project" — **dejalo en blanco** (no le damos permisos a nivel proyecto, solo a nivel sheet específico). Click **Continue**.
6. En "Grant users access" — **dejalo en blanco** también. Click **Done**.

### 3.4 Generar la key JSON

Es el "password" del bot. Esto solo se descarga una vez — guardalo bien.

1. En la lista de Service Accounts, click sobre **etl-writer@...iam.gserviceaccount.com**.
2. Pestaña **Keys** → **Add Key** → **Create new key**.
3. Tipo: **JSON**. Click **Create**.
4. Se descarga automáticamente un archivo `.json` (ej: `nexiu-ops-poc-abc123.json`).
5. **Renombralo a `etl-service-account.json`** y guardalo en una carpeta segura de tu compu (NO lo subas a GitHub ni a Drive).
6. Anotá el email del service account — está dentro del JSON con la key `client_email`. Es algo como:
   ```
   etl-writer@nexiu-ops-poc.iam.gserviceaccount.com
   ```

### 3.5 Compartir el Sheet con el bot

Este es el paso que más se olvida y rompe todo después. El bot solo puede escribir en sheets que vos le compartiste explícitamente.

1. Volvé al Sheet **`Nexiu Ops Warehouse`** en Drive.
2. Botón **Share** (arriba a la derecha).
3. En "Add people, groups, or calendar events" pegá el email del service account (`etl-writer@nexiu-ops-poc.iam.gserviceaccount.com`).
4. Permiso: **Editor**.
5. **Desmarcá** "Notify people" (no tiene sentido mandarle un mail a un robot).
6. Click **Share**.

> **Verificación:** entrá al Share dialog de nuevo y confirmá que el email del service account aparece listado como Editor.

---

## Paso 4 — Crear la carpeta de Drive para uploads manuales (5 min)

1. Dentro de la carpeta **"Nexiu Ops POC"** del Drive compartido, creá una subcarpeta llamada **`Nexiu Manual Uploads`**.
2. Adentro de esa, creá dos subcarpetas:
   - `portales/` — para los Excels descargados de Indeed, Computrabajo, OCC u otros portales
   - `plataforma/` — para los Excels descargados de tu plataforma de Nexiu, **uno por cliente**
3. Adentro de cada subcarpeta creá una sub-sub-carpeta `archivo/` — el Apps Script (Fase 4 del plan) va a mover ahí los archivos ya procesados para no procesarlos dos veces.
4. Compartí la carpeta `Nexiu Manual Uploads` con el mismo service account (`etl-writer@...`) como **Editor** (mismo flow que el Paso 3.5 pero en la carpeta).

> **Convención de naming crítica para los Excels de la plataforma:** el archivo TIENE QUE empezar con el `cliente_id` en MAYÚSCULAS, seguido de guión bajo. Ejemplos válidos:
> - `LAFA_2026-W17.xlsx` ✅
> - `KAVAK_abril_2026.xlsx` ✅
> - `GRUPALIA-leads-2026-04.xlsx` ❌ (guión en vez de guión bajo)
> - `lafa_W17.xlsx` ❌ (minúsculas)
>
> El ETL lee el filename con un regex `^([A-Z]+)_` para extraer el cliente_id. Si no matchea con un cliente de `dim_clients`, el archivo se ignora y queda registrado en `etl_logs`.

---

## Checklist de Fase 0 — para confirmarme cuando termines

Cuando hayas hecho todo lo de arriba, mandame estos cinco datos para arrancar la Fase 1:

- [ ] **SHEET_ID:** (el ID largo de la URL del Sheet)
- [ ] **Service account email:** `etl-writer@...iam.gserviceaccount.com`
- [ ] **Confirmaste que `dim_clients` tiene tus N clientes reales:** sí / no
- [ ] **Cargaste al menos 1 semana de inputs_semanales como prueba:** sí / no
- [ ] **Tenés guardado en tu compu el `etl-service-account.json`:** sí / no

Con eso ya podemos arrancar Fase 1: pedir el developer token de Google Ads (que tarda 1–3 días, conviene iniciarlo ya) y generar el access token de META.

---

## Errores comunes y cómo resolverlos

**"No tengo permiso para crear un Drive compartido"** — Si tu workspace de @nexiu.ai te limita esto, usá tu My Drive personal por ahora. Para producción, mejor que sea Drive compartido.

**"Google Cloud me pide tarjeta de crédito"** — Pasa cuando intentás habilitar APIs de Maps, BigQuery, etc. Para Sheets API, Drive API y Google Ads API NO te pide tarjeta. Si te aparece, revisá que estés en el proyecto correcto y no en uno con billing forzado.

**"Service Account no aparece en el dropdown del Share"** — Pegá el email completo manualmente, no uses autocomplete. Y confirmá que el service account está activo en IAM & Admin → Service Accounts.

**"Cuando descargo el JSON me da un archivo .key.json muy raro"** — Está bien. Renombralo a `etl-service-account.json` y listo. Lo importante es el contenido (texto JSON con `private_key`, `client_email`, etc.).

**"Aboutu el `cliente_id`: ¿y si un cliente tiene el mismo nombre legal pero opera con dos marcas?"** — Tratalos como dos clientes separados con distintos `cliente_id`. Vas a poder consolidarlos en el dashboard con un filtro o agrupación.
