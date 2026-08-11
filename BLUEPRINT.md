# The App Shell Blueprint - design profile & architecture skeleton

**What this is:** the settled design system, UX conventions, and architecture decisions this template implements, packaged so a fresh coding agent can build any app that looks, feels, and is engineered the same way, without re-deriving or re-litigating any of these decisions.

**How to use it:** paste this file (or point at this repo and say "read BLUEPRINT.md") along with a description of the new app's domain. Everything below is domain-agnostic. Where a rule says *firm*, follow it exactly; where it says *default*, deviate only with a stated reason.

> When you have this repo available, the ground-truth files are cited like `ui/src/index.css`. When you only have this document, everything you need is inlined - the citations are just provenance.

---

## 0. Operating principles (firm)

1. **Do not reinvent the design system.** Every token, recipe, and pattern below is settled. Spend your novelty budget on the new app's domain, not its buttons.
2. **One port, one container.** FastAPI serves both the API (`/api/*`) and the built SPA from a single port. Dev mode runs Vite + uvicorn separately with a proxy.
3. **The CLI is the canonical business-logic surface.** The API orchestrates by spawning the same CLI a human would type. No logic exists only behind an HTTP route.
4. **Schemas are contracts.** Pydantic models are the on-disk format and the LLM's target. Changing one requires a written one-paragraph case.
5. **Postgres is the source of truth; in-memory state is only a wake-up signal.** Anything the UI renders must be reconstructable from the DB after a process restart.
6. **Observability writes never break the primary path.** Spans + DB rows are dual-destination and best-effort (`try/except` -> `logger.debug`).
7. **Accessibility is not optional.** `aria-label` on every icon-only button, `focus-visible` rings, `prefers-reduced-motion` respected, skip link, WCAG AA contrast on both themes.
8. **Tests for everything you add.** Unit by default, integration opt-in via marker, fake LLM client that exercises the real wrapper.
9. **Use `just` for everything.** The justfile is the dev-loop source of truth. All Python runs via `uv run`.
10. **Don't add dependencies without a one-line justification.** The stack below was chosen deliberately.

---

## 1. Stack manifest

### Frontend (`ui/`)
| Choice | What | Notes |
|---|---|---|
| Runtime | React 19 + TypeScript ~6.0, `StrictMode` | named exports; no default exports except `App` |
| Build | Vite 8 + `@vitejs/plugin-react` | alias `@` -> `./src`; dev proxy `/api` -> `http://127.0.0.1:8765` |
| Styling | **Tailwind v4, CSS-first** via `@tailwindcss/vite` | **no** `tailwind.config.js`, no PostCSS - one `@theme` block in `src/index.css` |
| Routing | `react-router-dom` v7, `BrowserRouter` | nested under a single `<Layout/>` + `<Outlet/>` |
| Data | `@tanstack/react-query` v5 | polling for lists, SSE for live streams - **no websockets** |
| Icons | `lucide-react` primary + one bespoke brand-icon module | |
| Variants | `class-variance-authority` + `clsx` + `tailwind-merge` (`cn()` helper) | |
| Palette/search | `cmdk` command palette (⌘K) | |
| Charts | **none** - sparklines and diagrams are hand-rolled SVG | don't add a chart lib without cause |

### Backend (`src/<pkg>/`)
| Choice | What | Notes |
|---|---|---|
| Language | Python >=3.11 (container 3.13-slim), hatchling, **src-layout** | `uv` for everything; `uv.lock` committed |
| API | FastAPI + uvicorn + `sse-starlette` | plain sync handlers, **zero `Depends`** - see §6 |
| DB | Postgres 16 + SQLAlchemy 2.0 Core + `psycopg` v3 | **no ORM models, no Alembic** - raw SQL migrations + repo classes |
| Validation | Pydantic v2 (`ConfigDict`, `Field(description=...)` on everything) | |
| LLM | `anthropic` SDK direct - **no LangGraph/LangChain** | hand-rolled async stage functions over a `TypedDict` state |
| Logging | `structlog` with trace/span ids injected into every line | |
| CLI | `click` + `rich`, registered as `[project.scripts]` | |
| Obs | OTel SDK + OTLP-HTTP, `gen_ai.*` semconv spans | single instrumented LLM wrapper - see §8 |
| Lint/type | `ruff` (line-length 100, `E,F,W,I,N,UP,B,C4,PT,RET,SIM,TCH`), `mypy --strict` | config inline in `pyproject.toml`, no separate files |
| Tests | `pytest` + `pytest-asyncio` (`asyncio_mode="auto"`), `respx`, `testcontainers[postgres]` | `addopts = "-m 'not integration'"` |

### Tooling & deploy
- **justfile** (`set dotenv-load := true`): grouped by `# === Section ===` banners; two first-class *lanes* - **run lane** (`just run`: Docker, zero toolchain, for non-engineers) and **dev lane** (`just api` + `just ui`, hot reload). Quality gates: `just check = lint + typecheck + test`.
- **Docker**: 3-stage build - `node:22-alpine` builds the UI -> `uv` image builds the venv (`--frozen --no-dev`, cache mounts, deps layer before source layer) -> `python:3.13-slim` runtime, non-root user, UI dist copied in, `EXPOSE 8765`. Port binding is **`127.0.0.1:8765:8765` - localhost only, never the LAN**. Secrets never enter layers: `.dockerignore` excludes `.env*`; keys arrive via `env_file` + a **read-write bind mount of `.env`** so the in-app Setup page can persist keys.
- **Compose profiles** gate optional services (`--profile app`, `--profile cloud`) so `just up` starts only Postgres.
- **Env-var trap (firm):** the app calls `load_dotenv(override=True)`, which clobbers compose-injected vars. Infrastructure wiring must use a distinct env name the `.env` never defines (this template: `APPSHELL_POSTGRES_HOST: postgres` in compose, falling back to `POSTGRES_HOST` locally). Name yours `<APP>_POSTGRES_HOST`.

---

## 2. Design tokens (firm - copy verbatim, then rename)

All tokens live in **one `@theme` block** in `ui/src/index.css`. Convention: components reference them as arbitrary values - `bg-[var(--color-canvas-elev1)]`, `text-[var(--color-text-muted)]` - not via generated utility names.

### Dark (default)

