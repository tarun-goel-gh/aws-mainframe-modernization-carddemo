# Business Requirements

`prompt_type: business_requirements`

| Field | Value |
|---|---|
| Level | 2 — Business Documentation |
| Evidence plan | `z-business` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L2-business-documentation/business-requirements.md` |
| Ledger column | `business_requirements` |
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

## Prompt template — verbatim from `prompts/all_prompts.py::BUSINESS_REQUIREMENTS_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

    Generate detailed business specifications for {feature_name} in the {application_name} application.

Before generating the specifications, please:
1. Search for and review any existing {application_name} documentation, source code, or configuration files
2. Check the database schema for customer-related tables and relationships
3. Identify existing APIs, services, or integration points
4. Review any existing business rules or validation logic

Based on your findings, create comprehensive specifications including:

**Business Requirements**
- High-level business objectives
- Stakeholder needs
- Success criteria

**Functional Requirements**
- Detailed feature descriptions
- User stories and use cases
- System capabilities

**Data Requirements**
- Data entities and attributes
- Data relationships
- Data quality requirements
- Retention policies

**Process Flows**
- End-to-end process descriptions
- Decision points
- Exception handling

**Business Rules**
- Validation rules
- Calculation rules
- Workflow rules
- Authorization rules

**Validation Requirements**
- Input validation
- Business logic validation
- Cross-field validation

**Integration Requirements**
- External systems
- APIs and protocols
- Data exchange formats
- Security requirements

Please structure the output as a formal business specification document.
    
