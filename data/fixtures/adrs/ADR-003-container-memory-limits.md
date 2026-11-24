---
id: ADR-003
title: Fixed container memory limit of 512 MiB
status: superseded
date: 2025-11-20
services: [gateway, order, payment, inventory, notification]
supersedes: null
---

# ADR-003: Fixed container memory limit of 512 MiB

## Context
Containers ran without memory limits, and one service could use all the memory of a host.

## Decision
Every container gets a fixed memory limit of 512 MiB, with the JVM heap set to the default.

## Consequences
Hosts are protected, but services with larger workloads are killed by the out-of-memory killer
(OOMKilled). Superseded by ADR-005.