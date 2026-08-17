# Target Architecture

`prompt_type: target_architecture`

| Field | Value |
|---|---|
| Level | 8 — Modernization |
| Evidence plan | `z-structure` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L8-modernization/target-architecture.md` |
| Ledger column | `target_architecture` |
| Template placeholders | `{application_name}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`z-structure`** plan. Gather all
   evidence **before** writing any section.
3. Apply `references/z-substitutions.md` wherever the template names a distributed-stack
   artifact (pom.xml, REST endpoint, Docker, npm, ORM, git log …). Use the Z equivalent.
   If no Z equivalent exists, render the heading with `Not available from Z Premium analysis`.
4. Fill the placeholders: `{application_name}` = resolved application name,
   `{current_date}` = today's date from context, `{generated_by}` =
   `IBM Bob — Z Premium Package workflows`.
5. Emit the document to the Output file above, then update the ledger.

## Prompt template — verbatim from `prompts/all_prompts.py::TARGET_ARCHITECTURE_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Generate target architecture documentation for the **{application_name}** application.

Before generating the documentation, please:
1. Review modernization goals and constraints
2. Analyze current system limitations
3. Review reference architectures and cloud-native patterns
4. Identify future scalability, security, and operability needs

Based on your findings, produce a comprehensive specification including:

**Future-State Architecture**
- Architectural style and principles

**Technology Stack**
- Target platforms and frameworks

**Microservices Design**
- Service boundaries and responsibilities

**Cloud Architecture**
- Infrastructure, networking, and resiliency

**Security Architecture**
- Identity, access, and data protection (target)

**Data Architecture**
- Data platforms and integration (target)

**DevOps & Platform Engineering**
- CI/CD, automation, and SRE practices

Structure the output as a formal Target Architecture Document.
