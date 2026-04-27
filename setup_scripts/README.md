# Setup Scripts

Scripts que corrés **localmente en tu compu** una sola vez como parte del setup del POC.

No van al repo de GitHub del ETL — son helpers de bootstrapping.

## Archivos

- `generate_google_refresh_token.py` — Genera el refresh token de Google Ads. Ver Fase 1, sección A.4 de la guía.

## Cómo correrlos

```bash
cd "/Users/federiconaides/Documents/Claude/Projects/DASHBOARD FULLSTACK/setup_scripts"
pip install --user google-auth-oauthlib
python3 generate_google_refresh_token.py
```

## Qué NO subir a GitHub

- `oauth_client.json` — credenciales de OAuth client (no son secretas pero tampoco públicas)
- `etl-service-account.json` — la key del service account, esto SÍ es secret
- Cualquier output con tokens generados

Todos esos van directo a GitHub Secrets en Fase 3, no al repo.
