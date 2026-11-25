#!/bin/bash
# Shibboleth SP sidecar entrypoint: start shibd, then Apache.
# SPDX-License-Identifier: Apache-2.0

set -e

# Ensure daemon dirs exist (writable state lives on emptyDir /tmp in K8s)
mkdir -p /var/log/shibboleth /var/run/shibboleth /var/cache/shibboleth /var/run/apache2 /var/lock/apache2 /var/log/apache2
chown -R shib:shib /var/log/shibboleth /var/run/shibboleth /var/cache/shibboleth /var/run/apache2 /var/lock/apache2 /var/log/apache2 2>/dev/null || true

# Logs to stdout so `kubectl logs` works (container logs were empty before).
ln -sf /dev/stdout /var/log/shibboleth/shibd.log 2>/dev/null || true
ln -sf /dev/stdout /var/log/shibboleth/transaction.log 2>/dev/null || true
ln -sf /dev/stdout /var/log/apache2/access.log 2>/dev/null || true
ln -sf /dev/stdout /var/log/apache2/error.log 2>/dev/null || true

# Start shibd (SP daemon) in background, foreground mode (-f = stay in front
# in the background job; shibd -s was invalid in this build).
if [ ! -S /var/run/shibboleth/shibd.sock ]; then
    /usr/sbin/shibd -f &
fi

sleep 2

export APACHE_RUN_USER=shib APACHE_RUN_GROUP=shib
export APACHE_PID_FILE=/var/run/apache2/apache2.pid
export APACHE_RUN_DIR=/var/run/apache2
export APACHE_LOCK_DIR=/var/lock/apache2
export APACHE_LOG_DIR=/var/log/apache2

exec /usr/sbin/apache2 -DFOREGROUND
