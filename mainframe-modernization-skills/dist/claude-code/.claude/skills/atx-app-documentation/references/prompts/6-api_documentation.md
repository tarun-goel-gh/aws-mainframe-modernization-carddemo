# Interface & API Documentation

`prompt_type: api_documentation`

| Field | Value |
|---|---|
| Level | 6 — Integration & Interfaces |
| Evidence plan | `atx-api` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L6-integration/api-documentation.md` |
| Ledger column | `api_documentation` |
| Template placeholders | `{application_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`atx-api`** plan. Gather all
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

## Prompt template — verbatim from `prompts/all_prompts.py::API_DOCUMENTATION_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate comprehensive API documentation for the **{application_name}** application.

Before generating the documentation, please:
1. Review API definitions, controllers, and routing logic
2. Analyze OpenAPI/Swagger specifications if available
3. Identify authentication and authorization mechanisms
4. Review request/response payloads and validation logic
5. Analyze rate limiting and versioning strategies

Based on your findings, produce a detailed specification including:

**API Inventory**
- API name, purpose, and ownership
- Public vs internal APIs

**Endpoint Specifications**
- HTTP methods and paths
- Request and response schemas (OpenAPI-style)

**Security**
- Authentication and authorization
- Token scopes and roles

**Error Handling**
- Error codes and messages
- Failure scenarios

**Rate Limiting & Throttling**
- Limits and quotas
- Abuse prevention strategies

**Versioning Strategy**
- Backward compatibility
- Deprecation policy

Structure the output as a formal API Documentation.
