# AppealPilot

**Verified, human-approved responses to denied medical claims.**

AppealPilot takes a denied claim, the payer's remittance codes and the clinical record,
and decides what the billing team should do: correct and resubmit, appeal with
evidence, request missing documentation, take no action, or escalate to a person. It
then drafts the response, with every factual statement tied to an exact quote from the
payer's policy or the patient's record, checks each quote and its meaning
independently, and stops at a human reviewer before anything is sent.

> **Prototype on synthetic data.** No real patient data, no submission to any payer,
> and no clinical advice. The Medicare sample cases use real CMS denial codes and quote
> public CMS regulations and manuals verbatim; the patients and claims are invented.

---

## How it works

```
 Denied claim + remittance codes + clinical record
        │
        ▼
 1. Rules engine ........ deterministic checks: filing limits, appeal windows,
                          duplicates, modifiers, authorization requirements
 2. Policy retrieval .... selects the payer's applicable clauses (BM25 + rule citations)
 3. Record review ....... extracts facts from the record, each with an exact quote
 4. Record checks ....... code checks the verified facts for contradictions
                          (laterality, patient identity) that force escalation
 5. Triage .............. chooses one of five actions, with reasons
 6. Drafting ............ writes the response; every assertion carries citations
 7. Verification ........ code confirms each quote exists in its source, then an
                          independent model judges whether it supports the claim;
                          failed drafts are rewritten (up to two times)
 8. Human approval ...... a reviewer approves, edits or rejects; nothing is final
                          before this step
```

Design principles:

- **Code decides what code can check.** Deadlines, duplicates, missing modifiers and
  record contradictions are established deterministically; models handle language and
  judgement only.
- **Every claim is grounded.** Assertions must quote the policy or the record word for
  word; unverifiable statements are rejected before a reviewer sees them.
- **Independent verification.** The judge runs on a different provider from the writer,
  so one model never grades its own work.
- **Fail safe.** Contradictory or ambiguous cases are escalated to a person rather than
  resolved by the model.
- **Resumable and auditable.** Every step is checkpointed in PostgreSQL and recorded in
  an audit trail with model, tokens and latency; a failed run resumes from its last step.

## Features

- Five-way triage of denials: correct and resubmit, appeal with evidence, request
  documentation, no action, escalate to a person
- Citation-checked drafts with a self-correcting rewrite loop
- Live run progress over server-sent events
- Reviewer interface: source panel with highlighted quotes and links to official
  sources, verification status per assertion, approve / edit / reject with reason
- Medicare Part B policy set quoted from 42 CFR and CMS manuals, with three
  ready-to-run sample cases
- Evaluation harness: labelled cases, a single-prompt baseline for comparison, and a
  planted-error set for the verifier
- Provider-agnostic model clients (Groq, Gemini, Ollama, mock) with retries, rate-limit
  handling, request sizing and a response cache

## Tech stack

| Layer | Technology |
|---|---|
| API | Python 3.12, FastAPI, Pydantic v2 |
| Workflow | LangGraph with a PostgreSQL checkpointer |
| Data | PostgreSQL, SQLAlchemy 2 (async), Alembic; queries as SQL functions |
| Architecture | Layered (routers → services → repositories), dependency injection |
| Models | Groq (`gpt-oss-120b`) for agents, Google Gemini for the independent judge |
| Web | Next.js 16 (App Router, Server Components, Server Actions), React 19, TypeScript, Tailwind CSS 4, Radix UI |
| Quality | Ruff, mypy (strict), pytest, Vitest, Testing Library, Playwright, axe accessibility checks, GitHub Actions |

## Getting started

### Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- PostgreSQL 16 or later
- Node.js 20.9 or later (for the web app)

### 1. Configure

Create `env/.env` (git-ignored). The database URL is the only required setting:

```
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/appealpilot
```

Without model settings the agents run on a built-in mock, so the service starts with no
API keys. To use real models:

```
AGENT_LLM_PROVIDER=groq
AGENT_LLM_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=...
JUDGE_LLM_PROVIDER=gemini
JUDGE_LLM_MODEL=gemini-3.1-flash-lite
GEMINI_API_KEY=...
# Groq free tier only: size each request to the 8,000-token per-minute limit.
GROQ_REQUEST_TOKEN_LIMIT=8000
```

All settings and their defaults are defined in `app/core/settings.py`.

### 2. Run the API

```
uv sync --all-packages
uv run alembic upgrade head
uv run python -m app.main
```

The API listens on http://127.0.0.1:8000; interactive documentation is at `/docs` and
readiness at `/health/ready`. Tables are created only by migrations: the service checks
the schema at start-up and refuses to run against an unmigrated database.

### 3. Run the web app

```
cd web
npm install
npm run dev
```

Open http://localhost:3000 and choose **New case** to run one of the Medicare samples.
The web app's only setting is `API_URL` (default `http://127.0.0.1:8000`); the browser
never calls the API directly.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/cases` | Submit a denied claim; the workflow starts in the background |
| `GET` | `/cases` | List cases, paginated, filterable by status |
| `GET` | `/cases/{id}` | A case with its full state: findings, clauses, facts, draft, verification, audit |
| `GET` | `/cases/{id}/events` | Live progress as server-sent events |
| `POST` | `/cases/{id}/decision` | Approve, edit and approve, or reject (with a reason) |
| `POST` | `/cases/{id}/retry` | Resume a failed case from its last completed step |
| `GET` | `/samples` | Ready-to-run sample cases, re-dated to today |

Every response uses one envelope: `{ success, data, error, meta }`.

## Testing

```
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

```
cd web
npm run check       # lint, types, unit and component tests
npm run test:e2e    # Playwright against a production build and a mock API
```

Tests never call a real model. Integration tests run against PostgreSQL when
`TEST_POSTGRES_URL` is set. CI runs all of the above, applies the migrations, checks they
match the models, and fails if the web app's generated API types drift from the API.

## Evaluation

The evaluation compares the workflow with a single-prompt baseline: the same model and
the same policy clauses in one call, without the rules engine, record review, record
checks or verification.

```
uv run python -m tests.evals.runner --run NAME     # run the development set
uv run python -m tests.evals.report --run NAME     # summarise a run
```

- **90 labelled cases**: 60 for development, 30 locked for release runs only. Each case
  records its expected action, acceptable alternatives and the reasoning behind them.
- **Planted-error set**: drafts with deliberately wrong citations or claims, to measure
  how many errors the verifier catches.
- Metrics include action accuracy, unsafe actions, escalation recall, citation accuracy,
  model calls and cost per case.

## Project structure

```
app/
  agents/        LangGraph workflow: state, nodes, routing, prompts
  clients/       model provider clients behind interfaces
  services/      business rules: rules engine, retrieval, agents, verification
  repositories/  data access through SQL functions
  routers/       HTTP endpoints
  schemas/       request, response and domain models
  sql/           database functions, loaded by migrations
alembic/         database migrations
seeders/         payer policies and sample cases
scripts/         API contract export and test fixture generation
tests/           unit, API, integration tests and the evaluation harness
web/             the reviewer web app (Next.js)
```

## License

[MIT](LICENSE)
