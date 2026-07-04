<<<<<<< HEAD
# social-support-ai-platform
=======
# Social Support AI Workflow

- Project folder structure (`agents/`, `data/`, `observability/`, `tests/`, `scripts/`)
- `config.py` — centralized settings loader
- `agents/base.py` — base ReAct agent contract (Thought → Action → Observation)
- `observability/tracing.py` — in-memory trace recorder
- `data/synthetic_data_generator.py` — synthetic applicant + document generator

## Quickstart

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/phase1_smoke_test.py
```
>>>>>>> 95d49aa (Initial project structure, configuration, and synthetic data generator)