```css
/* Surfaces - slate-navy, cooler than near-black */
--color-canvas:        #0a0e14;
--color-canvas-elev1:  #131820;   /* cards */
--color-canvas-elev2:  #1c232d;   /* modals, popovers, dropdowns */
--color-canvas-elev3:  #252e3a;

--color-border:        rgba(180, 200, 230, 0.08);
--color-border-strong: rgba(180, 200, 230, 0.16);

--color-text:          #eef1f6;
--color-text-muted:    #9aa3b2;
--color-text-faint:    #6b7385;

/* Accent - teal. Primary actions, focus, active states, brand mark */
--color-accent:        #2dd4bf;
--color-accent-hover:  #5eead4;
--color-accent-deep:   #14b8a6;
--color-accent-bg:     rgba(45, 212, 191, 0.13);
--color-accent-border: rgba(45, 212, 191, 0.42);
--color-on-accent:     #04211e;

/* "Live" - something is actively flowing (distinct from success) */
--color-live:          #6ee7b7;
--color-live-bg:       rgba(110, 231, 183, 0.12);

/* Signal - sky secondary tier (sparklines, gradients, callouts) */
--color-signal:        #7dd3fc;
--color-signal-bg:     rgba(125, 211, 252, 0.12);

/* Semantic */
--color-success:  #34d399;  --color-success-bg: rgba(52, 211, 153, 0.13);
--color-warning:  #fbbf24;  --color-warning-bg: rgba(251, 191, 36, 0.13);
--color-danger:   #f87171;  --color-danger-bg:  rgba(248, 113, 113, 0.13);
--color-info:     #60a5fa;  --color-info-bg:    rgba(96, 165, 250, 0.13);
```

The theme also reserves a partner-brand color (`--color-partner: #FF8833`, swap the hex for your integration) used **only** to mean "live in the external system," never as idle decoration. If the app integrates a branded external system, keep that rule: brand color = live connection, nothing else.

### Light (`[data-theme="light"]` override block)

```css
--color-canvas:        #f7f8fa;
--color-canvas-elev1:  #ffffff;
--color-canvas-elev2:  #f0f2f6;
--color-canvas-elev3:  #e6e9ef;

--color-border:        rgba(20, 30, 50, 0.08);
--color-border-strong: rgba(20, 30, 50, 0.14);

--color-text:          #0f1623;
--color-text-muted:    #5a6478;
--color-text-faint:    #8a93a3;

--color-accent:        #0d9488;   /* deeper teal for AA on white */
--color-accent-hover:  #14b8a6;
--color-accent-deep:   #0f766e;
--color-accent-bg:     rgba(13, 148, 136, 0.10);
--color-accent-border: rgba(13, 148, 136, 0.30);
--color-on-accent:     #ffffff;

--color-live:    #047857;  --color-live-bg:    rgba(4, 120, 87, 0.10);
--color-signal:  #075985;  --color-signal-bg:  rgba(7, 89, 133, 0.10);

--color-success: #047857;  --color-success-bg: rgba(4, 120, 87, 0.10);
--color-warning: #b45309;  --color-warning-bg: rgba(180, 83, 9, 0.10);
--color-danger:  #b91c1c;  --color-danger-bg:  rgba(185, 28, 28, 0.09);
--color-info:    #1d4ed8;  --color-info-bg:    rgba(29, 78, 216, 0.09);
```

**Rule:** every semantic color must meet WCAG 2.1 AA against `--color-canvas` (4.5:1 text, 3:1 UI) in *both* themes. Light theme darkens hues rather than reusing dark-theme values.

### Radii, shadows, motion

```css
--radius-sm: 6px;  --radius: 10px;  --radius-lg: 16px;

/* dark */
--shadow-sm: 0 1px 2px rgba(0,0,0,0.25);
--shadow-md: 0 6px 18px -6px rgba(0,0,0,0.4);
--shadow-lg: 0 24px 60px -20px rgba(0,0,0,0.6);
/* light */
--shadow-sm: 0 1px 2px rgba(15,22,35,0.06);
--shadow-md: 0 6px 18px -8px rgba(15,22,35,0.18);
--shadow-lg: 0 24px 60px -24px rgba(15,22,35,0.28);

--motion-fast: 140ms;  --motion-normal: 240ms;  --motion-slow: 360ms;
--ease: cubic-bezier(0.22, 1, 0.36, 1);
--default-transition-timing-function: cubic-bezier(0.22, 1, 0.36, 1);
--default-transition-duration: 180ms;
```

In practice: `rounded-xl` (12px) for cards/modals, `rounded-md` for buttons/nav, `rounded-2xl` for hero inputs, `rounded-full` for pills.

### Typography

```css
--font-sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
--font-mono: "JetBrains Mono", ui-monospace, "SF Mono", monospace;
```

Global rules:

```css
:root {
  font-family: var(--font-sans);
  font-feature-settings: "cv02","cv03","cv04","cv11","ss01","ss03";
  font-variant-numeric: tabular-nums;
  -webkit-font-smoothing: antialiased;
  line-height: 1.5;
}
h1,h2,h3 { letter-spacing: -0.015em; line-height: 1.2; }
h1,h2 { font-weight: 600; }  h3 { font-weight: 500; }
```

To guarantee the fonts, load `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap` (the template relies on locally-installed fonts with system fallbacks).

**The signature typographic move:** micro-labels, eyebrows, table headers, and stat labels are always `font-mono uppercase` at 10-11px with `tracking-[0.06em]`-`[0.08em]` in `text-muted`/`text-faint`. Numbers are always `tabular-nums`. Big values are `text-[28px] font-semibold tracking-[-0.02em]`.

### Theme mechanism (firm)

- Attribute-based: `<html data-theme="dark|light">` - **not** `class="dark"`, not media-query-only.
- Preference in `localStorage["<app>.theme"]` as `"light"|"dark"|"system"`.
- **Inline boot script in `index.html`** sets `data-theme` synchronously before React paints (localStorage -> `matchMedia` fallback -> dark on error), plus inline FOUC CSS duplicating canvas/text pairs for both themes, plus `<meta name="theme-color">` per scheme and `<meta name="color-scheme" content="dark light">`.
- Runtime `ThemeContext.tsx`: `ThemeProvider` + `useTheme()` -> `{mode, resolved, setMode}`; listens to `matchMedia` change in `system` mode. Toggle lives in the user menu (Sun/Moon/Monitor icons).

