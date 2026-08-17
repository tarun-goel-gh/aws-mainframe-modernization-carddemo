# System Architecture

`prompt_type: system_architecture`

| Field | Value |
|---|---|
| Level | 3 — Technical Documentation |
| Evidence plan | `atx-structure` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L3-technical-documentation/system-architecture.md` |
| Ledger column | `system_architecture` |
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

## Prompt template — verbatim from `prompts/all_prompts.py::SYSTEM_ARCHITECTURE_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate a detailed system architecture document for the **{application_name}** application.

Before generating the architecture documentation, please:
1. Review existing architecture diagrams, documentation, and ADRs
2. Analyze source code structure, frameworks, and runtime configurations
3. Identify major subsystems, services, and deployment units
4. Review infrastructure, cloud resources, and runtime environments
5. Identify key non-functional requirements (scalability, availability, security)

Based on your findings, create a comprehensive architecture specification including:

**Architecture Overview**
- Architectural style and patterns used
- High-level system context
- Key design goals and constraints

**Logical Architecture**
- Major components and layers
- Responsibilities and interactions
- Dependency structure

**Physical / Deployment Architecture**
- Runtime environments
- Deployment topology
- Infrastructure components

**Integration Architecture**
- Internal and external integrations
- Communication protocols
- Message and data flow

**Non-Functional Architecture**
- Scalability and performance approach
- Reliability and fault tolerance
- Observability and monitoring

**Architecture Risks & Trade-offs**
- Identified risks
- Assumptions and constraints
- Mitigation strategies

Structure the output as a formal System Architecture Document.
