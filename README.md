# Social Support AI Workflow — Prototype

An agentic GenAI system that automates intake, validation, eligibility
assessment, and decisioning for government social support and economic
enablement applications.

Turns a 5–20 working day manual process into a same-session, chat-driven
experience: submit an application with supporting documents and get an
automated decision (or a clear "routed to a human reviewer" explanation)
in minutes, plus personalized upskilling/job-matching recommendations.

> **Built incrementally across 10 Git-tracked phases.** See
> [`PHASED_DEVELOPMENT_GUIDE.md`](./PHASED_DEVELOPMENT_GUIDE.md) for the
> complete phase-by-phase build history: what was added, how to install
> and configure it, how it connects to the previous phase, how to run it,
> how it was verified, the Git commit message used, and troubleshooting
> notes for each of the 10 phases. Run `git log --oneline` in this repo to
> see the 10 commits in order.

## What's inside

| Layer | Tool | Added in |
|---|---|---|
| Front-end | Streamlit | Phase 6 (chat tab in Phase 8) |
| API | FastAPI | Phase 6 |
| Orchestration | LangGraph (StateGraph) | Phase 5 |
| Reasoning framework | ReAct (Thought → Action → Observation) | Phase 1 (`agents/base.py`) |
| Agents | Custom Python | Extraction (2), Validation (3), Eligibility (4), Decision (5), Enablement (9) |
| ML | scikit-learn `HistGradientBoostingClassifier` | Phase 4 |
| LLM | Ollama (local, OpenAI-compatible API) | Phase 8 |
| Relational DB | PostgreSQL (SQLite fallback) | Phase 7 |
| Document store | MongoDB (in-memory fallback) | Phase 7 |
| Vector DB | Qdrant (in-memory fallback) | Phase 8 |
| Graph DB | Neo4j (in-memory fallback) | Phase 10 |
| Observability | Langfuse (optional) + local audit trail | Phase 7 (DB trail), Phase 10 (Langfuse) |

**Every external service has a graceful in-process fallback**, so the
whole pipeline runs standalone with zero infrastructure for demoing or
grading — `docker-compose.yml` brings up the full production-shaped stack
when you want it.

## Quickstart (zero infrastructure — fastest way to see it work)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 1. Generate synthetic applicants + sample documents
python -c "from data.synthetic_data_generator import generate_applicants, generate_sample_documents; generate_applicants(2000); generate_sample_documents(5)"

# 2. Train the eligibility model
python ml/train_eligibility_model.py

# 3. Run the automated test suite (all 10 phases' worth of functionality)
pytest tests/ -v
```

## Quickstart (full stack, API + UI)

```bash
cp .env.example .env

# Terminal 1: API
uvicorn api.main:app --reload --port 8000

# Terminal 2: UI
streamlit run frontend/streamlit_app.py
```

Open http://localhost:8501, fill in the application form, attach files
from `data/synthetic/sample_documents/` and submit. Without
Postgres/Mongo/Qdrant/Neo4j/Ollama running, everything still works via the
in-memory/rule-based fallbacks — start the local LLM to unlock full
generative reasoning instead of the deterministic fallback text.

## Full production-shaped stack (Docker)

```bash
docker compose up -d --build
docker exec -it ssai-phased-ollama-1 ollama pull llama3.1:8b-instruct-q4_K_M
docker exec -it ssai-phased-ollama-1 ollama pull llava:13b
```

- API: http://localhost:8000/docs (OpenAPI/Swagger)
- UI: http://localhost:8501
- Langfuse: http://localhost:3000
- Neo4j browser: http://localhost:7474

## Repository layout

```
config.py                    Centralized settings (env-driven, safe defaults) — grows each phase
data/synthetic_data_generator.py   Synthetic applicants + multimodal sample documents (Phase 1)
db/                           models.py, database.py, mongo_store.py (Phase 7); vector_store.py (Phase 8); graph_store.py (Phase 10)
ml/train_eligibility_model.py Trains + persists the eligibility classifier (Phase 4)
agents/
  base.py                     ReAct base class (Phase 1)
  llm_client.py                Local LLM (Ollama) client with offline fallback (Phase 8)
  data_extraction_agent.py     Multimodal ingestion (Phase 2, LLM-upgraded Phase 8)
  data_validation_agent.py     Cross-document consistency checks (Phase 3, LLM-upgraded Phase 8)
  eligibility_agent.py         Feature engineering + ML scoring (Phase 4)
  decision_agent.py            Policy thresholds + explanation (Phase 5, LLM-upgraded Phase 8)
  enablement_agent.py          Upskilling/job-matching recommendations (Phase 9)
  orchestrator.py              Master Orchestrator (Phase 5, extended Phase 9)
observability/tracing.py       Trace sink: in-memory (1) + DB (7) + Langfuse (10)
api/main.py                    FastAPI application (Phase 6, extended 7/8/9/10)
frontend/streamlit_app.py      Chat-driven UI (Phase 6, chat tab Phase 8, enablement display Phase 9)
tests/                         pytest suite (Phase 10, consolidates all phases)
scripts/                       Per-phase smoke tests (phase1_smoke_test.py ... phase9_smoke_test.py)
docs/                          Architecture diagrams + Solution Summary + this guide
docker-compose.yml             Full local stack (Postgres/Mongo/Qdrant/Neo4j/Ollama/Langfuse) — Phase 10
PHASED_DEVELOPMENT_GUIDE.md    Full 10-phase build history with setup/run/verify/commit/troubleshoot per phase
```

## Design notes

- **Human-in-the-loop by design.** High-severity data-inconsistency flags
  (e.g. expired Emirates ID, mismatched applicant name) always force
  routing to a human case officer regardless of the ML score — automation
  stays accountable rather than fully autonomous.
- **Every agent's reasoning is inspectable.** Each specialist agent logs a
  Thought → Action → Observation trace per step, surfaced live in the
  Streamlit UI, persisted to the `agent_traces` table, and mirrored to
  Langfuse when configured.
- **Offline-first.** No component throws or blocks if an external service
  is unreachable — every phase was verified to run standalone before the
  next phase was built on top of it (see `PHASED_DEVELOPMENT_GUIDE.md`).

See `docs/Solution_Summary.docx` for the full solution write-up:
architecture, tool justification, modular breakdown, and future
improvements / integration roadmap.
