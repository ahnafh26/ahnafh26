"""Draw the tech stack card at assets/stack.svg, styled like the Spotify card.

Run it again after editing STACK:  python scripts/stack.py
Logos come from the Simple Icons set (CC0).
"""
import re
import urllib.request

OUT = "assets/stack.svg"
ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@13.0.0/icons/{}.svg"

# (name, simple-icons slug, logo color, brightened where the brand color is too dark on the card)
STACK = [
    ("Python", "python", "#5A9FD4"),
    ("TypeScript", "typescript", "#4A8FE0"),
    ("React", "react", "#61DAFB"),
    ("Next.js", "nextdotjs", "#FFFFFF"),
    ("FastAPI", "fastapi", "#19B3A3"),
    ("Node.js", "nodedotjs", "#6CC24A"),
    ("PostgreSQL", "postgresql", "#6A8BEF"),
    ("Git", "git", "#F05032"),
]

W, PAD, GAP = 420, 14, 8
PILL_H, ICON, FONT = 30, 14, 12.5
TOP = 40  # space for the label


def text_width(s):
    # rough width for a semibold system sans at FONT px; no font metrics in an SVG
    narrow, wide = set("ilj.ft"), set("mwMW")
    return 0.9 * sum(FONT * (0.3 if c in narrow else 0.85 if c in wide else 0.62 if c.isupper() else 0.56) for c in s)


def icon_path(slug):
    with urllib.request.urlopen(ICONS.format(slug), timeout=20) as r:
        svg = r.read().decode()
    return re.search(r'<path d="([^"]+)"', svg).group(1)


def main():
    pills, x, y = [], PAD, TOP
    for name, slug, color in STACK:
        w = 10 + ICON + 7 + text_width(name) + 12
        if x + w > W - PAD:
            x, y = PAD, y + PILL_H + GAP
        s = ICON / 24
        pills.append(
            f'<g transform="translate({x:.1f},{y})">'
            f'<rect width="{w:.1f}" height="{PILL_H}" rx="8" fill="#ffffff" fill-opacity="0.06" stroke="#ffffff" stroke-opacity="0.06"/>'
            f'<path transform="translate(10,{(PILL_H - ICON) / 2}) scale({s:.4f})" fill="{color}" d="{icon_path(slug)}"/>'
            f'<text x="{10 + ICON + 7}" y="{PILL_H / 2 + 4.4}" class="name">{name}</text>'
            f"</g>"
        )
        x += w + GAP
    h = y + PILL_H + PAD

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="tech stack: {', '.join(n for n, _, _ in STACK)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1f1f1f"/>
      <stop offset="1" stop-color="#121212"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }}
    .label {{ font-size: 9.5px; font-weight: 700; letter-spacing: 1.6px; fill: #b3b3b3; }}
    .name {{ font-size: {FONT}px; font-weight: 600; fill: #e8e8e8; }}
  </style>
  <rect width="{W}" height="{h}" rx="14" fill="url(#bg)"/>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="13.5" fill="none" stroke="#ffffff" stroke-opacity="0.06"/>
  <text x="{PAD + 2}" y="26" class="label">TECH STACK</text>
  {"".join(pills)}
</svg>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
