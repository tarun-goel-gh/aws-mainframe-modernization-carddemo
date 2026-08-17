# Security Architecture

`prompt_type: security_architecture`

| Field | Value |
|---|---|
| Level | 4 — Design & Decisions |
| Evidence plan | `z-quality` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L4-design/security-architecture.md` |
| Ledger column | `security_architecture` |
| Template placeholders | `{application_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`z-quality`** plan. Gather all
   evidence **before** writing any section.
3. Apply `references/z-substitutions.md` wherever the template names a distributed-stack
   artifact (pom.xml, REST endpoint, Docker, npm, ORM, git log …). Use the Z equivalent.
   If no Z equivalent exists, render the heading with `Not available from Z Premium analysis`.
4. Fill the placeholders: `{application_name}` = resolved application name,
   `{current_date}` = today's date from context, `{generated_by}` =
   `IBM Bob — Z Premium Package workflows`.
5. Emit the document to the Output file above, then update the ledger.

## Prompt template — verbatim from `prompts/all_prompts.py::SECURITY_ARCHITECTURE_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate security architecture documentation for the **{application_name}** application.

Before generating the documentation, please:
1. Review authentication and authorization mechanisms
2. Analyze security configurations and secrets management
3. Review API security and data protection mechanisms
4. Identify compliance and regulatory requirements

Based on your findings, produce a comprehensive specification including:

**Security Architecture Overview**
- Security principles and goals
- Threat model summary

**Identity & Access Management**
- Authentication mechanisms
- Authorization and role models

**Data Security**
- Encryption at rest and in transit
- Data masking and tokenization

**Application Security**
- Input validation and protection
- Secure coding practices

**Operational Security**
- Monitoring and incident response
- Audit and compliance controls

Structure the output as a formal Security Architecture Document.
