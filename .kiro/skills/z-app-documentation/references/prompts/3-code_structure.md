# Code Structure

`prompt_type: code_structure`

| Field | Value |
|---|---|
| Level | 3 — Technical Documentation |
| Evidence plan | `z-module` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L3-technical-documentation/code-structure.md` |
| Ledger column | `code_structure` |
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

## Prompt template — verbatim from `prompts/all_prompts.py::CODE_STRUCTURE_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate detailed code structure documentation for the **{application_name}** application.

Before generating the documentation, please:
1. Analyze the repository layout and module structure
2. Review naming conventions and packaging strategies
3. Identify shared libraries, utilities, and frameworks
4. Review build files and dependency management

Based on your findings, produce a comprehensive specification including:

**Repository Overview**
- Repository type and layout
- Monorepo vs multirepo structure

**Module Organization**
- Module responsibilities
- Dependency relationships

**Layering Strategy**
- Presentation, business, data, and infrastructure layers
- Cross-cutting concerns

**Coding Standards & Conventions**
- Naming conventions
- Structural guidelines

**Extensibility & Maintainability**
- Extension points
- Refactoring considerations

Structure the output as a formal Code Structure Documentation.
