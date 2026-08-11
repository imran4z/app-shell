# APP_SPEC - describe your app here

Fill this in, then tell your coding agent: **"Read CLAUDE.md, BLUEPRINT.md,
and APP_SPEC.md, then build the app."** Everything below the line is yours;
the more concrete you are, the less the agent has to guess. Delete the
example answers (shown in *italics*) as you replace them.

Don't describe buttons, colors, or layouts - the design system is settled
(BLUEPRINT.md). Describe the domain, and the agent maps it onto the
patterns already wired into this repo.

---

## 1. What is it?

One or two sentences. Name it.

> *Example: "RenewalRadar - a tool that tracks our customers' contract
> renewal dates and drafts outreach plans before they lapse."*

## 2. What does it do?

The core loop, in plain language. What goes in, what happens, what comes out.

> *Example: "I paste in a customer name and contract end date. The app
> researches recent activity, scores renewal risk, and produces a one-page
> renewal plan I can review and edit."*

## 3. What's the outcome?

What does "it worked" look like? What artifact, decision, or state change
does a successful run produce?

> *Example: "A reviewed renewal plan per customer, and a dashboard that
> shows which renewals are at risk this quarter."*

## 4. Who is the audience?

Who uses it, and what do they already know? This calibrates copy, empty
states, and how much the UI explains itself.

> *Example: "Account managers. Non-technical. They live in the browser and
> will never run a CLI."*

## 5. Other context

Anything else that shapes the build. Prompts for you:

- **Entities** - what are the nouns? (customers, plans, runs, reports...)
  Which ones need history / audit? Which get deleted vs. archived?
- **Long-running work** - is there a pipeline (research -> generate ->
  review)? Should users watch it stream live?
- **LLM involvement** - which steps need a model? What should the model
  produce (use the schemas-as-contracts pattern)? Rough volume/cost
  tolerance?
- **Assistant** - the ⌘J assistant ships with the template. Which of
  your domain's actions should it get as tools, and which of those need
  human approval before running?
- **Integrations** - external systems, APIs, credentials. (If one has a
  brand color, remember the rule: brand color = live connection only.)
- **Scale & privacy** - single user on a laptop? Team? Anything sensitive
  that must never leave the machine?

> *Example: "Entities: customers, renewal_plans, research_runs. Research ->
> score -> draft is a 3-phase pipeline; users should watch it stream.
> Claude drafts plans; ~50 runs/month is fine. Yes to the assistant, with
> approval required before it edits a plan. Integration: Salesforce
> read-only via API key. Single team, runs in Docker Desktop."*

## 6. Name & identity (optional)

- App name (wordmark in the top bar): ...
- Python package name, if you care (default: rename `appshell` to a slug
  of the app name): ...
- Keep the teal/sky palette (recommended - it's AA-checked). Only note a
  change if there's a hard brand requirement.
