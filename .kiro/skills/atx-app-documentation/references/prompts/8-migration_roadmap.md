# Migration Roadmap

`prompt_type: migration_roadmap`

| Field | Value |
|---|---|
| Level | 8 — Modernization |
| Evidence plan | `atx-structure` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L8-modernization/migration-roadmap.md` |
| Ledger column | `migration_roadmap` |
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

## Prompt template — verbatim from `prompts/all_prompts.py::MIGRATION_ROADMAP_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate a migration roadmap for the **{application_name}** application.

Before generating the roadmap, please:
1. Review gap analysis and modernization strategy
2. Identify technical and business dependencies
3. Analyze risk and change impact
4. Review testing and validation requirements

Based on your findings, produce a comprehensive roadmap including:

**Migration Strategy**
- Overall migration approach

**Phases & Waves**
- Phase objectives and scope

**Dependencies**
- Technical and organizational dependencies

**Milestones & Timeline**
- Key milestones and deliverables

**Resource Requirements**
- Skills and capacity needs

**Risk Mitigation**
- Identified risks and mitigations

**Testing & Cutover**
- Validation strategy
- Cutover and rollback plans

**Success Criteria**
- Acceptance and completion metrics

Structure the output as a formal Migration Roadmap document.
