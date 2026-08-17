# Modernization Strategy

`prompt_type: modernization_strategy`

| Field | Value |
|---|---|
| Level | 8 — Modernization |
| Evidence plan | `atx-structure` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L8-modernization/modernization-strategy.md` |
| Ledger column | `modernization_strategy` |
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

## Prompt template — verbatim from `prompts/all_prompts.py::MODERNIZATION_STRATEGY_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate a modernization strategy for the **{application_name}** application.

Before generating the strategy, please:
1. Review current architecture, codebase, and infrastructure
2. Analyze technical debt, risks, and operational pain points
3. Identify business drivers and constraints
4. Review modernization patterns and reference architectures

Based on your findings, produce a comprehensive strategy including:

**Current State Assessment**
- Architecture and technology summary
- Key limitations and risks

**Target State Vision**
- Desired architectural outcomes
- Business and technical goals

**Modernization Options**
- Rehost, refactor, replatform, rebuild
- Pros and cons of each option

**Recommended Approach**
- Selected strategy and rationale

**High-Level Roadmap**
- Phases and milestones

**Success Criteria**
- Business and technical KPIs

Structure the output as a formal Modernization Strategy document.
