# 9. Architekturentscheidungen (ADR)

Format: Kontext → Entscheidung → Konsequenzen. Status nach Kap.-1-Legende.

---

## ADR-001 — PoC-Konfigurationen als Puppet-Klassen portieren ✅

**Kontext:** Der k8s-PoC (`SOGo5-Shib-PoC`) enthält lauffähige Shibboleth- und
SOGo-Konfigurationen, aber als Manifeste/ConfigMaps ohne Parameter.
**Entscheidung:** Neuimplementierung als `profile_sogo::shib` mit Parametern
(`entity_id`, `sso_entity_id`, `discovery_url`, `remote_user_attr`,
`idp_metadata_content`, `federation_cert`, `sp_cert`, `sp_key`) plus Templates.
**Konsequenzen:** (+) Hiera-steuerbar, testbar, wiederverwendbar; (−) kein
1:1-Vergleich mit dem PoC mehr, Abweichungen müssen begründet werden.

## ADR-002 — SAML-SP als zusätzlicher Pfad `/sso` ❌ verworfen, Code entfernt

**Kontext:** SSO war ursprünglich als SAML-SP gedacht; `/SOGo` sollte
Passwort-Login behalten.
**Entscheidung:** SP-Login unter `/sso` ergänzen, `SOGoTrustProxyAuthentication=YES`
nur auf dem Pilotknoten (Hiera `merge: deep`).
**Konsequenzen:** (+) Machbarkeit belegt, Header-Injection sauber gelöst
(global `unset`, dann aus `env=REMOTE_USER`); (−) **Proxy-Auth liefert kein
IMAP-Passwort** — SSO-Nutzer können ihr Postfach nicht abrufen. Damit als
Endlösung untauglich; **der Pilot-Code wurde mit dem Branch `feature/shibSSO`
gelöscht — es gilt nur OIDC (ADR-003).**

## ADR-003 — OIDC als Zielweg für Webmail-SSO ✅ entschieden, 🟡 Skeleton

**Kontext:** IMAP braucht ein Credential, das SOGo an Dovecot weitergeben kann.
**Entscheidung:** `SOGoAuthenticationType=openid`; SOGo authentifiziert IMAP mit
`XOAUTH2` gegen den IdP-Token (`NGImap4AuthMechanism=xoauth2`,
`SOGoSMTPAuthenticationType=xoauth2`).
**Konsequenzen:** (+) Ende-zu-Ende-Lösung ohne Passwort in der Session;
(−) instanzglobal (kein Per-User-Mix), benötigt IdP-Client-Registrierung,
`OCSOpenIdURL` und Dovecot-Introspection.

## ADR-004 — OIDC-Client-Konventionen des IdP-Teams übernehmen ✅

**Kontext:** Feedback aus der Abstimmung mit dem IdP-Team.
**Entscheidung:** `client_id` = FQDN des Dienstes
(`sogo-test.example.org`), Secret per `makepasswd --chars=32` in eyaml;
**kein** `employeeType`-Claim (nicht standardisiert, nicht implementiert) —
Benutzerdaten kommen über den LDAP-Sync (ldap-proxy), `SOGoOpenIdEmailParam=mail`.
**Konsequenzen:** (+) minimale Claims, keine Sonderlocke im IdP; (−) jede
Attribut-Anforderung ist künftig zu begründen.

## ADR-005 — Zweite SOGo-Instanz (`sogo-pw`) auf demselben Knoten ✅

**Kontext:** MFA-Ausnahme/Übergang braucht eine Passwort-Tür, SOGo kann den
Auth-Typ nicht pro Nutzer wählen.
**Entscheidung:** Zweite Instanz mit eigenem User/Home/Unit auf Port 20001,
gleiche SOGo-DB und gleicher memcached; Hostname `sogo-internal.example.org`.
**Konsequenzen:** (+) zwei Türen, ein Postfach; getrennte Cookies; kein
zusätzlicher Knoten. (−) zwei Prozesse mehr je Knoten, DB-Sessions müssen
kompatibel bleiben, Port-/Monitoring-Pflege.

