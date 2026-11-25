# 2. Randbedingungen

## 2.1 Technische Randbedingungen

| ID | Randbedingung | Konsequenz |
|---|---|---|
| T1 | SOGo 5.12.x auf Debian, Apache 2.4 (prefork), `sogod` als GNUstep-Daemon | Konfiguration über `sogo.conf` + GNUstep-User-Defaults, nicht über eine App-Config-API |
| T2 | GNUstep-**User-Defaults schlagen** `/etc/sogo/sogo.conf` | Pro-Instanz-Abweichungen (Port, Auth-Typ) sind ohne zweite Config-Datei möglich — Grundlage der Zweitinstanz |
| T3 | Ein Postfach = SOGo-Datenbank (`SOGoProfileURL`, `OCSFolderInfoURL`, `OCSSessionsFolderURL`) + memcached | Zwei Instanzen können dasselbe Postfach bedienen, wenn sie DB und memcached teilen |
| T4 | Puppet mit Hiera (JSON) + eyaml; `lookup_options` u. a. `sogo::config: {merge: deep}` | Knotenwerte überschreiben gezielt einzelne Keys; Secrets nur verschlüsselt |
| T5 | Serverweb als Apache-Vhost mit `ProxyPass /SOGo → 127.0.0.1:20000` | Zweite Instanz braucht eigenes Backend und `ProxyPass` in `<Location>` (Vorrang vor serverweit, mod_proxy-Doku) |
| T6 | Shibboleth-IdP 5.x mit OIDC-OP-Plugin (CSCfi), Föderation DFN-AAI | SP-Registrierung und Metadaten sind externe Vorgänge, nicht selbst herstellbar |
| T7 | PrivacyIDEA 3.12 (App-Specific-Password-Token seit 3.9, Service IDs) | App-Passwörter mit `service_id` sind verfügbar; Versionshürde genommen |
| T8 | `privacyidea-ldap-proxy` (Twisted/Python 3, AGPL), **kein STARTTLS** | LDAPS auf beiden Seiten zwingend: Dovecot→Proxy `ssl:…:1636`, Proxy→LDAP `tls:…:636` |
| T9 | central `ldap-proxy` (mail-node-01) hat Bind-Rate-Limiter und 30 s-Idle-Close | Verbindungs-Wiederverwendung und Login-Spitzen müssen getestet werden, bevor Prod umgestellt wird |
| T10 | Kein Puppet-Server-Zugriff aus der Entwicklungsumgebung | Kein lokaler Katalog-Compile; erster echter Test ist `puppet agent -t` auf dem Pilotknoten |
| T11 | Produktiv-Traffic erreicht Webmail über die www-Proxies (192.0.2.2/6/31) | „Nur Uni-Netz" ist **nicht** durch die Knoten-Firewall allein herstellbar |

## 2.2 Organisatorische Randbedingungen

| ID | Randbedingung | Konsequenz |
|---|---|---|
| O1 | MFA-Vorgabe der Security; Ausnahmen sind begründungs- und genehmigungspflichtig | Jede Passwort-Tür ohne 2FA braucht ein kompensierendes Control (Netzrestriktion) und Signoff |
| O2 | IdP-Team muss OIDC-Client registrieren (client_id = FQDN, Secret) | OIDC-Rollout ist an einen externen Termin gebunden ⛔ |
| O3 | Attribute im LDAP: Login historisch über `uid`; `eppn` = `user@example.org` | Ein falsches `remote_user_attr` bricht die Postfach-Zuordnung → im Onboarding entscheiden |
| O4 | Change-Prozess: Änderungen laufen als Branch + MR gegen `master` | Feature-Branches bleiben getrennt, kein direkter Produktions-Commit |
| O5 | Zielgruppe ist nicht technisch; Passwort-Änderungen müssen selbst erklärbar sein | App-Pass-Selbstbedienung im PI-Portal statt Helpdesk-Tickets |

## 2.3 Konventionen

- Sprache im Code-Kommentar: Deutsch, ASCII (keine Umlaute in `.pp`/`.erb`).
- Templates als EPP, wenn `\${…}`-Escapes nötig sind (Parser-Versionsabhängigkeit).
- Keine neuen Abhängigkeiten im Puppetfile ohne Not (bestehend: `thor77-sogo`, `puppetlabs-apache` 12.3.1, `stdlib` 9.7.0).
