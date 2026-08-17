# Data Lineage

`prompt_type: data_lineage`

| Field | Value |
|---|---|
| Level | 5 — Data |
| Evidence plan | `z-data` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L5-data/data-lineage.md` |
| Ledger column | `data_lineage` |
| Template placeholders | `{application_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`z-data`** plan. Gather all
   evidence **before** writing any section.
3. Apply `references/z-substitutions.md` wherever the template names a distributed-stack
   artifact (pom.xml, REST endpoint, Docker, npm, ORM, git log …). Use the Z equivalent.
   If no Z equivalent exists, render the heading with `Not available from Z Premium analysis`.
4. Fill the placeholders: `{application_name}` = resolved application name,
   `{current_date}` = today's date from context, `{generated_by}` =
   `IBM Bob — Z Premium Package workflows`.
5. Emit the document to the Output file above, then update the ledger.

## Prompt template — verbatim from `prompts/all_prompts.py::DATA_LINEAGE_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate comprehensive data lineage documentation for the **{application_name}** application.

Before generating the documentation, please:
1. Review database schemas, ETL jobs, and data pipelines
2. Analyze data access layers, APIs, and batch processes
3. Identify data transformations and enrichment logic
4. Review data validation and quality checks
5. Identify downstream systems and consumers

Based on your findings, produce a detailed specification including:

**Data Source Inventory**
- Source systems and databases
- Source ownership and data domains

**Data Flows**
- End-to-end data movement
- Batch vs real-time flows

**Transformations**
- Business and technical transformations
- Aggregation, filtering, and enrichment logic

**Data Quality Controls**
- Validation and reconciliation checks
- Error handling and data correction flows

**Downstream Consumers**
- Reports, APIs, analytics, and external systems
- Data usage purpose

**Refresh & Latency**
- Refresh schedules
- Latency and freshness expectations

Structure the output as a formal Data Lineage Documentation.
