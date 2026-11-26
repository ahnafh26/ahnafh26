"""Rewrite the <!--now:start--> ... <!--now:end--> block in README.md."""
import base64
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

USER = "ahnafh26"
START_YEAR = 2026  # first fall term at uwaterloo / laurier
README = "README.md"
SKIP_MESSAGES = {"update now"}  # this bot's own commits


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def clean(msg, limit=60):
    msg = msg.strip().splitlines()[0] if msg.strip() else ""
    msg = re.sub(r"[`*_\[\]<>|]", "", msg)  # keep markdown from breaking
    return msg if len(msg) <= limit else msg[: limit - 1].rstrip() + "…"


def latest_commit():
    """Newest public push by USER, skipping this profile repo's bot commits."""
    for ev in api(f"/users/{USER}/events/public?per_page=50"):
        if ev.get("type") != "PushEvent":
            continue
        repo = ev["repo"]["name"]
        p = ev.get("payload", {})
        msg = None
        commits = p.get("commits") or []
        if commits:
            msg = commits[-1].get("message")
        elif p.get("head"):  # newer payloads only carry the head sha
            try:
                msg = api(f"/repos/{repo}/commits/{p['head']}")["commit"]["message"]
            except Exception:
                continue
        msg = clean(msg or "")
        if not msg or msg.lower() in SKIP_MESSAGES:
            continue
        when = datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00"))
        return msg, repo, when
    return None


def spotify_track():
    """Now playing, else last played. Needs SPOTIFY_CLIENT_ID/SECRET/REFRESH_TOKEN."""
    cid = os.environ.get("SPOTIFY_CLIENT_ID")
    secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    refresh = os.environ.get("SPOTIFY_REFRESH_TOKEN")
    if not (cid and secret and refresh):
        return None
    body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": refresh}).encode()
    req = urllib.request.Request("https://accounts.spotify.com/api/token", data=body)
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{cid}:{secret}".encode()).decode())
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=20) as r:
        token = json.load(r)["access_token"]

    def get(path):
        req = urllib.request.Request(f"https://api.spotify.com/v1{path}")
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r) if r.status == 200 else None  # 204 = nothing playing

    item, playing = None, False
    cur = get("/me/player/currently-playing")
    if cur and cur.get("is_playing") and (cur.get("item") or {}).get("type") == "track":
        item, playing = cur["item"], True
    else:
        recent = get("/me/player/recently-played?limit=1") or {}
        if recent.get("items"):
            item = recent["items"][0]["track"]
    if not item:
        return None
    artist = ", ".join(a["name"] for a in item.get("artists", [])[:2])
    url = (item.get("external_urls") or {}).get("spotify", "")
    return clean(item["name"], 40), clean(artist, 30), url, playing


def ago(when):
    days = (datetime.now(timezone.utc) - when).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    return f"{days} days ago"


def year_of_study(today=None):
    today = today or date.today()
    # the school year starts in september
    return today.year - START_YEAR + (1 if today.month >= 9 else 0)


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def build_line():
    parts = []
    try:
        c = latest_commit()
    except Exception as e:  # API hiccup: keep the rest of the line
        print(f"commit lookup failed: {e}")
        c = None
    if c:
        msg, repo, when = c
        name = repo.split("/", 1)[1]
        parts.append(f'⚡ last commit: "{msg}" in [{name}](https://github.com/{repo}) ({ago(when)})')
    try:
        t = spotify_track()
    except Exception as e:
        print(f"spotify lookup failed: {e}")
        t = None
    if t:
        song, artist, url, playing = t
        label = "listening to" if playing else "last played"
        title = f"[{song}]({url})" if url else song
        parts.append(f"🎧 {label}: {title} by {artist}")
    parts.append(f"📍 {ordinal(year_of_study())} year @ uwaterloo × laurier")
    return " · ".join(parts)


def main():
    text = open(README, encoding="utf-8").read()
    new = re.sub(
        r"(<!--now:start-->\n).*?(\n<!--now:end-->)",
        lambda m: m.group(1) + build_line() + m.group(2),
        text,
        flags=re.S,
    )
    if new != text:
        open(README, "w", encoding="utf-8").write(new)
        print("README updated")
    else:
        print("no change")


if __name__ == "__main__":
    main()
