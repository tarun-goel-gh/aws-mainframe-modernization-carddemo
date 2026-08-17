# Database Schema (Full)

`prompt_type: database_schema_full`

| Field | Value |
|---|---|
| Level | 5 — Data |
| Evidence plan | `z-data` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L5-data/database-schema-full.md` |
| Ledger column | `database_schema_full` |
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

## Prompt template — verbatim from `prompts/all_prompts.py::DATABASE_SCHEMA_FULL_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate detailed database schema documentation for the **{application_name}** application.

Before generating the documentation, please:
1. Review database schemas and migration scripts
2. Analyze indexes, constraints, and triggers
3. Identify performance and scaling considerations
4. Review data access patterns from the application

Based on your findings, produce a comprehensive specification including:

**Schema Overview**
- Database type and version
- Logical vs physical schema

**Tables & Columns**
- Table purpose
- Column definitions and constraints

**Keys & Relationships**
- Primary and foreign keys
- Referential integrity rules

**Indexes & Performance**
- Indexing strategy
- Query optimization considerations

**Data Lifecycle**
- Archival and purge strategies
- Backup and recovery considerations

Structure the output as a formal Database Schema Documentation.
