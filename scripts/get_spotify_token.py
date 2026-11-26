"""Run once on your own computer to get SPOTIFY_REFRESH_TOKEN.

1. https://developer.spotify.com/dashboard -> Create app.
   Redirect URI: http://127.0.0.1:8888/callback   (tick "Web API")
2. python scripts/get_spotify_token.py <client_id> <client_secret>
3. Log in in the browser that opens; the refresh token prints here.
"""
import base64
import http.server
import json
import sys
import urllib.parse
import urllib.request
import webbrowser

REDIRECT = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-currently-playing user-read-recently-played"

cid, secret = sys.argv[1], sys.argv[2]
code = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code["value"] = q.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"done - you can close this tab")

    def log_message(self, *a):
        pass


url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(
    {"client_id": cid, "response_type": "code", "redirect_uri": REDIRECT, "scope": SCOPES}
)
print("opening:", url)
webbrowser.open(url)
http.server.HTTPServer(("127.0.0.1", 8888), Handler).handle_request()

body = urllib.parse.urlencode(
    {"grant_type": "authorization_code", "code": code["value"], "redirect_uri": REDIRECT}
).encode()
req = urllib.request.Request("https://accounts.spotify.com/api/token", data=body)
req.add_header("Authorization", "Basic " + base64.b64encode(f"{cid}:{secret}".encode()).decode())
with urllib.request.urlopen(req) as r:
    print("\nSPOTIFY_REFRESH_TOKEN =", json.load(r)["refresh_token"])
