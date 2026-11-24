# IncidentIQ — Offline AI Incident Investigator

Training proof of concept for the decisionX project (THEVIPGROUP, AI & Machine Learning).
An assistant that investigates software incidents using the service dependency graph,
semantic search over logs, incidents and ADRs, and a locally hosted language model.
Fully offline, using synthetic data.

## Status
- [x] Python environment (venv)
- [x] Service topology and upstream caller lookup (Python, with tests)
- [x] Synthetic data: 707 logs, 20 incidents, 5 ADRs (see docs/dataset.md)
- [ ] Labeled evaluation queries
- [x] Embeddings and retrieval (in memory: BGE-small, MiniLM; log deduplication)
- [x] Docker Compose (Postgres + pgvector, Neo4j) with health checks — engine on a company server via SSH
- [ ] Local LLM (Ollama)
- [ ] API (FastAPI) and UI (Streamlit)

## Development machine
| Component | Value |
|---|---|
| Operating system | Windows 11, no administrator rights |
| CPU | Intel Core i5-1145G7 @ 2.60 GHz (4 cores / 8 threads) |
| RAM | 16 GB (3200 MT/s) |
| GPU | Integrated Intel Iris Xe (no NVIDIA GPU: the LLM runs on CPU only) |
| Python | 3.12.7 |
| Docker | CLI 29.10 + Compose 5.8 on the laptop; engine on a company server (rootless), reached over SSH |

### Installation

### 1. Python environment
```
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

### 2. Configuration
```
copy .env.example .env
```
Edit `.env` and set your own passwords (Neo4j: at least 8 characters). `.env` is git-ignored.

### 3. Databases (Docker)
```
docker compose --env-file .env -f infra/docker-compose.yml up -d
docker compose --env-file .env -f infra/docker-compose.yml ps
```
Wait until both services are `(healthy)`.

**Remote Docker engine.** On the development laptop Docker cannot be installed (no working admin
elevation), so the Docker engine runs on a company server and is used over SSH:
- Docker CLI and Compose installed with `winget` (no admin needed);
- SSH alias `devsrv01` in `~/.ssh/config`, then
  `docker context create devsrv01 --docker "host=ssh://devsrv01"` and `docker context use devsrv01`;
- the server is shared and port 5432 was taken, so host ports are configurable in `.env`
  (`POSTGRES_HOST_PORT`, `NEO4J_HTTP_HOST_PORT`, `NEO4J_BOLT_HOST_PORT`); defaults 15432, 17474, 17687;
- an SSH tunnel maps them back to the standard ports on the laptop (keep it open while working):
  ```
  ssh -N -L 5432:127.0.0.1:15432 -L 7474:127.0.0.1:17474 -L 7687:127.0.0.1:17687 devsrv01
  ```

With a local Docker engine, no tunnel is needed: set the host ports to 5432, 7474 and 7687.

### 4. Check connectivity
```
python -m app.healthcheck
```
Expected: `[ OK ]` for PostgreSQL (with pgvector available) and Neo4j.
Neo4j Browser: http://localhost:7474 (user `neo4j`, password from `.env`).

## Usage
Generate the synthetic dataset:
python -m data.generate

Run the tests:
python -m pytest

Try a search:
python -m app.search_demo “payment cannot get a database connection” --model minilm


