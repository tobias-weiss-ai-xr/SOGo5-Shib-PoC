#!/usr/bin/env bash
# Rezept aus docs/arc42/README.md: Mermaid -> PNG (mmdc), Emoji -> Text,
# pandoc + xelatex -> docs/arc42/webmail-arc42.pdf.
# Voraussetzungen: mmdc (mermaid-cli), pandoc, xelatex.
set -euo pipefail
cd "$(dirname "$0")"

echo "== 1/2: Mermaid -> PNG + build.md (build_pdf.py) =="
python3 build_pdf.py

echo "== 2/2: pandoc -> webmail-arc42.pdf =="
pandoc .build/build.md \
  --pdf-engine=xelatex \
  --include-in-header=header.tex \
  --toc --toc-depth=2 \
  --number-sections \
  -o webmail-arc42.pdf

echo "== Verifikation: keine {} -Artefakte im PDF =="
n=$(pdftotext webmail-arc42.pdf - | grep -c '^{}$' || true)
echo "  literal '{}' Zeilen im PDF: $n"
if [ "$n" -gt 0 ]; then
  echo "  FEHLER: es sind noch {} im PDF" >&2
  exit 1
fi
echo "  OK"
