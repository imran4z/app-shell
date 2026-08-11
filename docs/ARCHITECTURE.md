# Architecture

Diagrams for the shipped template. **If you build an app from this
template, regenerate this file for your domain** (CLAUDE.md build step 8):
keep the diagram structure, swap the example entities and tools for
yours. GitHub renders the Mermaid blocks directly, so this file is the
always-current architecture page for your repo.

## System overview

One container, one port. FastAPI serves both the API and the built SPA;
Postgres is the source of truth; the assistant reaches Anthropic through
a single instrumented wrapper.

```mermaid
flowchart LR
    subgraph Browser
        SPA["React SPA<br/>Vite + Tailwind v4<br/>polling + SSE, no websockets"]
    end

    subgraph Container["Docker container (127.0.0.1:8765)"]
        API["FastAPI<br/>routes: items, profiles, users,<br/>assistant, health"]
        RUNS["Assistant run registry<br/>(in-memory event buffer,<br/>replay-then-tail SSE)"]
        LOOP["Agent loop (worker thread)<br/>tool catalog + approval gate"]
        WRAP["call_anthropic()<br/>one instrumented wrapper:<br/>TTFT, cost, streaming"]
        SPAFILES["Built SPA (ui/dist)<br/>served from the same port"]
    end

    subgraph Data["Postgres 16"]
        TABLES[("items - profiles - users<br/>assistant_conversations/turns<br/>llm_calls - _migrations")]
    end

    CLI["appshell CLI<br/>(canonical business logic:<br/>db, seeds, serve, doctor)"]
    ANTHROPIC["Anthropic API"]

    SPA -->|"/api/* JSON + SSE"| API
    SPA -.->|first load| SPAFILES
    API --> TABLES
    API --> RUNS
    RUNS --> LOOP
    LOOP --> WRAP
    LOOP --> TABLES
    WRAP --> ANTHROPIC
    WRAP -->|cost ledger, best effort| TABLES
    CLI --> TABLES
```

## Request paths

Plain resources are synchronous and boring on purpose. The assistant is
the one asynchronous surface, and its durable state lives in Postgres,
never in the event buffer.

```mermaid
sequenceDiagram
    participant U as Browser
    participant A as FastAPI
    participant R as Run registry
    participant L as Agent loop (thread)
    participant C as Anthropic
    participant P as Postgres

    Note over U,P: Resource request (items / profiles / users)
    U->>A: GET /api/items
    A->>P: repository query (session_scope)
    P-->>A: rows -> pydantic models
    A-->>U: {entries, total, limit, offset}

    Note over U,P: Assistant turn with an approval pause
    U->>A: POST /api/assistant/chat (SSE response)
    A->>P: persist user turn
    A->>R: start_run()
    R->>L: run loop in worker thread
    L->>P: rebuild messages from ALL turns
    L->>C: stream model call (tools attached)
    C-->>L: text deltas + tool_use blocks
    L-->>U: delta events (via registry tail)
    L->>P: persist assistant turn (with tool_calls)
    alt tool needs approval
        L-->>U: approval_required, run pauses
        U->>A: POST .../resume {decision}
        A->>R: start_run(resume)
        R->>L: execute or decline pending calls
    end
    L->>P: persist tool turn
    L->>C: continue loop (max 5 iterations)
    L-->>U: done
```

## Storage contract

Every persisted entity follows the same four steps. Skipping the
`drop_all()` registration is the classic silent breakage.

```mermaid
flowchart TD
    M["1. migrations/NNNN_name.sql<br/>(CREATE TABLE IF NOT EXISTS,<br/>TEXT CHECK states, JSONB, trigger)"]
    D["2. register table in drop_all()<br/>child tables first"]
    R["3. repository class<br/>(explicit Session, never commits)"]
    E["4. export from storage/__init__.py"]
    M --> D --> R --> E
```

## Screenshots

Light theme, captured from the seeded demo. Regenerate with
`just screenshots` while the app is running.

| Dashboard | Items |
| --- | --- |
| ![Dashboard](screenshots/dashboard.png) | ![Items](screenshots/items.png) |

| Profiles | Profile detail | Users |
| --- | --- | --- |
| ![Profiles](screenshots/profiles.png) | ![Profile detail](screenshots/profile-detail.png) | ![Users](screenshots/users.png) |