### Page ambience

```css
body {
  background:
    radial-gradient(900px 600px at 80% -10%, rgba(45,212,191,0.10), transparent 60%),
    radial-gradient(900px 600px at 10% 100%, rgba(125,211,252,0.08), transparent 60%),
    var(--color-canvas);
  background-attachment: fixed;
}
/* light: rgba(15,118,110,0.10) upper-right + rgba(7,89,133,0.07) lower-left */
```

### Global chrome
- Scrollbar: 10px, transparent track, thumb `rgba(255,255,255,0.06)` -> hover `0.16`, radius 8, `border: 2px solid transparent; background-clip: padding-box`.
- Focus: `:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; border-radius: 4px; }`
- Selection: `::selection { background: var(--color-accent-bg); color: var(--color-text); }`
- `@media (prefers-reduced-motion: reduce)` -> all durations `0.01ms`.
- Skip link as first focusable element, targeting `#main-content`.

### Key custom utilities (define in index.css)

| Class | Recipe |
|---|---|
| `.glass` | **the card primitive** - `linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01))` + 1px `--color-border` + `backdrop-filter: blur(8px)` |
| `.hover-wash` | hover/focus-visible -> `background: color-mix(in srgb, var(--color-accent) 9%, transparent)`, transitions at `--motion-fast`/`--ease` |
| `.h1-display` | gradient text `linear-gradient(120deg, accent, signal)` + `background-clip: text` |
| `.live-dot` | bg `--color-live` + `box-shadow: 0 0 0 4px rgba(live, .18)` + 1.8s pulse |
| `.row-flag` | 3×18px inline severity bar (radius 2, mr 8) with `.live/.warn/.muted/.danger` modifiers |
| sweep loader | indeterminate 90° gradient sweep (`transparent -> accent -> signal -> accent -> transparent`), `background-size: 200% 100%`, 1.3s linear infinite |

---

## 3. Component recipes (default - copy the class strings)

### App shell
Topbar-only, **no sidebar**. Provider nesting:

```
QueryClientProvider -> BrowserRouter -> ThemeProvider -> ToastProvider
  -> SetupGate -> <domain contexts> -> AssistantProvider -> Routes
```

Shell: `min-h-screen flex flex-col` -> TopBar -> `<main id="main-content" class="flex-1 max-w-[1400px] mx-auto w-full px-4 sm:px-6 py-6 sm:py-8"><Outlet/></main>` -> CommandPalette -> MobileNavDrawer -> Assistant drawer.

**TopBar:** `sticky top-0 z-30 border-b border-[var(--color-border)] backdrop-blur bg-[var(--color-canvas)]/75`, inner `h-16 max-w-[1400px] flex items-center gap-4`. Left->right: mobile hamburger (`md:hidden`), brand tile (36×36 `rounded-[10px]`, accent bg/border, custom mark) + wordmark `text-[16px] font-semibold tracking-tight`, primary nav (`hidden md:flex gap-1`), then `ml-auto`: live-activity pill, Search (⌘K), Assistant (⌘J), UserMenu.

Nav item: `h-8 px-3 rounded-md text-sm flex items-center gap-2 transition-colors` - active `bg-white/[0.06] text-[var(--color-text)]`, idle `text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-white/[0.03]`. Icons `size={14}`.

Keyboard trigger buttons carry a `<kbd>`: `text-[10px] font-mono px-1.5 py-0.5 rounded border border-[var(--color-border)] bg-[var(--color-canvas)]/60`.

Mobile drawer: `fixed inset-0 z-40 md:hidden`, backdrop `bg-black/60 backdrop-blur-sm`, panel `w-72 max-w-[85vw] bg-[var(--color-canvas-elev1)] border-r transition-transform duration-200 ease-out`; body scroll locked; closes on route change and Esc.

### Card
```tsx
<div className={cn("glass rounded-xl",
  hover && "transition-all duration-200 hover:border-[var(--color-border-strong)] hover:bg-white/[0.04]")} />
```
Padding per-use (`p-5` typical; `p-0 overflow-hidden` when wrapping a table). Solid variant for KPI tiles/modals: `bg-[var(--color-canvas-elev1)] border border-[var(--color-border)] rounded-xl`.

### Buttons (CVA)
Base: `inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-canvas)] focus-visible:outline-none`

- `primary`: `bg-[var(--color-accent)] text-black hover:bg-[var(--color-accent)]/90`
- `secondary` (default): `bg-white/[0.06] border border-[var(--color-border)] hover:bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)] hover:border-[color:var(--color-accent-border)]`
- `ghost`: `text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[color-mix(in_srgb,var(--color-accent)_9%,transparent)]`
- `danger`: `bg-[var(--color-danger)]/15 text-[var(--color-danger)] border border-[var(--color-danger)]/30 hover:bg-[var(--color-danger)]/25`

Sizes `sm h-8 px-3 / md h-9 px-4 / lg h-10 px-5`; leading lucide icon `size={12-14}`.

### Badges
`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium`; tone pattern `bg-[var(--color-X)]/12 text-[var(--color-X)] border-[var(--color-X)]/30`. Centralize domain-state -> tone in one exported mapper function (e.g. `reviewStateTone()`), never inline per-page.

### KPI tiles (two primitives)
- **StatKpi** (summary row on every list page): `rounded-[var(--radius)] border px-[18px] pt-4 pb-[18px]`, background `linear-gradient(150deg, color-mix(in srgb, {tone} 9%, var(--color-canvas-elev1)), var(--color-canvas-elev1) 62%)`, a **3px full-width bottom accent bar** (gradient `accent->signal` by default, tone-driven), a 28×28 icon tile (`rounded-lg`, tone color/bg/30% border, icon 15px), mono uppercase 11px label, `text-[28px] font-semibold tabular-nums` value, hand-rolled 56×22 `<polyline>` sparkline.
- **KpiCard** (drilldown-capable): `rounded-xl border bg-elev1 p-4` with a `::before` tone-tint layer that fades in on hover; selected = accent ring; chevron reveals on group-hover, rotates 90° when open. Pairs with **DrilldownPanel**: always in DOM, collapses `max-h-0 opacity-0` ↔ `max-h-[600px] opacity-100 mt-3`, `transition-all duration-200 ease-out`, panel `rounded-xl border-[var(--color-accent-border)] shadow-lg`.

