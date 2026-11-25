# 12. Glossar

| Begriff | Bedeutung |
|---|---|
| **App-Pass / Application-Specific Password** | Statisches Passwort-Token in PrivacyIDEA, an eine `service_id` gebunden; gedacht für Clients, die Passwörter cachen. |
| **`allow_nets`** | Dovecot-/passdb-Option, die eine Authentifizierungsquelle auf bestimmte Quellnetze beschränkt — hier zum Trennen von Webmail- und Client-Binds. |
| **C4** | Modell zur Architekturbeschreibung mit vier Ebenen: Context, Container, Component, Code; ergänzt um Dynamic und Deployment. |
| **client_id / client_secret** | OIDC-Clientkennung und -geheimnis; in this convention is `client_id` der FQDN des Dienstes. |
| **Dovecot passdb** | Authentifizierungs-Backend-Kette für IMAP/POP; Reihenfolge entscheidet, wer gefragt wird. |
| **EAS (ActiveSync)** | Exchange-ActiveSync-Protokoll für Mobilgeräte; in SOGo eine eigene `sogod`-Instanz (`sogoeas`). |
| **GNUstep-Defaults** | Property-List-Konfiguration (`GNUstep/Defaults/sogod.plist`) im Home eines Users; hat **Vorrang** vor `/etc/sogo/sogo.conf`. |
| **hierarchical Hiera / `merge: deep`** | Puppet-Datenmodell; `merge: deep` erlaubt es, einzelne Keys einer Hash-Struktur pro Knoten zu überschreiben. |
| **`OCSOpenIdURL`** | SOGo-Einstellung für die Datenbank, in der OIDC-Sessions abgelegt werden (Pflicht bei `SOGoAuthenticationType=openid`). |
| **OTP / TOTP** | Einmalpasswort mit Zeitfenster; nach Ablauf ungültig. |
| **`pass_on_no_token`** | PrivacyIDEA-Policy: Nutzer ohne Token werden gegen das Benutzerverzeichnis authentifiziert (Fallback-Schraube der Migration). |
| **PrivacyIDEA (PI)** | MFA-Server (Version 3.12 im HRZ) mit Policies, Token und Service IDs. |
| **privacyidea-ldap-proxy** | Twisted-Dienst, der LDAP-Binds abfängt und gegen PrivacyIDEA validiert; spricht nur LDAPS, kein STARTTLS. |
| **`profile_sogo`** | Puppet-Modul dieses Repos mit den Klassen `webmailer`, `pw_instance`, `shib`. |
| **`REMOTE_USER`** | Vom Webserver gesetzter Benutzername; bei Proxy-Auth die Grundlage für `SOGoTrustProxyAuthentication`. |
| **Service ID** | Identifier in PI (z. B. `mailserver`, `webmail`), der ein Token an einen Dienst bindet; nachträgliches Umbenennen ist nicht möglich. |
| **Shibboleth SP / IdP** | SAML-Software auf Dienst- bzw. Identitätsseite; IdP 5.x mit OIDC-OP-Plugin. |
| **SOGo** | Groupware/Webmail (Version 5.12.x) mit `sogod` als GNUstep-Daemon. |
| **`SOGoAuthenticationType`** | SOGo-Einstellung für den Login-Typ: leer (Passwort), `openid`, `saml2`. Gilt **instanzglobal**. |
| **`SOGoTrustProxyAuthentication`** | Erlaubt SOGo, den Nutzer aus einem Proxy-Header zu übernehmen (nur mit sauberem `unset`/`set` sicher). |
| **`sogo-pw`** | Zweitinstanz dieses Konzepts (`profile_sogo::pw_instance`), Passwort-Login, Port 20001, intern erreichbar. |
| **`service_id`** | Parameter im `/validate/check`, der das App-Pass einem Dienst zuordnet. |
| **WOPort** | Port, auf dem `sogod` lauscht (Hauptinstanz 20000, PW-Tür 20001). |
| **XOAUTH2** | SASL-Mechanismus für OAuth2-Token bei IMAP/SMTP; löst das Passwort-Problem der Proxy-Auth. |
| **XSRF/CSRF** | Schutz gegen Cross-Site-Request-Forgery in SOGo (`SOGoXSRFValidationEnabled`). |
| **Zwei Türen, ein Postfach** | Muster: mehrere SOGo-Instanzen auf derselben DB/demselben memcached, unterschiedliche Hostnamen und Login-Typen. |
