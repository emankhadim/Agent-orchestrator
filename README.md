# Agentic Orchestrator

I kept running into the same problem with agent projects I'd built before:
give an LLM a loop and a set of tools, and it mostly works — until it
doesn't. It skips a step, declares "done" without actually having an
answer, or gets stuck retrying the same tool call forever. Debugging why
is miserable because there's no fixed structure to point at — the
"logic" is just whatever the prompt happened to produce that run.

This project is my attempt at fixing that. Instead of letting the model
freely decide what happens next, I built an explicit state machine
around it: `intake → planning → tool execution → validation → complete`.
The model only ever *suggests* a move. A separate piece of code checks
whether that move is actually allowed from the current state before
anything happens. If it isn't, the run fails loudly instead of quietly
doing the wrong thing.

## How it's put together

**Backend (Python, FastAPI)**
- All the data that moves through the system — task requests, tool
  calls, tool results, state transitions — goes through Pydantic models
  with `extra="forbid"`, so a malformed payload gets rejected immediately
  instead of causing a weird bug three steps later.
- The state machine itself is just a small transition table + a guard
  function. It's boring on purpose — I wanted the one part of the system
  I could reason about with total confidence.
- Tools (a calculator, a knowledge-base search, a mocked web search) are
  registered as plain functions with a common signature, so adding a new
  one doesn't touch the orchestration loop at all.
- The knowledge-base search runs against a small in-memory vector store
  I wrote myself (hashed bag-of-words embeddings, cosine similarity) —
  no external embedding API needed to run the demo. It's built with the
  same shape a real vector DB client would have (`upsert` / `search`),
  so swapping it for an actual one later is a config change, not a
  rewrite.
- The model call itself sits behind one function, `propose_next_step()`.
  If an API key is set, it calls out to a real model; if not, a small
  rule-based fallback takes over so the whole thing still runs end to
  end with zero setup. I wanted to be able to demo this without handing
  anyone my API key.
- Every step gets logged as a structured span (trace id, timing,
  attributes) to a local file — enough to answer "what did the agent
  actually do on this run" after the fact, and shaped so it wouldn't be
  hard to point at a real tracing backend later.
- Runs persist to SQLite through SQLAlchemy. Swapping to Postgres is one
  environment variable.

**Frontend (Node.js, Express, TypeScript)**
- A small server that sits between the browser and the Python backend —
  proxies requests, keeps the browser from talking to FastAPI directly.
- A plain dashboard (no framework) where you can fire off a query and
  watch the state transitions happen in order, tool call included.
- The TypeScript types on this side are hand-mirrored from the Pydantic
  models on the backend, so I stayed honest about what fields actually
  exist across the API boundary.

## Running it

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8420
```
Runs immediately with no API key (falls back to the rule-based planner).
To use a real model:
```bash
export ANTHROPIC_API_KEY=sk-...
uvicorn app.main:app --reload --port 8420
```

**Frontend**
```bash
cd frontend
npm install
npm run build
BACKEND_URL=http://localhost:8420 PORT=3000 npm start
```
Then open `http://localhost:3000` and try something like `12 * (5 + 3)`
or `what tools does the orchestrator have`.

## Layout

```
backend/
  app/
    models.py         # Pydantic contracts
    state_machine.py  # transition table + guard
    tools.py           # calculator / knowledge_base_search / web_search
    vectorstore.py       # small in-memory vector store
    llm.py                # model call, with a no-key fallback
    tracing.py              # step-by-step span logging
    db.py                    # SQLAlchemy persistence
    orchestrator.py           # the actual loop
    main.py                    # FastAPI routes
frontend/
  src/
    server.ts    # Express server, proxies to the backend
    types.ts      # TS types mirroring the Pydantic models
  public/          # dashboard (HTML/CSS/vanilla JS)
```

## What I'd do next

- Swap the hand-written vector store for real Qdrant once I need more
  than a handful of documents
- Add a second, slower "critic" pass in validation instead of a plain
  presence check
- Push traces to something queryable instead of a flat file once there's
  more than one run to look at