#!/usr/bin/env python3
"""
Builds the animated SVGs used by the profile README.

    pip install fonttools brotli
    python3 scripts/build_assets.py

Edit the CONTENT section, re-run, then commit the files in assets/.

Every SVG comes in a dark and a light variant (the README picks one with
<picture> to match the viewer's GitHub theme), except the terminal, which
stays dark in both. Headings are converted to outlines from Martian Mono
(SIL OFL 1.1, see fonts/OFL.txt) so they look the same on every machine;
smaller text uses the viewer's system fonts, with typed text pinned to a
fixed width so the cursor always lines up.
"""

from html import escape
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"

# ─────────────────────────────────────────────────────────────── CONTENT ──

NAME = "Ridham Pansara"
INTRO = [
    "Master's student in computer engineering, building cloud",
    "platforms with Kubernetes, Terraform, GitOps and CI/CD.",
]
OPEN_TO = "Open to a master's thesis, internship or working-student role"

# Typed one after another in the hero. Text after "#" is shown dimmed.
HERO_COMMANDS = [
    "terraform apply   # OCI network, OKE cluster, storage",
    "argocd app sync cloudops-insight   # GitOps rollout",
    "trivy image --exit-code 1 api   # block risky images",
    "aws sts assume-role --external-id …   # no stored keys",
]

TABLE_HEAD = ["NAME", "STATUS", "OPEN-TO", "LOCATION", "LANGUAGES"]
TABLE_ROW = ["ridham", "Ready", "master's thesis, internship, working student",
             "Karlsruhe, DE", "English, German (A2-B1)"]

# (kind, payload). "cmd" is typed, "out" appears at once: a list of (text, color).
TERMINAL = [
    ("cmd", "whoami"),
    ("out", [("Ridham Pansara, M.Sc. student in Computer Engineering for IoT Systems "
              "at Hochschule Nordhausen", "text")]),
    ("cmd", "cat focus.txt"),
    ("out", [("cloud infrastructure, DevOps, platform engineering, cloud security, "
              "observability, FinOps", "text")]),
    ("cmd", "kubectl get engineer ridham -o wide"),
    ("table", None),
]

PIPELINE_TITLE = "CloudOps Insight"
DELIVERY = [  # (label, detail)
    ("git push", "app repo"),
    ("build + test", "GitHub Actions"),
    ("Trivy scan", "image gate"),
    ("GHCR", "multi-arch image"),
    ("promote", "GitOps repo"),
    ("Argo CD", "sync"),
    ("OKE", "production"),
]
DELIVERY_NOTE = ("Images are immutable and built for several architectures; the cluster runs "
                 "only what Git declares. Terraform owns the OCI network, OKE and storage.")
RUNTIME = [
    ("AWS account", "tenant"),
    ("STS AssumeRole", "+ External ID"),
    ("Celery workers", "sync jobs"),
    ("PostgreSQL", "+ Redis"),
    ("FastAPI", "tenant RBAC"),
    ("React UI", "cost, health views"),
]
RUNTIME_NOTE = ("Syncs inventory, CloudWatch health and Cost Explorer data through short-lived "
                "STS credentials; no customer keys are stored.")