### Tables
Always inside `<Card className="p-0 overflow-hidden">`, pagination as footer in the same card.

```html
<table class="w-full text-sm">
  <thead class="text-[10px] text-[var(--color-text-faint)] uppercase tracking-wider font-mono border-b border-[var(--color-border)]">
    <th class="text-left font-medium px-4 py-2.5">...</th>   <!-- numeric: text-right -->
  <tbody>
    <tr class="border-b border-[var(--color-border)] last:border-0 cursor-pointer transition-colors hover:bg-white/[0.02]">
      <td class="px-4 py-3">...
```

Cells: IDs `font-mono text-xs`; numbers `text-right tabular-nums`; missing values render `-` in `text-faint`; timestamps right-aligned `text-xs text-muted`. In-flight rows tint `bg-[var(--color-info)]/5` with a spinning `Loader2 size={11}` + verb.

Pagination: `flex flex-wrap items-center justify-between gap-3 px-3 py-2.5 border-t`; left "1-10 of 28" (`text-xs tabular-nums`) + page-size select (10/25/50, `h-7 font-mono text-xs`); right page buttons `min-w-[28px] h-7 rounded-md text-xs font-mono`, active `bg-accent-bg text-accent border-accent-border`; window = all if <=7 pages else first + ±1 + last with `...`.

### Modals / overlays
Backdrop grammar everywhere: `fixed inset-0 z-50 bg-black/50-60 backdrop-blur-sm`, close on backdrop click (panel `stopPropagation`) and Esc, `role="dialog" aria-modal="true"`.

- Confirm: centered `<Card class="w-[520px] max-w-[90vw] p-5">`, warning icon, right-aligned `Cancel` + `danger|primary`.
- Command palette: `pt-32` top-anchored, `w-[640px] rounded-xl shadow-2xl` - **solid `elev2`, not glass**, `border-strong`. cmdk selected row: `bg-accent-bg text-accent ring-1 ring-accent-border`. Queries `enabled: open`.
- Form modal: `pt-[10vh]`, `max-w-[560px] rounded-2xl`, plus a radial accent wash `radial-gradient(120% 80% at 100% 0%, var(--color-accent-bg), transparent 60%)` layered over `elev1`.
- Right drawer (assistant): `fixed top-0 right-0 z-50 h-full w-full sm:w-[440px] bg-elev1 border-l shadow-2xl transition-transform duration-200 ease-out` toggling `translate-x-0 ↔ translate-x-full`; header `h-[60px]` with radial accent wash + 32×32 gradient orb (`linear-gradient(135deg, accent, signal)`). User chat bubbles: `max-w-[85%] rounded-2xl rounded-br-sm bg-[var(--color-accent-bg)] px-3.5 py-2 text-sm`.

### Forms
Input: `w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-elev1)] py-2 text-sm placeholder:text-[var(--color-text-faint)] outline-none transition-colors focus:border-[var(--color-accent)]`. Wizard-style fields add `box-shadow: 0 0 0 3px var(--color-accent-bg)` on focus, mono 13px input text, and 11px mono uppercase labels. Validity hints: 11px, `--color-live` valid / `--color-danger` invalid. Radio presets render as bordered tiles (active `bg-accent-bg border-accent-border text-accent`) with proper `role="radiogroup"`. Hero command bar: `h-[64px] rounded-2xl`, focused `shadow-[0_0_0_4px_var(--color-accent-bg),var(--shadow-lg)]`.

### Feedback patterns
- **Loading:** no skeletons. In-card `p-8 text-center text-faint "Loading..."`; inline `Loader2 animate-spin` + present-tense verb ("Researching..."); buttons disable on `isPending`.
- **Empty states:** centered in a Card - `p-12 text-center`, illustration/icon, `text-sm font-medium` title, `text-xs text-muted mt-1 max-w-sm mx-auto` hint that **names the next action**.
- **Toasts:** provider + `useToasts()` -> `{push, dismiss}`; container `fixed bottom-4 right-4 z-50 flex flex-col gap-2 sm:max-w-sm`, `aria-live="polite"`; card `rounded-xl border bg-elev2 backdrop-blur shadow-xl`, tone border at /40-50, slide-in via a 10ms mounted flag, `role="alert"` for danger else `status`, default 6s, `0` = sticky.
- **Errors:** inline `text-xs text-danger` under forms; warning banners `rounded-lg border-[color:var(--color-warning)]/40 bg-warning-bg px-3 py-2.5`; a full-page "API unreachable" screen with a `<details>` disclosure containing the raw error and a copy-pasteable fix command. Never `window.alert()`.
- **Log views:** left-border severity tinting - error `border-l-4 border-l-danger bg-danger-bg`, warn `border-l-2 warning /30`, success `/15`, info transparent, debug `opacity-75`.

### Typography hierarchy (quick table)
| Role | Recipe |
|---|---|
| Eyebrow | `text-[11px] font-mono uppercase tracking-[0.08em] text-faint` |
| Page title | `text-[28px] font-semibold tracking-[-0.02em]` (+ gradient span via `.h1-display` for heroes at 34-46px) |
| Lede | `mt-2 max-w-[64ch] text-sm leading-relaxed text-muted` |
| Section H2 | `text-lg font-medium` + `text-xs text-muted` subtitle |
| Card title | `text-sm font-medium` |
| Micro-label | `text-[11px] font-mono uppercase tracking-[0.08em] text-faint` |
| Big value | `text-[28px] font-semibold tracking-[-0.02em] tabular-nums leading-none` |
| Modal title | `text-[22px] font-semibold tracking-tight` |
| IDs | `font-mono text-xs` |

### Icons
lucide-react sizes are fixed by context: 12 in buttons/kbd, 13-14 nav/chips/tables, 15-16 section headers/modals, 20-28 empty states. Build one bespoke brand-icon module (`components/icons/`) with a mark + a string-keyed glyph map for domain concepts, all stroking `currentColor`, plus a `TONE` map from domain states to CSS vars (`running->info, done->success, failed->danger, pending->faint`).

---

## 4. Frontend architecture conventions

