"""One-time TikTok login. Run on your own computer:

  pip install requests cryptography
  python scripts/get_tiktok_token.py

It opens TikTok in your browser. Log in with the Daily English TikTok account and allow access.
You land on a page that shows a code: copy it and paste it here. The script prints the 4 secrets
to add in GitHub (Settings -> Secrets and variables -> Actions).
"""
import getpass, secrets, sys, urllib.parse, webbrowser
import requests

REDIRECT = "https://phongmanh.github.io/daily-english-videos/tiktok-callback.html"

key = input("TikTok app Client key: ").strip()
secret = getpass.getpass("TikTok app Client secret (hidden): ").strip()
state = secrets.token_urlsafe(16)
url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
    "client_key": key, "response_type": "code", "scope": "user.info.basic,video.upload",
    "redirect_uri": REDIRECT, "state": state})
print("\nOpening TikTok login. If no browser opens, open this link yourself:\n" + url + "\n")
webbrowser.open(url)
code = urllib.parse.unquote(input("Paste the code from the page: ").strip())

r = requests.post("https://open.tiktokapis.com/v2/oauth/token/", timeout=60, data={
    "client_key": key, "client_secret": secret, "code": code,
    "grant_type": "authorization_code", "redirect_uri": REDIRECT})
d = r.json()
if "refresh_token" not in d:
    sys.exit(f"Login failed: {d}")
if "video.upload" not in d.get("scope", ""):
    print(f"Warning: TikTok did not grant video.upload (granted: {d.get('scope')}). Check the app's scopes.")

from cryptography.fernet import Fernet
print("\nAdd these 4 repository secrets in GitHub:\n")
print("TT_CLIENT_KEY     =", key)
print("TT_CLIENT_SECRET  = (the client secret you typed)")
print("TT_REFRESH_TOKEN  =", d["refresh_token"])
print("TT_TOKEN_KEY      =", Fernet.generate_key().decode())
print("\nThe refresh token lasts about a year; the workflow keeps it fresh by itself.")
