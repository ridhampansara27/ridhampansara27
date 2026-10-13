#!/usr/bin/env python3
"""Generate the animated terminal/neofetch-style profile information card."""
from __future__ import annotations

import html
import os
from pathlib import Path

OUTPUT = Path("assets/info-card.svg")
STATIC = os.getenv("STATIC") == "1"
ROWS = [
    ("role", "Cloud & DevOps Engineering"),
    ("study", "M.Sc. Computer Engineering for IoT Systems"),
    ("current", "CloudOps Insight"),
    ("focus", "Kubernetes · Terraform · GitOps"),
    ("cloud", "AWS · OCI · Azure · GCP"),
    ("automation", "GitHub Actions · Jenkins · Argo CD"),
    ("code", "Python · TypeScript · Bash"),
    ("status", "Open to Thesis · Internship · Working Student"),
]

def main() -> None:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="500" height="340" viewBox="0 0 500 340" role="img" aria-labelledby="title desc">',
        '<title id="title">Ridham Pansara terminal profile card</title>',
        '<desc id="desc">A terminal-style card summarizing cloud, DevOps, education and career focus.</desc>',
        '<rect width="100%" height="100%" rx="14" fill="#0d1117" stroke="#30363d"/>',
        '<rect x="16" y="14" width="8" height="8" rx="4" fill="#ff5f56"/>',
        '<rect x="30" y="14" width="8" height="8" rx="4" fill="#ffbd2e"/>',
        '<rect x="44" y="14" width="8" height="8" rx="4" fill="#27c93f"/>',
        '<text x="250" y="22" text-anchor="middle" fill="#8b949e" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-size="10">whoami</text>',
        '<text x="24" y="54" fill="#58a6ff" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-weight="700" font-size="17">RIDHAM PANSARA</text>',
        '<text x="24" y="75" fill="#3fb950" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-size="11">cloud-native • automation • platform engineering</text>',
    ]

    y = 108
    for i, (key, value) in enumerate(ROWS):
        delay = 0 if STATIC else 0.18 + i * 0.10
        opacity = "1" if STATIC else "0"
        parts.append(f'<g opacity="{opacity}" transform="translate(0 4)">')
        if not STATIC:
            parts.append(f'<animate attributeName="opacity" from="0" to="1" dur="0.24s" begin="{delay:.2f}s" fill="freeze"/>')
            parts.append(f'<animateTransform attributeName="transform" type="translate" from="0 4" to="0 0" dur="0.24s" begin="{delay:.2f}s" fill="freeze"/>')
        parts.append(f'<text x="24" y="{y}" fill="#a371f7" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-size="11">{html.escape(key)}</text>')
        parts.append(f'<text x="118" y="{y}" fill="#c9d1d9" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-size="11">{html.escape(value)}</text>')
        parts.append("</g>")
        y += 27

    parts.extend([
        '<line x1="24" y1="306" x2="476" y2="306" stroke="#21262d"/>',
        '<text x="24" y="326" fill="#8b949e" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-size="10">$ build --automate --observe --improve</text>',
        "</svg>",
    ])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\\n".join(parts), encoding="utf-8")
    print(f"wrote {OUTPUT}")

if __name__ == "__main__":
    main()