### Folder layout (`ui/src`)
```
main.tsx            # createRoot + StrictMode + "./index.css"
index.css           # THE ENTIRE design system (@theme + globals + bespoke component CSS)
App.tsx             # QueryClient + router + provider stack + route table
components/         # flat PascalCase.tsx, one named export per file; feature subfolders only when a page grows (plan/)
components/icons/   # brand icon module
pages/              # one file per route area; list + detail pages COLOCATED (PlansListPage + PlanDetailPage in Plans.tsx)
lib/                # api.ts, cn.ts, *Context.tsx (Provider + useX() that throws outside), pure derivation/*.ts helpers
```
- Imports always via `@/` alias, never `../..`. External packages -> blank line -> internal.
- Every non-trivial file opens with a block comment: why it exists, constraints, rejected alternatives. **This documentation density is part of the house style.**
- Section dividers in long files: `// --- Name -------------`.
- localStorage keys namespaced `<app>.*`.

### API client (`lib/api.ts`)
Single hand-written client, no codegen. `const BASE = "/api"` (Vite proxies in dev, same-origin in the container). One private `request<T>(path, init)`: JSON headers, special-case setup-gate responses (503 + `X-<App>-Setup: required` header -> throw `SetupRequiredError`), unwrap `detail` from error bodies into `Error("API {status}: {detail}")`, return `undefined` on 204. Every endpoint = exported TS interface + one-line arrow function next to it.

### Data loading
QueryClient defaults: `staleTime: 5_000, refetchOnWindowFocus: true, retry: 1`. **Polling for lists** (5s hot lists, 10-15s dashboards, 30s audit), **SSE for live streams**, no websockets. Flat literal query keys (`["plans", filter ?? "all"]`). Paginated queries use `placeholderData: (prev) => prev`. Mutations invalidate an explicit fan-out of keys in `onSuccess`.

### UX chrome
- **⌘K** command palette (cmdk): groups = Pages / top entities / recent activity; nothing fetches until open.
- **⌘J** assistant drawer. **Esc** closes topmost overlay; clears focused search inputs first (`stopPropagation`).
- `aria-keyshortcuts` on trigger buttons.
- **SetupGate** wraps the router: probe `/api/setup/status` -> ready ? children : full-screen setup wizard; network failure -> ApiUnreachable screen. An in-session `SetupRequiredError` flips the gate without reload.

### Canonical list page (default composition)
```tsx
<div className="space-y-6">
  <PageHeader eyebrow title lede actions={<Button variant="primary" size="sm"/>} />
  <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">{/* 4 x StatKpi */}</div>
  <SearchInput/>
  <section>{/* "Recent" highlights: grid of <=6 KpiCards, hidden while searching */}</section>
  <section><Card className="p-0 overflow-hidden">{/* table + Pagination */}</Card></section>
</div>
```
Detail pages: `PageHeader back={{to,label}}` + a row of mono breadcrumb chips. The dashboard/home is the one exception: centered hero with a giant input, decorative aurora layer, content bands separated by `border-t mt-12 pt-9`.

---

## 5. Backend: FastAPI app skeleton

### `api/main.py` - assembly order (firm)
1. `lifespan`: `load_dotenv(override=True)` **before** telemetry init -> configure structlog -> `init_telemetry()` -> **reap orphans** (mark DB rows still `running` from a dead process as failed - no phantom spinners after restart) -> spawn background `asyncio.create_task` loops (health heartbeat, reapers); on shutdown cancel + await each.
2. `FastAPI(title, version, lifespan)`; OTel `FastAPIInstrumentor` in a bare try/except ("instrumentation must never block boot").
3. `CORSMiddleware` with explicit localhost dev origins only, `allow_credentials=False`, minimal methods/headers.
4. Routers - setup router first.
5. Setup-gate middleware: pass `OPTIONS` + non-`/api/` paths + an explicit open-prefix tuple; otherwise 503 + `X-<App>-Setup: required` until configured. Saving the wizard refreshes `os.environ` in-process (no restart).
6. `mount_ui()` **last**: mount `/assets` static, then a catch-all that (a) 404s JSON for `api/*`, (b) serves real files with an `is_relative_to` containment check, (c) falls back to `index.html` for SPA routing. No-op when dist is missing (dev lane).

### Route modules (`api/routes/<resource>.py`)
- `APIRouter(prefix="/api/<resource>", tags=[...])`, one module per resource.
- **No `Depends` anywhere.** Handlers are plain sync `def` (FastAPI threadpool); async only for SSE/background-task starters. Repos instantiated directly; DB work inside `with session_scope() as s:` blocks in the handler.
- DTOs (`XSummary`, `XRequest`, paginated envelopes) declared locally in the route module; full domain pydantic models returned directly when the whole artifact is wanted. Every route declares `response_model=`.
- Pagination: `?limit=&offset=`, **clamped not 422'd** (`limit = max(1, min(limit, 500))`), envelope `{entries, total, limit, offset}` so one UI Pagination component serves everything.
- Literal routes **before** `/{param}` routes (or `/audit` gets matched as an id).

### Long-running work: the three-layer orchestration pattern
1. **`runner.py`** - subprocess driver. UI-triggered work spawns the same CLI a human would type; a `Literal`-typed **whitelist of allowed subcommands** prevents escalation; stderr merged into stdout; a drain task pumps lines into a buffer; `stream_run_lines()` yields buffered then polls until a `__exit__ <rc>` sentinel; cancel = SIGTERM. Fresh process per run = clean cancellation + no cached-singleton pollution.
2. **`pipeline.py`** - a linear `PHASES: tuple[str, ...]` and an **async generator yielding plain event dicts** with a tiny documented vocabulary: `{"event":"pipeline"|"phase"|"log"|..., "status":"started"|"done"|"failed", ...}`. Supports `starting_phase`/`stop_after_phase` resume; already-done phases are emitted as `done` so the UI renders them green. Context (pipeline id, phase, creds) is injected into the subprocess **env** so instrumentation inside the child stamps spans with zero plumbing. Emit `phase:failed` **before** `pipeline:failed` or the UI row spins forever.
3. **`pipeline_registry.py`** - durability + fan-out. **Postgres is the source of truth** (`pipelines`, `pipeline_events` with a monotonic `seq`, `pipeline_phases`); the in-process `_LIVE` dict holds only an `asyncio.Event` wake-up + task handle. **The `stream(id, after_seq=-1)` contract (copy verbatim):** replay DB events where `seq > after_seq` in chunks -> if terminal, return -> if no live entry (prior process), reap stale + converge to DB status -> else loop `wait_for(new_event.wait(), timeout=30)` re-querying for new rows. Routes wrap it in `sse-starlette`'s `EventSourceResponse`; the `?after=` param lets clients tail only what's new.