# (slug, title, badge, badge_kind, description, tags)
# badge_kind: "live" pulses green, "tag" is a quiet cyan label, None hides it.
CARDS = [
    ("inbox-lookout", "inbox-lookout", "v1.0.0", "tag",
     "Watches every inbox for you: twice-daily digests, instant alerts and a "
     "self-updating job tracker, pushed to your phone.",
     ["Python", "GitHub Actions", "ntfy"]),
    ("cloudops-gitops", "cloudops-gitops", "live", "live",
     "Helm charts and Argo CD applications for CloudOps Insight, with controlled "
     "promotion and operational recovery.",
     ["Kubernetes", "Helm", "Argo CD"]),
    ("cloudops-infrastructure", "cloudops-infrastructure", "live", "live",
     "Terraform for the OCI network, OKE cluster, storage, backups and recovery "
     "behind CloudOps Insight.",
     ["Terraform", "OCI", "OKE"]),
    ("aws-ecs-terraform-task-manager", "aws-ecs-terraform-task-manager", None, None,
     "A containerised workload on AWS ECS, with the infrastructure defined and "
     "automated in Terraform.",
     ["AWS", "ECS", "Terraform"]),
    ("binance-trading-agent", "binance-trading-agent", None, None,
     "Python automation that picks trending markets and acts on EMA and RSI "
     "signals.",
     ["Python", "EMA", "RSI"]),
    ("portfolio", "ridham-resume-portfolio", "live", "live",
     "Terminal-themed portfolio on S3 and CloudFront, shipped by a GitLab "
     "build, test and deploy pipeline.",
     ["AWS S3", "CloudFront", "GitLab CI/CD"]),
]

# ──────────────────────────────────────────────────────────────── THEME ──
# cyan = desired state, amber = in progress, green = healthy.

PALETTES = {
    "dark": dict(bg="#0e1726", panel="#132036", line="#26384f", grid="#1d2d46",
                 text="#e8eef7", muted="#8a9bb4", faint="#4f617c",
                 cyan="#5cc8ff", amber="#ffb547", green="#4fd18b"),
    "light": dict(bg="#f6f8fb", panel="#ffffff", line="#d3dce8", grid="#dde5ef",
                  text="#13203a", muted="#55667f", faint="#9aa9bd",
                  cyan="#0a7cbd", amber="#a86200", green="#16834a"),
}
TERMINAL_PALETTE = dict(bg="#0b1320", bar="#111c2e", line="#22324a", text="#dfe7f3",
                        muted="#7f90aa", cyan="#5cc8ff", amber="#ffb547", green="#4fd18b")

SANS = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, "
        "Arial, sans-serif")
MONO = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'Liberation Mono', 'DejaVu Sans Mono', monospace")

# ────────────────────────────────────────────────────────────── HELPERS ──


def f(n, places=2):
    """Compact number formatting for SVG attributes."""
    s = f"{n:.{places}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


class Outliner:
    """Turns a string into SVG path data using a real font."""

    def __init__(self, path):
        self.font = TTFont(path)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm
        self.hmtx = self.font["hmtx"]

    def width(self, text, size):
        return sum(self.hmtx[self.cmap[ord(c)]][0] for c in text) * size / self.upm

    def path(self, text, x, y, size):
        scale = size / self.upm
        pen = SVGPathPen(self.glyphs, ntos=lambda v: f(v, 1))
        advance = 0
        for ch in text:
            glyph = self.cmap[ord(ch)]
            self.glyphs[glyph].draw(
                TransformPen(pen, (scale, 0, 0, -scale, x + advance * scale, y)))
            advance += self.hmtx[glyph][0]
        return pen.getCommands()


def discrete(attr, events, period):
    """A looping SMIL animation that jumps between values at given seconds."""
    merged = {}
    for t, v in sorted(events, key=lambda e: e[0]):
        merged[round(t / period, 4)] = v
    if 0.0 not in merged:
        raise ValueError("events must start at t=0")
    kt = ";".join(f(k, 4) for k in merged)
    vals = ";".join(str(v) for v in merged.values())
    return (f'<animate attributeName="{attr}" dur="{f(period)}s" repeatCount="indefinite" '
            f'calcMode="discrete" keyTimes="{kt}" values="{vals}"/>')


def typing(start, n, cps):
    """Per-character (time, chars) steps for typing n characters."""
    return [(start + k / cps, k) for k in range(1, n + 1)]


def text_width_estimate(text, size):
    """Rough width of system sans text, good enough for line wrapping."""
    narrow, wide = set("ilj.,:;'!|() "), set("mwMW@")
    units = sum(0.3 if c in narrow else 0.85 if c in wide else 0.62 if c.isupper() else 0.53
                for c in text)
    return units * size


