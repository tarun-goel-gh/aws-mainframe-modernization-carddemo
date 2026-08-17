# Disaster Recovery

`prompt_type: disaster_recovery`

| Field | Value |
|---|---|
| Level | 7 — Operations |
| Evidence plan | `atx-operations` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L7-operations/disaster-recovery.md` |
| Ledger column | `disaster_recovery` |
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

## Prompt template — verbatim from `prompts/all_prompts.py::DISASTER_RECOVERY_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate a disaster recovery plan for the **{application_name}** application.

Before generating the plan, please:
1. Review infrastructure topology and redundancy
2. Analyze backup and replication mechanisms
3. Identify critical business functions and dependencies
4. Review prior DR tests and incidents

Based on your findings, produce a detailed specification including:

**DR Strategy**
- Recovery objectives (RPO / RTO)
- Criticality classification

**Backup Procedures**
- Backup scope and frequency
- Storage and retention

**Recovery Procedures**
- Step-by-step recovery actions
- Validation steps

**Failover Strategy**
- Manual vs automated failover
- Rollback considerations

**Testing & Validation**
- DR drill schedules
- Success criteria

**Communication Plan**
- Stakeholder notification
- Incident communication flow

Structure the output as a formal Disaster Recovery Plan.
