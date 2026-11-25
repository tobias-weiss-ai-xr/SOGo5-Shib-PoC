# 6. Laufzeitsicht

## 6.1 Login-Wege im Überblick

| # | Weg | Status | Authentifizierung | IMAP/SMTP danach |
|---|---|---|---|---|
| L1 | Passwort gegen LDAP (heute) | ✅ | LDAP-Bind | Passwort aus Session |
| L2 | SAML-SSO (`/sso`) | ❌ entfernt | Shibboleth-SP, `REMOTE_USER` (Branch `feature/shibSSO` gelöscht) | ❌ kein Passwort ⇒ Postfach bricht |
| L3 | OIDC (Ziel) | 🟡 Skeleton | IdP OIDC, SOGo `openid` | `XOAUTH2` mit Token |
| L4 | Mail-Client mit App-Pass | 🔵 geplant | LDAP-Proxy → PI, `service_id=mailserver` | App-Passwort |
| L5 | Mail-Client mit Passwort+OTP | 🔵 geplant | LDAP-Proxy → PI, `service_id=mailserver` | nur mit aktuellem OTP |
| L6 | Interne Passwort-Tür (`sogo-pw`) | ✅ Code, `pw_instance=true` auf Pilot | LDAP (Revert der OIDC-Keys) | Passwort aus Session |

## 6.2 L2 — SAML-SSO (historisch, Code entfernt)

> Der SAML-Pilot existierte nur auf dem inzwischen gelöschten Branch
> `feature/shibSSO` und ist nicht Teil von `feature/oidcSSO`. Der folgende
> Ablauf ist als Architektur-Hintergrund festgehalten, nicht als Ist-Zustand.

```mermaid
C4Dynamic
    title SAML-Login über /sso (Pilot mail-node-01)
    Container(sp, "Apache + mod_shib", "SP")
    Container(sogo, "sogod :20000")
    System_Ext(idp, "IdP")
    Person(u, "Nutzer")
    Rel(u, sp, "GET /sso")
    Rel(sp, idp, "AuthnRequest")
    Rel(idp, u, "Login + 2FA im IdP")
    Rel(idp, sp, "Assertion → REMOTE_USER")
    Rel(sp, sogo, "Proxy mit x-webobjects-remote-user (TrustProxyAuthentication=YES)")
    Rel(sogo, u, "Session ohne IMAP-Passwort → Mail nicht abrufbar")
```

**Kernbefund:** Der Weg beweist die SP-Anbindung, löst aber das IMAP-Problem
nicht. Deshalb ❌ als Endlösung; der Pilot-Code wurde mit dem Branch gelöscht
und wird nicht weitergeführt.

## 6.3 L3 — OIDC (Zielbild Webmail)

```mermaid
C4Dynamic
    title OIDC-Login mit anschließendem IMAP-Zugriff
    Container(sogo, "sogod (openid)", "Auth-Typ openid")
    System_Ext(idp, "IdP OIDC")
    Container(dovecot, "Dovecot", "XOAUTH2/introspection")
    ContainerDb(pg, "SOGo-DB (sogo_openid)")
    Person(u, "Nutzer")
    Rel(u, sogo, "Login-Seite (Redirect)")
    Rel(sogo, idp, "authorize (client_id=FQDN, scope=openid profile email)")
    Rel(idp, u, "Login + 2FA")
    Rel(idp, sogo, "code → token")
    Rel(sogo, pg, "Session in OCSOpenIdURL")
    Rel(sogo, dovecot, "IMAP AUTHENTICATE XOAUTH2 <token>")
    Rel(dovecot, idp, "Token-Validierung (audience/resource)")
    Rel(dovecot, sogo, "Postfach")
```

**Kritische Punkte** (aus den Referenz-Threads verifiziert):
- Der IdP muss ein **audience-restriktives** Access-Token ausstellen, sonst
  scheitert Dovecot. Weg: Client sendet RFC-8707-`resource` beim **authorize**
  (nicht am Token-Endpoint); IdP-seitig `OAUTH2.TokenAudience`.
