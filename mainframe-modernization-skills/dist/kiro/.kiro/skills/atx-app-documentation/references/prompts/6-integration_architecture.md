# Integration Architecture

`prompt_type: integration_architecture`

| Field | Value |
|---|---|
| Level | 6 — Integration & Interfaces |
| Evidence plan | `atx-integration` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L6-integration/integration-architecture.md` |
| Ledger column | `integration_architecture` |
| Template placeholders | `{application_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`atx-integration`** plan. Gather all
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

## Prompt template — verbatim from `prompts/all_prompts.py::INTEGRATION_ARCHITECTURE_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate integration architecture documentation for the **{application_name}** application.

Before generating the documentation, please:
1. Review integration diagrams, APIs, and messaging configurations
2. Analyze synchronous and asynchronous integration patterns
3. Identify external systems and data exchanges
4. Review error handling, retries, and compensation logic
5. Analyze observability and monitoring mechanisms

Based on your findings, produce a comprehensive specification including:

**Integration Landscape**
- Internal and external systems
- Integration ownership and boundaries

**Integration Patterns**
- REST, messaging, events, file-based integrations
- Orchestration vs choreography

**Message & Data Flows**
- Request/response and event flows
- Sequencing and dependencies

**Error Handling**
- Error categories
- Retry, dead-letter, and compensation strategies

**Monitoring & Observability**
- Integration health metrics
- Logging and traceability

Structure the output as a formal Integration Architecture Document.
