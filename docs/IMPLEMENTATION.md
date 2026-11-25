# SOGo5 + Federation SSO via Shibboleth — Implementation Guide

> **Deployment-Status (2026-09-20):** Die Shib-Sidecar-Manifeste liegen build-verifiziert unter
> `k8s/sogo5/` (ns `sogo5`, kustomize build grün, entityID `webmail.example.org/shibboleth-sp`, certs als emptyDir-Platzhalter).
> NICHT deployt: das Cluster betreibt SOGo5 bereits als `sogo`-Deployment im ns `mail-sso` (managed-by nix, image bookworm-5.12.11-us4-r4).
> Offene Entscheidung vor Deployment: Shib parallel als ns sogo5 (Produkt-Test isoliert) ODER am Bestand integrieren. DB/IMAP/SMTP/LDAP-Anbindung + Secrets inkl. SP-Zertifikate aus `deploy/sogo-shibboleth/` sind Voraussetzung.


> **Document Type:** Implementation Guide  
> **Status:** Draft  
> **Owner:** openDesk Team  
> **Version:** 1.0.0

## Overview

This guide provides **step-by-step implementation instructions** for integrating **SOGo5** with **the federation** authentication via **Shibboleth** (SAML 2.0).

Since the federation uses Shibboleth as its primary authentication mechanism (operated by the federation operator), this integration enables SOGo5 users to authenticate using their existing federation credentials.

## Architecture

```
User Browser → Traefik Ingress → Apache+mod_shib (container 1) → SOGo5 (container 2)
                                       ↑
                                SAML AuthN Flow
                                       ↓
                          the federation IdP (operated by the federation operator)
```