- `SOGoXSRFValidationEnabled=NO` wird bei SOGo 5.12.x mit OpenID berichtet —
  erst beim Flip ändern, dann testen.
- `OCSOpenIdURL` (eigene Tabelle/DB) ist Pflicht, sonst keine OpenID-Sessions.

## 6.4 L4/L5 — Mail-Clients über den 2FA-LDAP-Proxy

```mermaid
C4Dynamic
    title IMAP-Bind mit App-Passwort oder Passwort+OTP
    Person(c, "Mail-Client", "Thunderbird / Smartphone")
    Container(dc, "Dovecot", "passdb-Reihenfolge")
    Container(px, "2FA-LDAP-Proxy", "service_id=mailserver")
    System_Ext(pi, "PrivacyIDEA 3.12")
    System_Ext(ldap, "LDAP-Backend")
    Rel(c, dc, "IMAPS LOGIN / AUTHENTICATE")
    Rel(dc, px, "LDAP-Bind (Quelle: Client-IP)")
    Rel(px, pi, "validate/check + service_id")
    Rel(pi, px, "ok (App-Pass ODER PIN+OTP)")
    Rel(px, ldap, "ggf. Suche/Bind als service-account")
    Rel(px, dc, "Bind erfolgreich")
    Rel(dc, c, "Postfach")
```

**Quellrouting** — entscheidend für die Trennung Webmail ↔ Client:

```mermaid
flowchart LR
    subgraph Dovecot["Dovecot passdb-Reihenfolge"]
      A["[1] Direkt-LDAP<br/>allow_nets = Webmail-Knoten-IPs"] --> B["[2] 2FA-LDAP-Proxy<br/>service_id=mailserver"]
      B --> C["[3] Direkt-LDAP<br/>geparkt = Rollback"]
    end
    W["Bind von Webmail-Knoten"] --> A
    M["Bind von Client-IP"] --> B
```

## 6.5 L6 — Interne Passwort-Tür (`sogo-pw`)

```mermaid
C4Dynamic
    title Zugriff auf die zweite Instanz (Port 20001)
    Person(u, "Nutzer im Uni-Netz")
    Container(ap, "Apache", "Vhost sogo-intern")
    Container(pw, "sogod (sogo-pw) :20001")
    Container(main, "sogod (Hauptinstanz) :20000")
    ContainerDb(db, "SOGo-DB")
    Rel(u, ap, "HTTPS (nur intern erreichbar)")
    Rel(ap, main, "serverweiter ProxyPass /SOGo → 20000")
    Rel(ap, pw, "ProxyPass in Location gewinnt → 20001")
    Rel(pw, db, "gleiche Profile/Ordner/Sessions")
    Rel(pw, u, "Passwort-Login (Auth-Typ leer, IMAP PLAIN)")
```

**Verifikation nach dem ersten `puppet agent -t`:**
`curl http://127.0.0.1:20001/SOGo` muss das **Passwort-Formular** zeigen, obwohl
die Hauptinstanz ggf. auf `openid` steht — das beweist den GNUstep-Defaults-
Vorrang gegenüber `sogo.conf`.

## 6.6 Fehlerfälle

| Fall | Verhalten |
|---|---|
| `sogod`-Worker stirbt | `Restart=always` + Icinga-Event-Handler `restart_sogo` |
| `/run/sogo` fehlt nach Reboot | `RuntimeDirectory=` legt es beim Unit-Start an (Kaltstart-Fix) |
| OTP abgelaufen bei SOGo-Session | IMAP-Reconnect scheitert → OTP für `service_id=webmail` blockieren (ADR-010) |
| PI nicht erreichbar | Binds scheitern ⇒ Mail-Logins scheitern. Fallback/HA und Monitoring nötig (⛔ offen) |
| IdP nicht erreichbar | OIDC-Login unmöglich; Passwort-Tür als Notfallzugang (nur intern) |
