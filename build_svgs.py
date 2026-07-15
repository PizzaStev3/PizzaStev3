"""
build_svgs.py — render dark_mode.svg and light_mode.svg in the Andrew6rant
neofetch format: dot-leader right-aligned values, section divider rules, and a
two-column GitHub Stats block.

This module is the single source of truth for the card layout. Two entry points:

    render_all(data)   -> write both SVGs with the given stats (called by today.py)
    python build_svgs.py  -> render both SVGs with placeholder/zero stats (preview)

The dot leaders are recomputed from the actual value lengths every render, so the
columns stay aligned no matter how the live numbers change.
"""

from xml.sax.saxutils import escape

ART_FILE = "ascii-art.txt"
ART_FONT = 6
ART_LINE = 6.8
ART_X = 14
ART_Y = 16

INFO_X = 390
INFO_START_Y = 30
INFO_LINE_H = 20
INFO_FONT = 15

WIDTH = 1000
HEIGHT = 470

# Character-grid widths (monospace). Values are right-aligned to these columns.
PANEL_W = 60          # total width of the info panel, in characters
LCOL_W = 42           # left column width in the two-column stats block
REPOS_FIELD = 13      # sub-field for the Repos/Commits value before the "|"

# ---- Static (editable) card text --------------------------------------------
NAME_HEADER = "ahmed@mohammed"
STATIC = {
    "OS": "Linux, Windows, Kali",
    "Host": "October University for Modern Sciences & Arts - MSA",
    "Skills": "Web App Pentesting, OSINT",
    "Languages.Programming": "Python, C++",
    "Languages.Markup": "HTML, CSS, Markdown",
    "Languages.Real": "English, Arabic",
    "Hobbies.Security": "CTFs, Reading Blogs",
    "Hobbies.Software": "AI Security, Automation",
    "LinkedIn": "ahmed-mohamm3d",
    "Discord": "pizzast3ve",
}

PALETTES = {
    "dark_mode.svg": {
        "bg": "#161b22", "border": "none", "text": "#c9d1d9", "key": "#ffa657",
        "value": "#a5d6ff", "add": "#3fb950", "del": "#f85149", "cm": "#8b949e",
        "dots": "#484f58", "rule": "#484f58", "sec": "#c9d1d9", "ascii": "#7d8590",
    },
    "light_mode.svg": {
        "bg": "#ffffff", "border": "#d0d7de", "text": "#24292f", "key": "#953800",
        "value": "#0a3069", "add": "#116329", "del": "#cf222e", "cm": "#59636e",
        "dots": "#afb8c1", "rule": "#d0d7de", "sec": "#24292f", "ascii": "#57606a",
    },
}


def _len(segs):
    return sum(len(text) for _, text in segs)


def rjust(label, value_segs, width=PANEL_W):
    """label + ': ' + dots + ' ' + value_segs, right-aligned to `width` chars."""
    left = [("key", label), ("cm", ":"), ("cm", " ")]
    right = [("cm", " ")] + value_segs
    dots = max(1, width - _len(left) - _len(right))
    return left + [("dots", "." * dots)] + right


def name_header(name):
    dashn = max(1, PANEL_W - len(name) - 1)
    return [("key", name), ("cm", " "), ("rule", "─" * dashn)]


def section(title):
    dashn = max(1, PANEL_W - 2 - len(title) - 1)
    return [("rule", "─ "), ("sec", title), ("cm", " "), ("rule", "─" * dashn)]


def stats_rows(d):
    # Row 1: Repos {Contributed} | Stars
    part1 = rjust("Repos", [("value", d["repos"])], REPOS_FIELD)
    contrib = [("cm", " {"), ("key", "Contributed"), ("cm", ": "),
               ("value", d["contrib"]), ("cm", "}")]
    left1 = part1 + contrib
    left1 += [("cm", " " * max(1, LCOL_W - _len(left1)))]
    right1 = rjust("Stars", [("value", d["stars"])], PANEL_W - LCOL_W)
    row1 = left1 + right1

    # Row 2: Commits | Followers
    left2 = rjust("Commits", [("value", d["commits"])], REPOS_FIELD)
    left2 += [("cm", " " * max(1, LCOL_W - _len(left2)))]
    right2 = rjust("Followers", [("value", d["followers"])], PANEL_W - LCOL_W)
    row2 = left2 + right2

    # Row 3: Lines of Code (net) ( additions++, deletions-- )
    loc = [("value", d["loc_net"]), ("cm", " ( "), ("add", d["loc_add"]),
           ("add", "++"), ("cm", ", "), ("del", d["loc_del"]), ("del", "--"),
           ("cm", " )")]
    row3 = rjust("Lines of Code on GitHub", loc, PANEL_W)
    return [row1, row2, row3]


