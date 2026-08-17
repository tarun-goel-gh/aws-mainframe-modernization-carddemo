# Feature Catalog

`prompt_type: feature_catalog`

| Field | Value |
|---|---|
| Level | 2 — Business Documentation |
| Evidence plan | `z-business` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L2-business-documentation/feature-catalog.md` |
| Ledger column | `feature_catalog` |
| Template placeholders | `{application_name}`, `{feature_name}` |
| Scope | Feature-scoped — requires `feature_name`; emit one file per feature under `L2-business-documentation/feature-catalog/` |

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
   `IBM Bob — Z Premium Package workflows`, `{feature_name}` = the feature being documented.
5. Emit the document to the Output file above, then update the ledger.

## Prompt template — verbatim from `prompts/all_prompts.py::FEATURE_CATALOG_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate a detailed feature catalog for the feature **{feature_name}** in the **{application_name}** application.

Before generating the catalog, please:
1. Review application documentation and product backlog
2. Analyze source code modules and service boundaries
3. Identify user roles, permissions, and feature toggles
4. Review telemetry, logs, or usage analytics if available

Based on your findings, produce a comprehensive specification including:

**Business Requirements**
- Business value of the feature
- Target users and stakeholders
- Success metrics

**Feature Inventory**
- Feature ID and name
- Feature scope and boundaries
- Dependencies on other features

**Feature Description**
- Functional overview
- Key capabilities and limitations

**User Roles & Access**
- Roles authorized to use the feature
- Access levels and constraints

**Business Rules**
- Rules enforced by the feature
- Preconditions and validations

**Technical Implementation**
- Modules, services, or APIs involved
- Data stores and integrations
- Configuration and feature flags

**Usage Metrics**
- Adoption metrics
- Performance indicators
- Operational monitoring points

**Modernization Approach**
- Refactoring or re-architecture opportunities
- Cloud-native or AI enablement potential

Structure the output as a formal Feature Catalog document.
