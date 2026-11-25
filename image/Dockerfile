# Shibboleth SP sidecar for SOGo5 (Apache + mod_shib)
# SPDX-FileCopyrightText: 2026 Example Contributors
# SPDX-License-Identifier: Apache-2.0
#
# Replaces the dead upstream image registry.example.org/sogo5-shibboleth-sp:latest
# (DNS no longer resolves; manifestes referenced a dead host).
#
# Architecture (per IMPLEMENTATION_SOGO5_NEXTHESSENBOX_SHIBBOLETH.md):
#   Browser -> Ingress -> Apache+mod_shib (this sidecar, port 80)
#     /Shibboleth.sso/* handled locally, everything else proxied to SOGo on 127.0.0.1:20000
#   REMOTE_USER (eppn) set by mod_shib, SOGo trusts it.
#
# Runs non-root (uid 1001) with file-capability cap_net_bind_service so Apache
# can bind port 80 without running as root / extra container caps.

FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        apache2 \
        libapache2-mod-shib \
        opensaml-schemas \
        curl \
        libcap2-bin \
        openssl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Enable modules
RUN a2enmod shib ssl proxy proxy_http proxy_ajp rewrite headers && \
    a2dismod mpm_event && a2enmod mpm_prefork

# Apache state must live in writable dirs for uid 1001 (read-only rootfs not required,
# but keep pid + run dirs owned by the app user).
RUN useradd -u 1001 -m -d /home/shib -s /bin/bash shib && \
    mkdir -p /var/run/apache2 /var/lock/apache2 /var/log/apache2 /tmp/shibboleth /var/run/shibboleth /var/cache/shibboleth && \
    chown -R shib:shib /var/run/apache2 /var/lock/apache2 /var/log/apache2 /tmp/shibboleth /var/run/shibboleth /var/cache/shibboleth

# File capability: allow binding port 80 as non-root (works even with drop: ALL caps).
RUN setcap cap_net_bind_service=+ep /usr/sbin/apache2

# Default (runtime overridden by ConfigMap mounts)
COPY shibboleth2.xml /etc/shibboleth/shibboleth2.xml
COPY attribute-filter.xml /etc/shibboleth/attribute-filter.xml
COPY shibboleth.apache.conf /etc/shibboleth/shibboleth.apache.conf
# Placeholder IdP metadata (real one is mounted at runtime via ConfigMap/Secret)
COPY idp-metadata.xml /etc/shibboleth/idp-metadata.xml

# Default self-signed SP credentials so the image works standalone / for tests.
# Overridden in production by the SP secret mounted over these files.
RUN openssl req -x509 -newkey rsa:3072 -nodes -days 3650 \
        -keyout /etc/shibboleth/sp-signing.key -out /etc/shibboleth/sp-signing.crt \
        -subj "/CN=webmail.example.org/O=ExampleOrg/C=DE" && \
    openssl req -x509 -newkey rsa:3072 -nodes -days 3650 \
        -keyout /etc/shibboleth/sp-encryption.key -out /etc/shibboleth/sp-encryption.crt \
        -subj "/CN=webmail.example.org/O=ExampleOrg/C=DE" && \
    chmod 600 /etc/shibboleth/sp-signing.key /etc/shibboleth/sp-encryption.key

# Apache must include the shibboleth apache config
RUN echo "Include /etc/shibboleth/shibboleth.apache.conf" > /etc/apache2/conf-enabled/shibboleth.conf

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/Shibboleth.sso/Status 2>/dev/null | grep -qE "200|401|403" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
