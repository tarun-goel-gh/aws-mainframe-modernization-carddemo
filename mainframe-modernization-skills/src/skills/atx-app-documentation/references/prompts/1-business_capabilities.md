# Business Capabilities Map

`prompt_type: business_capabilities`

| Field | Value |
|---|---|
| Level | 1 — Business Context |
| Evidence plan | `atx-business` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L1-business-context/business-capabilities.md` |
| Ledger column | `business_capabilities` |
| Template placeholders | `{application_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`atx-business`** plan. Gather all
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

1. Capability Inventory — table: capability, supporting programs, supporting jobs, grouping criterion, provenance
2. Capability Detail — one subsection per capability: purpose, trigger, inputs, outputs, owning members
3. Current State Assessment — evidence-backed condition of each capability (complexity, quality findings)
4. Modernization Impact per Capability — risk, coupling, data dependency
5. Gaps and Unresolved Items
6. Evidence Index

## Prompt template — verbatim from `prompts/all_prompts.py::BUSINESS_CAPABILITIES_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

# Business Capabilities Map

Generate a comprehensive business capabilities map for {application_name}.

Focus on:
- Capability inventory
- Current vs. future state
- Gap analysis
- Modernization impact on each capability
