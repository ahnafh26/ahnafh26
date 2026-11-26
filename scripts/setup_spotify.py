"""One-time Spotify setup. Run on your own computer from the repo folder:

    python scripts/setup_spotify.py

Paste your Client ID and Client Secret when asked,
log in to Spotify in the browser that opens, and the three GitHub secrets
are saved for you. Nothing is printed or written to disk.
"""
import base64
import http.server
import json
import subprocess
import urllib.parse
import urllib.request
import webbrowser

REPO = "ahnafh26/ahnafh26"
REDIRECT = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-currently-playing user-read-recently-played"

cid = input("Spotify Client ID: ").strip()
secret = input("Spotify Client Secret: ").strip()
code = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code["value"] = q.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"done - you can close this tab and go back to the terminal")

    def log_message(self, *a):
        pass


url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(
    {"client_id": cid, "response_type": "code", "redirect_uri": REDIRECT, "scope": SCOPES}
)
print("Opening Spotify login in your browser...")
webbrowser.open(url)
http.server.HTTPServer(("127.0.0.1", 8888), Handler).handle_request()
if not code.get("value"):
    raise SystemExit("Spotify login was cancelled or failed. Run this again.")

body = urllib.parse.urlencode(
    {"grant_type": "authorization_code", "code": code["value"], "redirect_uri": REDIRECT}
).encode()
req = urllib.request.Request("https://accounts.spotify.com/api/token", data=body)
req.add_header("Authorization", "Basic " + base64.b64encode(f"{cid}:{secret}".encode()).decode())
with urllib.request.urlopen(req) as r:
    refresh = json.load(r)["refresh_token"]

for name, value in [
    ("SPOTIFY_CLIENT_ID", cid),
    ("SPOTIFY_CLIENT_SECRET", secret),
    ("SPOTIFY_REFRESH_TOKEN", refresh),
]:
    subprocess.run(["gh", "secret", "set", name, "-R", REPO], input=value, text=True, check=True)
    print(f"saved {name}")

subprocess.run(["gh", "workflow", "run", "now.yml", "-R", REPO], check=True)
print("\nAll set. Your profile will show your song in about a minute.")
