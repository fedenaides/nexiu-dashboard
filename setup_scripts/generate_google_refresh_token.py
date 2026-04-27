"""
Generate a Google Ads refresh token for the ETL.

Run this ONCE locally on your computer. It opens a browser, asks you to log in
with your Google account that has access to the Ads MCC, and prints the
refresh_token to stdout.

Save the printed value as the GitHub Secret GOOGLE_ADS_REFRESH_TOKEN later.

Prerequisites:
  pip install --user google-auth-oauthlib

  Place oauth_client.json (downloaded from Google Cloud Console → Credentials
  → OAuth 2.0 Client ID, Desktop app) in the SAME folder as this script.

Usage:
  python3 generate_google_refresh_token.py

If the automatic browser flow doesn't work for any reason (corporate network,
sandboxed env, etc.), the script falls back to printing the URL so you can
open it manually and paste the auth code back.
"""

import json
import os
import sys
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("ERROR: missing dependency. Run:")
    print("  pip install --user google-auth-oauthlib")
    sys.exit(1)


# Scopes needed: Ads API + Sheets API (so the same token can write to the
# warehouse if we ever want to use user creds instead of the service account).
SCOPES = [
    "https://www.googleapis.com/auth/adwords",
    "https://www.googleapis.com/auth/spreadsheets",
]

CLIENT_FILE = Path(__file__).resolve().parent / "oauth_client.json"


def main() -> None:
    if not CLIENT_FILE.exists():
        print(f"ERROR: {CLIENT_FILE} not found.")
        print(
            "Download the OAuth client JSON from Google Cloud Console "
            "(Credentials → your Desktop OAuth client → Download JSON), "
            "rename it to 'oauth_client.json', and place it in this folder."
        )
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)

    try:
        creds = flow.run_local_server(
            port=0,
            prompt="consent",        # force refresh_token to be returned
            access_type="offline",
            authorization_prompt_message=(
                "\nA browser window will open. Log in with the Google account "
                "that has access to your Google Ads MCC and approve the scopes.\n"
            ),
        )
    except Exception as exc:
        print(f"\nLocal server flow failed ({exc}). Falling back to console flow.\n")
        creds = flow.run_console()

    print("\n" + "=" * 60)
    print("SUCCESS. Copy the value below into your notes file as")
    print("GOOGLE_ADS_REFRESH_TOKEN — you'll paste it into GitHub Secrets later.")
    print("=" * 60)
    print(f"\n{creds.refresh_token}\n")
    print("=" * 60)
    print("Also confirm these (should match what's in oauth_client.json):")
    with open(CLIENT_FILE, "r", encoding="utf-8") as fh:
        client_data = json.load(fh)
    installed = client_data.get("installed") or client_data.get("web") or {}
    print(f"  GOOGLE_ADS_CLIENT_ID:     {installed.get('client_id', '(missing)')}")
    print(f"  GOOGLE_ADS_CLIENT_SECRET: {installed.get('client_secret', '(missing)')}")
    print("=" * 60)
    print(
        "\nDo NOT commit this refresh_token to git. It is equivalent to a password.\n"
    )


if __name__ == "__main__":
    main()
