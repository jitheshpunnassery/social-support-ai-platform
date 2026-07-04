# Social Support AI Workflow — Prototype

An agentic GenAI system that automates intake, validation, eligibility
assessment, and decisioning for government social support and economic
enablement applications — built for a locally-hosted, multimodal, agentic
AI pipeline challenge.

Turns a 5–20 working day manual process into a same-session, chat-driven
experience: submit an application with supporting documents and get an
automated decision (or a clear "routed to a human reviewer" explanation)
in minutes, plus personalized upskilling/job-matching recommendations.

## What's inside

| Layer | Tool | Purpose |
|---|---|---|
| Front-end | Streamlit | Chat-driven application intake, status lookup, Q&A chatbot |
| API | FastAPI | `/applications` (submit + fetch), `/chat` (RAG chatbot), `/health` |
| Orchestration | LangGraph (StateGraph) | Wires the 5 specialist agents into one pipeline with conditional routing |
| Reasoning framework | ReAct (Thought → Action → Observation) | Implemented per-agent in `agents/base.py`, logged via `observability/tracing.py` |
| Agents | Custom Python | Data Extraction, Data Validation, Eligibility Assessment, Decision Recommendation, Economic Enablement |
| ML | scikit-learn `HistGradientBoostingClassifier` | Eligibility scoring (see `ml/train_eligibility_model.py` for rationale) |
| LLM | Ollama (local, OpenAI-compatible API) | Free-text extraction, validation summaries, decision explanations, chatbot |
| Relational DB | PostgreSQL (SQLite fallback) | Applicants, applications, decisions, audit trail |
| Document store | MongoDB (in-memory fallback) | Raw multimodal document content |
| Vector DB | Qdrant (in-memory fallback) | RAG over policy text + precedent case retrieval |
| Graph DB | Neo4j (in-memory fallback) | Applicant/household/document relationship graph (duplicate/fraud signals) |
| Observability | Langfuse (optional) | End-to-end agent trace/latency/cost tracking |

**Every external service has a graceful in-process fallback** (see
`config.py` / `db/*.py`), so the whole pipeline runs standalone with zero
infrastructure for demoing or grading — `docker-compose.yml` brings up the
full production-shaped stack when you want it.

## Quickstart (zero infrastructure — fastest way to see it work)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 1. Generate synthetic applicants + sample documents
python data/synthetic_data_generator.py

# 2. Train the eligibility model
python ml/train_eligibility_model.py

# 3. Run the full pipeline against a synthetic application, no services needed
python scripts/smoke_test_pipeline.py

# 4. Run the automated test suite
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
from `data/synthetic/sample_documents/` (generated in step 1 above) and
submit. Without Postgres/Mongo/Qdrant/Neo4j/Ollama running, everything
still works via the in-memory/rule-based fallbacks described above — start
the local LLM (below) to unlock full generative reasoning instead of the
deterministic fallback text.

## Full production-shaped stack (Docker)

```bash
docker compose up -d --build
docker exec -it social-support-ai-ollama-1 ollama pull llama3.1:8b-instruct-q4_K_M
docker exec -it social-support-ai-ollama-1 ollama pull llava:13b
```

- API: http://localhost:8000/docs (OpenAPI/Swagger)
- UI: http://localhost:8501
- Langfuse: http://localhost:3000
- Neo4j browser: http://localhost:7474

## Repository layout

```
config.py                    Centralized settings (env-driven, safe defaults)
data/synthetic_data_generator.py   Synthetic applicants + multimodal sample documents
db/                           models.py (Postgres/SQLite), mongo_store.py, vector_store.py, graph_store.py
ml/train_eligibility_model.py Trains + persists the eligibility classifier
agents/
  base.py                     ReAct base class + trace logging
  llm_client.py                Local LLM (Ollama) client with offline fallback
  data_extraction_agent.py     Multimodal ingestion
  data_validation_agent.py     Cross-document consistency checks
  eligibility_agent.py         Feature engineering + ML scoring
  decision_agent.py            Policy thresholds + natural-language explanation
  enablement_agent.py          Upskilling/job-matching recommendations
  orchestrator.py              Master Orchestrator (LangGraph, sequential fallback)
observability/tracing.py       Unified trace sink (in-memory + Langfuse + DB)
api/main.py                    FastAPI application
frontend/streamlit_app.py      Chat-driven UI
tests/test_pipeline.py         pytest suite (agents + validation rules)
scripts/                       Standalone smoke tests (pipeline-only, API-only)
docs/                          Architecture diagrams + this solution summary
docker-compose.yml             Full local stack (Postgres/Mongo/Qdrant/Neo4j/Ollama/Langfuse)
```

## Design notes

- **Human-in-the-loop by design.** High-severity data-inconsistency flags
  (e.g. expired Emirates ID, mismatched applicant name) always force
  routing to a human case officer regardless of the ML score — this keeps
  the automation accountable rather than fully autonomous, directly
  addressing the brief's "subjective decision-making" pain point without
  removing human oversight for edge cases.
- **Every agent's reasoning is inspectable.** Each specialist agent logs a
  Thought → Action → Observation trace per step, surfaced live in the
  Streamlit UI, mirrored to Langfuse, and persisted to the `agent_traces`
  table for audit.
- **Offline-first.** No component throws or blocks if an external service
  is unreachable — this made local development and automated testing
  possible without spinning up the full docker-compose stack every time.

See `docs/Solution_Summary.docx` for the full write-up: architecture,
tool justification, modular breakdown, and future improvements /
integration roadmap.
