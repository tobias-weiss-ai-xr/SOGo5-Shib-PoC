# 8. Querschnittliche Konzepte

## 8.1 Konfiguration und Hiera

- **Hierarchie:** `data/defaults.json` → `data/role/*.json` → `data/node/*.json`.
- **Merge-Verhalten:** `sogo::config` ist `merge: deep` in
  `data/defaults.json` — Knoten überschreiben einzelne Keys, ohne die Basis zu
  verlieren. Genau deshalb landet `SOGoTrustProxyAuthentication=YES` nur auf dem
  Pilotknoten, während Rollen-Dateien weiter `NO` setzen.
- **Syntax-Falle:** Werte in `sogo::config` enthalten die Anführungszeichen des
  `sogo.conf`-Formats mit, z. B. `"SOGoIMAPServer": "\"imaps://…:993\""`.
  Ausnahmen: `WOPidFile` wird in `webmailer.pp` per `regsubst` von Quotes befreit,
  weil systemd `PIDFile=` sie nicht akzeptiert.

## 8.2 Secrets

| Secret | Ablage | Erzeugung / Rotation |
|---|---|---|
| OIDC `client_secret` | eyaml (`keys/`) | `makepasswd --chars=32` |
| IdP-Metadaten/Föderationszertifikat | Hiera (`federation_cert`) | vom IdP-Team (SP-Zertifikat SAML entfernt, nur noch OIDC) |
| PI-Serviceaccount (LDAP-Proxy) | Proxy-`proxy.ini`, root-only | NetKnights-Vorgabe |
| DB-Passwörter (`SOGoProfileURL`, `OCSOpenIdURL`) | eyaml | bestehende Praxis |

Regeln: keine Secrets im Klartext-Diff, keine Secrets in Commit-Messages, keine
Wiederverwendung des Web-Zertifikats für SP-Zwecke.

## 8.3 Instanz-Muster (GNUstep-Defaults)

Zwei Instanzen auf einem Knoten teilen `sogo.conf` und SOGo-DB. Unterschieden
werden sie **nur** durch:

1. Systemuser + Home (`sogo` vs. `sogo-pw` vs. `sogoeas`),
2. `GNUstep/Defaults/sogod.plist` im Home (schlägt `sogo.conf`),
3. eigene systemd-Unit und PID/RuntimeDirectory,
4. eigenes `/etc/default/<user>` (`PREFORK`, `LOGFILE`).

Das Muster stammt aus dem erprobten EAS-Zweig (`sogoeas`) und wird von
`pw_instance` wiederverwendet — inklusive der Revert-Keys:

| Key | Hauptinstanz (OIDC-Ziel) | `sogo-pw` |
|---|---|---|
| `SOGoAuthenticationType` | `openid` | `''` (Passwort) |
| `NGImap4AuthMechanism` | `xoauth2` | `PLAIN` |
| `SOGoSMTPAuthenticationType` | `xoauth2` | `''` |
| `SOGoTrustProxyAuthentication` | `NO` | `NO` |
| `SOGoXSRFValidationEnabled` | `NO` (nur falls nötig) | `YES` |

## 8.4 systemd-Betrieb

Einheitliches Muster für alle `sogod`-Instanzen:

- `Type=forking` + `PIDFile` (sogod daemonisiert sich selbst; `Type=simple`
  würde die überlebende cgroup killen),
- `ExecStart=/usr/sbin/sogod …` **direkt** (kein `sh -c`, kein LSB-Skript —
  dessen `start-stop-daemon --stop` killt sonst alle `sogod`-Prozesse),
- `ExecStop=` leeren (sonst greift wieder das LSB-Skript),
- `RuntimeDirectory=<user>` als Kaltstart-Fix (`/run` ist tmpfs),
- `Restart=always`, `RestartSec=10`, `KillMode=control-group`,
- `LimitNOFILE=1048576`.

## 8.5 Apache-Vhost-Muster

- Ein interner Vhost braucht `ProxyPass` **innerhalb von `<Location /SOGo>`** —
  mod_proxy wertet Location-spezifische Direktiven vor den serverweiten aus.
  Damit bleibt `SOGo.conf` unverändert (serverweit → 20000), und nur der interne
  Vhost zeigt auf 20001.
- Header-Block muss mitgespiegelt werden (`x-webobjects-server-port/-name/-url`,
  `-server-protocol`) und `x-webobjects-remote-user` **entfernen**, sonst könnte
  ein Client Proxy-Trust vortäuschen.

## 8.6 Authentifizierungsschichten

| Schicht | Wer entscheidet | Konfigurationsort |
|---|---|---|
| Web-Login | SOGo (`SOGoAuthenticationType`: leer = Passwort, `openid`, `saml2`) | `sogo.conf` + Instanz-Defaults |
| Mail-Login | Dovecot-passdb-Kette (Direkt-LDAP vs. PI-Proxy) | Dovecot-Config, nicht SOGo |
| Zweiter Faktor | PrivacyIDEA-Policies (tokentype, service_id, Fallback) | PI-WebUI/API |
| Netz-Zugang | Perimeter/DNS/Firewall | Netzteam |

## 8.7 Logging, Monitoring, Betrieb

- **Icinga/NRPE** prüft Dienste; Event-Handler `restart_sogo` startet bei
  Zustandswechsel neu (Crash-Detection statt Memory-Fence — MemoryHigh/Max
  wurden als wirkungslos verworfen, da systemd die gesamte cgroup rechnet).
- Logs: `LOGFILE` je Instanz (`/var/log/sogo/…`), `sogo-ealarms` und
  `expire-sessions` als Cronjobs (nur wenn `use_db_cron`).
- **Offen:** NRPE-Check für `sogo-pw` fehlt; Bind-Test vom Mail-Knoten zum
  2FA-LDAP-Proxy fehlt.

## 8.8 Fehlerbehandlung und Rückfall

- Jede neue Schicht hat einen „aus"-Zustand, der dem Vorzustand entspricht:
  `pw_instance=false`, OIDC-Keys ohne `SOGoAuthenticationType=openid` (inert),
  `ensure => absent` für SP-Konfiguration, passdb-Eintrag entfernbar.
- Inerte Konfiguration ist explizit erlaubt und dokumentiert (🟡): Werte stehen
  im Hiera, wirken aber erst beim Flip.

## 8.9 Testbarkeit ohne Puppet-Server

Kein Katalog-Compile in der Entwicklung. Prüfmittel:

| Prüfung | Werkzeug |
|---|---|
| Manifest-Stil | `puppet-lint` (Baseline: 8 bestehende >140-Zeichen-Warnungen) |
| Templates | Ruby-ERB-Rendering + `xmllint` (plist/XML) |
| Unit-Dateien | `systemd-analyze verify` |
| JSON/Hiera | `python3 -m json.tool` bzw. `json.load` |
| Erstkontakt mit Realität | `puppet agent -t --noop`, dann echt auf Pilotknoten |
