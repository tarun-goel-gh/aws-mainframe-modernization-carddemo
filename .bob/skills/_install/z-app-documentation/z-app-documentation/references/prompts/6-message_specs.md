# Message Specifications

`prompt_type: message_specs`

| Field | Value |
|---|---|
| Level | 6 — Integration & Interfaces |
| Evidence plan | `z-integration` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L6-integration/message-specs.md` |
| Ledger column | `message_specs` |
| Template placeholders | `{application_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`z-integration`** plan. Gather all
   evidence **before** writing any section.
3. Apply `references/z-substitutions.md` wherever the template names a distributed-stack
   artifact (pom.xml, REST endpoint, Docker, npm, ORM, git log …). Use the Z equivalent.
   If no Z equivalent exists, render the heading with `Not available from Z Premium analysis`.
4. Fill the placeholders: `{application_name}` = resolved application name,
   `{current_date}` = today's date from context, `{generated_by}` =
   `IBM Bob — Z Premium Package workflows`.
5. Emit the document to the Output file above, then update the ledger.

## Prompt template — verbatim from `prompts/all_prompts.py::MESSAGE_SPECS_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate message and file interface specifications for the **{application_name}** application.

Before generating the specifications, please:
1. Review messaging systems, queues, topics, and file exchanges
2. Analyze message producers and consumers
3. Review schemas, formats, and validation logic
4. Identify processing workflows and failure handling

Based on your findings, produce a detailed specification including:

**Message & File Catalog**
- Message or file name
- Purpose and triggering events

**Schemas & Formats**
- Payload structure
- Data types and constraints

**Validation Rules**
- Mandatory fields
- Schema and business validations

**Processing Logic**
- Consumer behavior
- Idempotency and ordering guarantees

**Error & Exception Handling**
- Rejection and retry logic
- Dead-letter processing

Structure the output as a formal Message & File Interface Specification.