---

## 6. Storage contract (firm - the most transferable pattern)

Four files, no ORM models, no Alembic, no generic CRUD. "It keeps the surface auditable."

### `storage/db.py` (~60 lines, copy nearly as-is)
- `build_dsn()` from env (`postgresql+psycopg://...`), honoring the compose-only host var (`<APP>_POSTGRES_HOST` -> fallback `POSTGRES_HOST` -> `localhost`).
- `@lru_cache(maxsize=1) connect() -> Engine` with `pool_pre_ping=True`.
- `@lru_cache(maxsize=1) _session_factory()` with **`expire_on_commit=False`** (hydrated pydantic objects must survive the commit).
- `@contextmanager session_scope()`: yield -> commit; except -> rollback + re-raise; finally -> close.
- `reset_engine_cache()` test hook clearing both caches.

### `storage/migrator.py`
- Migrations = raw SQL files `storage/migrations/NNNN_name.sql` (4-digit zero-padded), discovered via `importlib.resources` (they ship in the wheel), sorted lexically.
- Bootstrap `_migrations(filename PK, applied_at)` ledger.
- `apply_migrations()`: each unapplied file's SQL + its ledger INSERT run in **one transaction**; returns newly-applied list; idempotent - call on every boot.
- `drop_all()`: DEV ONLY; iterates an **explicit hand-maintained FK-safe ordered list** (children before parents, inline comments per group), `DROP TABLE IF EXISTS ... CASCADE`, `_migrations` last, then shared functions.

### Migration file conventions
- Banner header: `-- ==== NNNN - <table> ====` + 2-4 sentences: what it records, why, what consumes it, lifecycle notes.
- `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` - re-runnable.
- PKs: `BIGSERIAL` for append-only logs; natural `TEXT`/`UUID` for entities. Timestamps `TIMESTAMPTZ NOT NULL DEFAULT NOW()`. Blobs `JSONB`. States `TEXT NOT NULL CHECK (col IN (...))` - **never Postgres ENUMs**. FKs explicit: `ON DELETE CASCADE` when meaningless without the parent, `SET NULL` when history should survive. Index naming `idx_<table>_<cols>`; partial unique indexes for "one active X per Y".

### The four-step contract for any new persisted entity (firm)
1. Write `migrations/NNNN_name.sql`.
2. **Register the table in `drop_all()`'s ordered list**, child-first. *This is the #1 recurring miss - skipping it silently breaks db-reset.*
3. Add a repository class in `repositories.py`.
4. Export it from `storage/__init__.py` (import + `__all__`).

### `storage/repositories.py`
- One class per artifact, `# ==== Name ====` banners. **All methods take an explicit `Session`; repos never commit** - callers own the transaction via `session_scope()`.
- Narrow surfaces: `upsert/get/list/delete/record` + explicit state-transition helpers. No generic CRUD.
- Raw SQL via `sqlalchemy.text()` + bound params; JSONB via `bindparam(type_=JSONB)` and `_to_jsonable(model) = json.loads(model.model_dump_json())`; upserts `ON CONFLICT (pk) DO UPDATE SET col = EXCLUDED.col`.
- Reads return hydrated pydantic models for artifact tables (`Model.model_validate(row[0])`), plain-dict `_x_row()` mappers for log/telemetry tables.
- `delete` returns `bool`; docstrings state exactly what cascades and what the caller still owns.

---

## 7. Schemas (`schemas/`)
- One module per artifact family, flat re-export `__init__.py`. The package docstring states: **the JSON serialization of these models is the on-disk format.**
- Closed vocabularies as `class X(str, Enum)` with documented members - enums are the contract the LLM must hit; sanitizers coerce toward them.
- Constrained scalars as `Annotated[str, Field(pattern=...)]` type aliases.
- **Every field has `description=`**; classes and enum members carry prose docstrings explaining why the category exists - these double as LLM-facing documentation when schemas render into prompts.
- For any LLM-generated artifact, provenance is structural: required `provenance: list[...]` + `synthesized_flags: list[...]` - every claim is cited or explicitly flagged as invented.

---

## 8. LLM layer

### Agents (`agents/`)
- One module per agent; a sub-package (`config.py`, `types.py`, `stages/`) when one grows complex. State = `TypedDict(total=False)`; each stage `async def stage(state) -> state`; a top-level `run_x()` chains them. **No graph framework.**
- Prompts are inline module-level triple-quoted strings composed with helper functions returning guidance blocks. No template engine, no prompt directory.
- Per-module `_llm_json(system, user, *, agent_name)` helper: system prompt as a single `cache_control={"type":"ephemeral"}` block (multi-call builds share it -> ~90% input-cost saving on later calls), then a **three-tier JSON parse**: strict -> tolerant repair (trailing commas/prose/comments, logged as `llm_json.repaired`) -> dump raw to disk + re-raise with a ±200-char window around the failure.
- Defensive `_sanitize_*_payload()` coerces LLM output into schema enums before pydantic validation (enum drift is the top failure mode); truncate overlong strings by introspecting pydantic `max_length`.

### The single instrumented wrapper (`observability/llm_client.py`) - firm
Every model call in the app goes through one function:

```python
call_anthropic(client, request, *, agent_name, prompt_template=None,
               conversation_id="", tags=None) -> (response, generation_id)
```