def wrap(text, size, max_width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if text_width_estimate(trial, size) <= max_width:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def svg_open(w, h, title, desc, extra_css=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">\n'
            f'<title id="t">{escape(title)}</title>\n<desc id="d">{escape(desc)}</desc>\n'
            f'<style>.sans{{font-family:{SANS}}}.mono{{font-family:{MONO}}}'
            f'.blink{{animation:blink 1.05s steps(1) infinite}}'
            f'@keyframes blink{{50%{{opacity:0}}}}'
            f'.pulse{{animation:pulse 2.4s ease-in-out infinite;transform-box:fill-box;'
            f'transform-origin:center}}'
            f'@keyframes pulse{{0%,100%{{opacity:.35;transform:scale(1)}}'
            f'50%{{opacity:0;transform:scale(2.4)}}}}{extra_css}</style>\n')


def split_comment(cmd):
    if "#" in cmd:
        i = cmd.index("#")
        return cmd[:i], cmd[i:]
    return cmd, ""


# ───────────────────────────────────────────────────────────────── HERO ──


def hero(p, display):
    W, H = 1000, 300
    out = [svg_open(W, H, f"{NAME}, cloud and platform engineering",
                    "Animated banner: name, a typed rotation of infrastructure commands, "
                    "and a reconciliation loop moving a change from Git to a healthy cluster.")]
    out.append(f'<defs><pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
               f'<circle cx="1.5" cy="1.5" r="1.1" fill="{p["grid"]}"/></pattern>'
               f'<clipPath id="frame"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="16"/></clipPath>'
               f'</defs>')
    out.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="16" fill="{p["bg"]}" '
               f'stroke="{p["line"]}"/>')
    out.append(f'<rect x="640" y="1" width="{W-641}" height="{H-2}" fill="url(#dots)" '
               f'clip-path="url(#frame)"/>')

    # name, outlined
    x0, size = 48, 44
    name_w = display.width(NAME, size)
    assert name_w < 560, f"name too wide: {name_w}"
    out.append(f'<path fill="{p["text"]}" d="{display.path(NAME, x0, 100, size)}"/>')

    out.append(f'<g class="sans" font-size="17" fill="{p["muted"]}">')
    for i, line in enumerate(INTRO):
        out.append(f'<text x="{x0}" y="{142 + i * 25}">{escape(line)}</text>')
    out.append('</g>')

    # typed rotation
    cw, fs, y = 9.0, 15, 222
    tx = x0 + 2 * cw
    period, t, cursor = 0.0, 0.5, [(0, 0)]
    plans = []
    for cmd in HERO_COMMANDS:
        n = len(cmd)
        assert tx + n * cw < 690, f"hero command too long: {cmd}"
        type_end = t + n / 26
        delete_at = type_end + 2.6
        delete_end = delete_at + n / 70
        steps = [(0, 0)] + typing(t, n, 26) + [
            (delete_at + (n - k) / 70, k) for k in range(n - 1, -1, -1)]
        plans.append((cmd, steps))
        cursor += steps[1:]
        t = delete_end + 0.45
    period = t
    out.append(f'<text class="mono" x="{x0}" y="{y}" font-size="{fs}" fill="{p["cyan"]}">$</text>')
    for i, (cmd, steps) in enumerate(plans):
        body, comment = split_comment(cmd)
        out.append(f'<clipPath id="h{i}"><rect x="{tx}" y="{y - 16}" height="22" width="0">'
                   + discrete("width", [(s, f(k * cw)) for s, k in steps], period)
                   + '</rect></clipPath>')
        out.append(f'<text class="mono" x="{tx}" y="{y}" font-size="{fs}" '
                   f'textLength="{f(len(cmd) * cw)}" lengthAdjust="spacing" '
                   f'clip-path="url(#h{i})" fill="{p["text"]}" xml:space="preserve">'
                   f'{escape(body)}<tspan fill="{p["muted"]}">{escape(comment)}</tspan></text>')
    out.append(f'<rect class="blink" x="{tx}" y="{y - 13}" width="{f(cw * 0.9)}" height="17" '
               f'fill="{p["cyan"]}">'
               + discrete("x", [(s, f(tx + k * cw)) for s, k in cursor], period) + '</rect>')

    # open-to line
    out.append(f'<circle cx="{x0 + 6}" cy="261" r="5" fill="{p["green"]}"/>'
               f'<circle class="pulse" cx="{x0 + 6}" cy="261" r="5" fill="{p["green"]}"/>')
    out.append(f'<text class="sans" x="{x0 + 20}" y="266" font-size="15" fill="{p["text"]}">'
               f'{escape(OPEN_TO)}</text>')

    # reconciliation loop
    cx, cy, r, nr, P = 818, 132, 78, 26, 8.0
    c30, s30 = 0.8660254 * r, 0.5 * r
    nodes = [  # (label, sub, x, y, sub_x, sub_y, anchor, arrive_t, colour)
        ("git", "desired state", cx, cy - r, cx + nr + 10, cy - r + 4, "start", 0.0, "cyan"),
        ("ci", "build, scan", cx + c30, cy + s30, cx + c30, cy + s30 + nr + 18, "middle", 2.0, "amber"),
        ("k8s", "actual state", cx - c30, cy + s30, cx - c30, cy + s30 + nr + 18, "middle", 4.0, "green"),
    ]
    ring = (f"M{f(cx)} {f(cy - r)} A{r} {r} 0 0 1 {f(cx)} {f(cy + r)} "
            f"A{r} {r} 0 0 1 {f(cx)} {f(cy - r)}")
    out.append(f'<path d="{ring}" fill="none" stroke="{p["line"]}" stroke-width="2"/>')
    out.append(f'<path d="{ring}" fill="none" stroke="{p["faint"]}" stroke-width="2" '
               f'stroke-dasharray="3 9"><animate attributeName="stroke-dashoffset" '
               f'from="0" to="-24" dur="1.6s" repeatCount="indefinite"/></path>')
    for label, sub, nx, ny, sx, sy, anchor, at, colour in nodes:
        hold_end = 7.6 if label == "k8s" else at + 2.0
        stroke_ev = [(0, p["line"]), (at, p[colour]), (hold_end, p["line"])]
        if at == 0.0:
            stroke_ev = [(0, p[colour]), (hold_end, p["line"])]
        out.append(f'<circle cx="{f(nx)}" cy="{f(ny)}" r="{nr}" fill="{p["panel"]}" '
                   f'stroke-width="2" stroke="{p["line"]}">'
                   + discrete("stroke", stroke_ev, P) + '</circle>')
        out.append(f'<text class="mono" x="{f(nx)}" y="{f(ny + 4.5)}" font-size="13" '
                   f'font-weight="700" text-anchor="middle" fill="{p["text"]}">{label}</text>')
        out.append(f'<text class="sans" x="{f(sx)}" y="{f(sy)}" font-size="12" '
                   f'text-anchor="{anchor}" fill="{p["muted"]}">{sub}</text>')
    out.append(f'<circle r="6" fill="{p["cyan"]}">'
               + discrete("fill", [(0, p["cyan"]), (2.0, p["amber"]), (4.0, p["green"])], P)
               + f'<animateMotion dur="{f(P)}s" repeatCount="indefinite" path="{ring}" '
               f'keyPoints="0;0.3333;0.6667;1" keyTimes="0;0.25;0.5;1" calcMode="linear"/>'
               '</circle>')

    # status pill
    states = [("new commit", "cyan", 0.0, 2.0), ("rolling out", "amber", 2.0, 4.0),
              ("synced, healthy", "green", 4.0, P)]
    pw, ph, py = 150, 28, 262
    out.append(f'<rect x="{cx - pw / 2}" y="{py - ph / 2}" width="{pw}" height="{ph}" rx="14" '
               f'fill="{p["panel"]}" stroke="{p["line"]}">'
               + discrete("stroke", [(a, p[c]) for _, c, a, _ in states], P) + '</rect>')
    for label, colour, a, b in states:
        ev = [(0, 0), (a, 1), (b, 0)] if a > 0 else [(0, 1), (b, 0)]
        start = cx - (12 + text_width_estimate(label, 13) * 1.05) / 2
        out.append(f'<g opacity="{1 if a == 0 else 0}">'
                   + discrete("opacity", ev, P)
                   + f'<circle cx="{f(start + 4)}" cy="{py}" r="4" fill="{p[colour]}"/>'
                   f'<text class="sans" x="{f(start + 13)}" y="{py + 4.5}" font-size="13" '
                   f'fill="{p[colour]}" font-weight="600">{label}</text></g>')
    out.append('</svg>\n')
    return "".join(out)


