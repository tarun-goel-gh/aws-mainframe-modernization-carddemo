# Build & Deployment

`prompt_type: build_deployment`

| Field | Value |
|---|---|
| Level | 3 — Technical Documentation |
| Evidence plan | `atx-operations` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L3-technical-documentation/build-deployment.md` |
| Ledger column | `build_deployment` |
| Template placeholders | `{application_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`atx-operations`** plan. Gather all
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

## Prompt template — verbatim from `prompts/all_prompts.py::BUILD_DEPLOYMENT_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate build and deployment documentation for the **{application_name}** application.

Before generating the documentation, please:
1. Review build scripts, pipelines, and CI/CD configurations
2. Analyze artifact generation and versioning strategies
3. Identify deployment environments and promotion workflows
4. Review rollback and recovery mechanisms

Based on your findings, produce a comprehensive specification including:

**Build Process**
- Build tools and configurations
- Dependency resolution
- Artifact generation

**CI/CD Pipelines**
- Pipeline stages
- Quality gates and approvals

**Deployment Strategy**
- Deployment models (blue-green, canary, rolling)
- Environment promotion flow

**Configuration Management**
- Environment variables
- Secrets and credentials handling

**Operational Controls**
- Rollback strategy
- Deployment validation and monitoring

Structure the output as a formal Build & Deployment Specification document.
