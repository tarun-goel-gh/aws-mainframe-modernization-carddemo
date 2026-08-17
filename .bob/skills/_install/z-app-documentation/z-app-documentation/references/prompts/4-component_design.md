# Component Design

`prompt_type: component_design`

| Field | Value |
|---|---|
| Level | 4 — Design & Decisions |
| Evidence plan | `z-module` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L4-design/component-design.md` |
| Ledger column | `component_design` |
| Template placeholders | `{application_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`z-module`** plan. Gather all
   evidence **before** writing any section.
3. Apply `references/z-substitutions.md` wherever the template names a distributed-stack
   artifact (pom.xml, REST endpoint, Docker, npm, ORM, git log …). Use the Z equivalent.
   If no Z equivalent exists, render the heading with `Not available from Z Premium analysis`.
4. Fill the placeholders: `{application_name}` = resolved application name,
   `{current_date}` = today's date from context, `{generated_by}` =
   `IBM Bob — Z Premium Package workflows`.
5. Emit the document to the Output file above, then update the ledger.

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