# ───────────────────────────────────────────────────────────── TERMINAL ──


def terminal():
    p = TERMINAL_PALETTE
    W, fs, cw, lh, x0, y0 = 1000, 14.5, 8.7, 27, 28, 78
    head = "".join(h.ljust(w) for h, w in zip(TABLE_HEAD, [9, 9, 48, 16, 0]))
    row = "".join(v.ljust(w) for v, w in zip(TABLE_ROW, [9, 9, 48, 16, 0]))

    # expand the script into rows
    rows = []
    for kind, payload in TERMINAL:
        if kind == "table":
            rows.append(("out", [(head, "muted")]))
            rows.append(("out", [(row[:9], "text"), (row[9:14], "green"), (row[14:], "text")]))
        else:
            rows.append((kind, payload))
    rows.append(("prompt", ""))

    H = y0 + (len(rows) - 1) * lh + 30
    out = [svg_open(W, H, "Terminal session about Ridham",
                    "A terminal types whoami, cat focus.txt and a kubectl command, "
                    "revealing study programme, focus areas and availability.")]
    out.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="{p["bg"]}" '
               f'stroke="{p["line"]}"/>')
    out.append(f'<path d="M1 13 a12 12 0 0 1 12 -12 H{W - 13} a12 12 0 0 1 12 12 V38 H1 Z" '
               f'fill="{p["bar"]}"/><path d="M1 38 H{W - 1}" stroke="{p["line"]}"/>')
    for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        out.append(f'<circle cx="{24 + i * 20}" cy="20" r="6" fill="{c}"/>')
    out.append(f'<text class="sans" x="{W / 2}" y="24.5" font-size="12.5" text-anchor="middle" '
               f'fill="{p["muted"]}">ridham@karlsruhe: ~</text>')

    # pass 1: timeline. Each row gets the second it appears; commands also get typing steps.
    cps, cmd_x = 17, x0 + 2 * cw
    t, timeline = 0.0, []
    cursor_x, cursor_y = [(0, f(cmd_x))], [(0, y0 - 11)]
    for i, (kind, payload) in enumerate(rows):
        y = y0 + i * lh
        if kind in ("cmd", "prompt"):
            appear = t
            cursor_x.append((appear, f(cmd_x)))
            cursor_y.append((appear, y - 11))
            steps = []
            if kind == "cmd":
                steps = typing(appear + 0.7, len(payload), cps)
                cursor_x += [(s, f(cmd_x + k * cw)) for s, k in steps]
                t = steps[-1][0] + 0.45
            timeline.append((kind, y, payload, appear, steps))
        else:
            timeline.append((kind, y, payload, t, None))
            more_output = i + 1 < len(rows) and rows[i + 1][0] == "out"
            t += 0.12 if more_output else 0.5
    period = t + 4.5

    # pass 2: render
    for i, (kind, y, payload, appear, steps) in enumerate(timeline):
        if kind in ("cmd", "prompt"):
            dollar = (f'<text class="mono" x="{x0}" y="{y}" font-size="{fs}" font-weight="700" '
                      f'fill="{p["green"]}" ')
            if appear == 0:
                out.append(dollar + 'opacity="1">$</text>')
            else:
                out.append(dollar + 'opacity="0">$'
                           + discrete("opacity", [(0, 0), (appear, 1)], period) + '</text>')
            if kind == "cmd":
                n = len(payload)
                out.append(f'<clipPath id="c{i}"><rect x="{f(cmd_x)}" y="{y - 15}" height="21" '
                           f'width="0">'
                           + discrete("width", [(0, 0)] + [(s, f(k * cw)) for s, k in steps],
                                      period)
                           + '</rect></clipPath>')
                out.append(f'<text class="mono" x="{f(cmd_x)}" y="{y}" font-size="{fs}" '
                           f'textLength="{f(n * cw)}" lengthAdjust="spacing" '
                           f'clip-path="url(#c{i})" fill="{p["text"]}" xml:space="preserve">'
                           f'{escape(payload)}</text>')
        else:
            full = "".join(s for s, _ in payload)
            assert x0 + len(full) * cw < W - 20, f"terminal line too long: {full}"
            spans = "".join(f'<tspan fill="{p[c]}"'
                            + (' font-weight="700"' if c == "muted" else "")
                            + f'>{escape(s)}</tspan>' for s, c in payload)
            out.append(f'<text class="mono" x="{x0}" y="{y}" font-size="{fs}" '
                       f'textLength="{f(len(full) * cw)}" lengthAdjust="spacing" '
                       f'xml:space="preserve" opacity="0">'
                       + discrete("opacity", [(0, 0), (appear, 1)], period)
                       + spans + '</text>')
    out.append(f'<rect class="blink" x="{f(cmd_x)}" y="{y0 - 11}" width="{f(cw)}" height="15" '
               f'fill="{p["cyan"]}">' + discrete("x", cursor_x, period)
               + discrete("y", cursor_y, period) + '</rect>')
    out.append('</svg>\n')
    return "".join(out)


