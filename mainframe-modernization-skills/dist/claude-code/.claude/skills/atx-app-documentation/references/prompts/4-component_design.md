# Component Design

`prompt_type: component_design`

| Field | Value |
|---|---|
| Level | 4 — Design & Decisions |
| Evidence plan | `atx-module` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L4-design/component-design.md` |
| Ledger column | `component_design` |
| Template placeholders | `{application_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`atx-module`** plan. Gather all
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

## Prompt template — verbatim from `prompts/all_prompts.py::COMPONENT_DESIGN_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate detailed component design specifications for the **{application_name}** application.

Before generating the specifications, please:
1. Identify core components and services
2. Analyze component boundaries and responsibilities
3. Review interfaces, APIs, and data contracts
4. Analyze component-level non-functional requirements

Based on your findings, produce a detailed specification including:

**Component Overview**
- Component name and purpose
- Scope and responsibilities

**Interfaces**
- Provided and required interfaces
- API contracts

**Internal Design**
- Core classes or modules
- Key algorithms or workflows

**Data Management**
- Data ownership
- Persistence strategy

**Error Handling & Resilience**
- Failure modes
- Retry and fallback strategies

Structure the output as a formal Component Design Specification.
