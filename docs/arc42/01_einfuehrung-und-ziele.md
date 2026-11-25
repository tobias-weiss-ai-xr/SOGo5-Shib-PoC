# 1. Einführung und Ziele

## 1.1 Aufgabenstellung

Das HRZ betreibt für Studierende und Beschäftigte Webmail auf Basis von SOGo 5
(`profile_sogo`, Puppet-Environment `webmail-puppet`) sowie IMAP/SMTP über
Dovecot/Postfix. Der Login in SOGo erfolgt heute mit Benutzername und Passwort;
die Anmeldung am Mail-Stack (Thunderbird, Smartphone, Webmail) authentifiziert
gegen LDAP.

Daraus folgen drei offene Punkte:

1. **Kein SSO.** Nutzer haben ein zweites Konto-/Passwort-Erlebnis im Webmail,
   obwohl die Universität einen zentralen IdP (Shibboleth, föderiert über
   DFN-AAI) betreibt.
2. **Kein zweiter Faktor im Mail-Stack.** MFA ist für andere Dienste etabliert
   (PrivacyIDEA 3.12), IMAP/SMTP hängen aber direkt am LDAP-Passwort.
3. **Spannungsfeld Webmail ↔ Mail-Clients.** Ein Proxy-Auth-Login (SAML) liefert
   dem Webmail eine Session, aber **kein IMAP-Passwort** — der Postfachzugriff
   bricht. Deshalb ist die Reihenfolge der Maßnahmen architekturrelevant.

Ziel ist eine Architektur, in der SSO und MFA eingeführt werden können, **ohne
dass ein Nutzer am Umstellungstag etwas tun muss** und ohne dass bestehende
Mail-Clients aufhören zu funktionieren.

## 1.2 Qualitätsziele

Rangfolge ist bindend bei Zielkonflikten (oben schlägt unten).

| Prio | Ziel | Konkretes Szenario |
|---|---|---|
| 1 | **Kein Mail-Bruch** | Ein Thunderbird mit gespeichertem Passwort funktioniert am Tag der Umstellung unverändert weiter. |
| 2 | **Reibungsfreie Einführung** | Ein Nutzer ohne Token merkt von der 2FA-Einführung nichts; ein Nutzer mit Token erhält 2FA automatisch. |
| 3 | **Rückrollbarkeit** | Jede Stufe ist in ≤ 15 Minuten und ohne Datenmigration zurücknehmbar (eine passdb-Zeile, ein Hiera-Key, ein Branch-Revert). |
| 4 | **Nachvollziehbarkeit** | Jede Änderung an Login-Wegen ist im Puppet-Repo als Diff + ADR belegt; keine Handeingriffe auf Produktionsknoten. |
| 5 | **Sicherheit ohne Sackgasse** | 2FA ist flächendeckend möglich, ohne Clients zu zwingen, mit OTP-Passwörtern zu arbeiten. |
| 6 | **Wartbarkeit** | Neue Login-Variante = eine Puppet-Klasse + Hiera, kein Copy-Paste von Konfiguration. |

## 1.3 Stakeholder

| Stakeholder | Erwartung / Interesse |
|---|---|
| Webmail-Team (HRZ) | Betriebssicherheit, Puppet-Idiomatik, klare Rollback-Pfade |
| IdP-Team | Registrierung von SP/OIDC-Clients, Attribut-Mapping, Föderations-Metadaten |
| Mail-/Dovecot-Team | Unveränderte Zustellung, planbare passdb-Umstellung, TLS-Anforderungen |
| Netz-/Perimeter-Team | Interne Vhosts wirklich nur intern erreichbar (Proxy/DNS/Firewall) |
| Security | 2FA-Wirksamkeit, Begründung jeder Ausnahme, Auditierbarkeit |
| Studierende/Beschäftigte | Login funktioniert, Clients bleiben konfiguriert, nachvollziehbare App-Passwörter |
| Helpdesk | Wenige, klar erklärbare Fehlerbilder; keine Passwort-Sonderfälle |

## 1.4 Was diese Doku nicht ist

Keine Betriebsanleitung (Runbooks liegen in `docs/` des Repos) und keine
PoC-Dokumentation — der k8s-PoC in `SOGo5-Shib-PoC` ist Referenzquelle für
erprobte Konfigurationen, das Zielsystem ist der Puppet-Stack.
