---
id: ADR-004
title: Rotation of credentials and certificates
status: accepted
date: 2026-08-20
services: [gateway, order, payment, inventory, notification]
supersedes: null
---

# ADR-004: Rotation of credentials and certificates

## Context
API keys, client secrets and TLS certificates were stored in configuration files and rotated by hand.
Several outages happened because a credential expired unnoticed.

## Decision
All credentials and certificates are stored in the secrets vault.
They are rotated automatically every 90 days, and an alert fires 14 days before any expiry.
Signing keys are rotated with an overlap period in which both the old and the new key are valid.

## Consequences
Expired credentials should no longer cause outages. A 401 Unauthorized from an external system
now points first to the vault: check the expiry date and the last rotation of the credential.