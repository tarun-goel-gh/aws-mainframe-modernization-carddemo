# Gap Analysis

`prompt_type: gap_analysis`

| Field | Value |
|---|---|
| Level | 8 — Modernization |
| Evidence plan | `atx-structure` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L8-modernization/gap-analysis.md` |
| Ledger column | `gap_analysis` |
| Template placeholders | `{application_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`atx-structure`** plan. Gather all
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

## Prompt template — verbatim from `prompts/all_prompts.py::GAP_ANALYSIS_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate a gap analysis for the **{application_name}** application.

Before generating the analysis, please:
1. Review current-state and target-state documentation
2. Identify architectural, technical, and operational differences
3. Analyze business and compliance impacts
4. Review dependencies and constraints

Based on your findings, produce a detailed analysis including:

**Current vs Target Comparison**
- Architecture
- Technology
- Processes

**Gap Identification**
- Gaps by category (People, Process, Technology)

**Impact Assessment**
- Business and technical impact

**Remediation Approach**
- Recommended actions
- Dependencies and sequencing

**Effort & Complexity**
- Relative effort estimation

**Prioritization**
- Priority ranking and rationale

Structure the output as a formal Gap Analysis document.
