#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter
from pathlib import Path


def normalize_hex(value):
    value = value.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", value):
        return "#" + "".join(ch * 2 for ch in value[1:]).upper()
    if re.fullmatch(r"#[0-9a-f]{6}", value):
        return value.upper()
    return None


def usable(rgb):
    r, g, b = rgb
    if r >= 245 and g >= 245 and b >= 245:
        return False
    if r <= 15 and g <= 15 and b <= 15:
        return False
    return True


def svg_colors(path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    found = []
    for raw in re.findall(r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?", text):
        color = normalize_hex(raw)
        if color:
            rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
            if usable(rgb):
                found.append(color)
    counts = Counter(found)
    return [c for c, _ in counts.most_common(8)]


def raster_colors(path):
    from PIL import Image
    img = Image.open(path).convert("RGBA")
    img.thumbnail((512, 512))
    pixels = []
    data = img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata()
    for r, g, b, a in data:
        if a < 64 or not usable((r, g, b)):
            continue
        # coarse quantization reduces antialiasing noise
        q = tuple(min(255, int(round(v / 16) * 16)) for v in (r, g, b))
        pixels.append(q)
    if not pixels:
        return []
    counts = Counter(pixels)
    return ["#%02X%02X%02X" % rgb for rgb, _ in counts.most_common(8)]


def main():
    ap = argparse.ArgumentParser(description="Derive candidate brand colors from an official logo asset.")
    ap.add_argument("input")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    path = Path(args.input)
    if not path.exists():
        raise SystemExit(f"input not found: {path}")

    colors = svg_colors(path) if path.suffix.lower() == ".svg" else raster_colors(path)
    payload = {
        "status": "Derived" if colors else "Unavailable",
        "source_basis": "OfficialLogoAsset" if colors else "None",
        "primary_color": colors[0] if colors else None,
        "secondary_colors": colors[1:4],
        "accent_colors": colors[4:6],
        "candidate_colors": colors,
        "notes": [
            "Machine-derived candidate palette; review against the official website or brand guide before downstream use."
        ] if colors else ["No usable non-neutral colors could be derived from the asset."],
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