## ADR-006 — 2FA über PrivacyIDEA-LDAP-Proxy statt Direkt-LDAP 🔵 geplant

**Kontext:** IMAP/SMTP soll 2FA-fähig werden; PI 3.12 ist vorhanden.
**Entscheidung:** Dovecot authentifiziert gegen `privacyidea-ldap-proxy`
(LDAPS beidseitig, `allow-connection-reuse=true`), Nutzer verwenden
App-Specific-Password (`service_id=mailserver`) oder Passwort+OTP.
**Konsequenzen:** (+) 2FA ohne Client-Umbau, Self-Service-App-Pässe;
(−) jeder Bind erzeugt einen PI-Call (Durchsatz/HA), Proxy ist ein
Verfügbarkeits-Single-Point, STARTTLS nicht möglich.

## ADR-007 — Fallback `pass_on_no_token` als Migrationsschraube 🔵 geplant

**Entscheidung:** Zum Start bleibt Nutzern ohne Token der Passwort-Login
erhalten; die Schraube wird gruppen-/OU-weise geschlossen.
**Konsequenzen:** (+) nutzerunsichtbare Einführung, kein „Big Bang";
(−) 2FA ist zunächst freiwillig — Security-Signoff braucht einen Stichtag-Plan.

## ADR-008 — Dienst-Trennung im Dovecot, nicht in PrivacyIDEA 🔵 geplant

**Kontext:** PI sieht nur den LDAP-Bind, nicht die Anwendung; `service_id` muss
aber unterschieden werden (Webmail vs. Mail-Client).
**Entscheidung:** Quellrouting in der passdb-Kette: Webmail-Knoten-IPs über
`allow_nets` auf Direkt-LDAP (später Proxy-W mit `service_id=webmail`), alle
anderen auf den Proxy (`service_id=mailserver`).
**Konsequenzen:** (+) keine IP-Heuristik in PI, klar testbar pro Pfad;
(−) Dovecot-Konfiguration wird komplexer, `allow_nets`-Semantik muss verifiziert
werden.

## ADR-009 — `ProxyPass` im `<Location>` statt eigener `SOGo.conf` ✅

**Entscheidung:** Der interne Vhost überschreibt das Backend per
`ProxyPass` in `<Location /SOGo>`; `SOGo.conf` bleibt unverändert.
**Konsequenzen:** (+) ein Template, keine Duplizierung; (−) Wissen über die
mod_proxy-Vorrangregel ist im Code kommentiert, sonst überraschend.

## ADR-010 — OTP für `service_id=webmail` blockieren 🟡 geplant

**Kontext:** SOGo hält das Passwort in der Session und nutzt es bei jedem
IMAP-Reconnect; ein OTP ist dann längst abgelaufen (PI-Doku empfiehlt für
Cache-Clients App-Pässe).
**Entscheidung:** Für die Webmail-`service_id` nur Passwort-/App-Pass-Auth
zulassen, OTP dort per tokentype-Policy ausschließen; der experimentelle
Bind-Cache des Proxy wird **nicht** als Lösung verwendet.
**Konsequenzen:** (+) keine sporadischen „Postfach nicht erreichbar"-Fehler;
(−) Webmail-2FA kommt erst mit OIDC (dort ist 2FA im IdP verortet).

## ADR-011 — Properties statt Zustand im Login-Pfad ✅ (Prinzip)

Jede Login-Variante wird über **Konfiguration** (Hiera-Key, passdb-Zeile,
Instanz-Parameter) ein- und ausgeschaltet, nie durch manuelle Eingriffe. Das ist
die Voraussetzung für Qualitätsziel 3 (Rückrollbarkeit ≤ 15 Minuten).
