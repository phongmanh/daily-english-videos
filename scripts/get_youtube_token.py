"""Run this ONCE on your own computer to get YT_REFRESH_TOKEN.

  pip install google-auth-oauthlib
  python scripts/get_youtube_token.py path/to/client_secret.json

A browser window opens: sign in and choose the "Daily English" channel (Brand Account).
The refresh token is printed. Put it in GitHub Secrets as YT_REFRESH_TOKEN. Never commit it.
"""
import json, sys
from google_auth_oauthlib.flow import InstalledAppFlow

if len(sys.argv) != 2:
    sys.exit(__doc__)
flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], scopes=["https://www.googleapis.com/auth/youtube.upload"])
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
cs = json.load(open(sys.argv[1]))
cs = cs.get("installed") or cs.get("web")
print("\nAdd these three GitHub Secrets:\n")
print("YT_CLIENT_ID     =", cs["client_id"])
print("YT_CLIENT_SECRET =", cs["client_secret"])
print("YT_REFRESH_TOKEN =", creds.refresh_token)
