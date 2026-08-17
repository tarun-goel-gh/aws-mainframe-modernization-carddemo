# User Stories

`prompt_type: user_stories`

| Field | Value |
|---|---|
| Level | 2 — Business Documentation |
| Evidence plan | `z-business` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L2-business-documentation/user-stories.md` |
| Ledger column | `user_stories` |
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

## Prompt template — verbatim from `prompts/all_prompts.py::USER_STORIES_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate detailed user stories and use cases for the feature **{feature_name}** in the **{application_name}** application.

Before generating the content, please:
1. Review existing {application_name} documentation, source code, and configuration files
2. Identify authentication roles, authorization rules, and personas
3. Analyze relevant APIs, UI components, and workflows
4. Review any existing user journeys or acceptance criteria

Based on your findings, produce a comprehensive specification covering:

**Business Requirements**
- Business goals addressed by this feature
- Target users and stakeholders
- Success and adoption criteria

**User Personas**
- Persona definitions derived from roles
- Responsibilities, goals, and constraints

**User Stories**
- Structured stories in the format:
  - As a <persona>
  - I want <capability>
  - So that <business value>
- Priority and dependencies per story

**Use Case Catalog**
- Use case ID and name
- Primary and alternate flows
- Preconditions and postconditions

**User Journey Maps**
- End-to-end journey steps
- System touchpoints
- Pain points and opportunities

**Acceptance Criteria**
- Functional acceptance criteria per story
- Edge cases and negative scenarios
- Traceability to business objectives

Structure the output as a formal User Stories & Use Case Specification document.
