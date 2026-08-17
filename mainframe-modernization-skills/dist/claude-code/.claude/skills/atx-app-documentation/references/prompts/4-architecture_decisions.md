# Architecture Decision Records

`prompt_type: architecture_decisions`

| Field | Value |
|---|---|
| Level | 4 — Design & Decisions |
| Evidence plan | `atx-structure` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L4-design/architecture-decisions.md` |
| Ledger column | `architecture_decisions` |
| Template placeholders | `{application_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`atx-structure`** plan. Gather all
   evidence **before** writing any section.
3. Apply `references/atx-substitutions.md` wherever the template names a distributed-stack
   artifact (pom.xml, REST endpoint, Docker, npm, ORM, git log …). Use the AWS Transform equivalent.
   If no AWS Transform equivalent exists, render the heading with `Not available from AWS Transform analysis`.
4. State **Coverage** before the first content section: which business functions this
   document's content covers, which scoped functions delivered no specification, and
   which were excluded. Never generalise from delivered functions to the whole
   application, and never state a count without its denominator.
5. Fill the placeholders: `{application_name}` = resolved application name,
   `{current_date}` = today's date from context, `{generated_by}` =
   `AWS Transform — mainframe reverse engineering (assess + reimagine)`.
6. Emit the document to the Output file above, then update the ledger.

> **Template gap.** This template is a stub in the origin service
> (`all_prompts.py`) — it names the document and its focus but supplies no
> OUTPUT STRUCTURE. Bob must therefore choose the section set. Keep it stable
> across runs: use the section list below, and do not vary it between
> regenerations. Extend this file if you want a richer fixed structure.
### Fixed section set for this document

1. Decision Register — table: ADR ID (`ADR-001`), title, status, date, affected members
2. One ADR per decision, each with: Context, Decision, Consequences, Evidence
3. Decisions Inferred vs. Decisions Documented — separate the two explicitly; an inferred decision is an `Assumption — not tool-verified`
4. Superseded / Open Decisions
5. Evidence Index

**Sourcing rule.** An ADR may only be written for a decision that is *observable in the
codebase* — a chosen access method, a copybook-sharing convention, an error-handling pattern,
a program-decomposition rule. Do not write ADRs for decisions you cannot point at in source.

## Prompt template — verbatim from `prompts/all_prompts.py::ARCHITECTURE_DECISIONS_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

# Architecture Decision Records (ADRs)

Generate Architecture Decision Records for {application_name}.
