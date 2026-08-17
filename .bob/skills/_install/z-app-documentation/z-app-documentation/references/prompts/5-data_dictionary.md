# Data Dictionary

`prompt_type: data_dictionary`

| Field | Value |
|---|---|
| Level | 5 — Data |
| Evidence plan | `z-data` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L5-data/data-dictionary.md` |
| Ledger column | `data_dictionary` |
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

## Prompt template — verbatim from `prompts/all_prompts.py::DATA_DICTIONARY_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate a comprehensive data dictionary for the **{application_name}** application.

Before generating the data dictionary, please:
1. Review database schemas and ORM models
2. Analyze data access layers and APIs
3. Identify reference and master data
4. Review data validation and constraints

Based on your findings, produce a structured specification including:

**Data Entity Inventory**
- Entity name and description
- Business meaning

**Attributes**
- Attribute name
- Data type and format
- Mandatory vs optional

**Relationships**
- Entity relationships
- Cardinality

**Data Quality Rules**
- Validation constraints
- Default values

**Retention & Privacy**
- Retention policies
- Sensitivity classification

Structure the output as a formal Data Dictionary document.
