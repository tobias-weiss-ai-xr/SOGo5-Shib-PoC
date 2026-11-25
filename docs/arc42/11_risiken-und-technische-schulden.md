# 11. Risiken und technische Schulden

## 11.1 Register

| ID | Risiko / Schuld | Auswirkung | Mitigation | Status |
|---|---|---|---|---|
| R1 | SAML-Proxy-Auth liefert kein IMAP-Passwort | SSO-Nutzer ohne Mailzugriff | OIDC-Pfad (ADR-003); SAML nicht produktiv | bekannt, entschieden |
| R2 | SOGo hält Passwort in der Session, OTP läuft ab | sporadische IMAP-Fehler nach längerer Session | OTP für `service_id=webmail` sperren (ADR-010), App-Pässe | 🔵 offen |
| R3 | Föderations-Onboarding (IdP, the federation) nicht abgeschlossen | Platzhalter-IdP ⇒ SAML scheitert **by design** | echte Metadaten + Zertifikat via Hiera `federation_cert` | ⛔ extern |
| R4 | OIDC-Client nicht registriert | kein `client_secret`, kein Live-Test (nur Skeleton) | Termin IdP-Team; `client_id`=FQDN vorbereitet | ⛔ extern |
| R5 | Dovecot-Introspection/`XOAUTH2` nicht freigegeben | OIDC-Login ohne Mailfunktion | Abstimmung Mail-Team, `OAUTH2.TokenAudience` + RFC-8707-`resource` | ⛔ extern |
| R6 | Kein lokaler Katalog-Compile | Syntaxfehler erst auf dem Pilotknoten sichtbar | `--noop`-Lauf zuerst; Lint/ERB/XML-Prüfungen lokal | dauerhaft |
| R7 | Port-Kollision 20001 ↔ `eas_port` | Startfehler einer Instanz | Regel dokumentiert (Kap. 7.3); EAS-Fail-Guard erweitern | 🟡 |
| R8 | central `ldap-proxy` Rate-Limiter + 30 s Idle-Close | Verbindungsabbrüche bei Wiederverwendung, Login-Spitzen | Proxy-`allow-connection-reuse` testen, Limits prüfen | 🔵 Test nötig |
| R9 | `privacyidea-ldap-proxy` Pflege-Tempo (letzte Aktivität 2024, v0.8) | Sicherheitslücken bleiben evtl. länger offen | Version pinnen, LDAPS, Netzsegmentierung, Monitoring | dauerhaft |
| R10 | PI wird Single Point of Failure für Mail-Login | Massenausfall bei PI-Störung | HA (PI-Master/Replica, 2 Proxy-Instanzen), Alarmierung, dokumentierter Notbetrieb | ⛔ offen |
| R11 | „Nur Uni-Netz" nicht durch Knoten-Firewall durchsetzbar | interne Tür theoretisch öffentlich | DNS/Perimeter-Regel (Kap. 7.4), Defense-in-Depth-Firewall | ⛔ extern |
| R12 | MFA-Ausnahme braucht Security-Signoff | Tür ohne 2FA ohne Genehmigung | Netzrestriktion als kompensierendes Control; mit App-Pässen ggf. sogar 2FA auf der Tür | ⛔ offen |
| R13 | `eppn` (`user@example.org`) vs. `uid` bei SAML | Login-Mapping bricht | Parameter `remote_user_attr` vorhanden; im Onboarding entscheiden | ⛔ extern |
| R14 | Kein SSO-Logout (SAML), OIDC-Logout ungetestet | Session bleibt nach Logout im IdP bestehen | `SOGoOpenIdLogoutEnabled` beim Flip testen | 🔵 |
| R15 | `SOGoXSRFValidationEnabled` Default YES bei 5.12.x | OIDC-Login bricht mit XSRF-Fehlern | Testfall beim Flip, dann ggf. `NO` | 🔵 |
| R16 | SP-Schlüsselerzeugung (Debian postinst) + Default-`attribute-map.xml` | SP startet, mappt aber falsch | Keys/Mapping explizit über Hiera/Template setzen | 🟡 |
| R17 | Kein NRPE-Check für `sogo-pw` | Ausfall der zweiten Tür unbemerkt | Check ergänzen (Port + HTTP-Status) | 🔵 |
| R18 | Zwei Instanzen erhöhen Speicher-/Worker-Bedarf | OOM-Risiko auf kleinen Knoten | `pw_workers_count=2` klein halten, RSS beobachten | 🟡 |

## 11.2 Technische Schulden (bewusst eingegangen)

1. **OIDC-Konfiguration liegt inert im Hiera** (🟡) statt in einem eigenen
   Branch — bewusst, damit der Flip ein Einzeiler bleibt; Preis: Werte können
   veralten.
2. **`sogo-pw` teilt sich `sogo.conf`** statt eigener Datei — bewusst (ADR-005),
   Preis: Revert-Keys müssen bei jeder neuen Hauptinstanz-Option gepflegt werden.
3. **Vhost-Fragment dupliziert Header-Block** aus `SOGo.conf.erb` — bewusst
   (Port-Unterschied), Preis: zwei Stellen bei Header-Änderungen.
4. **SAML-Code bleibt als Referenz im Branch** — bewusst, Preis: zwei
   Feature-Branches zu pflegen.

## 11.3 Offene Entscheidungen

| Frage | Wer entscheidet |
|---|---|
| OIDC live schalten (Termin, Claims, Audience-Konfiguration) | IdP-Team + Webmail-Team |
| App-Passwörter: Lebensdauer, Anzahl, Sperr-Policies | Security + PI-Admin |
| „Nur Uni-Netz" technisch: DNS-Split, Perimeter-Regel, VPN-Zugang | Netz-/Perimeter-Team |
| 2FA-Verbindlichkeit: Stichtag, Reihenfolge der OU-/Gruppen-Schärfung | Security + HRZ-Leitung |
| MFA-Ausnahme genehmigen oder App-Pass-Pflicht auf der internen Tür | Security |
