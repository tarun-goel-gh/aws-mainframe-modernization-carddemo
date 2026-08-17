# Business Feature Identification

`prompt_type: business_features`

| Field | Value |
|---|---|
| Level | 1 — Business Context |
| Evidence plan | `atx-business` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L1-business-context/business-features.md` |
| Ledger column | `business_features` |
| Template placeholders | `{application_name}` |
| Scope | Feature-scoped — requires `feature_name`; emit one file per feature under `L1-business-context/business-features/` |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`atx-business`** plan. Gather all
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

## Prompt template — verbatim from `prompts/all_prompts.py::BUSINESS_FEATURES_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

Identify and list the business features of the {application_name} application.

A business feature represents a cohesive, user- or business-facing capability that delivers measurable business value.
Features must be suitable for driving independent Functional Specifications.

Before identifying features, please:
- Review existing application documentation and requirement artifacts
- Analyze source code to understand exposed business capabilities (not technical components)
- Review APIs, UI flows, and business processes
- Identify business rules, validations, and workflows
- Consider stakeholder goals and user journeys

Apply the following rules while identifying features:
- Focus on WHAT the business does, not HOW it is implemented
- Avoid technical or infrastructure concerns
- Features must be cohesive, independently specifiable, and testable
- Exclude cross-cutting technical capabilities (logging, security frameworks, CI/CD, etc.)
- Use business language, not code or class names

Output Requirements (STRICT):
- Return ONLY valid JSON
- Do NOT include explanations, notes, markdown, or additional text
- The output must be a single JSON object
- The root property name must be: features
- features must be an array
- Each array item must contain:
    - feature_id (string, formatted as F-001, F-002, increment sequentially)
    - feature_type (string, always "business_feature")
    - feature_title (string, short 3-6 word label suitable for display, e.g. "OAuth2.0 Authentication Support")
    - feature_description (string, one concise sentence explaining the business value, max 20 words)

feature_title MUST follow these strict rules:
- Use ONLY alphabets (A–Z, a–z), numbers (0–9), and spaces
- DO NOT use any special characters such as: / \ - _ . : ; ( ) [ ] {{ }} & % $ # @ ! * + = < > ? |
- DO NOT use symbols like arrows (→)
- DO NOT use hyphens or slashes
- Words must be separated ONLY by a single space
- Use clean business-friendly wording

Examples:
- Valid: "User Account Management"
- Valid: "Transaction History Review"
- Invalid: "User-Account/Management"
- Invalid: "Fraud_Detection-System"
- Invalid: "Payment & Billing"

- If any feature_title contains invalid characters, automatically replace them with spaces before returning the output

- Maintain ordered feature IDs starting from F-001

Now generate the business feature list for {application_name}.
