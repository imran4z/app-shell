# CLAUDE.md - how to build an app from this template

You are working in **app-blueprint**: a clonable app shell implementing the
Clarion blueprint. The plumbing (FastAPI + Postgres + React/Tailwind v4 +
Docker + tests) already works end to end. Your job is to replace the
example domain with the user's real one, described in `APP_SPEC.md`.

## Read first, in this order

1. `APP_SPEC.md` - what to build (the domain).
2. `BLUEPRINT.md` - how to build it (every design and architecture
   decision, already settled - do not re-litigate; spend novelty on the
   domain, not the buttons).
3. This file - how the template maps onto the blueprint.

If APP_SPEC.md is still the unfilled template, stop and ask the user to
fill it in (or interview them section by section).

## What's already here

| Blueprint concept | Where it lives in this repo |
|---|---|
| Design tokens + all custom utilities | `ui/src/index.css` (verbatim from Clarion - do not fork it) |
| UI primitives (Button, Card, Badge, Toast, StatKpi, Pagination, PageHeader, SearchInput, ConfirmDialog) | `ui/src/components/` |
| App shell: TopBar, theme, ⌘K palette, mobile drawer | `ui/src/components/Layout.tsx`, `CommandPalette.tsx`, `ui/src/lib/ThemeContext.tsx` |
| API client pattern | `ui/src/lib/api.ts` |
| Canonical list page (copy me) | `ui/src/pages/Items.tsx` |
| List->detail + enrichment pattern (copy me) | `ui/src/pages/Profiles.tsx` + `0004_profiles.sql` -> `ProfileRepository` -> `api/routes/profiles.py` |
| Storage contract: db/migrator/repositories | `src/appshell/storage/` |
| Example entity end-to-end | `0001_items.sql` -> `ItemRepository` -> `api/routes/items.py` -> `pages/Items.tsx` |
| Instrumented LLM wrapper + llm_calls cost ledger | `src/appshell/observability/llm_client.py`, `0002_llm_calls.sql` |
| Assistant (⌘J drawer, SSE chat, approval gate) | `agents/assistant.py`, `agents/assistant_tools.py`, `api/assistant_runs.py`, `api/routes/assistant.py`, `0003_assistant.sql`, `ui/src/components/Assistant.tsx` |
| CLI (canonical business-logic surface) | `src/appshell/cli/main.py` |
| Docker run lane (one port, localhost only) | `deploy/docker/` + `just run` |
| Test harness (fake LLM client, testcontainers PG) | `tests/conftest.py` |

Not shipped (build per-app when the spec needs them, patterns in
BLUEPRINT.md): the runner/pipeline/registry trio (§5), domain agents
(§8), setup wizard. Also deliberately absent: a monitoring/telemetry
stack (no OTel) - do not add one unless the spec asks.

## Build procedure

1. **Rename (if the spec names the app).** Package `appshell` -> new slug:
   directory `src/appshell`, imports, `pyproject.toml` (name + script),
   `APPSHELL_*` env vars, Dockerfile/compose references, `appshell.theme`
   localStorage key, and the wordmark/`<title>` in the UI. Mechanical -
   grep for `appshell` and `APPSHELL` and `App Shell`.
2. **Domain schemas** (`schemas/`): pydantic contracts for the spec's
   entities. Enums for closed vocabularies, `description=` on every field,
   provenance fields on anything LLM-generated.
3. **Storage**: for each entity follow the four-step contract -
   migration file -> register in `drop_all()` (child-first!) -> repository
   class -> export from `storage/__init__.py`. Map each spec entity onto a
   shipped pattern: flat list + state machine -> copy the Items thread;
   container enriched over time (list->detail) -> copy the Profiles thread.
   Keep the examples until your replacements work, then delete `items`
   and `profiles` everywhere (migration, drop_all, repo, routes, pages,
   nav, palette, CLI seed, assistant tools).
4. **Routes + pages**: one route module per resource (clamped pagination,
   envelope shape); one list page per resource copied from
   `pages/Items.tsx`'s composition. Register nav in `Layout.tsx` NAV and
   the palette.
5. **CLI first, API second** for every piece of business logic (§0.3).
6. **Assistant tools**: replace the example item tools in
   `agents/assistant_tools.py` with your domain's (keep the registry
   shape + never-throwing execute_tool; put risky ones in
   NEEDS_APPROVAL_TOOL_NAMES). Pipelines/domain agents only if the spec
   calls for them - follow §5/§8 and the contracts in §12.
7. **Gates**: `just check` green, then `just run` and verify the app works
   in Docker Desktop end to end.

## House rules (the ones people break)

- Every model call goes through `call_anthropic()` - never the SDK direct.
  Default model: `claude-opus-5`.
- New table ⇒ update `drop_all()` in the same commit (silent db-reset
  breakage is the #1 recurring miss).
- Observability writes never break the primary path (try/except -> debug log).
- No new dependencies without a one-line justification.
- No websockets (polling + SSE), no chart libraries (hand-rolled SVG),
  no `window.alert()`, no skeleton loaders.
- Components reference tokens as `var(--color-...)` arbitrary values; never
  hardcode hex in components.
- `aria-label` on every icon-only button; Esc closes the topmost overlay.
- **Layout is fluid edge-to-edge** - a deliberate deviation from
  BLUEPRINT.md §3's `max-w-[1400px]` column. The shell uses full width
  with `px-[clamp(1rem,2.5vw,4rem)]` gutters so phones through 4K
  monitors all use the available real estate. Never reintroduce a
  page-level max-width; cap only *text measure* (`max-w-[64ch]` on
  ledes) for readability.