# ───────────────────────────────────────────────────────────── PIPELINE ──


def lane_nodes(items, x_start, x_end, w):
    gap = (x_end - x_start - len(items) * w) / (len(items) - 1)
    return [(x_start + i * (w + gap), label, detail) for i, (label, detail) in enumerate(items)], gap


def pipeline(p, display):
    W, H = 1000, 384
    x1, x2, h = 32, W - 32, 54
    out = [svg_open(W, H, f"{PIPELINE_TITLE} delivery and runtime flow",
                    "Delivery lane: each stage from git push to production turns amber while "
                    "running and green when it passes. Runtime lane: data flows from tenant AWS "
                    "accounts through STS and Celery into PostgreSQL, FastAPI and the React UI.",
                    extra_css=".flow{animation:flow 1.2s linear infinite}"
                              "@keyframes flow{to{stroke-dashoffset:-20}}")]
    out.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16" fill="{p["bg"]}" '
               f'stroke="{p["line"]}"/>')
    out.append(f'<path fill="{p["text"]}" d="{display.path(PIPELINE_TITLE, x1, 50, 22)}"/>')
    tw = display.width(PIPELINE_TITLE, 22)
    out.append(f'<text class="sans" x="{f(x1 + tw + 14)}" y="49" font-size="14" '
               f'fill="{p["muted"]}">how a change reaches production, and how AWS data reaches '
               f'the dashboard</text>')
    out.append(f'<circle cx="{W - 116}" cy="44" r="5" fill="{p["green"]}"/>'
               f'<circle class="pulse" cx="{W - 116}" cy="44" r="5" fill="{p["green"]}"/>'
               f'<text class="sans" x="{W - 104}" y="49" font-size="14" font-weight="600" '
               f'fill="{p["green"]}">live in prod</text>')

    def lane_header(y, name, note):
        out.append(f'<text class="sans" x="{x1}" y="{y}" font-size="14.5" font-weight="700" '
                   f'fill="{p["text"]}">{name}<tspan dx="10" font-weight="400" font-size="13" '
                   f'fill="{p["muted"]}">{escape(note)}</tspan></text>')

    def node(nx, y, w, label, detail):
        out.append(f'<text class="sans" x="{f(nx + 12)}" y="{y + 24}" font-size="13.5" '
                   f'font-weight="600" fill="{p["text"]}">{escape(label)}</text>'
                   f'<text class="sans" x="{f(nx + 12)}" y="{y + 42}" font-size="11.5" '
                   f'fill="{p["muted"]}">{escape(detail)}</text>')

    # delivery lane: stages go amber while running, green once passed
    lane_header(98, "Delivery", "every change goes through Git")
    y, w, P, step = 114, 118, 9.0, 0.75
    nodes, _ = lane_nodes(DELIVERY, x1, x2, w)
    out.append(f'<path d="M{x1} {y + h / 2} H{x2}" stroke="{p["line"]}" stroke-width="2"/>')
    for i, (nx, label, detail) in enumerate(nodes):
        run, done = 0.4 + i * step, 0.4 + (i + 1) * step
        states = [(0, "line"), (run, "amber"), (done, "green"), (P - 0.35, "line")]
        out.append(f'<rect x="{f(nx)}" y="{y}" width="{w}" height="{h}" rx="10" '
                   f'fill="{p["panel"]}" stroke="{p["line"]}" stroke-width="1.6">'
                   + discrete("stroke", [(t, p[c]) for t, c in states], P) + '</rect>')
        node(nx, y, w, label, detail)
        dots = [(t, p["faint" if c == "line" else c]) for t, c in states]
        out.append(f'<circle cx="{f(nx + w - 13)}" cy="{y + 13}" r="4" fill="{p["faint"]}">'
                   + discrete("fill", dots, P) + '</circle>')
    rail_y, end_t = y + h + 14, 0.4 + len(nodes) * step
    out.append(f'<rect x="{x1}" y="{rail_y}" width="{x2 - x1}" height="3" rx="1.5" '
               f'fill="{p["line"]}"/>')
    out.append(f'<rect x="{x1}" y="{rail_y}" width="0" height="3" rx="1.5" fill="{p["green"]}">'
               f'<animate attributeName="width" dur="{f(P)}s" repeatCount="indefinite" '
               f'keyTimes="0;{f(0.4 / P, 4)};{f(end_t / P, 4)};{f((P - 0.35) / P, 4)};1" '
               f'values="0;0;{x2 - x1};{x2 - x1};0"/></rect>')
    for i, line in enumerate(wrap(DELIVERY_NOTE, 12.5, x2 - x1)):
        out.append(f'<text class="sans" x="{x1}" y="{rail_y + 26 + i * 18}" font-size="12.5" '
                   f'fill="{p["muted"]}">{escape(line)}</text>')

    # runtime lane: data keeps flowing left to right
    out.append(f'<path d="M{x1} 234 H{x2}" stroke="{p["line"]}"/>')
    lane_header(264, "Runtime", "read-only, isolated per tenant")
    y, w = 280, 140
    nodes, _ = lane_nodes(RUNTIME, x1, x2, w)
    out.append(f'<path class="flow" d="M{x1} {y + h / 2} H{x2}" stroke="{p["cyan"]}" '
               f'stroke-width="2.4" stroke-dasharray="6 14" stroke-linecap="round"/>')
    for nx, label, detail in nodes:
        out.append(f'<rect x="{f(nx)}" y="{y}" width="{w}" height="{h}" rx="10" '
                   f'fill="{p["panel"]}" stroke="{p["line"]}" stroke-width="1.6"/>')
        node(nx, y, w, label, detail)
    note = wrap(RUNTIME_NOTE, 12.5, x2 - x1)
    assert len(note) == 1, "keep RUNTIME_NOTE to one line"
    for i, line in enumerate(note):
        out.append(f'<text class="sans" x="{x1}" y="{y + h + 26 + i * 18}" font-size="12.5" '
                   f'fill="{p["muted"]}">{escape(line)}</text>')
    out.append('</svg>\n')
    return "".join(out)


