# Agentic Orchestrator

Perosonal Project 


A small, fully-working full-stack agent orchestration platform, built to
exercise a specific architecture: **the LLM proposes, a deterministic
state machine decides.** No brittle prompt-chaining — every transition
the agent can make is enumerated in code and validated before it happens.

## Architecture

```
┌─────────────────────┐      REST       ┌──────────────────────────┐
│  Node.js / Express   │ ───────────────▶│   FastAPI (Python)       │
│  + TypeScript         │◀─────────────── │   orchestration service │
│  dashboard (BFF)      │                 │                          │
└─────────────────────┘                 │  ┌────────────────────┐  │
                                          │  │ Pydantic contracts │  │
                                          │  │ (strict typing)    │  │
                                          │  └────────────────────┘  │
                                          │  ┌────────────────────┐  │
                                          │  │ Deterministic       │  │
                                          │  │ state machine       │  │
                                          │  │ (legal-transition   │  │
                                          │  │  table)             │  │
                                          │  └────────────────────┘  │
                                          │  ┌────────────────────┐  │
                                          │  │ Tool registry:       │  │
                                          │  │ calculator,          │  │
                                          │  │ knowledge_base_search│  │
                                          │  │ (in-memory vector    │  │
                                          │  │  store), web_search  │  │
                                          │  └────────────────────┘  │
                                          │  ┌────────────────────┐  │
                                          │  │ LLM abstraction      │  │
                                          │  │ layer (LiteLLM-style,│  │
                                          │  │ demo fallback if no  │  │
                                          │  │ API key set)         │  │
                                          │  └────────────────────┘  │
                                          │  ┌────────────────────┐  │
                                          │  │ Structured tracing   │  │
                                          │  │ (OTel-shaped spans,  │  │
                                          │  │  Langfuse-swappable) │  │
                                          │  └────────────────────┘  │
                                          │  ┌────────────────────┐  │
                                          │  │ SQLAlchemy + SQLite  │  │
                                          │  │ (Postgres-ready)     │  │
                                          │  └────────────────────┘  │
                                          └──────────────────────────┘
```

### Why a state machine instead of a prompt chain

Prompt chains ("ask the LLM what to do, do it, ask again") are flexible
but non-deterministic: nothing stops the model from skipping validation,
looping forever, or declaring success with no actual answer. Here, the
LLM's job is narrowed to *proposing* a transition; `state_machine.py`
holds the only table of legal transitions and rejects anything else.
The result: you can swap models, rewrite prompts, or add tools, and the
process guarantees (e.g. "no run reaches COMPLETE without passing
VALIDATION with a non-empty answer") never change.

## Running it

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8420
```

Runs with zero configuration in **demo mode** (a small rule-based planner
stands in for the LLM). To use a real model, set an API key LiteLLM
recognizes, e.g.:

```bash
export ANTHROPIC_API_KEY=sk-...
uvicorn app.main:app --reload --port 8420
```

### Frontend

```bash
cd frontend
npm install
npm run build
BACKEND_URL=http://localhost:8420 PORT=3000 npm start
```

Open `http://localhost:3000`.

## Project layout

```
backend/
  app/
    models.py        # Pydantic v2 contracts (strict, extra="forbid")
    state_machine.py  # Legal-transition table + guard
    tools.py           # calculator / knowledge_base_search / web_search
    vectorstore.py      # in-memory Qdrant-shaped vector store
    llm.py               # LiteLLM-style provider abstraction + demo fallback
    tracing.py            # OTel-shaped structured spans -> traces.jsonl
    db.py                  # SQLAlchemy persistence (SQLite, Postgres-ready)
    orchestrator.py         # ties it all together
    main.py                  # FastAPI routes
frontend/
  src/
    server.ts    # Express BFF, proxies to FastAPI
    types.ts      # TS contracts mirroring the Pydantic models
  public/          # dashboard (HTML/CSS/vanilla JS)
```

## What this demonstrates

- Strictly-typed API contracts end-to-end (Pydantic on the backend, hand-
  mirrored TypeScript types on the frontend)
- A deterministic, auditable agent architecture instead of an unbounded
  prompt loop
- A pluggable tool-calling layer
- A provider-agnostic LLM layer that degrades gracefully without an API key
- An in-memory vector-search tool with a Qdrant-shaped interface, swappable
  for a real Qdrant collection
- Structured span-based tracing, swappable for a real Langfuse/OTel exporter
- A Node.js/TypeScript BFF talking REST to a Python service — a realistic
  polyglot full-stack split
