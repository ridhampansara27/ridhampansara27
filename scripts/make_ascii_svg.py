#!/usr/bin/env python3
"""Generate a self-revealing monochrome ASCII portrait SVG from a photo or URL."""
from __future__ import annotations

import argparse
import html
import io
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps
import requests

RAMP = "@%#*+=-:. "

def load_image(input_path: str | None, url: str | None) -> Image.Image:
    if input_path:
        return Image.open(input_path).convert("RGB")
    if url:
        response = requests.get(url, timeout=20, headers={"User-Agent": "github-profile-art/1.0"})
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGB")
    raise SystemExit("Provide either --input or --url")

def cover_crop(image: Image.Image, target_ratio: float = 0.84) -> Image.Image:
    w, h = image.size
    current = w / h
    if current > target_ratio:
        new_w = int(h * target_ratio)
        left = max(0, (w - new_w) // 2)
        return image.crop((left, 0, left + new_w, h))
    new_h = int(w / target_ratio)
    top = max(0, (h - new_h) // 2)
    return image.crop((0, top, w, min(h, top + new_h)))

def to_ascii_lines(image: Image.Image, cols: int = 58, rows: int = 48) -> list[str]:
    gray = ImageOps.grayscale(cover_crop(image))
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = ImageEnhance.Contrast(gray).enhance(1.45)
    gray = gray.resize((cols, rows), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    lines = []
    for y in range(rows):
        chars = []
        for x in range(cols):
            value = pixels[y * cols + x]
            idx = min(len(RAMP) - 1, int(value / 256 * len(RAMP)))
            chars.append(RAMP[idx])
        lines.append("".join(chars).rstrip())
    return lines

def render_svg(lines: list[str], output: Path) -> None:
    width, height = 360, 340
    x0, y0 = 18, 31
    font_size, line_height = 5.65, 6.15
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Animated ASCII portrait of Ridham Pansara</title>',
        '<desc id="desc">A monochrome terminal-style ASCII portrait that reveals row by row.</desc>',
        '<rect width="100%" height="100%" rx="14" fill="#0d1117" stroke="#30363d"/>',
        '<rect x="16" y="14" width="8" height="8" rx="4" fill="#ff5f56"/>',
        '<rect x="30" y="14" width="8" height="8" rx="4" fill="#ffbd2e"/>',
        '<rect x="44" y="14" width="8" height="8" rx="4" fill="#27c93f"/>',
        '<text x="180" y="22" text-anchor="middle" fill="#8b949e" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-size="10">ridham@github:~</text>',
        "<defs>",
    ]
    for i in range(len(lines)):
        y = y0 + i * line_height
        parts.append(
            f'<clipPath id="row{i}"><rect x="{x0}" y="{y-font_size:.2f}" width="0" height="{line_height+1:.2f}">'
            f'<animate attributeName="width" from="0" to="322" dur="0.42s" begin="{i*0.035:.3f}s" fill="freeze"/>'
            '</rect></clipPath>'
        )
    parts.append("</defs>")
    for i, line in enumerate(lines):
        y = y0 + i * line_height
        parts.append(
            f'<text x="{x0}" y="{y:.2f}" clip-path="url(#row{i})" fill="#c9d1d9" '
            f'font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" '
            f'font-size="{font_size}" xml:space="preserve">{html.escape(line)}</text>'
        )
    parts.extend([
        '<text x="18" y="327" fill="#58a6ff" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-size="10">$ portrait --ascii --cloud-native</text>',
        "</svg>",
    ])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\\n".join(parts), encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input")
    source.add_argument("--url")
    parser.add_argument("--output", default="assets/ridham-ascii.svg")
    parser.add_argument("--cols", type=int, default=58)
    parser.add_argument("--rows", type=int, default=48)
    args = parser.parse_args()
    image = load_image(args.input, args.url)
    render_svg(to_ascii_lines(image, args.cols, args.rows), Path(args.output))
    print(f"wrote {args.output}")

if __name__ == "__main__":
    main()
