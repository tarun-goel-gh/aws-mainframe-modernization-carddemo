# Stakeholder Analysis

`prompt_type: stakeholder_analysis`

| Field | Value |
|---|---|
| Level | 1 — Business Context |
| Evidence plan | `atx-business` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L1-business-context/stakeholder-analysis.md` |
| Ledger column | `stakeholder_analysis` |
| Template placeholders | `{application_name}`, `{current_date}` |
| Scope | Application-scoped — one file per application |

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
   `AWS Transform — mainframe reverse engineering (assess + reimagine)`.
6. Emit the document to the Output file above, then update the ledger.

## Prompt template — verbatim from `prompts/all_prompts.py::STAKEHOLDER_ANALYSIS_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

# Stakeholder Analysis & Engagement Plan

Generate a comprehensive stakeholder analysis for {application_name} modernization.

## ANALYSIS TASKS

1. **Identify Stakeholders**
   - Review codebase for user roles, permissions
   - Review database for user/role tables
   - Search for documentation mentioning users, teams
   - Identify external integrations (external stakeholders)
   - Look for support/incident tickets (user feedback)

2. **Understand Current Usage**
   - Find usage analytics if available
   - Review login/access patterns from logs
   - Identify key user workflows
   - Find feature usage data

3. **Assess Impact**
   - Identify which users are affected by which changes
   - Understand critical workflows that might be disrupted
   - Identify training needs
   - Assess change readiness

## OUTPUT STRUCTURE

# Stakeholder Analysis: {application_name} Modernization

**Project:** {application_name} Modernization
**Date:** {current_date}
**Purpose:** Identify, analyze, and plan engagement with all stakeholders

---

## 1. Executive Summary

### Stakeholder Overview
| Stakeholder Category | Count | Engagement Level Required | Change Impact |
|---------------------|-------|--------------------------|---------------|
| Executive Sponsors | [count] | High | Low - Strategic oversight |
| Business Owners | [count] | High | Medium - Process changes |
| End Users (Internal) | [count] | Medium | High - Daily tool changes |
| End Users (External/Customers) | [count] | Low | Medium - UX changes |
| IT/Development Team | [count] | High | High - New tech stack |
| Operations Team | [count] | High | High - New deployment |
| External Partners | [count] | Medium | Medium - API changes |
| Regulatory/Compliance | [count] | Medium | Low - Compliance review |

**Total Stakeholders Identified:** [count]

### Key Stakeholder Challenges
1. **[Challenge #1, e.g., User resistance to UI changes]**
   - Affected: [stakeholder groups]
   - Mitigation: [strategy]

2. **[Challenge #2, e.g., Business process disruption]**
   - Affected: [stakeholder groups]
   - Mitigation: [strategy]

---

## 2. Detailed Stakeholder Inventory

... (content truncated for brevity; follows the full structure you provided) ...
