#!/usr/bin/env python3
"""Baue aus docs/arc42 ein kombiniertes LaTeX-PDF (pandoc + xelatex).

- Mermaid-Bloecke -> PNG (mmdc, Scale 3, weisser Hintergrund)
- Emoji-Statusmarker -> Klartext
- Diagramm-Caption aus der Mermaid 'title'-Zeile
- Portrait-Diagramme mit height=, Landschaft mit width= (kein Seiten-Overflow)

Aufruf:
    python3 docs/arc42/build_pdf.py          # erzeugt docs/arc42/.build/build.md
    bash docs/arc42/build.sh                 # build.md + pandoc -> webmail-arc42.pdf
"""
import re, subprocess, sys, os, datetime, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = HERE
OUT = os.path.join(HERE, ".build")
DIA = os.path.join(OUT, "diagrams")
os.makedirs(DIA, exist_ok=True)

ORDER = ["README.md"] + [f"{i}_{n}.md" for i, n in [
    ("01", "einfuehrung-und-ziele"), ("02", "randbedingungen"),
    ("03", "kontextabgrenzung"), ("04", "loesungsstrategie"),
    ("05", "bausteinsicht"), ("06", "laufzeitsicht"),
    ("07", "verteilungssicht"), ("08", "querschnittliche-konzepte"),
    ("09", "architekturentscheidungen"), ("10", "qualitaetsanforderungen"),
    ("11", "risiken-und-technische-schulden"), ("12", "glossar"),
]]

EMOJI = {
    "✅": "[OK]", "🟡": "[VORBEREITET]", "🔵": "[GEPLANT]",
    "⛔": "[BLOCKIERT]", "❌": "[VERWORFEN]", "⚠": "[ACHTUNG]",
}
EMOJI_RE = re.compile("[" + "".join(re.escape(e) for e in EMOJI) + "]")


def render_mermaid(code: str, idx: int) -> str:
    """Mermaid-Code -> PNG-Datei; liefert pandoc-Bildsyntax."""
    mmd = os.path.join(OUT, f"_mm_{idx:02d}.mmd")
    png = os.path.join(DIA, f"fig-{idx:02d}.png")
    with open(mmd, "w", encoding="utf-8") as f:
        f.write(code)
    r = subprocess.run(["mmdc", "-i", mmd, "-o", png, "-s", "3", "-b", "white",
                       "-p", os.path.join(os.path.dirname(os.path.abspath(__file__)), "puppeteer.json"),
                       "-q"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  !! mmdc FAIL fig-{idx:02d}: {r.stderr[:300]}")
        return f"*Diagramm {idx} (Render-Fehler)*"
    fr = subprocess.run(["file", png], capture_output=True, text=True)
    m = re.search(r"(\d+)\s*x\s*(\d+)", fr.stdout)
    w, h = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    aspect = (w / h) if h else 0
    attr = '{height=0.8\\textheight}' if 0 < aspect < 1.3 else "{width=100%}"
    cap = ""
    tm = re.search(r"(?m)^\s*title\s+(.+)$", code)
    if tm:
        cap = re.sub(EMOJI_RE, lambda e: EMOJI[e.group(0)], tm.group(1).strip())
    return f"![{cap}]({os.path.abspath(png)}){attr}\n\n"


def process_md(src: str, idx: int, out: list):
    txt = open(os.path.join(SRC, src), encoding="utf-8").read()
    buf, pos = [], 0
    n = 0
    for m in re.finditer(r"```mermaid\n(.*?)```", txt, re.S):
        n += 1
        buf.append(txt[pos:m.start()])
        buf.append(render_mermaid(m.group(1), idx * 100 + n))
        pos = m.end()
    buf.append(txt[pos:])
    body = "".join(buf)
    body = re.sub(EMOJI_RE, lambda e: EMOJI[e.group(0)], body)
    # Kapitel-Trenner: nur ein unsichtbarer Marker (kein {} im PDF!)
    out.append(f"\n\n<!-- chapter {src} -->\n\n")
    out.append(body)


def main():
    out = []
    for k, src in enumerate(ORDER, start=1):
        print(f"[{k:2d}/{len(ORDER)}] {src}")
        process_md(src, k, out)
    body = "".join(out)

    front = f"""---
title: "Webmail & Email-SSO/MFA — Architekturdokumentation"
subtitle: "arc42 · SOGo 5 · OIDC/SAML · PrivacyIDEA 2FA"
author: "Webmail-Team (Referenz)"
date: "{datetime.date.today().isoformat()}"
lang: de
toc-depth: 2
---
"""

    combined = front + "\n\\newpage\n\n" + body
    with open(os.path.join(OUT, "build.md"), "w", encoding="utf-8") as f:
        f.write(combined)
    print(f"\n-> build.md ({len(combined)//1024} KB) unter {OUT}")


if __name__ == "__main__":
    shutil.rmtree(DIA, ignore_errors=True)
    os.makedirs(DIA, exist_ok=True)
    main()