**Approach:** Apache + mod_shib runs as a **sidecar container** in the same pod as SOGo5.
- Apache terminates TLS and handles Shibboleth SP authentication
- mod_shib validates via the federation Shibboleth IdP
- Apache proxies authenticated requests to SOGo5 on `localhost:20000`
- SOGo5 trusts `REMOTE_USER` set by mod_shib (which contains the user's `eppn`)
- SOGo5 looks up user in LDAP using `eppn` as the `uid` attribute

## Prerequisites

### Information Required from the federation operator

> **Status 2026-09-20 (geklärt):** der Ziel-Dienst ist in der
> Uni-Shibboleth-Föderation **bereits als SP registriert** — keine neue
> Registrierung beim Föderationsbetreiber erforderlich:
>
> ```
> Name des Dienstes:  the federation storage service
> entityID:           https://federation.example.org/shibboleth
> Anbieter:           Example University
> Beschreibung:       Sync-and-Share-Dienst für die hessischen Hochschulen
> Datenschutz:        Datenschutzinformationen des Dienstes (Föderationsportal)
> ```
>
> Offen bleibt damit nur die **gegenseitige** Seite: unser eigener SP
> (`webmail.example.org/shibboleth-sp`) muss der Föderation / dem
> the federation-IdP bekannt gemacht werden, damit die Authentifizierung
> in beide Richtungen funktioniert.

Contact `federation-operator@example.org` or `federation-storage@example.org` for:

```
the federation Shibboleth IdP Configuration:
- Entity ID: https://login.the federation.de/idp/shibboleth
- Metadata URL: https://login.the federation.de/idp/shibboleth/metadata/idp-metadata.xml
- SAML 2.0 SingleSignOnService: https://login.the federation.de/idp/profile/SAML2/Redirect/SSO
- SAML 2.0 SingleLogoutService: https://login.the federation.de/idp/profile/SAML2/Redirect/SLO

Released Attributes (to request):
- eppn (urn:oid:1.3.6.1.4.1.5923.1.1.1.6) *REQUIRED*
- mail (urn:oid:0.9.2342.19200300.100.1.3) *REQUIRED*
- givenName (urn:oid:2.5.4.42) *RECOMMENDED*
- sn (urn:oid:2.5.4.4) *RECOMMENDED*
- affiliation (urn:oid:1.3.6.1.4.1.5923.1.1.1.1) *OPTIONAL*
- displayName (urn:oid:2.16.840.1.113730.3.1.241) *OPTIONAL*
```

### Kubernetes Environment

- Existing SOGo5 deployment in namespace `sogo5`
- Traefik as ingress controller
- cert-manager with Let's Encrypt for TLS
- LDAP with user entries (uid must match eppn from the federation)

### DNS

- A record: `webmail.example.org` → cluster ingress

## Implementation

---

## Step 1: Generate SP Certificates

```bash
mkdir -p k8s/mail-sso/sogo5/shibboleth
cd k8s/mail-sso/sogo5/shibboleth

# Generate signing key/cert (RSA 4096, 10 years)
openssl req -x509 -nodes -days 3650 -newkey rsa:4096 \
  -keyout sp-signing.key \
  -out sp-signing.crt \
  -subj "/C=DE/ST=State/L=City/O=ExampleOrg/CN=webmail.example.org"

# Generate encryption key/cert (RSA 4096, 10 years)
openssl req -x509 -nodes -days 3650 -newkey rsa:4096 \
  -keyout sp-encryption.key \
  -out sp-encryption.crt \
  -subj "/C=DE/ST=State/L=City/O=ExampleOrg/CN=webmail.example.org"

chmod 600 sp-*.key
```

**Save certificate contents** - you'll need to provide `sp-signing.crt` and `sp-encryption.crt` to the IdP operator when registering your SP.

---

## Step 2: Create Shibboleth SP Configuration

### Shibboleth SP ConfigMap

```yaml
# k8s/mail-sso/sogo5/sogo5-shibboleth-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sogo5-shibboleth-config
  namespace: sogo5
  labels:
    app.kubernetes.io/name: sogo5-shibboleth
    app.kubernetes.io/component: authentication

data:

  # Main Shibboleth SP configuration
  shibboleth2.xml: |
    <SPConfig xmlns="urn:mace:shibboleth:2.0:native:sp:config"
              xmlns:conf="urn:mace:shibboleth:2.0:native:sp:config"
              xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
              xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
              xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
              clockSkew="180" logger="syslog" logLevel="INFO">

      <ApplicationDefaults entityID="https://webmail.example.org/shibboleth-sp"
                           REMOTE_USER="eppn" homeURL="https://webmail.example.org/SOGo">
        
        <Sessions lifetime="28800" timeout="3600" checkAddress="false"
                  handlerURL="/Shibboleth.sso" redirectURL="/Shibboleth.sso/DS"
                  redirectLimit="exact" idpHistory="true" idpHistoryDays="7">
          
          <!-- SAML SSO: supports both SAML2 and SAML1 -->
          <SSO entityID="https://webmail.example.org/shibboleth-sp"
               discoveryProtocol="SAMLDS" discoveryURL="https://login.the federation.de/wayf">
            SAML2 SAML1
          </SSO>
          
          <!-- SAML SLO -->
          <Logout>SAML2 Local</Logout>
          
          <!-- Handlers -->
          <Handler type="Session" Location="/Shibboleth.sso/Session" showMethod="true"/>
          <Handler type="Status" Location="/Shibboleth.sso/Status" acl="127.0.0.1"/>
          <Handler type="MetadataGenerator" Location="/Shibboleth.sso/Metadata" signing="true"/>
          <Handler type="Admin" Location="/Shibboleth.sso/Admin" acl="127.0.0.1"/>
        </Sessions>
        
        <!-- Accept all requested attributes -->
        <AttributeFilter type="XML" validate="true" path="attribute-filter.xml"/>
        
      </ApplicationDefaults>

      <Applications>
        <Application id="sogo5" policyId="sogo5-policy"/>
      </Applications>

      <!-- federation IdP metadata provider -->
      <MetadataProvider type="XML" 
                        uri="https://login.the federation.de/idp/shibboleth/metadata/idp-metadata.xml"
                        backingFilePath="/etc/shibboleth/idp-metadata.xml" reloadInterval="3600">
        <MetadataFilter type="Signature" signatureAlgorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
        <MetadataFilter type="EntityRoleWhiteList">
          <RetainedRole>urn:oasis:names:tc:SAML:2.0:metadata:IDPSSODescriptor</RetainedRole>
        </MetadataFilter>
      </MetadataProvider>

      <!-- Security & Protocol -->
      <SecurityPolicyProvider type="XML" validate="true" path="sogo5-security.xml"/>
      <ProtocolProvider type="XML" validate="true" path="protocol.xml"/>

    </SPConfig>

  # Attribute Filter - allow required attributes from the federation
  attribute-filter.xml: |
    <AttributeFilterPolicy id="sogo5">
      <PolicyRequirementRule xsi:type="basic:ANY"/>
      <AttributeRule attributeID="eppn">
        <PermitValueRule xsi:type="basic:ANY"/>
      </AttributeRule>
      <AttributeRule attributeID="mail">
        <PermitValueRule xsi:type="basic:ANY"/>
      </AttributeRule>
      <AttributeRule attributeID="givenName">
        <PermitValueRule xsi:type="basic:ANY"/>
      </AttributeRule>
      <AttributeRule attributeID="sn">
        <PermitValueRule xsi:type="basic:ANY"/>
      </AttributeRule>
      <AttributeRule attributeID="affiliation">
        <PermitValueRule xsi:type="basic:ANY"/>
      </AttributeRule>
      <AttributeRule attributeID="displayName">
        <PermitValueRule xsi:type="basic:ANY"/>
      </AttributeRule>
    </AttributeFilterPolicy>

  # Attribute Map - map OIDs to attribute names
  attribute-map.xml: |
    <Attributes xmlns="urn:mace:shibboleth:2.0:attribute-map">
      <Attribute name="urn:oid:1.3.6.1.4.1.5923.1.1.1.6" id="eppn"/>
      <Attribute name="urn:oid:0.9.2342.19200300.100.1.3" id="mail"/>
      <Attribute name="urn:oid:2.5.4.42" id="givenName"/>
      <Attribute name="urn:oid:2.5.4.4" id="sn"/>
      <Attribute name="urn:oid:1.3.6.1.4.1.5923.1.1.1.1" id="affiliation"/>
      <Attribute name="urn:oid:2.16.840.1.113730.3.1.241" id="displayName"/>
    </Attributes>

  # Security Policy - use our SP certificates
  sogo5-security.xml: |
    <SecurityPolicyConfig xmlns="urn:mace:shibboleth:2.0:security">
      <Policy id="sogo5-policy-security" validate="true">
        <Rule type="credential" use="signing" xsi:type="FileCredentials"
              key="sp-signing.key" certificate="sp-signing.crt"/>
        <Rule type="credential" use="encryption" xsi:type="FileCredentials"
              key="sp-encryption.key" certificate="sp-encryption.crt"/>
      </Policy>
    </SecurityPolicyConfig>

  # Protocol configuration
  protocol.xml: |
    <ProtocolProviderConfig xmlns="urn:mace:shibboleth:2.0:protocol"/>

  # Apache Shibboleth module configuration
  shib.conf: |
    LoadModule mod_shib /usr/lib64/shibboleth/mod_shib_24.so
    <Location /Shibboleth.sso>
      SetHandler shib
    </Location>

  # Apache VirtualHost for SOGo5 with Shibboleth
  sogo-vhost.conf: |
    Listen 443
    
    <VirtualHost *:443>
      ServerName webmail.example.org
      
      # TLS from cert-manager
      SSLEngine on
      SSLCertificateFile /etc/ssl/certs/tls.crt
      SSLCertificateKeyFile /etc/ssl/certs/tls.key
      SSLCertificateChainFile /etc/ssl/certs/ca.crt
      
      # Security headers
      Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
      Header always set X-Frame-Options "SAMEORIGIN"
      Header always set X-Content-Type-Options "nosniff"
      
      # Shibboleth
      ShibCompatWith24 On
      
      # Protect /SOGo with Shibboleth
      <Location /SOGo>
        AuthType shibboleth
        ShibRequireSession On
        require shib-session
        
        # Pass Shibboleth headers to SOGo
        ShibUseHeaders On
        
        # Proxy to SOGo
        ProxyPreserveHost On
        ProxyPass http://127.0.0.1:20000/SOGo
        ProxyPassReverse http://127.0.0.1:20000/SOGo
        
        # Allow static files without auth
        <FilesMatch "\.(css|js|png|jpg|jpeg|gif|woff2?|svg|eot|ttf|otf|ico)$">
          require all granted
        </FilesMatch>
      </Location>
      
      # Shibboleth endpoints
      <Location /Shibboleth.sso>
        SetHandler shib
      </Location>
      
      <Location /Shibboleth.sso/Metadata>
        SetHandler shib
      </Location>
      
      # SOGo static files
      Alias /SOGo/static /usr/lib/GNUstep/SOGo/WebServerResources/
      <Directory /usr/lib/GNUstep/SOGo/WebServerResources/>
        Require all granted
      </Directory>
      
      # Logging
      ErrorLog /var/log/apache2/error.log
      CustomLog /var/log/apache2/access.log combined
      LogLevel warn
      
    </VirtualHost>
    
    <VirtualHost *:80>
      ServerName webmail.example.org
      Redirect permanent / https://webmail.example.org/
    </VirtualHost>
```

### Shibboleth SP Secrets

```yaml
# k8s/mail-sso/sogo5/sogo5-shibboleth-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: sogo5-shibboleth-secrets
  namespace: sogo5
  labels:
    app.kubernetes.io/name: sogo5-shibboleth
type: Opaque
stringData:
  sp-signing.key: |
    -----BEGIN PRIVATE KEY-----
    [PASTE CONTENTS OF sp-signing.key]
    -----END PRIVATE KEY-----
  sp-signing.crt: |
    -----BEGIN CERTIFICATE-----
    [PASTE CONTENTS OF sp-signing.crt]
    -----END CERTIFICATE-----
  sp-encryption.key: |
    -----BEGIN PRIVATE KEY-----
    [PASTE CONTENTS OF sp-encryption.key]
    -----END PRIVATE KEY-----
  sp-encryption.crt: |
    -----BEGIN CERTIFICATE-----
    [PASTE CONTENTS OF sp-encryption.crt]
    -----END CERTIFICATE-----
```

Apply both files:
```bash
kubectl apply -f k8s/mail-sso/sogo5/sogo5-shibboleth-configmap.yaml
kubectl apply -f k8s/mail-sso/sogo5/sogo5-shibboleth-secret.yaml
```

---

## Step 3: Build Apache + mod_shib Docker Image

The existing SOGo5 image doesn't include Apache + mod_shib. We need a separate container.

### Dockerfile

```dockerfile
# k8s/mail-sso/sogo5/images/Dockerfile-shibboleth
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Berlin

# Install Apache2 + mod_shib
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    apache2 \
    libapache2-mod-ssl \
    libapache2-mod-proxy \
    libapache2-mod-proxy-http \
    libapache2-mod-headers \
    libapache2-mod-shib2 \
    shibboleth-sp2-utils \
    && rm -rf /var/lib/apt/lists/*

# Enable Apache modules
RUN a2enmod ssl proxy proxy_http headers rewrite shib2

# Create Shibboleth directories
RUN mkdir -p /etc/shibboleth /var/cache/shibboleth /var/run/shibboleth /var/log/shibboleth
RUN chown -R www-data:www-data /var/cache/shibboleth /var/run/shibboleth
RUN chmod 700 /var/cache/shibboleth /var/run/shibboleth

# Set timezone
RUN ln -sf /usr/share/zoneinfo/Europe/Berlin /etc/localtime && \
    echo "Europe/Berlin" > /etc/timezone

# Copy entrypoint
COPY entrypoint-shibboleth.sh /entrypoint-shibboleth.sh
RUN chmod +x /entrypoint-shibboleth.sh

ENTRYPOINT ["/entrypoint-shibboleth.sh"]
CMD ["apache2ctl", "-D", "FOREGROUND"]
```

### Entrypoint Script

```bash
#!/bin/bash
# k8s/mail-sso/sogo5/images/entrypoint-shibboleth.sh
set -e

# Timezone
export TZ=Europe/Berlin
ln -sf /usr/share/zoneinfo/$TZ /etc/localtime
echo $TZ > /etc/timezone

# Create directories
mkdir -p /etc/shibboleth /var/cache/shibboleth /var/run/shibboleth /var/log/shibboleth
chown -R www-data:www-data /var/cache/shibboleth /var/run/shibboleth
chmod 700 /var/cache/shibboleth /var/run/shibboleth

# Copy configs from mount
for f in shibboleth2.xml attribute-filter.xml attribute-map.xml sogo5-security.xml protocol.xml shib.conf sogo-vhost.conf; do
  if [ -f "/mnt/config/$f" ]; then
    cp "/mnt/config/$f" "/etc/shibboleth/$f" 2>/dev/null || cp "/mnt/config/$f" "/etc/apache2/sites-enabled/${f%.xml}.conf" 2>/dev/null
  fi
done

# Generate self-signed certs if missing (dev only)
for type in signing encryption; do
  if [ ! -f "/etc/shibboleth/sp-$type.key" ] || [ ! -f "/etc/shibboleth/sp-$type.crt" ]; then
    openssl req -x509 -nodes -days 30 -newkey rsa:4096 \
      -keyout "/etc/shibboleth/sp-$type.key" \
      -out "/etc/shibboleth/sp-$type.crt" \
      -subj "/C=DE/ST=State/L=City/O=ExampleOrg/CN=webmail.example.org"
    chmod 600 "/etc/shibboleth/sp-$type.key"
  fi
done

chmod 644 /etc/shibboleth/shibboleth2.xml
chmod 644 /etc/shibboleth/*.crt
chmod 600 /etc/shibboleth/*.key

# Enable site
if [ -f /etc/apache2/sites-enabled/sogo-vhost.conf ]; then
  mv /etc/apache2/sites-enabled/sogo-vhost.conf /etc/apache2/sites-enabled/sogo.conf
fi

# Syntax check
apache2ctl -t 2>/dev/null || true

# Start shibd
/sbin/shibd -f 2>/dev/null || true

# Start Apache
exec apache2ctl -D FOREGROUND
```

### Build and Push

```bash
cd k8s/mail-sso/sogo5/images
docker build -t registry.example.org/sogo5-shibboleth-sp:latest -f Dockerfile-shibboleth .
docker push registry.example.org/sogo5-shibboleth-sp:latest
```

---

## Step 4: Update SOGo5 Deployment

Modify the existing deployment to add the Shibboleth SP sidecar container.

```yaml
# k8s/mail-sso/sogo5/sogo5-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sogo5
  namespace: sogo5
  # ... existing metadata ...
spec:
  # ... existing spec (replicas, selector, strategy, etc.) ...

  template:
    metadata:
      labels:
        app: sogo
        version: "5.8.0"
        component: app
        shibboleth: enabled
      # ... existing annotations ...

    spec:
      # ... existing securityContext, affinity, tolerations ...

      containers:
        
        # ====== NEW: Container 1 - Apache + Shibboleth SP ======
        - name: shibboleth-sp
          image: registry.example.org/sogo5-shibboleth-sp:latest
          imagePullPolicy: IfNotPresent
          
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: false
            runAsNonRoot: true
            runAsUser: 33
            capabilities:
              drop: ["ALL"]
          
          ports:
            - containerPort: 80
              name: http
              protocol: TCP
            - containerPort: 443
              name: https
              protocol: TCP
          
          env:
            - name: TZ
              value: "Europe/Berlin"
          
          volumeMounts:
            # Config from ConfigMap
            - name: shibboleth-config
              mountPath: /mnt/config
              readOnly: true
            
            # Actual config destination
            - name: shibboleth-config-final
              mountPath: /etc/shibboleth/shibboleth2.xml
              subPath: shibboleth2.xml
              readOnly: true
            - name: shibboleth-config-final
              mountPath: /etc/shibboleth/attribute-filter.xml
              subPath: attribute-filter.xml
              readOnly: true
            - name: shibboleth-config-final
              mountPath: /etc/shibboleth/attribute-map.xml
              subPath: attribute-map.xml
              readOnly: true
            - name: shibboleth-config-final
              mountPath: /etc/shibboleth/sogo5-security.xml
              subPath: sogo5-security.xml
              readOnly: true
            - name: shibboleth-config-final
              mountPath: /etc/shibboleth/protocol.xml
              subPath: protocol.xml
              readOnly: true
            - name: apache-config
              mountPath: /etc/apache2/mods-available/shib2.conf
              subPath: shib.conf
              readOnly: true
            - name: apache-config
              mountPath: /etc/apache2/sites-enabled/sogo.conf
              subPath: sogo-vhost.conf
              readOnly: true
            
            # Certificates from Secrets
            - name: shibboleth-secrets
              mountPath: /etc/shibboleth/sp-signing.key
              subPath: sp-signing.key
              readOnly: true
            - name: shibboleth-secrets
              mountPath: /etc/shibboleth/sp-signing.crt
              subPath: sp-signing.crt
              readOnly: true
            - name: shibboleth-secrets
              mountPath: /etc/shibboleth/sp-encryption.key
              subPath: sp-encryption.key
              readOnly: true
            - name: shibboleth-secrets
              mountPath: /etc/shibboleth/sp-encryption.crt
              subPath: sp-encryption.crt
              readOnly: true
            
            # TLS certificates from cert-manager
            - name: tls-secret
              mountPath: /etc/ssl/certs/tls.crt
              subPath: tls.crt
              readOnly: true
            - name: tls-secret
              mountPath: /etc/ssl/certs/tls.key
              subPath: tls.key
              readOnly: true
            - name: tls-secret
              mountPath: /etc/ssl/certs/ca.crt
              subPath: ca.crt
              readOnly: true
            
            # Runtime directories
            - name: shibboleth-cache
              mountPath: /var/cache/shibboleth
            - name: shibboleth-run
              mountPath: /var/run/shibboleth
          
          livenessProbe:
            httpGet:
              path: /Shibboleth.sso/Metadata
              port: https
              scheme: HTTPS
            initialDelaySeconds: 60
            periodSeconds: 30
            timeoutSeconds: 5
          
          readinessProbe:
            httpGet:
              path: /SOGo
              port: https
              scheme: HTTPS
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
          
          resources:
            limits:
              cpu: "1"
              memory: "512Mi"
            requests:
              cpu: "200m"
              memory: "256Mi"

        # ====== EXISTING: Container 2 - SOGo5 ======
        - name: sogo5
          image: registry.example.org/sogo5:5.8.0
          imagePullPolicy: IfNotPresent
          
          # ... EXISTING securityContext, env, ports, livenessProbe, readinessProbe ...
          
          # Add these environment variables for proxy authentication:
          env:
            # ... existing env vars ...
            - name: SOGoTrustedProxies
              value: "127.0.0.1,::1"
            - name: SOGoTrustProxyAuthentication
              value: "YES"
          
          # ... existing volumeMounts ...

      # ... existing imagePullSecrets ...

      volumes:
        # ... existing volumes ...
        
        # New volumes for Shibboleth
        - name: shibboleth-config
          configMap:
            name: sogo5-shibboleth-config
            defaultMode: 420
        
        - name: shibboleth-config-final
          configMap:
            name: sogo5-shibboleth-config
            defaultMode: 420
        
        - name: apache-config
          configMap:
            name: sogo5-shibboleth-config
            defaultMode: 420
            items:
              - key: shib.conf
                path: shib.conf
              - key: sogo-vhost.conf
                path: sogo-vhost.conf
        
        - name: shibboleth-secrets
          secret:
            secretName: sogo5-shibboleth-secrets
            defaultMode: 384
        
        - name: tls-secret
          secret:
            secretName: sogo5-tls-secret
            defaultMode: 420
        
        - name: shibboleth-cache
          emptyDir: {}
        
        - name: shibboleth-run
          emptyDir: {}
```

### Update Service to Point to Apache (Port 443)

```yaml
# k8s/mail-sso/sogo5/sogo5-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: sogo5
  namespace: sogo5
spec:
  selector:
    app: sogo
    version: "5.8.0"
    component: app
    shibboleth: enabled
  ports:
    - name: https
      port: 443
      targetPort: https
      protocol: TCP
  type: ClusterIP
```

---

## Step 5: Update SOGo5 Configuration

Update `sogo.conf` in the SOGo5 ConfigMap to trust proxy authentication and use LDAP with eppn:

```yaml
# k8s/mail-sso/sogo5/sogo5-configmap.yaml (updates to data.sogo.conf)
_data:
  sogo.conf: |
    {
      /* ===== Database Configuration ===== */
      SOGoProfileURL = "postgresql://sogo:${DB_PASSWORD}@${DB_HOST}:5432/sogo";
      OCSFolderInfoURL = "postgresql://sogo:${DB_PASSWORD}@${DB_HOST}:5432/sogo";
      OCSSessionsFolderURL = "postgresql://sogo:${DB_PASSWORD}@${DB_HOST}:5432/sogo";
      
      /* ===== User Sources =====
       * Look up users in LDAP using eppn (REMOTE_USER) as uid
       */
      SOGoUserSources = (
        {
          type = ldap;
          host = "ldap://${LDAP_HOST}:389";
          baseDN = "${LDAP_BASE_DN}";
          bindDN = "${LDAP_BIND_DN}";
          bindPassword = "${LDAP_BIND_PASSWORD}";
          
          idFieldName = "uid";
          UIDFieldName = "uid";
          /* Search by uid which equals the REMOTE_USER (eppn) set by mod_shib */
          UIDFieldNames = ("uid", "eppn");
          searchFilter = "(uid=%{login})";
          searchBaseDN = "ou=users,${LDAP_BASE_DN}";
          scope = SUB;
          
          isAddressBook = YES;
          displayName = "openDesk LDAP";
          canAuthenticate = YES;
          timeout = 10;
          connectionUseTLS = YES;
          maxRetryCount = 3;
        }
      );
      
      /* ===== Trust Proxy Authentication =====
       * Apache mod_shib sets REMOTE_USER to eppn
       * SOGo trusts this as the authenticated user
       */
      SOGoTrustedProxies = ("127.0.0.1", "::1");
      SOGoTrustProxyAuthentication = YES;
      
      /* ===== External Authentication =====
       * This tells SOGo to accept REMOTE_USER from Apache
       */
      SOGoExternalAuthenticationType = "remote_address";
      SOGoExternalAuthenticationMethod = "shibboleth";
      
      /* ===== Disable Password Change =====
       * Password managed by the federation
       */
      SOGoPasswordChangeEnabled = NO;
      
      /* ===== Rest of existing configuration ===== */
      /* Keep all other existing settings unchanged */
    }
```

**Critical:** Ensure LDAP entries have `uid` matching the user's `eppn` from the federation:
```ldif
dn: uid=user@example.org,ou=users,dc=example,dc=org
objectClass: inetOrgPerson
uid: user@example.org
cn: User Name
mail: user@example.org
givenName: User
sn: Name
```

---

## Step 6: Register SP with the federation IdP

Provide SP metadata to the IdP operator (`federation-operator@example.org`):

```
To: federation-operator@example.org / federation-storage@example.org
Subject: Request: Register openDesk SOGo5 Shibboleth SP

Please register the following Service Provider:

Entity ID: https://webmail.example.org/shibboleth-sp
Metadata URL: https://webmail.example.org/Shibboleth.sso/Metadata
ACS URLs:
  - https://webmail.example.org/Shibboleth.sso/SAML2/POST
  - https://webmail.example.org/Shibboleth.sso/SAML2/Redirect
SLO URLs:
  - https://webmail.example.org/Shibboleth.sso/SLO/Redirect
  - https://webmail.example.org/Shibboleth.sso/SLO/POST

SP Signing Certificate:
-----BEGIN CERTIFICATE-----
[PASTE sp-signing.crt CONTENTS]
-----END CERTIFICATE-----

Required Attributes:
- eppn (urn:oid:1.3.6.1.4.1.5923.1.1.1.6)
- mail (urn:oid:0.9.2342.19200300.100.1.3)
- givenName (urn:oid:2.5.4.42)
- sn (urn:oid:2.5.4.4)
- affiliation (urn:oid:1.3.6.1.4.1.5923.1.1.1.1)
- displayName (urn:oid:2.16.840.1.113730.3.1.241)

Contact:
Technical: maintainer@example.org
Admin: service-management@example.org
```

**After registration:** Verify the IdP metadata is accessible:
```bash
curl https://login.the federation.de/idp/shibboleth/metadata/idp-metadata.xml
```

---

## Step 7: Configure Ingress

```yaml
# k8s/mail-sso/sogo5/sogo5-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sogo5
  namespace: sogo5
  annotations:
    kubernetes.io/ingress.class: traefik
    cert-manager.io/cluster-issuer: letsencrypt-production
    traefik.ingress.kubernetes.io/affinity: "true"
    traefik.ingress.kubernetes.io/session-cookie-name: shib_session_sogo5
    traefik.ingress.kubernetes.io/session-cookie-maxage: "28800"
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.tls: "true"
    traefik.ingress.kubernetes.io/router.tls.certresolver: letsencrypt
    traefik.ingress.kubernetes.io/router.headers.sslredirect: "true"
    traefik.ingress.kubernetes.io/router.headers.stsseconds: "31536000"
    traefik.ingress.kubernetes.io/router.headers.stsincludesubdomains: "true"
    traefik.ingress.kubernetes.io/router.headers.forcestsheader: "true"
    traefik.ingress.kubernetes.io/router.headers.frameoptions: "SAMEORIGIN"

spec:
  tls:
    - hosts:
        - webmail.example.org
      secretName: sogo5-tls-secret
  rules:
    - host: webmail.example.org
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: sogo5
                port:
                  number: 443
```

---

## Step 8: Deploy and Test

### Apply Configuration
```bash
kubectl apply -f k8s/mail-sso/sogo5/
```

### Wait for Rollout
```bash
kubectl rollout status -n sogo5 deployment/sogo5 --timeout=10m
```

### Test Shibboleth Configuration
```bash
# Check metadata endpoint
curl https://webmail.example.org/Shibboleth.sso/Metadata

# Check Apache is running
kubectl logs -n sogo5 <pod-name> -c shibboleth-sp

# Check SOGo is running
kubectl logs -n sogo5 <pod-name> -c sogo5
```

### Test Authentication Flow
1. Visit `https://webmail.example.org/SOGo`
2. Should redirect to the federation Shibboleth IdP
3. Login with the federation credentials
4. Should redirect back to SOGo and show interface

### Verify Headers (Optional)
Add a test endpoint to Apache to dump Shibboleth headers:
```yaml
# In sogo-vhost.conf, add:
<Location /test-shib-headers>
  AuthType shibboleth
  ShibRequireSession On
  require shib-session
</Location>
```
Then visit: `https://webmail.example.org/test-shib-headers`

---

## Troubleshooting

| Symptom | Diagnosis | Solution |
|---------|-----------|----------|
| **403 Forbidden on /SOGo** | mod_shib not passing auth | Check `AuthType shibboleth`, `ShibRequireSession On`, `require shib-session` |
| **Redirect loop to IdP** | Session cookie issue | Check `handlerURL`, cookie settings, Session handler |
| **502 Bad Gateway** | Apache can't reach SOGo | Verify SOGo is on localhost:20000 in same pod |
| **500 Internal Server Error** | Shibboleth SP error | Check Apache error logs, `shibd -t -c /etc/shibboleth/shibboleth2.xml` |
| **Blank page after login** | SOGo not reading headers | Enable `ShibUseHeaders On`, check `SOGoTrustProxyAuthentication` |
| **401 on SOGo** | LDAP lookup failed | Verify LDAP `uid` matches Shibboleth `eppn` |

### Check Logs
```bash
# Apache + Shibboleth logs
kubectl logs -n sogo5 <pod> -c shibboleth-sp
kubectl exec -n sogo5 <pod> -c shibboleth-sp -- cat /var/log/shibboleth/native.log

# SOGo logs
kubectl logs -n sogo5 <pod> -c sogo5 | grep -i "login\|auth\|remote\|shib"
```

### Enable Debug Logging
```xml
<!-- In shibboleth2.xml -->
<SPConfig ... logLevel="DEBUG">

<!-- In Apache -->
LogLevel debug

# Then restart
kubectl rollout restart -n sogo5 deployment/sogo5
```

---

## Security Considerations

1. **Certificates:** Rotate SP signing/encryption certificates annually
2. **Session:** Timeout 8 hours (match IdP), Secure/HttpOnly cookies
3. **Network:** Force HTTPS, restrict access to Shibboleth endpoints
4. **Attributes:** Only request minimum required (eppn, mail, name)
5. **Privacy:** Comply with GDPR, don't store sensitive attributes

---

## Contacts

- **Implementation:** maintainer@example.org
- **Service Management:** service-management@example.org  
- **IdP Admin:** federation-operator@example.org
- **Federation service:** federation-storage@example.org

---

## References

- [Shibboleth SP Documentation](https://wiki.shibboleth.net/confluence/display/SP3)
- [SOGo Documentation](http://www.sogo.nu/files/docs/SOGo%20Installation%20Guide.html)
- [Apache mod_shib](https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPApacheConfig)
