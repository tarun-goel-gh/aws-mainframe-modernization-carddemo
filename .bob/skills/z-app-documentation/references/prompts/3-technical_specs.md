# Technical Specifications

`prompt_type: technical_specs`

| Field | Value |
|---|---|
| Level | 3 — Technical Documentation |
| Evidence plan | `z-module` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L3-technical-documentation/technical-specs.md` |
| Ledger column | `technical_specs` |
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

## Prompt template — verbatim from `prompts/all_prompts.py::TECHNICAL_SPECS_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate detailed technical specifications for the **{application_name}** application.

Before generating the specifications, please:
1. Review source code, configuration files, and build descriptors
2. Identify technology stacks, frameworks, and libraries
3. Analyze APIs, services, and integration mechanisms
4. Review infrastructure and environment configurations

Based on your findings, produce a comprehensive specification including:

**Technology Stack**
- Programming languages
- Frameworks and libraries
- Runtime environments

**Application Architecture**
- Layering and module structure
- Core services and utilities

**API & Service Specifications**
- API types (REST, GraphQL, messaging)
- Authentication and authorization mechanisms

**Configuration & Environment Management**
- Environment-specific configurations
- Feature flags and secrets management

**Operational Considerations**
- Logging and monitoring
- Error handling strategies

Structure the output as a formal Technical Specification document.
