# Fase 1 — Acceso a APIs (META + Google Ads)

**Tiempo total estimado:** ~1.5 horas tuyas + 1 a 3 días hábiles de espera de Google
**Costo:** $0

Esta fase deja listas las "llaves" que el ETL usa para entrar a META Ads y Google Ads. Al terminar vas a tener 8 valores anotados que después pegamos como GitHub Secrets en Fase 3.

---

## Orden estratégico (importante)

Hacé las cosas en este orden, NO al revés:

1. **HOY** — Parte A.1 y A.2: solicitar el Developer Token de Google Ads. Es lo único que tarda 1–3 días hábiles. Cuanto antes lo pidas, antes te aprueban.
2. **HOY** — Parte B completa: META. Se cierra en 30–60 min.
3. **CUANDO TE APRUEBEN GOOGLE** (te llega un mail) — Partes A.3 a A.5.

---

# PARTE A — Google Ads

## A.1 Solicitar Developer Token (10 min de trabajo + espera de Google)

El "Developer Token" es la llave que Google le da a tu MCC para usar la API. Se pide una sola vez por cuenta.

1. Logueate en https://ads.google.com con la cuenta que es admin del MCC (la cuenta "manager" que ve todas las cuentas de los clientes).
2. Click en el ícono de herramienta arriba a la derecha (🔧) → **API Center** (en español puede aparecer como "Centro de API").
   - Si no te aparece "API Center" en el menú, **es porque NO estás en la cuenta MCC**. Cambiá al MCC desde el selector de cuenta arriba a la derecha.
3. Vas a ver un formulario que pide:
   - **Company / Business name:** `Nexiu`
   - **Website:** `https://nexiu.ai` (o el que tengas)
   - **Contact email:** tu mail @nexiu.ai
   - **Use case / business model:** elegí "Internal use" o "Manage own ads accounts"
   - **API tools you'll use:** "Google Ads API"
   - **Tools you've built in the past:** elegí "None" o algo simple. No te bloquea.
4. Aceptá los términos y enviá.
5. **Inmediatamente** te devuelve un Developer Token con etiqueta **"Test Access"**. Ese token funciona pero solo lee cuentas de test (sirve para empezar a desarrollar pero no para tu data real).
6. **En el mismo formulario** vas a ver un botón **"Apply for Basic access"**. Hacelo ahora — esto inicia la revisión humana de Google que tarda 1–3 días hábiles. Hasta que no te aprueben Basic access, no podés leer tu cuenta real.

> **Anotá en tu archivo de notas:** `GOOGLE_ADS_DEVELOPER_TOKEN = "..."` (te lo muestran en el API Center una vez aprobado).

---

## A.2 Habilitar Google Ads API en tu proyecto Cloud (3 min)

Esto ya lo deberías tener hecho de Fase 0, pero confirmalo:

1. https://console.cloud.google.com → seleccioná el proyecto **nexiu-ops-poc**.
2. Menú (☰) → **APIs & Services** → **Enabled APIs & services**.
3. Si **Google Ads API** aparece en la lista, perfecto. Si no, hacé click en **+ Enable APIs and Services** arriba, buscá "Google Ads API" y habilitala.

---

## A.3 Crear OAuth 2.0 Client ID (10 min)

Esto es lo que le da identidad al script ETL cuando habla con Google Ads.

1. En Google Cloud Console → **APIs & Services** → **Credentials**.
2. Si arriba te dice "Configure consent screen first", hacelo:
   - **User Type:** Internal (porque sos Workspace).
   - **App name:** `Nexiu Ops ETL`
   - **User support email:** tu mail @nexiu.ai
   - **Developer contact:** tu mail @nexiu.ai
   - Save and continue. En "Scopes" agregá `.../auth/adwords` y `.../auth/spreadsheets`. Save.
3. Volvé a **Credentials** → **+ Create Credentials** → **OAuth client ID**.
4. **Application type:** **Desktop app**.
5. **Name:** `nexiu-etl-desktop`.
6. **Create**.
7. Te muestra un popup con `Client ID` y `Client secret`. Click en **Download JSON** y guardalo como `oauth_client.json` en la misma carpeta donde vas a correr el script de la sección A.4.

> **Anotá:**
> - `GOOGLE_ADS_CLIENT_ID = "..."`
> - `GOOGLE_ADS_CLIENT_SECRET = "..."`

