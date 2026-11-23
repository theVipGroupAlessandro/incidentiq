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
- [ ] Embeddings and retrieval
- [ ] Docker Compose (Postgres + pgvector, Neo4j) — blocked: waiting for administrator rights
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

## Installation
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt

## Usage
Generate the synthetic dataset:
python -m data.generate

Run the tests:
python -m pytest

