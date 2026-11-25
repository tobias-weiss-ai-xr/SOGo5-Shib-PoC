# arc42 — Webmail & Mail-SSO/MFA

Architekturdokumentation für Webmail (SOGo 5) und die SSO-/MFA-Strategie des
Mail-Stacks der einer Universitäts-IT (anonymisierte Referenzlandschaft).

**Scope:** `webmail-puppet` (Puppet-Environment, produktiv ausgerollt) plus die
daraus abgeleiteten Änderungen. Der k8s-PoC (`SOGo5-Shib-PoC`) ist Referenz,
nicht Zielsystem.

## Kapitel

| # | Kapitel | Inhalt |
|---|---|---|
| 1 | [Einführung und Ziele](01_einfuehrung-und-ziele.md) | Aufgabenstellung, Qualitätsziele, Stakeholder |
| 2 | [Randbedingungen](02_randbedingungen.md) | Technisch und organisatorisch |
| 3 | [Kontextabgrenzung](03_kontextabgrenzung.md) | C4-Kontext, Nachbarsysteme |
| 4 | [Lösungsstrategie](04_loesungsstrategie.md) | Die fünf Pfeiler |
| 5 | [Bausteinsicht](05_bausteinsicht.md) | C4-Container + Komponenten (`profile_sogo`) |
| 6 | [Laufzeitsicht](06_laufzeitsicht.md) | Login-Wege als C4-Dynamic |
| 7 | [Verteilungssicht](07_verteilungssicht.md) | Knoten, Ports, Netze |
| 8 | [Querschnittliche Konzepte](08_querschnittliche-konzepte.md) | Hiera/eyaml, systemd, Apache, Monitoring |
| 9 | [Architekturentscheidungen](09_architekturentscheidungen.md) | ADR-001 … ADR-011 |
| 10 | [Qualitätsanforderungen](10_qualitaetsanforderungen.md) | Szenarien mit Messkriterien |
| 11 | [Risiken und technische Schulden](11_risiken-und-technische-schulden.md) | Register mit Mitigation |
| 12 | [Glossar](12_glossar.md) | Begriffe |

## Status-Legende

In allen Kapiteln gilt:

| Symbol | Bedeutung |
|---|---|
| ✅ | umgesetzt und im Repo (Branch/Commit genannt) |
| 🟡 | vorbereitet, aber inert/abgeschaltet (z. B. Platzhalter-Werte) |
| 🔵 | geplant, noch kein Code |
| ⛔ | blockiert (externer Input nötig) |
| ❌ | verworfen (mit Begründung) |

## Diagramme

Alle C4-Diagramme sind [Mermaid](https://mermaid.js.org/)-C4 und rendern direkt
in GitLab. Lokal: `mermaid-cli` oder VS-Code-Extension. C4-Ebenen:
`C4Context` (Kap. 3), `C4Container`/`C4Component` (Kap. 5), `C4Dynamic`
(Kap. 6), `C4Deployment` (Kap. 7).

**PDF erzeugen** (reproduzierbar, ohne `{}`-Artefakte):

```bash
bash docs/arc42/build.sh   # build_pdf.py (mmdc -> PNG, Emoji->Text) + pandoc/xelatex
```

Liefert `docs/arc42/webmail-arc42.pdf` (Titelblatt + TOC). Voraussetzungen:
`mermaid-cli` (`mmdc`), `pandoc`, `xelatex`, `pdftotext` (Verifikation).

### Hinweise zum Mermaid-Rendering

- **Viewport statt `UpdateLayoutConfig`:** Mermaid-C4 legt die Zeilenbreite an
  `screen.availWidth` (Puppeteer-Fenster) aus — `UpdateLayoutConfig` wirkt auf
  die C4-Diagramme kaum/nicht (Shape-Wrapping wird durch die 216px-Shape-Breite
  dominiert). `build_pdf.py` übergibt deshalb `puppeteer.json` mit einem breiten
  Viewport (1100×1400 → `--window-size`), damit die Diagramme horizontal
  aufgelöst werden und ein normales Seitenverhältnis bekommen (Statt
  endloser Einspalten-Portraits). `.build/` enthält dabei die Zwischenstände.
- **Kreuzungsarme Anordnungen:** Für die Diagramme 601/602/401 sind die
  Deklarationen so sortiert, dass die Kantenkreuzungen minimiert werden
  (601: `user` als letzte Person; 602: Externe `sysd, templ, hiera` + Komponenten
  `wm, shib, oidc, pwi, eas`; 401: `admin` als letzter Person).
- **801 (Deployment):** `UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="3")`
  reduziert die Kreuzungen von 11 auf 5 (getestet mit SVG-Pfad-Messung).

## Pflege

Diese Doku beschreibt den Stand des Branches `feature/oidcSSO` sowie den
Planungsstand für den 2FA-LDAP-Proxy. Der frühere SAML-Ansatz
(`feature/shibSSO`) ist verworfen und der Branch wurde entfernt — es gilt nur
noch der OIDC-Weg. Bei Änderung der Login-Wege, Ports oder IdP-Anbindung:
betroffenes Kapitel und ADR aktualisieren — nicht nur den Code.
