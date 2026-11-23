---
id: ADR-001
title: Database connection pool limits
status: accepted
date: 2026-02-10
services: [order, payment, inventory]
supersedes: null
---

# ADR-001: Database connection pool limits

## Context
The shared PostgreSQL cluster accepts at most 200 connections. Services opened connections freely,
and during peaks one service could starve the others.

## Decision
Every service that uses the database gets a fixed connection pool of at most 50 connections.
Requests wait at most 5 seconds for a free connection, then fail with a clear error.
Pool usage is monitored and an alert fires when it stays above 80% for 5 minutes.
Batch jobs must use their own, smaller pool and never share the pool of live traffic.

## Consequences
A single service can no longer exhaust the whole database. Under heavy load a service fails fast with
"connection pool exhausted" instead of hanging, so its callers see timeouts and 5xx errors.
Pool size changes must go through review.