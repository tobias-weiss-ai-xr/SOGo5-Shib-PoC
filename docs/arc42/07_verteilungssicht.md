# 7. Verteilungssicht

## 7.1 Deployment-Diagramm

```mermaid
C4Deployment
    title Verteilung — Webmail-Knoten, Mail-Stack, IdP/MFA

    Deployment_Node(inet, "Internet / Campus-Netz", "") {
        Deployment_Node(users, "Nutzer-Endgeräte", "Browser, Thunderbird, Mobile") {
            Container(browser, "Browser", "HTTPS")
            Container(client, "Mail-Client", "IMAPS/Submission")
        }
    }

    Deployment_Node(proxyzone, "Proxy-Zone", "") {
        Deployment_Node(wwwproxy, "www-Proxies", "192.0.2.2 / .6 / .31") {
            Container(p1, "Reverse Proxy", "Apache/HAProxy")
        }
    }

    Deployment_Node(webnodes, "Webmail-Knoten (Debian, Puppet)", "") {
        Deployment_Node(mail-node-02, "mail-node-02 / mail-node-03 (prod)", "SOGo Webmailer") {
            Container(a1, "Apache + sogod :20000", "SOGo 5.12")
        }
        Deployment_Node(mail-node-01, "mail-node-01 (Pilot sogo-test)", "SOGo Test") {
            Container(a2, "Apache + sogod :20000", "SOGo 5.12")
            Container(a3, "sogod-pw :20001", "Passwort-Tür (intern)")
        }
        Deployment_Node(mail-node-05, "mail-node-05 (sogo-test.staff)", "SOGo Test") {
            Container(a4, "Apache + sogod :20000", "SOGo 5.12")
        }
        Deployment_Node(mail-node-04, "mail-node-04 (shared memcached / EAS)", "SOGo EAS") {
            Container(mc, "memcached :11211", "geteilt")
            Container(a5, "sogod (EAS)", "ActiveSync")
        }
    }

    Deployment_Node(mailzone, "Mail-Zone", "") {
        Deployment_Node(mailhost, "Dovecot / Postfix", "imap.example.org, smtp.example.org") {
            Container(dc, "Dovecot", "IMAPS 993, Sieve 4190")
            Container(pf, "Postfix", "Submission 587")
        }
        Deployment_Node(idpzone, "IdP / MFA", "") {
            Container(idp, "IdP", "Shibboleth 5 + OIDC")
            Container(pi, "PrivacyIDEA 3.12", "")
            Container(pxy, "2FA-LDAP-Proxy", "LDAPS 1636 / 636")
        }
        Deployment_Node(ldapzone, "Verzeichnis", "") {
            Container(ldap, "LDAP + central ldap-proxy", "LDAPS")
        }
    }

    Rel(users, p1, "HTTPS 443")
    Rel(p1, a1, "HTTPS")
    Rel(p1, a2, "HTTPS")
    Rel(p1, a4, "HTTPS")
    Rel(client, dc, "IMAPS 993")
    Rel(client, pf, "587")
    Rel(a1, dc, "IMAPS")
    Rel(a2, dc, "IMAPS")
    Rel(a3, dc, "IMAPS (PLAIN)")
    Rel(dc, pxy, "LDAP-Bind")
    Rel(pxy, pi, "validate/check")
    Rel(pxy, ldap, "Suche/Auth")
    Rel(a1, ldap, "Benutzerdaten")
    Rel(a2, idp, "SAML/OIDC")
    Rel(a1, mc, "Cache")
    UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="3")
```

## 7.2 Knoten und Rollen

| Knoten | Rolle (Hiera) | Webmail-Instanz | Besonderheit |
|---|---|---|---|
| mail-node-02 | `sogo_webmailer` | Haupt :20000 | produktiv |
| mail-node-03 | `sogo_webmailer` | Haupt :20000 | produktiv |
| mail-node-04 | `sogo_webmailer` / `sogo_eas_server` | Haupt + EAS + shared memcached | geteilter Cache für alle Webmailer |
| mail-node-05 | `sogo_webmailer` (sogo-test.staff) | Haupt :20000 | Test-/Staff-Instanz |
| mail-node-01 | `sogo_webmailer` (sogo-test) | Haupt :20000 **+ sogo-pw :20001** | Pilot: OIDC-Skeleton, PW-Tür (SAML-SP entfernt mit Branch `feature/shibSSO`) |

## 7.3 Ports und Endpunkte

| Dienst | Port | Bindung | Sichtbarkeit |
|---|---|---|---|
| Haupt-`sogod` | 20000 | 127.0.0.1 | nur lokal, via Apache |
| `sogod-pw` | 20001 | 127.0.0.1 | nur lokal, via internem Vhost |
| EAS-`sogod` | 20000 (auf EAS-Knoten) | 127.0.0.1 | via Apache-Proxy |
| Apache HTTP/HTTPS | 80 / 443 | 0.0.0.0 bzw. Vhost-IP | über www-Proxies |
| memcached | 11211 | 127.0.0.1 bzw. intern | Knoten-intern |
| IMAPS | 993 | Dovecot | Nutzer |
| Sieve | 4190 | Dovecot | SOGo/Nutzer |
| Submission | 587 | Postfix | Nutzer |
| 2FA-LDAP-Proxy | 1636 (LDAPS) | Proxy | nur Mail-Knoten |
| PI→LDAP | 636 (LDAPS) | Proxy | nur Proxy |

**Port-Kollisionsregel:** `sogo-pw` belegt 20001. Der EAS-Zweig in
`webmailer.pp` erzwingt `eas_port != 20000`, wenn `eas_host == 127.0.0.1` — wird
EAS später auf demselben Knoten aktiviert, darf **nicht** 20001 gewählt werden.

## 7.4 Netzrestriktion „nur Uni-Netz"

Produktiver Web-Traffic erreicht die Webmail-Knoten über die www-Proxies
(`192.0.2.2/6/31`, in `defense::ignored_ips`). Eine Knoten-Firewall allein
kann einen internen Vhost deshalb **nicht** durchsetzen — nötig sind:

1. DNS-Name `sogo-internal.example.org` (Netzteam),
2. Proxy-/Perimeter-Regel, die diesen Namen nur intern auflöst/zulässt,
3. optional zusätzlich `profile_firewall::allow` mit `perimeter::hrz::clients`
   und `perimeter::vpn::hrz` als Defense-in-Depth.

Das ist ⛔ extern (Netz-/Perimeter-Team), nicht Teil des Puppet-Rollouts.