---

## A.4 Generar el Refresh Token (15 min, lo hacés UNA SOLA VEZ en tu compu)

El refresh token es lo que permite al script ETL re-autenticarse automáticamente sin que vos te tengas que loguear cada 6 horas.

Te dejé un script `setup_scripts/generate_google_refresh_token.py` listo en esta carpeta del proyecto. Procedimiento:

1. Abrí Terminal y andá a la carpeta del proyecto:
   ```bash
   cd "/Users/federiconaides/Documents/Claude/Projects/DASHBOARD FULLSTACK/setup_scripts"
   ```
2. Asegurate de tener Python 3 instalado: `python3 --version` (debería dar 3.10+).
3. Instalá la dependencia (una sola vez):
   ```bash
   pip install --user google-auth-oauthlib
   ```
4. Movele el `oauth_client.json` que descargaste en A.3 a esta misma carpeta.
5. Corré el script:
   ```bash
   python3 generate_google_refresh_token.py
   ```
6. El script abre tu navegador → te pide loguearte con tu cuenta de Google que tiene acceso al MCC → autorizás los scopes que pide la app.
7. Cuando vuelvas a la terminal vas a ver impreso el `refresh_token`.

> **Anotá:** `GOOGLE_ADS_REFRESH_TOKEN = "1//0..."` (es un string largo).

> **Importante:** este refresh token NO expira mientras no lo revoces, pero **es como un password**. No lo subas a GitHub público, no lo pegues en chats. Va directo a GitHub Secrets en Fase 3.

---

## A.5 Anotar el Customer ID (1 min)

El "Customer ID" es el número de cuenta de Google Ads que querés leer.

1. En https://ads.google.com, arriba a la derecha vas a ver un número en formato `123-456-7890`. Ese es tu Customer ID.
2. **Si tenés MCC:** anotá el ID **del MCC** (la cuenta manager) — el ETL va a usar el MCC como "login" y especificar qué cuenta hijo leer en cada query.
3. Si manejás varias cuentas hijas (una por cliente), anotá también esos IDs por separado.

> **Anotá:**
> - `GOOGLE_ADS_LOGIN_CUSTOMER_ID = "1234567890"` (sin guiones, el ID del MCC)
> - `GOOGLE_ADS_CUSTOMER_IDS = "1112223334,4445556667"` (sin guiones, separados por coma — los IDs de las cuentas hijas que querés leer)

---

# PARTE B — META Marketing API

## B.1 Crear una app en Meta for Developers (10 min)

1. Andá a https://developers.facebook.com con tu cuenta personal (la que es admin del Meta Business).
2. **My Apps** (arriba a la derecha) → **Create App**.
3. **Use case:** elegí **"Other"** y después **"Business"**. (Si te aparece "Manage business integrations" elegí esa).
4. **App name:** `Nexiu Ops ETL`.
5. **App contact email:** tu mail @nexiu.ai.
6. **Business Account:** seleccioná el Business Manager que tiene la cuenta de ads de Nexiu. Si no aparece, asegurate de estar logueado con la cuenta de admin.
7. Create. La app queda en "Development mode" — está bien para nuestro caso de uso interno.

---

## B.2 Agregar el caso de uso "Crear y administrar anuncios con la API de Marketing" (2 min)

> **Nota:** la UI de Meta cambió. Lo que antes era "Add products → Marketing API" ahora se maneja desde "Casos de uso".

1. En el dashboard de la app, menú lateral izquierdo → **Casos de uso**.
2. Click **Agregar casos de uso**.
3. Filtrar por **"Anuncios y monetización"** y elegir **"Crear y administrar anuncios con la API de Marketing"**. (Si no aparece, probar también el filtro "Otros" → "Crear una app sin un caso de uso" y agregar Marketing API a mano).
4. Una vez agregado, click en el **lápiz (✏️)** que aparece a la derecha de la card del caso de uso.
5. Confirmá que entre los permisos disponibles estén tildados:
   - `ads_read`
   - `business_management`

---

## B.3 Generar un Access Token con scope `ads_read` (10 min)

> **Nota:** la opción antigua "Marketing API → Tools" ya no existe. Ahora se genera desde el Graph API Explorer.

