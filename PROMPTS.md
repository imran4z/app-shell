# PROMPTS - hand this template to a coding agent

Copy one of these into Claude Code (or any coding agent) from the root of
your clone. Each prompt does three things: points the agent at the three
docs that drive the build, carries your domain context in the APP_SPEC
shape, and states the definition of done. Swap the details for your own -
the *structure* is what makes the agent effective.

The short version, if you'd rather fill in `APP_SPEC.md` yourself:

```
Read CLAUDE.md, BLUEPRINT.md and APP_SPEC.md, then build the app.
```

Everything below is the long version: spec included inline so you can
paste one message and walk away.

---

## Example 1 - Healthcare patient portal

```
Read CLAUDE.md first, then BLUEPRINT.md, then this message. This repo is a
working app-shell template; your job is to replace its example domain
(Items, Profiles) with the real one below, following the build procedure
in CLAUDE.md. Do not re-derive design or architecture decisions - they are
settled in BLUEPRINT.md.

Write this spec into APP_SPEC.md (replacing the template text), then build:

1. WHAT IS IT
   CarePortal - a patient portal for a small specialty clinic.

2. WHAT IT DOES
   Staff register patients and manage their upcoming appointments and care
   tasks. Each patient has a record that accumulates facts over time
   (allergies, medications, insurance details). A morning dashboard shows
   today's appointments and overdue care tasks.

3. OUTCOME
   The front desk works entirely out of this portal: today's schedule at a
   glance, no patient question requiring a dig through paper files, and a
   care-task list that never silently goes stale.

4. AUDIENCE
   Clinic front-desk staff and nurses. Non-technical, browser-only, often
   on an iPad at the desk - the responsive layout matters.

5. CONTEXT
   - Entities:
     * patients - replace the template's Profiles pattern: list -> detail,
       with attributes (allergies, medications, insurance) added over time
       on the detail page; lifecycle active -> discharged -> archived.
     * appointments - replace the Items pattern: state machine
       scheduled -> checked_in -> completed / no_show; belongs to a patient
       (FK, ON DELETE CASCADE); list page filterable by day.
     * care_tasks - per-patient follow-ups with a due date; state
       open -> done; overdue = open AND past due (derive in SQL, not UI).
   - Dashboard: replace the hero with "today at the clinic" - appointment
     count, checked-in count, overdue care tasks (danger tone when > 0).
   - Assistant tools: read-only list_patients, todays_appointments,
     overdue_care_tasks; approval-gated check_in_patient and
     complete_care_task. Replace the example item/profile tools.
   - LLM use beyond the assistant: none in v1.
   - Privacy: demo data only for now, but write nothing to logs that
     contains patient names (log ids).
   - Rename the package appshell -> careportal per CLAUDE.md step 1.

DEFINITION OF DONE
   - `just check` green; unit + integration tests updated for the new
     entities (follow tests/ patterns; the four-step storage contract for
     every table, including drop_all registration).
   - The example Items/Profiles code is fully deleted (migrations, repos,
     routes, pages, nav, palette, CLI seeds, assistant tools).
   - `just seed` creates a believable demo clinic (10 patients, today's
     appointments, some overdue tasks).
   - `just run` boots it in Docker Desktop; walk the whole flow once and
     fix what you find before declaring done.
   - docs/ARCHITECTURE.md regenerated for this domain (CLAUDE.md step 8)
     and `just screenshots` rerun against the seeded app.
```

## Example 2 - E-commerce customer portal

```
Read CLAUDE.md first, then BLUEPRINT.md, then this message. This repo is a
working app-shell template; replace its example domain (Items, Profiles)
with the real one below, following CLAUDE.md's build procedure. Design and
architecture are settled - spend your effort on the domain.

Write this spec into APP_SPEC.md (replacing the template text), then build:

1. WHAT IS IT
   ShopDesk - the support-side customer portal for a small e-commerce
   store.

2. WHAT IT DOES
   Support agents look up customers, see their orders, and process
   returns. Customers accumulate notes and preferences on their record.
   Orders move through a fulfillment lifecycle; returns are requests that
   an agent approves or rejects with a reason.

3. OUTCOME
   A support agent resolves "where is my order?" and "I want to return
   this" tickets from one screen, and management sees return volume and
   pending-return backlog at a glance.

4. AUDIENCE
   Support agents (power users - keyboard-first, they will live in the
   ⌘K palette) and a team lead who checks the dashboard numbers daily.

5. CONTEXT
   - Entities:
     * customers - the Profiles pattern: list -> detail; attributes
       (shipping notes, preferences, loyalty tier) and tags added over
       time on the detail page.
     * orders - the Items pattern, richer: order number, customer FK,
       total_cents (integer, never float), state machine
       placed -> paid -> shipped -> delivered / cancelled; detail JSONB
       holds line items.
     * returns - FK to order; state requested -> approved / rejected ->
       received -> refunded; a rejection requires a reason string.
   - Dashboard: orders today, open returns (warning tone), refunds issued
     this week; keep the two-band composition.
   - Assistant tools: read-only lookup_customer, order_status,
     list_open_returns; approval-gated approve_return and reject_return
     (rejection reason as a tool arg). This is the main demo: an agent
     asks "approve the return on order #1042" and the approval card shows
     exactly what will run.
   - Money: integer cents everywhere; render dollars only in the UI.
   - Rename the package appshell -> shopdesk per CLAUDE.md step 1.

DEFINITION OF DONE
   - `just check` green; the storage four-step contract honored for every
     new table (drop_all child-first: returns before orders before
     customers).
   - Example Items/Profiles code fully deleted.
   - `just seed` builds a demo store (25 customers, 60 orders across all
     states, a handful of returns in each state).
   - `just run` works in Docker Desktop; process one return end-to-end
     through the assistant with the approval gate before declaring done.
   - docs/ARCHITECTURE.md regenerated for this domain (CLAUDE.md step 8)
     and `just screenshots` rerun against the seeded app.
```

## Writing your own prompt

Keep the skeleton, change the middle:

1. **Opening paragraph** - always the same: read CLAUDE.md -> BLUEPRINT.md
   -> this message; replace the example domain; don't re-litigate settled
   decisions.
2. **The five spec sections** - what / does / outcome / audience /
   context. In *context*, map every entity you name onto one of the two
   shipped patterns: "the Items pattern" (flat list + state machine) or
   "the Profiles pattern" (list -> detail + enrichment). That single
   sentence is what lets the agent reuse working code instead of
   inventing structure.
3. **Assistant tools** - name the read-only tools and the approval-gated
   ones explicitly. The gate is already built; the agent only writes the
   tool defs and executors.
4. **Definition of done** - always demand: `just check` green, example
   domain deleted, a believable `just seed`, a `just run` walkthrough in
   Docker Desktop, and a regenerated docs/ARCHITECTURE.md with fresh
   `just screenshots`. Agents cut these corners unless told not to.
```

