# Monitoring & Alerting

`prompt_type: monitoring_alerting`

| Field | Value |
|---|---|
| Level | 7 — Operations |
| Evidence plan | `z-operations` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L7-operations/monitoring-alerting.md` |
| Ledger column | `monitoring_alerting` |
| Template placeholders | `{application_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`z-operations`** plan. Gather all
   evidence **before** writing any section.
3. Apply `references/z-substitutions.md` wherever the template names a distributed-stack
   artifact (pom.xml, REST endpoint, Docker, npm, ORM, git log …). Use the Z equivalent.
   If no Z equivalent exists, render the heading with `Not available from Z Premium analysis`.
4. Fill the placeholders: `{application_name}` = resolved application name,
   `{current_date}` = today's date from context, `{generated_by}` =
   `IBM Bob — Z Premium Package workflows`.
5. Emit the document to the Output file above, then update the ledger.

## Prompt template — verbatim from `prompts/all_prompts.py::MONITORING_ALERTING_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate monitoring and alerting documentation for the **{application_name}** application.

Before generating the documentation, please:
1. Review monitoring tools and configurations
2. Analyze logs, metrics, and traces
3. Identify SLAs, SLOs, and error budgets
4. Review incident history and alert fatigue issues

Based on your findings, produce a comprehensive specification including:

**Monitoring Strategy**
- Observability goals
- Golden signals

**Metrics Catalog**
- Application, infrastructure, and business metrics

**Alert Definitions**
- Alert conditions and thresholds
- Severity levels and routing

**Dashboards**
- Dashboard layouts and KPIs
- Stakeholder views

**Log & Trace Management**
- Log aggregation
- Distributed tracing

**SLA & SLO Tracking**
- Availability and performance targets
- Compliance tracking

Structure the output as a formal Monitoring & Alerting Specification.