1. Andá a https://developers.facebook.com/tools/explorer/
2. En el panel derecho, en **"App de Meta"**, seleccioná **"Nexiu Ops ETL"**.
3. En **"Usuario o página"** elegí **"Obtener token (User Access Token)"**.
4. En la sección **"Permisos"**, agregá tildando estos dos:
   - `ads_read`
   - `business_management`
5. Click **"Generate Access Token"** (botón azul).
6. Te abre una ventana de Facebook pidiéndote loguearte y aceptar los scopes. Aceptá.
7. Vuelve al Explorer y el campo "Token de acceso" se llena con el string largo (`EAA...`). **Copialo a tu archivo de notas inmediatamente** — dura solo ~1 hora, en el siguiente paso lo extendemos.

---

## B.4 Convertir a Long-Lived Token (60 días) (5 min)

1. Andá a https://developers.facebook.com/tools/debug/accesstoken/
2. Pegá el token de B.3 en el campo y click **Debug**.
3. Vas a ver detalles del token. Buscá el botón **"Extend Access Token"** abajo.
4. Click ahí — te genera un token nuevo que dura ~60 días.
5. Copialo. **Este es el `META_ACCESS_TOKEN` que usamos en el ETL.**

> **Anotá:** `META_ACCESS_TOKEN = "EAA..."` (string largo).

> **Calendar reminder:** poné un recordatorio en tu calendario en 50 días. Antes de que el token expire (día 60), tenés que volver acá y extenderlo de nuevo. Para producción esto se automatiza, pero para POC con recordatorio alcanza.

---

## B.5 Anotar el Ad Account ID (1 min)

1. https://business.facebook.com/settings/ad-accounts (asegurate de estar en el Business correcto arriba a la izquierda).
2. Click en la cuenta de ads de Nexiu.
3. El ID aparece arriba, formato `1234567890123456`.

> **Anotá:** `META_AD_ACCOUNT_ID = "act_1234567890123456"` (con prefijo `act_`).

---

# Checklist final de Fase 1

Cuando termines, mandame estos 8 valores (los voy a guardar como GitHub Secrets en Fase 3, así que pasámelos en un mensaje seguro):

**De Google Ads:**

- [ ] `GOOGLE_ADS_DEVELOPER_TOKEN`
- [ ] `GOOGLE_ADS_CLIENT_ID`
- [ ] `GOOGLE_ADS_CLIENT_SECRET`
- [ ] `GOOGLE_ADS_REFRESH_TOKEN`
- [ ] `GOOGLE_ADS_LOGIN_CUSTOMER_ID` (el del MCC)
- [ ] `GOOGLE_ADS_CUSTOMER_IDS` (las cuentas hijas que querés leer)

**De META:**

- [ ] `META_ACCESS_TOKEN`
- [ ] `META_AD_ACCOUNT_ID`

**Plus, los datos pendientes de Fase 0** (creo que ya los tenés pero confirmame):

- [ ] `SHEET_ID`
- [ ] Service account email (`etl-writer@...iam.gserviceaccount.com`)

Con eso pasamos a Fase 2: escribir el ETL en Python.

---

# Errores comunes

**"No me aparece API Center en el menú de Google Ads"** — Estás en una cuenta hija, no en el MCC. Cambiá al MCC con el selector arriba a la derecha.

**"Google Ads me dijo que rechazó mi solicitud de Basic Access"** — Suele pasar por respuestas vagas en el formulario. Reaplicá detallando: "Use the API to read campaign performance data (cost, impressions, clicks) for internal reporting in our HR-tech company that manages talent attraction campaigns for clients." Suele aprobarse en el segundo intento.

**"El access token de Meta dice que ya expiró cuando trato de extenderlo"** — Pasaron más de 1 hora desde que lo generaste. Volvé a B.3 y regeneralo, después extendelo inmediatamente.

**"No puedo crear la app en Meta porque no tengo Business Manager"** — Si tu cuenta de ads vive en una cuenta personal y no en un Business, primero tenés que crear un Business Manager (https://business.facebook.com/overview) y migrar la cuenta de ads ahí. Es 10 min adicionales y es highly recommended para producción.

**"El refresh token de Google sigue sin generarse después del flow de OAuth"** — Asegurate que el `oauth_client.json` esté en la misma carpeta que el script. Si el navegador se cuelga, abrí la URL manualmente que imprime el script en consola.
