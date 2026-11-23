---
id: ADR-002
title: Timeouts, retries and circuit breakers for external APIs
status: accepted
date: 2026-03-02
services: [order, payment, inventory, notification]
supersedes: null
---

# ADR-002: Timeouts, retries and circuit breakers for external APIs

## Context
Calls to external providers (payment provider, warehouse API, tax API, SMTP) had no timeout.
When a provider was slow, threads piled up and the slowdown spread to our own services.

## Decision
Every call to an external API has a timeout of 3 seconds.
Failed calls are retried at most 3 times with exponential backoff.
A circuit breaker opens after 5 consecutive failures and stays open for 30 seconds.

## Consequences
A slow provider causes fast, visible errors ("timed out", "circuit breaker opened") instead of
silent queueing. Retries must be idempotent. Retry storms are avoided by the backoff and the retry cap.