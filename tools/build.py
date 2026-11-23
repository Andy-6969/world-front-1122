"""Fill the placeholders in src/front.html and write out/front.html.

- {{WORLD_LAND}}: coastlines from Natural Earth's ne_110m_land.geojson (public domain), read from the
  folder named by the NE_DIR environment variable (not committed), projected equirectangular onto the
  300 x 138 map box and thinned to points at least 0.9 px apart.
- {{WORLD_PINS}}: one numbered pin per lead and card story, coloured by region.
- {{SEAT_ARC}}: the House as a half circle of 435 seats, the first 258 filled for the Democrats.
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NE = os.environ.get("NE_DIR")
if not NE:
    sys.exit("set NE_DIR to a folder holding ne_110m_land.geojson")

REGION = {"eu": "#2459a6", "me": "#b3261e", "af": "#c06a00", "as": "#17806a",
          "am": "#6b3fa0", "oc": "#0b7896", "gl": "#3d4450"}

# story number -> (lon, lat, region); numbers match the page
PINS = {
    1: (30.7, 36.9, "gl"),     # Antalya
    2: (20.07, 32.12, "af"),   # Benghazi
    3: (30.4, 50.8, "eu"),     # Dymer, Kyiv region
    4: (-77.0, 38.9, "am"),    # Washington
    5: (114.17, 22.3, "as"),   # Hong Kong
    6: (126.98, 37.57, "as"),  # Seoul
    7: (106.15, -6.12, "as"),  # Serang, Banten
    8: (32.53, 15.5, "af"),    # Khartoum
    9: (30.25, 1.56, "af"),    # Ituri
    10: (34.84, 32.16, "me"),  # Herzliya
    11: (7.68, 45.07, "eu"),   # Turin
    12: (-8.54, 37.14, "eu"),  # Portimao
    13: (174.78, -41.29, "oc"),  # Wellington
}
# small nudges (px) so pins in crowded spots do not cover each other
NUDGE = {1: (2, 6), 2: (-7, 2), 3: (3, -5), 10: (6, 5), 11: (-1, -7), 12: (-6, 2), 8: (3, 3), 9: (-2, 5),
         5: (-4, 4), 6: (2, -4)}


def rings(geom):
    if geom["type"] == "Polygon":
        yield from geom["coordinates"]
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            yield from poly


def projector(lon0, lon1, lat0, lat1, width, height):
    """Equirectangular box: lon0..lon1 fills the width, latitude keeps true proportions."""
    k = math.cos(math.radians((lat0 + lat1) / 2))
    s = width / ((lon1 - lon0) * k)
    top = (lat0 + lat1) / 2 + height / s / 2

    def p(lon, lat):
        return (lon - lon0) * k * s, (top - lat) * s

    return p


def land_path(features, proj, box, min_step):
    w, h = box
    out = []
    for f in features:
        for ring in rings(f["geometry"]):
            pts = [proj(lon, lat) for lon, lat in ring]
            xs = [x for x, _ in pts]
            ys = [y for _, y in pts]
            if max(xs) < -5 or min(xs) > w + 5 or max(ys) < -5 or min(ys) > h + 5:
                continue
            keep = [pts[0]]
            for x, y in pts[1:]:
                lx, ly = keep[-1]
                if abs(x - lx) + abs(y - ly) >= min_step:
                    keep.append((x, y))
            if len(keep) < 3:
                continue
            out.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in keep) + "Z")
    return "".join(out)


def pins_svg(proj):
    out = []
    for n, (lon, lat, reg) in sorted(PINS.items()):
        x, y = proj(lon, lat)
        dx, dy = NUDGE.get(n, (0, 0))
        x, y = x + dx, y + dy
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.4" fill="{REGION[reg]}" stroke="#fff" stroke-width="1.2"/>'
                   f'<text x="{x:.1f}" y="{y + 2.9:.1f}" font-family="Bahnschrift" font-weight="700" '
                   f'font-size="{7 if n >= 10 else 8}" fill="#fff" text-anchor="middle">{n}</text>')
    return "".join(out)


def seat_arc(won=258, total=435, cx=50, cy=60, r_out=44, r_in=22):
    """The House as a half ring: the Democrats' 258 of 435 seats in blue from the left, the rest pale red,
    with a white tick at the 218-seat majority line."""

    def pt(a, r):
        return cx - r * math.cos(a), cy - r * math.sin(a)

    def band(a0, a1, fill):
        x0, y0 = pt(a0, r_out)
        x1, y1 = pt(a1, r_out)
        x2, y2 = pt(a1, r_in)
        x3, y3 = pt(a0, r_in)
        big = 1 if a1 - a0 > math.pi else 0
        return (f'<path d="M{x0:.1f},{y0:.1f} A{r_out},{r_out} 0 {big} 1 {x1:.1f},{y1:.1f} '
                f'L{x2:.1f},{y2:.1f} A{r_in},{r_in} 0 {big} 0 {x3:.1f},{y3:.1f} Z" fill="{fill}"/>')

    split = math.pi * won / total
    tick = math.pi * 218 / total
    tx0, ty0 = pt(tick, r_in - 3)
    tx1, ty1 = pt(tick, r_out + 3)
    return (band(0, split, "#2a4ea8") + band(split, math.pi, "#d9a0a0")
            + f'<path d="M{tx0:.1f},{ty0:.1f} L{tx1:.1f},{ty1:.1f}" stroke="#fff" stroke-width="2"/>')


def main():
    ww, wh = 300, 138
    world = projector(-170, 180, -56, 76, ww, wh)
    with open(os.path.join(NE, "ne_110m_land.geojson"), encoding="utf-8") as fh:
        land = json.load(fh)["features"]
    land = [f for f in land if min(lat for r in rings(f["geometry"]) for _, lat in r) > -60]

    with open(os.path.join(ROOT, "src", "front.html"), encoding="utf-8") as fh:
        page = fh.read()
    page = (page.replace("{{WORLD_LAND}}", land_path(land, world, (ww, wh), 0.9))
                .replace("{{WORLD_PINS}}", pins_svg(world))
                .replace("{{SEAT_ARC}}", seat_arc()))
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    with open(os.path.join(ROOT, "out", "front.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    print("out/front.html:", len(page), "chars")


if __name__ == "__main__":
    main()