- **Context propagation:** `contextvars.ContextVar`s for `pipeline_id`, `phase`, `prompt_template`, ... each defaulting to an env var read at import - so CLI subprocesses inherit the orchestrator's context with zero plumbing. A `pipeline_context(**overrides)` context manager sets/resets cleanly.
- Opens a `gen_ai.chat {model}` span with `gen_ai.*` semconv attrs; always streams internally (even for non-streaming callers) to timestamp **TTFT** on first delta, reassembling the final message so call sites see the normal shape.
- Errors classified by class-name/message matching into coarse buckets (`rate_limit/timeout/context_length/auth/server_error/unknown`) - deliberately not importing the SDK exception hierarchy.
- Cost computed from a `MODEL_PRICES` table (input/output/cache_write/cache_read per MTok); unknown model -> warn + $0, never raise.
- Persists one row per call (`llm_calls`: tokens, cache stats, cost, ttft, attempt, error_type, template, pipeline id + phase) - **best-effort, no-throw**; then anomaly checks in a separate try block.

---

## 9. The assistant subsystem (the full loop)

An app-wide agentic chat in a right drawer (⌘J) that can operate the app with tools, an approval gate, and full observability. Replicate these pieces in order:

### Persistence
Two tables: `conversations(id, actor, title, status CHECK('active','archived'), timestamps, last_message_at)` and `turns(role CHECK('user','assistant','tool'), content, tool_calls JSONB, tool_results JSONB, context_scope JSONB, token counts)`. Storing `tool` as its own turn means replays read left-to-right without re-execution.

### Tool catalog (`agents/<domain>_tools.py`) - firm pattern
Each tool is two independent pieces: a module-level raw Anthropic tool-def dict (`TOOL_X = {"name","description","input_schema"}` - no decorators, no framework) and an executor `def _exec_x(args, session) -> Any`. Wired in registries:

```python
TOOLS_READONLY / TOOLS_MUTATING / TOOLS_ALL
MUTATING_TOOL_NAMES: frozenset      # UI badges
NEEDS_APPROVAL_TOOL_NAMES: frozenset  # human-in-the-loop gate
EXECUTORS_... : dict[str, Callable[[dict, Session], Any]]

def execute_tool(name, args, session) -> tuple[Any, bool]:  # (result, is_error)
    # unknown tool and exceptions -> ({"error": ...}, True) - the model recovers
```

Result contract: JSON-serializable and **bounded** - the agent re-sends every tool_result each iteration, so a 50KB blob costs 50KB x N. `list_x` tools take a shared clamped `limit` schema fragment (default 20, max 100) and return slim rows; `get_x` returns full detail. Enum params are generated from the pydantic schemas at import so tool schemas can't drift.

### Server-owned background runs (`api/assistant_runs.py`)
One `Run` per conversation: status ∈ `running|awaiting_approval|done|failed|cancelled`, append-only seq'd event list, asyncio task, threading.Event for cancel. `start_run()` returns `(run, created)` - a second start returns the existing one instead of racing. `emit()` does a wakeup-swap (`wake, self._wakeup = self._wakeup, Event(); wake.set()`) so N tailers each wake once; `tail(after)` snapshots the wakeup before scanning (closes the missed-event race). Finished runs linger ~120s for late reattach. In-memory is OK **because** full turns persist to Postgres after every loop iteration.

### The agent loop
1. Rebuild `messages` from all DB turns; heal orphaned `tool_use` blocks (a crash mid-batch otherwise wedges the conversation - the API rejects `tool_use` without a matching `tool_result`).
2. Stream with `tools=TOOLS_ALL`; emit `delta` events per text chunk.
3. No `tool_use` blocks in the final message -> persist assistant turn, done. Else persist the turn with `tool_calls`, then resolve.
4. Per tool: emit `tool_call`; if in `NEEDS_APPROVAL_TOOL_NAMES` and approvals are on -> emit `approval_required`, set status `awaiting_approval`, **stop** (the paused state is recoverable purely from the DB: last turn is assistant-with-tool_calls and no tool turn follows). Otherwise execute under an `execute_tool {name}` span.
5. Threading rule: tools that schedule asyncio work run inline on the loop; everything else via `asyncio.to_thread` with **its own DB session** (sessions never cross threads).
6. Persist one `tool` turn per batch; loop. Rails: hard iteration cap (5), generous `max_tokens` so structured edits can't truncate mid-JSON, 409 if a run is already active (checked *before* persisting the user turn), declined tools return `{"declined": true, "message": "...do not retry without a new instruction"}`.

### API surface
`POST /chat` (SSE tail), `POST /conversations/{id}/resume` (`{decision: approve|reject}`), `GET /conversations/{id}/run/events?after=N` (reattach), `POST .../run/cancel`, `GET/POST` conversation CRUD + archive, `GET /runs` (for completion toasts). SSE vocabulary: `delta, tool_call, tool_result, approval_required, turn_persisted, cancelled, done, error`.

### Frontend
- `AssistantContext` holds only UI intent: `{open, scope, seedPrompt, newThreadNonce, openAssistant(opts), ...}` + a `deriveScopeFromPath(pathname)` regex map so a bare ⌘J still carries page context; explicit scopes merge over route-derived.
- Streaming via `fetch` + a manual SSE frame parser (**not** `EventSource` - chat needs POST bodies): buffer, split `\n\n`, parse `event:`/`data:` lines, dispatch to a typed handlers interface; returns an `AbortController`. **The connection is only a viewer - aborting never stops the run** (cancel is a server call).
- Drawer state: durable transcript from react-query; a separate ephemeral `live` object (text, calls, results) discarded on finish + refetch. A polling effect finds active runs for the open conversation and reattaches (`?after=0`) - that's how refresh/reopen rejoins mid-stream. 409 on send returns the text to the composer and lets reattach take over.
- Tool rendering: a `TOOL_LABEL` map, a one-line input hint fn, and a result-detail fn that reads live SSE events **or** persisted JSON identically through one chip component. Assistant prose passes through a linkifier that turns internal paths into router `<Link>`s - the agent hands off navigation by mentioning a path.

---

## 10. Observability & guardrails package

Shape: `observability/{__init__, otlp, llm_client, tools, evals, policy, hooks, health, preflight}.py`.

