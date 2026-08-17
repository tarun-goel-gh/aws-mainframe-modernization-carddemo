# Business Rules Catalog

`prompt_type: business_rules`

| Field | Value |
|---|---|
| Level | 2 — Business Documentation |
| Evidence plan | `atx-module` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L2-business-documentation/business-rules.md` |
| Ledger column | `business_rules` |
| Template placeholders | `{application_name}`, `{feature_name}` |
| Scope | Feature-scoped — requires `feature_name`; emit one file per feature under `L2-business-documentation/business-rules/` |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`atx-module`** plan. Gather all
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
   `AWS Transform — mainframe reverse engineering (assess + reimagine)`, `{feature_name}` = the feature being documented.
6. Emit the document to the Output file above, then update the ledger.

## Prompt template — verbatim from `prompts/all_prompts.py::BUSINESS_RULES_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

 Generate a comprehensive business rules catalog for the feature **{feature_name}** in the **{application_name}** application.

Before generating the rules, please:
1. Review existing business logic in code, configuration, and workflows
2. Analyze database constraints, validations, and triggers
3. Identify API-level and UI-level validations
4. Review existing test cases and defect history

Based on your findings, produce a structured specification including:

**Business Requirements**
- Purpose and intent of the rules
- Regulatory or policy drivers
- Stakeholder ownership

**Business Rule Inventory**
- Rule ID (BR-001 format)
- Rule name and description
- Rule category (Validation, Calculation, Authorization, Workflow)

**Rule Definition**
- Condition → Action → Outcome
- Inputs and dependencies
- Priority and execution order

**Implementation Locations**
- Code modules or services
- Database constraints or triggers
- Configuration or rules engines

**Validation & Test Cases**
- Positive and negative test scenarios
- Boundary conditions
- Data setup requirements

**Exception Handling**
- Rule override scenarios
- Error messages and user feedback
- Audit and compliance considerations

Structure the output as a formal Business Rules Specification document.
