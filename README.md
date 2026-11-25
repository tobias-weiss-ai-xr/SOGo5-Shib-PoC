# SOGo5 SSO PoC — webmail single sign-on without breaking mail clients

> **The idea:** give SOGo 5 webmail proper single sign-on via Shibboleth —
> **without ever touching the login path of Thunderbird, Outlook, or any
> other mail client.** SSO is strictly a *webmail* concern; IMAP/SMTP clients
> with saved passwords keep working unchanged.

## The trap this PoC avoids

In a university setting, webmail users log in with the same account they use
in Thunderbird & co. A naive SSO rollout (proxying all of SOGo behind a
SAML gate) breaks every non-browser client, because the browser SSO
credential never reaches IMAP/SMTP. This repository documents and implements
the decomposition that avoids that trap:

| Login path | Users | Mechanism | State |
|---|---|---|---|
| **Webmail (browser)** | humans, via central IdP | Shibboleth SP sidecar in front of SOGo → target: native OIDC | SP sidecar proven; OIDC is the decided end state |
| **Mail clients** | Thunderbird, Outlook, K-9, … | password (or XOAUTH2) directly against IMAP/SMTP | untouched by design — quality goal #1: *no mail breakage* |

## Architecture

One Kubernetes pod, one shared network namespace, two containers:

```
Browser ──TLS──▶ Apache + mod_shib (SP sidecar, :443)
                    │  /Shibboleth.sso/*  → shibd (SAML SP)
                    │  everything else    → proxied to 127.0.0.1:8080
                    ▼
                 sogod (SOGo 5, :8080)
                    │  REMOTE_USER / x-webobjects headers
                    ▼
                 LDAP (attributes) · IMAP/SMTP (XOAUTH2 or password)
```

- **SAML phase (proven in this PoC):** the sidecar terminates the IdP
  session and hands `REMOTE_USER` to SOGo
  (`SOGoTrustProxyAuthentication`). Works with any Shibboleth IdP;
  metadata is mounted at runtime — the manifests ship **placeholders**.
- **OIDC end state (decided):** SOGo speaks OIDC natively
  (`SOGoAuthenticationType = openid`) against an IdP OIDC plugin, and the
  webmail token doubles as the IMAP credential via **XOAUTH2**, validated
  by the mail server against the IdP's **published JWKS — no shared
  introspection secret, no master account**. Mail clients simply keep
  using passwords; `sub`/`uid` mapping carries the mailbox identity.

## Repository layout

| Path | Content |
|---|---|
| `image/` | Shibboleth-SP image (Apache + shibd, non-root, uid 1001 + `cap_net_bind_service`), idp-agnostic placeholder metadata |
| `k8s/` | Kustomize manifests: SOGo5 deployment with SP sidecar (shared netns), ConfigMap, Ingress, NetworkPolicies |
| `docs/arc42/` | Full arc42 architecture documentation (German): context, runtime, deployment view, ADRs, risk register |
| `docs/IMPLEMENTATION.md` | Step-by-step federation onboarding & implementation guide |

## Quickstart

```bash
# Build the SP sidecar image and push to your registry
docker build -t registry.example.org/shibboleth-sp:latest image/

# Adjust registry + hostnames in k8s/kustomization.yaml, then deploy
kubectl apply -k k8s/

# SP alive?
curl -k https://webmail.example.org/Shibboleth.sso/Status
```

Bring your own IdP: mount its metadata over `k8s/shibboleth/`'s placeholder
ConfigMap, set the SSO `entityID` in `shibboleth2.xml`, and open egress to
the IdP (see NetworkPolicy). Federation onboarding, SP registration and
attribute release (`uid` vs `eppn`!) are organizational steps — the
checklist lives in `docs/IMPLEMENTATION.md`.

## Status

Showcase of a completed PoC: SP sidecar, signed AuthnRequests, egress and
ingress verified against a real university IdP; OIDC/XOAUTH2 chain proven
end-to-end in a dedicated test stack (Shibboleth IdP + Dovecot + SOGo).
The production-wired variant (real metadata, network policies) lives in an
internal repository; everything here is sanitized and placeholder-based.

## License

MIT — see [LICENSE](LICENSE).