def build_rows(d):
    return [
        name_header(NAME_HEADER),
        rjust("OS", [("value", STATIC["OS"])]),
        rjust("Uptime", [("value", d["age"])]),
        rjust("Host", [("value", STATIC["Host"])]),
        rjust("Skills", [("value", STATIC["Skills"])]),
        None,
        rjust("Languages.Programming", [("value", STATIC["Languages.Programming"])]),
        rjust("Languages.Markup", [("value", STATIC["Languages.Markup"])]),
        rjust("Languages.Real", [("value", STATIC["Languages.Real"])]),
        None,
        rjust("Hobbies.Security", [("value", STATIC["Hobbies.Security"])]),
        rjust("Hobbies.Software", [("value", STATIC["Hobbies.Software"])]),
        None,
        section("Contact"),
        rjust("LinkedIn", [("value", STATIC["LinkedIn"])]),
        rjust("Discord", [("value", STATIC["Discord"])]),
        None,
        section("GitHub Stats"),
    ] + stats_rows(d)


def build_art():
    with open(ART_FILE, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    tspans = []
    for i, line in enumerate(lines):
        dy = "0" if i == 0 else str(ART_LINE)
        tspans.append('    <tspan x="{}" dy="{}">{}</tspan>'.format(
            ART_X, dy, escape(line.rstrip("\n"))))
    return ('  <text class="ascii" x="{}" y="{}" xml:space="preserve" '
            'font-size="{}px">\n{}\n  </text>').format(
        ART_X, ART_Y, ART_FONT, "\n".join(tspans))


def row_to_svg(segs, y, delay):
    tspans = "".join('<tspan class="{}">{}</tspan>'.format(cls, escape(text))
                     for cls, text in segs)
    return ('    <text class="fadein" x="{}" y="{}" style="animation-delay:{:.2f}s" '
            'xml:space="preserve">{}</text>').format(INFO_X, y, delay, tspans)


def write_svg(filename, pal, rows):
    y = INFO_START_Y
    delay = 0.08
    lines = []
    for row in rows:
        if row is None:
            y += INFO_LINE_H
            continue
        lines.append(row_to_svg(row, y, delay))
        y += INFO_LINE_H
        delay += 0.035
    info = "  <g>\n" + "\n".join(lines) + "\n  </g>"

    stroke = "" if pal["border"] == "none" else \
        ' stroke="{}" stroke-width="1"'.format(pal["border"])

    style = """  <style>
    svg {{ font-family: 'Consolas', 'Menlo', 'DejaVu Sans Mono', 'Courier New', monospace; }}
    text {{ fill: {text}; }}
    .ascii {{ fill: {ascii}; white-space: pre; }}
    .key {{ fill: {key}; }}
    .value {{ fill: {value}; }}
    .add {{ fill: {add}; }}
    .del {{ fill: {del}; }}
    .cm  {{ fill: {cm}; }}
    .dots {{ fill: {dots}; }}
    .rule {{ fill: {rule}; }}
    .sec {{ fill: {sec}; }}
    .fadein {{ font-size: {font}px; opacity: 0; animation: fadeIn 0.5s ease-in-out forwards; }}
    @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
  </style>""".format(font=INFO_FONT, **pal)

    svg = """<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none" xmlns="http://www.w3.org/2000/svg">
{style}
  <rect x="0" y="0" width="{w}" height="{h}" rx="6" fill="{bg}"{stroke} />

{art}

{info}
</svg>
""".format(w=WIDTH, h=HEIGHT, style=style, bg=pal["bg"], stroke=stroke,
           art=build_art(), info=info)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", filename)


def _fmt(n):
    return "{:,}".format(int(n))


def render_all(data):
    """data: age (str) + repos/contrib/stars/commits/followers/loc_net/loc_add/loc_del (ints)."""
    d = {
        "age": data.get("age", "XX years, XX months, XX days"),
        "repos": _fmt(data.get("repos", 0)),
        "contrib": _fmt(data.get("contrib", 0)),
        "stars": _fmt(data.get("stars", 0)),
        "commits": _fmt(data.get("commits", 0)),
        "followers": _fmt(data.get("followers", 0)),
        "loc_net": _fmt(data.get("loc_net", 0)),
        "loc_add": _fmt(data.get("loc_add", 0)),
        "loc_del": _fmt(data.get("loc_del", 0)),
    }
    rows = build_rows(d)
    for name, pal in PALETTES.items():
        write_svg(name, pal, rows)


if __name__ == "__main__":
    # Preview render with placeholder stats (Action fills real numbers later).
    render_all({"age": "22 years, 0 months, 9 days"})
