# 5. Bausteinsicht

## 5.1 Ebene 1 — Container

```mermaid
C4Container
    title Container-Sicht — Webmail-Knoten und Mail-Stack

    System_Ext(proxy, "www-Proxies", "Reverse Proxy")
    System_Ext(idp, "IdP", "SAML + OIDC")
    System_Ext(pi, "PrivacyIDEA 3.12", "MFA")
    System_Ext(ldapbe, "LDAP-Backend", "Benutzerverzeichnis")

    Container(ldapproxy, "2FA-LDAP-Proxy", "privacyidea-ldap-proxy, LDAPS 1636", "Bind-Interception → PI")

    Container_Boundary(node, "Webmail-Knoten (Puppet: profile_sogo)") {
        Container(apache, "Apache 2.4", "Vhosts, mod_proxy", "TLS-Terminierung, /SOGo-Proxy")
        Container(sogod, "sogod (Hauptinstanz)", "SOGo 5.12, Port 20000", "Webmail-UI, DAV, EAS-Proxy-Ziel")
        Container(sogopw, "sogod (sogo-pw)", "SOGo 5.12, Port 20001", "Passwort-Login-Tür, intern")
        Container(eas, "sogod (sogoeas)", "SOGo 5.12, eigener User", "ActiveSync, ggf. auf eigenem Knoten")
        ContainerDb(db, "SOGo-DB", "PostgreSQL/MySQL", "Profile, Ordner, Sessions, OIDC-Sessions")
        ContainerDb(mc, "memcached", "11211", "Session-/Objekt-Cache, geteilt")
    }

    Container_Boundary(mail, "Mail-Stack") {
        Container(dovecot, "Dovecot", "IMAPS 993, Sieve 4190", "Postfach, Authentifizierung")
        Container(postfix, "Postfix", "Submission 587", "Versand; SASL-Backend prüfen")
    }

    Person(user, "Nutzer", "Browser, Mail-Client")

    Rel(user, proxy, "HTTPS")
    Rel(proxy, apache, "HTTPS")
    Rel(apache, sogod, "HTTP 127.0.0.1:20000")
    Rel(apache, sogopw, "HTTP 127.0.0.1:20001 (interner Vhost)")
    Rel(apache, eas, "HTTP (ActiveSync)")
    Rel(apache, idp, "SAML / OIDC")
    Rel(sogod, db, "SQL")
    Rel(sogod, mc, "Cache")
    Rel(sogopw, db, "SQL (gleiche DB)")
    Rel(sogopw, mc, "Cache (gleiche Instanz)")
    Rel(sogod, dovecot, "IMAPS 993")
    Rel(sogod, postfix, "Submission 587")
    Rel(user, dovecot, "IMAPS 993")
    Rel(user, postfix, "Submission 587")
    Rel(dovecot, ldapproxy, "LDAP-Bind (LDAPS)")
    Rel(ldapproxy, pi, "validate/check")
    Rel(ldapproxy, ldapbe, "Suche (service-account)")
    Rel(sogod, ldapbe, "Benutzerdaten / Auth")
```

## 5.2 Ebene 2 — Komponenten in `profile_sogo`

```mermaid
C4Component
    title Komponenten — Puppet-Modul profile_sogo

    Container_Ext(sysd, "systemd", "sogo.service + Drop-in")
    Container_Ext(templ, "Templates", "ERB/EPP")
    Container_Ext(hiera, "Hiera", "data/*.json + eyaml")

    Container_Boundary(ps, "profile_sogo (Puppet-Modul)") {
        Component(wm, "webmailer", "Klasse", "Basis-Setup: SOGo-Paket, sogo.conf, Apache-Vhosts, systemd-Override, Cron, Monitoring-Anbindung")
        Component(oidc, "OIDC-Konfiguration", "Hiera-Keys", "SOGoAuthenticationType=openid, Client-ID/Secret, Scope, IMAP-Auth")
        Component(pwi, "pw_instance", "Klasse", "Zweite Instanz: User+Home, GNUstep-Defaults, systemd-Unit, Port 20001")
        Component(eas, "EAS-Block", "Logik in webmailer", "Zweite Instanz sogoeas + eigener Vhost-Block für ActiveSync")
    }

    Rel(hiera, wm, "Parameter")
    Rel(hiera, oidc, "Werte")
    Rel(hiera, pwi, "Parameter")
    Rel(wm, templ, "rendert")
    Rel(pwi, templ, "rendert")
    Rel(wm, sysd, "Override-Drop-in")
    Rel(pwi, sysd, "eigene Unit")
    Rel(wm, pwi, "inkludiert bei pw_instance=true")
```

## 5.3 Baustein-Verantwortlichkeiten

| Baustein | Datei | Verantwortung |
|---|---|---|
| `profile_sogo::webmailer` | `manifests/webmailer.pp` | SOGo-Paket, `sogo.conf` via `sogo::config`, Apache inkl. Module/Vhosts, systemd-Override, Cronjobs, Footer-Sieve, Branding, EAS- und PW-Vhost-Zweige |
| `profile_sogo::pw_instance` | `manifests/pw_instance.pp` | Isolierte Zweitinstanz: `sogo-pw` + Home, `sogod-pw.plist` (WOPort + Auth-Revert), `/etc/default/sogo-pw`, `sogo-pw.service` |
| `profile_sogo::eas_server` | `manifests/eas_server.pp` | ActiveSync-Zweitinstanz `sogoeas`, eigener Vhost-Block |
| `SOGo.conf.erb` | `templates/SOGo.conf.erb` | Serverweite Proxy-Regeln (`/SOGo` → 20000), Header für `x-webobjects-*`, DAV-Redirects |
| `sogo-pw-vhost.epp` | `templates/sogo-pw-vhost.epp` | `<Location>`-ProxyPass auf 20001, eigener `<Proxy>`-Header-Block ohne `remote-user` |
| `systemd-sogo-override.conf.epp` | `templates/` | Type=forking, Restart=always, RuntimeDirectory, KillMode=control-group |
| `sogod-pw.plist.epp` | `templates/` | WOPort 20001 + Revert der OIDC-/xoauth2-Keys für die PW-Tür |

## 5.4 Bewusste Nicht-Bausteine

- **Kein zweites SOGo-Datenbankschema** je Instanz (wäre ein zweites Postfach).
- **Keine eigene Auth-Middleware** im Webmail — Authentifizierung bleibt bei
  SOGo (OIDC/Passwort) bzw. Dovecot/PI (Mail).
- **Kein SAML-Logout-Integration** (offener Punkt, siehe Kap. 11).
