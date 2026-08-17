# Business Process

`prompt_type: business_process`

| Field | Value |
|---|---|
| Level | 2 — Business Documentation |
| Evidence plan | `z-business` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L2-business-documentation/business-process.md` |
| Ledger column | `business_process` |
| Template placeholders | `{application_name}`, `{feature_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`z-business`** plan. Gather all
   evidence **before** writing any section.
3. Apply `references/z-substitutions.md` wherever the template names a distributed-stack
   artifact (pom.xml, REST endpoint, Docker, npm, ORM, git log …). Use the Z equivalent.
   If no Z equivalent exists, render the heading with `Not available from Z Premium analysis`.
4. Fill the placeholders: `{application_name}` = resolved application name,
   `{current_date}` = today's date from context, `{generated_by}` =
   `IBM Bob — Z Premium Package workflows`.
5. Emit the document to the Output file above, then update the ledger.

## Prompt template — verbatim from `prompts/all_prompts.py::BUSINESS_PROCESS_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate detailed business process documentation for the feature **{feature_name}** in the **{application_name}** application.

Before generating the documentation, please:
1. Review existing process documentation and workflow definitions
2. Analyze source code, orchestration logic, and background jobs
3. Identify integration points and system actors
4. Review exception handling and audit mechanisms

Based on your findings, produce a comprehensive specification including:

**Business Requirements**
- Purpose of the process
- Business outcomes supported
- Key stakeholders and owners

**Process Inventory**
- List of business processes and sub-processes
- Triggering events and outcomes

**Process Flows**
- Step-by-step process descriptions
- Text-based swim lanes (User / System / External)
- System interactions per step

**Decision Points**
- Business decision rules
- Conditional branching logic
- Manual vs automated decisions

**Exception Handling**
- Failure scenarios
- Retry, escalation, and compensation logic
- Audit and traceability requirements

**Process Metrics**
- KPIs and SLAs
- Throughput, latency, and error rates

**Pain Points & Improvements**
- Identified inefficiencies
- Automation or modernization opportunities

Structure the output as a formal Business Process Specification document.
