# Operations Manual

`prompt_type: operations_manual`

| Field | Value |
|---|---|
| Level | 7 — Operations |
| Evidence plan | `atx-operations` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L7-operations/operations-manual.md` |
| Ledger column | `operations_manual` |
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

## Prompt template — verbatim from `prompts/all_prompts.py::OPERATIONS_MANUAL_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate an operations manual for the **{application_name}** application.

Before generating the manual, please:
1. Review deployment architecture and runtime environments
2. Analyze operational scripts and runbooks
3. Review monitoring, alerting, and health checks
4. Identify support and escalation procedures

Based on your findings, produce a comprehensive manual including:

**System Overview**
- Application purpose and architecture summary

**Operational Procedures**
- Startup and shutdown steps
- Scheduled jobs and maintenance

**Health Checks**
- Application and infrastructure checks
- Dependency health validation

**Backup & Recovery**
- Backup processes
- Restore procedures

**Troubleshooting Guide**
- Common issues and resolutions
- Diagnostic steps

**Runbooks & Escalation**
- Incident response runbooks
- Escalation paths and contacts

Structure the output as a formal Operations Manual.
