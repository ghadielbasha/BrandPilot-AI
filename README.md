# BrandPilot AI

BrandPilot AI is an AI-powered branding and digital-marketing assistant for OMSAR. It is an internal-team pilot for an OMSAR-controlled server and does not publish automatically.

## Overview and features

BrandPilot combines Streamlit, local Ollama generation, governed OMSAR and Dawlati knowledge, deterministic validation, one controlled repair attempt, local authentication, role-based review, SQLite persistence, immutable versions, and audit history. Human approval is required before publication. The LLM is never the source of truth.

## Architecture and security model

The browser reaches Streamlit through an HTTPS reverse proxy. UI actions call service-layer authorization and workflow rules backed by parameterized repository queries. SQLite stores users, campaigns, versions, and audit events. Passwords use Argon2id hashes. Ollama remains server-side and uses configurable `qwen3:4b` by default.

The pipeline is input security validation → approved strategy → governed knowledge retrieval → local model → terminology normalization → output security, terminology, factual, and language validation. Failure permits exactly one repair with the same grounding, followed by every validator again; a second failure blocks the draft.

Only explicitly approved records and approved source IDs load. Retrieval is deterministic and preserves provenance. Dawlati service capabilities are included only when the approved service catalog provides evidence; missing or empty catalogs never authorize invented services.

## Human workflow and roles

- `ADMIN`: user management plus all campaign, review, and audit functions.
- `EDITOR`: create, generate, revise, and submit; cannot approve.
- `REVIEWER`: review, approve/reject, comment, and inspect campaign history.

Workflow: Draft → Submitted for Review → Approved, or Submitted → Rejected → revised Draft → resubmitted. A creator cannot approve their own campaign. Approved versions remain immutable; later edits create a new draft version.

## Local installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
ollama pull qwen3:4b
python scripts/init_db.py
python scripts/create_admin.py
streamlit run app.py
```

On Linux activate with `source .venv/bin/activate`. Start Ollama with `ollama serve` when it is not already a service. Run tests with `python -m unittest discover -s tests -v`.

## Environment variables

Use `.env.example` as a reference and inject protected server configuration outside Git: `BRANDPILOT_DB_PATH`, `OLLAMA_HOST`, `BRANDPILOT_MODEL`, and `BRANDPILOT_ENV`.

## Project structure

- `app.py`: Streamlit UI
- `services.py`, `repositories.py`, `database.py`, `auth.py`: application and persistence
- `grounding_engine.py`, `knowledge_loader.py`, `knowledge/`: governed knowledge
- `ai_engine.py`, `content_generator.py`, `repair_engine.py`: strategy and controlled generation
- `validators/`: deterministic safety validators
- `scripts/`: initialization, admin bootstrap, and backups
- `docs/DEPLOYMENT.md`: Windows/Linux deployment and restore guidance

## Limitations and privacy

SQLite suits the initial small internal pilot, not a high-concurrency public service. Publication remains manual. Keep sensitive data out of briefs, do not expose Ollama or database files publicly, retain only necessary data, protect backups, and review every approved draft. See `docs/DEPLOYMENT.md` for server controls.
