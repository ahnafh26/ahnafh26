"""Rewrite the <!--now:start--> ... <!--now:end--> block in README.md
and draw the mini Spotify player at assets/now-playing.svg."""
import base64
import html
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date

START_YEAR = 2026  # first fall term at uwaterloo / laurier
README = "README.md"
CARD = "assets/now-playing.svg"
PLAYER_RE = re.compile(r'<a href="[^"]*"><img src="assets/now-playing\.svg[^>]*></a>')


def clean(msg, limit=60):
    msg = msg.strip().splitlines()[0] if msg.strip() else ""
    msg = re.sub(r"[`*_\[\]<>|]", "", msg)  # keep markdown from breaking
    return msg if len(msg) <= limit else msg[: limit - 1].rstrip() + "…"


def fetch(url, headers=None, data=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read()


def spotify_track():
    """Now playing, else last played. Needs SPOTIFY_CLIENT_ID/SECRET/REFRESH_TOKEN."""
    cid = os.environ.get("SPOTIFY_CLIENT_ID")
    secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    refresh = os.environ.get("SPOTIFY_REFRESH_TOKEN")
    if not (cid and secret and refresh):
        return None
    body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": refresh}).encode()
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    _, raw = fetch(
        "https://accounts.spotify.com/api/token",
        {"Authorization": "Basic " + auth, "Content-Type": "application/x-www-form-urlencoded"},
        body,
    )
    token = json.loads(raw)["access_token"]

    def get(path):
        status, raw = fetch(f"https://api.spotify.com/v1{path}", {"Authorization": f"Bearer {token}"})
        return json.loads(raw) if status == 200 and raw else None  # 204 = nothing playing

    item, playing, progress = None, False, None
    cur = get("/me/player/currently-playing")
    if cur and cur.get("is_playing") and (cur.get("item") or {}).get("type") == "track":
        item, playing, progress = cur["item"], True, cur.get("progress_ms")
    else:
        recent = get("/me/player/recently-played?limit=1") or {}
        if recent.get("items"):
            item = recent["items"][0]["track"]
    if not item:
        return None

    images = (item.get("album") or {}).get("images") or []
    # smallest image that is still sharp at 2x of the 76px art slot
    images = sorted(images, key=lambda i: i.get("width") or 0)
    art = next((i for i in images if (i.get("width") or 0) >= 160), images[-1] if images else None)
    return {
        "song": item["name"],
        "artist": ", ".join(a["name"] for a in item.get("artists", [])[:2]),
        "url": (item.get("external_urls") or {}).get("spotify", ""),
        "art": art["url"] if art else None,
        "playing": playing,
        "progress": progress,
        "duration": item.get("duration_ms") or 0,
    }


def mmss(ms):
    s = int(ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


def short(text, limit):
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def render_card(t):
    """A small dark player card. Everything is inlined, since GitHub blocks
    external images and fonts inside SVGs."""
    art = ""
    if t["art"]:
        try:
            _, raw = fetch(t["art"])
            art = "data:image/jpeg;base64," + base64.b64encode(raw).decode()
        except Exception as e:
            print(f"album art failed: {e}")

    duration = t["duration"]
    progress = t["progress"] if t["playing"] and t["progress"] is not None else duration
    frac = max(0.0, min(1.0, progress / duration)) if duration else 1.0
    bar_w = 254
    label = "NOW PLAYING" if t["playing"] else "LAST PLAYED"
    song = html.escape(short(t["song"], 30))
    artist = html.escape(short(t["artist"], 38))

    # equalizer bars: they bounce while a song is playing and sit still otherwise
    eq = []
    for i, (lo, hi, dur) in enumerate([(3, 11, 0.9), (5, 13, 0.7), (2, 9, 1.1), (4, 12, 0.8)]):
        x = 392 + i * 5
        if t["playing"]:
            eq.append(
                f'<rect x="{x}" y="{26 - hi}" width="3" height="{hi}" rx="1.5" fill="#1ed760">'
                f'<animate attributeName="height" values="{lo};{hi};{lo}" dur="{dur}s" repeatCount="indefinite"/>'
                f'<animate attributeName="y" values="{26 - lo};{26 - hi};{26 - lo}" dur="{dur}s" repeatCount="indefinite"/>'
                f"</rect>"
            )
        else:
            eq.append(f'<rect x="{x}" y="{26 - lo}" width="3" height="{lo}" rx="1.5" fill="#6a6a6a"/>')

    art_tag = (
        f'<image href="{art}" x="14" y="14" width="76" height="76" clip-path="url(#art)" preserveAspectRatio="xMidYMid slice"/>'
        if art
        else '<rect x="14" y="14" width="76" height="76" rx="8" fill="#2a2a2a"/>'
    )
    accent = "#1ed760" if t["playing"] else "#b3b3b3"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="420" height="104" viewBox="0 0 420 104" role="img" aria-label="{label.lower()}: {song} by {artist}">
  <defs>
    <clipPath id="art"><rect x="14" y="14" width="76" height="76" rx="8"/></clipPath>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1f1f1f"/>
      <stop offset="1" stop-color="#121212"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }}
    .label {{ font-size: 9.5px; font-weight: 700; letter-spacing: 1.6px; fill: {accent}; }}
    .song {{ font-size: 15px; font-weight: 700; fill: #ffffff; }}
    .artist {{ font-size: 12.5px; fill: #b3b3b3; }}
    .time {{ font-size: 9.5px; fill: #8a8a8a; font-variant-numeric: tabular-nums; }}
  </style>
  <rect width="420" height="104" rx="14" fill="url(#bg)"/>
  <rect x="0.5" y="0.5" width="419" height="103" rx="13.5" fill="none" stroke="#ffffff" stroke-opacity="0.06"/>
  {art_tag}
  <text x="106" y="27" class="label">{label}</text>
  {"".join(eq)}
  <text x="106" y="50" class="song">{song}</text>
  <text x="106" y="67" class="artist">{artist}</text>
  <rect x="106" y="80" width="{bar_w}" height="3" rx="1.5" fill="#3e3e3e"/>
  <rect x="106" y="80" width="{bar_w * frac:.1f}" height="3" rx="1.5" fill="{accent}"/>
  <circle cx="{106 + bar_w * frac:.1f}" cy="81.5" r="4" fill="#ffffff"/>
  <text x="406" y="84.5" class="time" text-anchor="end">{mmss(duration)}</text>
</svg>
"""


def year_of_study(today=None):
    today = today or date.today()
    # the school year starts in september
    return today.year - START_YEAR + (1 if today.month >= 9 else 0)


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def build_block(old_block):
    lines = [f"📍 {ordinal(year_of_study())} year @ uwaterloo × laurier"]
    try:
        t = spotify_track()
    except Exception as e:
        print(f"spotify lookup failed: {e}")
        t = None
    if t:
        os.makedirs(os.path.dirname(CARD), exist_ok=True)
        with open(CARD, "w", encoding="utf-8") as f:
            f.write(render_card(t))
        alt = html.escape(f"{'listening to' if t['playing'] else 'last played'}: {clean(t['song'])} by {clean(t['artist'])}")
        lines.append(f'<a href="{html.escape(t["url"])}"><img src="{CARD}" alt="{alt}" width="420"></a>')
    else:
        keep = PLAYER_RE.search(old_block)  # spotify hiccup: keep the last card
        if keep:
            lines.append(keep.group(0))
    return "\n\n".join(lines)


def main():
    text = open(README, encoding="utf-8").read()
    m = re.search(r"(<!--now:start-->\n)(.*?)(\n<!--now:end-->)", text, flags=re.S)
    new = text[: m.start(2)] + build_block(m.group(2)) + text[m.end(2) :]
    if new != text:
        open(README, "w", encoding="utf-8").write(new)
        print("README updated")
    else:
        print("no change")


if __name__ == "__main__":
    main()