- `init_telemetry()` is `@lru_cache`d + registers an **`atexit` flush** - without it, short-lived CLI subprocesses drop all spans ("the most common cause of an empty observability page").
- `track_tool_call(...)` context manager -> one span + one durable row + a scope check, in lockstep; yields a mutable dict the caller writes its output summary into.
- **Structural evals**: after each phase, check artifact *shape* (not correctness); record as both a DB row and a span event; failures show red on a dashboard but don't block - hard failures belong to pydantic.
- **Policy guards** (all audit-only, never blocking, no-throw): cost-spike/runaway-output anomalies from a `THRESHOLDS` dict; conservative substring-based prompt-injection screening of external text; per-agent tool allowlist where absent = unscoped. All write to a violations table + span event.
- **Preflight guard hook**: optional synchronous guard-service POST before requests reach the model (redact PII / deny); default off; fail-open by default; never rewrites structured tool_use/tool_result content.
- **Health heartbeat**: lifespan task probing each external dependency every 60s into a `system_health` table, surfaced at `/api/health/services`.
- **Config preflight**: per-signal checks naming the exact credential scope missing; consumed by the setup wizard, boot warnings, and a CLI `doctor` command.

---

## 11. Testing conventions

- `tests/{unit,integration,fixtures}`; unit mirrors the src package layout. Default `pytest` runs unit only (`addopts = "-m 'not integration'"`); integration modules declare `pytestmark = pytest.mark.integration`.
- **Fake LLM client**: hand-rolled `SimpleNamespace` fakes reproducing the SDK surface (`content` blocks, `usage` with cache fields, `stop_reason`, a `messages.stream()` context manager with `text_stream` + `get_final_message()`), with canned JSON keyed per agent phase - so the real wrapper, sanitizers, and pydantic validation all execute; only the network is faked.
- **Ephemeral Postgres**: one session-scoped `testcontainers` `PostgresContainer("postgres:16-alpine")` (skip if lib missing); a per-test `engine` fixture monkeypatches the two `lru_cache`d factories in `storage/db.py` so all in-package callers transparently hit the container; tests call `apply_migrations()` themselves, exercising the real migration path.
- **Teardown rule**: have the fixture teardown call `drop_all(engine)` instead of maintaining a second table list in `conftest.py` (a duplicated list always drifts eventually).

---

## 12. The four contracts (memorize these)

1. **Four-step persisted-entity contract** - migration file -> `drop_all()` registration -> repo class -> storage `__init__` export. (§6)
2. **`stream(after_seq)` replay-then-tail SSE contract** - DB replay -> terminal check -> stale-reap convergence -> event-driven tail with 30s heartbeat. (§5)
3. **Single instrumented LLM wrapper** with ContextVar+env context propagation, TTFT-capturing internal streaming, priced cost rows, no-throw persistence. (§8)
4. **Tool-def + executor + registry split** with `READONLY`/`MUTATING`/`NEEDS_APPROVAL` sets and a never-throwing `execute_tool`. (§9)

---

## 13. Repo skeleton

```
pyproject.toml                  # uv; ruff/pytest/mypy inline; [project.scripts] CLI entry
justfile                        # install/up/run/db-*/api/ui/test/test-integration/lint/fmt/typecheck/check
.env.example                    # every var documented; app copies to .env on first `just run`
deploy/docker/{Dockerfile,compose.yaml}
src/<pkg>/
  api/
    main.py                     # lifespan -> routers -> setup-gate middleware -> mount_ui (last)
    routes/<resource>.py        # APIRouter, local DTOs, session_scope in handlers, no Depends
    runner.py                   # whitelisted subprocess driver
    pipeline.py                 # PHASES tuple + async generator of event dicts
    pipeline_registry.py        # DB-durable events + _LIVE wakeups; stream(after_seq)
    assistant_runs.py           # server-owned chat run buffer
    setup/                      # first-run wizard: status/validate/persist
  storage/{db,migrator,repositories}.py + migrations/NNNN_*.sql
  schemas/                      # pydantic contracts, flat re-export __init__
  agents/                       # one module per agent + <domain>_tools.py catalog
  observability/                # init_telemetry/llm_client/tools/evals/policy/hooks/health/otlp/preflight
  cli/main.py                   # click CLI - canonical business-logic surface
tests/{unit,integration,fixtures}/
ui/                             # per §§2-4
```

---

## 14. Build order for a new app

Work in this sequence; each stage has a demo-able exit criterion.

1. **Scaffold** - pyproject + justfile + compose + `.env.example`; `storage/` (db, migrator, first migration, one repo); `just db-init` works; unit + integration test harness runs green.
2. **Walking skeleton** - FastAPI `main.py` (lifespan, CORS, health route, mount_ui), Vite UI with `index.css` tokens pasted in, Layout/TopBar/Card/Button/Badge/Toast primitives, one list page with StatKpi row + table + pagination against a real endpoint. *Exit: `just run` serves a themed, keyboard-navigable app on one port.*
3. **Domain schemas + first agent** - pydantic contracts with descriptions/enums/provenance; one agent module using the instrumented wrapper + `_llm_json`; CLI command; fake-LLM unit tests. *Exit: CLI produces a validated artifact into Postgres.*
4. **Pipeline + live UI** - runner/pipeline/registry trio, SSE endpoint, journey/progress UI, orphan reaper. *Exit: kick off a build from the UI, close the tab, reopen, watch it still streaming.*
5. **Assistant** - tables, tool catalog (start with 3 read-only tools), run registry, `/chat` SSE, drawer with ⌘J. Add mutating tools + approval gate second. *Exit: the assistant can answer "what's in the system?" and start one gated action.*
6. **Guardrails + polish** - evals, policy checks, health heartbeat, setup wizard, command palette, empty states, `just check` green, README with the run lane.

## 15. Things that are easy to get wrong (learned the hard way)

- Forgetting `drop_all()` registration for a new table (breaks db-reset silently).
- Emitting `pipeline:failed` without `phase:failed` first (UI spins forever).
- Letting a compose-injected env var share a name with a `.env` var while using `load_dotenv(override=True)` (it gets clobbered - use the `<APP>_`-prefixed infra name).
- Mounting the SPA catch-all before the API routers, or forgetting the `api/` JSON-404 carve-out.
- Skipping the `atexit` telemetry flush in CLI subprocesses (spans silently vanish).
- Sessions crossing threads in tool executors (each `to_thread` executor opens its own session).
- Unbounded tool results (re-sent every agent iteration - cost multiplies).
- Trusting the model to honor schema `limit` bounds (always re-clamp server-side).
- Two hand-maintained copies of the table list (conftest vs drop_all) - use `drop_all` in the fixture.
- `window.alert()` for errors - use inline errors, banners, or toasts.