# ───────────────────────────────────────────────────────────────── CARDS ──


def card(p, display, title, badge, kind, desc, tags):
    W, H = 480, 152
    out = [svg_open(W, H, title, desc)]
    out.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="{p["panel"]}" '
               f'stroke="{p["line"]}"/>')
    size = 16
    while display.width(title, size) > 340:
        size -= 0.5
    out.append(f'<path fill="{p["text"]}" d="{display.path(title, 22, 40, size)}"/>')

    if kind == "live":
        out.append(f'<circle cx="{W - 58}" cy="34" r="4.5" fill="{p["green"]}"/>'
                   f'<circle class="pulse" cx="{W - 58}" cy="34" r="4.5" fill="{p["green"]}"/>'
                   f'<text class="sans" x="{W - 47}" y="38.5" font-size="13" font-weight="600" '
                   f'fill="{p["green"]}">{escape(badge)}</text>')
    elif kind == "tag":
        bw = 12 + len(badge) * 7.6
        out.append(f'<rect x="{f(W - 22 - bw)}" y="22" width="{f(bw)}" height="23" rx="11.5" '
                   f'fill="none" stroke="{p["cyan"]}"/>'
                   f'<text class="mono" x="{f(W - 22 - bw / 2)}" y="37.5" font-size="12" '
                   f'text-anchor="middle" fill="{p["cyan"]}">{escape(badge)}</text>')

    lines = wrap(desc, 13.5, W - 44)
    assert len(lines) <= 2, f"description for {title} needs {len(lines)} lines"
    for i, line in enumerate(lines):
        out.append(f'<text class="sans" x="22" y="{70 + i * 20}" font-size="13.5" '
                   f'fill="{p["muted"]}">{escape(line)}</text>')

    x = 22
    for tag in tags:
        out.append(f'<rect x="{f(x)}" y="{H - 34}" width="7" height="7" rx="1.5" fill="{p["cyan"]}"/>'
                   f'<text class="sans" x="{f(x + 13)}" y="{H - 26.5}" font-size="12.5" '
                   f'fill="{p["text"]}">{escape(tag)}</text>')
        x += 13 + text_width_estimate(tag, 12.5) + 20
    out.append(f'<path d="M{W - 34} {H - 36} l10 0 l0 10 M{W - 24} {H - 36} l-11 11" fill="none" '
               f'stroke="{p["faint"]}" stroke-width="1.8" stroke-linecap="round"/>')
    out.append('</svg>\n')
    return "".join(out)


# ────────────────────────────────────────────────────────────────── MAIN ──


def main():
    ASSETS.mkdir(exist_ok=True)
    bold = Outliner(HERE / "fonts" / "MartianMono-Bold.woff2")
    xbold = Outliner(HERE / "fonts" / "MartianMono-ExtraBold.woff2")
    written = {}
    for theme, p in PALETTES.items():
        written[f"hero-{theme}.svg"] = hero(p, xbold)
        written[f"cloudops-flow-{theme}.svg"] = pipeline(p, bold)
        for slug, title, badge, kind, desc, tags in CARDS:
            written[f"card-{slug}-{theme}.svg"] = card(p, bold, title, badge, kind, desc, tags)
    written["terminal.svg"] = terminal()
    for name, svg in written.items():
        (ASSETS / name).write_text(svg, encoding="utf-8")
        print(f"{name:48s} {len(svg.encode()) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
