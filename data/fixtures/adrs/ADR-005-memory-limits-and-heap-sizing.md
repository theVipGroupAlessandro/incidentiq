---
id: ADR-005
title: Memory limits and heap sizing per service
status: accepted
date: 2026-06-30
services: [gateway, order, payment, inventory, notification]
supersedes: ADR-003
---

# ADR-005: Memory limits and heap sizing per service

## Context
The fixed 512 MiB limit of ADR-003 was too small for order and inventory, which were killed
repeatedly (OOMKilled) during peaks and large exports.

## Decision
Each service gets a memory limit based on measured usage: 1024 MiB for gateway, payment and notification,
2048 MiB for order and inventory. The JVM heap is set to 75% of the container limit.
In-process caches and queues must be bounded, and large data must be processed as streams.

## Consequences
Out-of-memory restarts should become rare. An OutOfMemoryError now usually points to a leak or an
unbounded structure, not to a limit that is too small. Limits are reviewed every quarter.