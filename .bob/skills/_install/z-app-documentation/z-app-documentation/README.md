# z-app-documentation

A Bob skill that generates the **full application documentation suite — 31 documents across
9 levels** — for a mainframe application, using only IBM-shipped Bob IDE + Z Premium Package
capabilities.

It is a port of the documentation generator in `ACE-Agents/services/cast-integration`.
The prompt catalog, grounding contract, determinism rules and evidence-plan mechanism are
carried over 1:1. **The evidence source is different**: the service queried a CAST Imaging
MCP server; this skill uses Z Premium Package workflows and the source members in the
workspace. There is no CAST dependency.

---

## The 9 levels

| Level | Name | Documents |
|---|---|---|
| L0 | Discovery & Assessment | `application_inventory`, `as_is_assessment` |
| L1 | Business Context | `executive_summary`, `stakeholder_analysis`, `business_capabilities`, `business_features` |
| L2 | Business Documentation | `business_requirements`, `user_stories`, `business_process`, `feature_catalog`, `business_rules` |
| L3 | Technical Documentation | `system_architecture`, `technical_specs`, `code_structure`, `build_deployment` |
| L4 | Design & Decisions | `architecture_decisions`, `component_design`, `security_architecture` |
| L5 | Data | `data_dictionary`, `database_schema_full`, `data_lineage` |
| L6 | Integration & Interfaces | `integration_architecture`, `api_documentation`, `message_specs` |
| L7 | Operations | `operations_manual`, `monitoring_alerting`, `disaster_recovery` |
| L8 | Modernization | `modernization_strategy`, `target_architecture`, `gap_analysis`, `migration_roadmap` |

**31 documents total.** Full table with output paths in `references/document-catalog.md`.

---

## How to invoke

### Auto-activation

Bob activates this skill when you ask to generate application documentation, produce a
modernization document set, build an as-is assessment, document business rules or data
lineage, or produce an executive summary or migration roadmap.

### Slash commands

```
/generate-docs [all|L0..L8|<prompt_type>] [path|inventory.csv|glob] [--dry-run]
/docs-status   [path-to-bob-z-app-docs]
```

| Example | Effect |
|---|---|
| `/generate-docs` | All 31 documents over the open workspace |
| `/generate-docs L0` | Just discovery and as-is assessment |
| `/generate-docs L0-L2` | Levels 0 through 2 |
| `/generate-docs data_lineage` | One document |
| `/generate-docs L5 Cobol/` | Level 5 scoped to the `Cobol/` folder |
| `/generate-docs all inventory.csv` | All documents over the programs in an inventory CSV |
| `/generate-docs --dry-run` | PLAN mode: scope, capability map and batch, writes nothing |
| `/docs-status` | Coverage report from the ledger, no generation |

---

## Requirements

| Requirement | Notes |
|---|---|
| IBM Bob IDE | Advanced mode must be enabled |
| Z Premium Package | Required for Generate documentation, Generate data dictionary, Explain code, Z Code Scan |
| Z Understand server | Optional. Without it, `/impact-analysis` and `/implementation-planning` are unavailable and the L8 gap-analysis sections that would use them are downgrade-labeled. |
| Mode | Z Code or Z Architect |
| CAST Imaging | **Not required and not used.** |

---

## Output tree

```
bob-z-app-docs/
  00-manifest/                    documentation-manifest.json, document-ledger.csv,
                                  program-inventory.csv, generation-log.md,
                                  evidence-cache/, run-history/, AGENTS.md
  L0-discovery/
  L1-business-context/
  L2-business-documentation/      business-features/, feature-catalog/, business-rules/
  L3-technical-documentation/
  L4-design/
  L5-data/
  L6-integration/
  L7-operations/
  L8-modernization/
  17-qa-validation/               dd-review-queue.md, business-review-queue.md,
                                  validation-report.md, sme-signoff-log.md
```

---

## Execution flow

```
Step  1  Resolve source scope + document scope
Step  2  Declare approvals + preflight environment check
Step  3  Create output tree (idempotent)
Step  4  Write documentation-manifest.json, seed outOfScope entries
Step  5  Build program inventory + document ledger; reuse any bob-z-knowledge-extract tree
Step  6  Governance baseline (AGENTS.md) — first run only
Step  7  Select document batch (level order, ≤8 documents)
Step  8  Per document: evidence pass → compose → self-check → file → queue review
Step  9  Cross-document consistency (names, counts, orphans, provenance)
Step 10  Close batch: update ledger, recompute coverage, report
```

---

## The evidence cache — why 31 documents is affordable

The service paid a fresh CAST MCP query for every prompt. Here, Z Premium workflows are the
expensive part, so workflow output is cached **per program per workflow** under
`00-manifest/evidence-cache/` and reused across every document that needs it.

A run over 50 programs pays roughly 50 docgen runs and 50 Z Code Scan runs **once**, not once
per document. Cache entries are invalidated when the source member's `mtime` or `size_bytes`
changes. `/docs-status` reports the hit rate and names any program whose cached evidence has
gone stale.

If a `bob-z-knowledge-extract/` tree already exists (from the `cobol-knowledge-extraction`
skill), Step 5c harvests it as pre-existing evidence, carrying its provenance labels forward.

---

## Grounding

`references/grounding-contract.md` overrides every template and the skill file itself:

- **Evidence-only** — every fact traces to a workflow result or a source read from this run.
- **No parametric recall** — no training knowledge about "typical" COBOL or this application.
- **No fabrication** — ungrounded fields read `Not available from Z Premium analysis`.
- **Traceability** — `[source: <workflow> -> <MEMBER:lines>]` per claim, Evidence Index per document.
- **Determinism** — fixed ordering, verbatim identifiers, fixed section sets.
- **Provenance labels** — `z-workflow-verified`, `source-read-verified`,
  `narrative-per-program-not-tool-verified`, `z-understand-verified`.

---

## Deferred review gates

The skill is autonomous, but two kinds of **content** are never auto-approved:

| Gate | Queue | Effect |
|---|---|---|
| Data dictionary business meanings | `17-qa-validation/dd-review-queue.md` | Filed `status: draft` |
| Business assertions (capabilities, stakeholders, personas, requirements) | `17-qa-validation/business-review-queue.md` | Labelled `Assumption — not tool-verified` |

Neither blocks document completeness; both are reported every run. Sign off by telling Bob
*"Approve CUSTADD dictionary"* or *"Approve business capabilities"*.

To suspend autonomy mid-session, send: **"pause for approval"**

---

## Coverage definition

A document is **complete** when all three ledger flags are `Y`:

```
evidence_gathered=Y  AND  generated=Y  AND  self_check_passed=Y
```

`reviewed=Y` is tracked separately and never blocks completeness. The Step 10 report always
shows `complete/planned (%)` plus a named list of every incomplete document and every section
that could not be grounded.

---

## Known gaps vs. the CAST-backed service

These sections existed in the service because CAST supplied them. There is no Z Premium
equivalent, so the skill renders the heading and marks it unavailable rather than inventing it.

| Lost capability | CAST source | Effect |
|---|---|---|
| ISO 5055 characteristic scoring | `application_iso_5055_explorer` | `security_architecture`, `as_is_assessment` sections unavailable |
| CVE / vulnerability mapping | `quality_insights` (nature=cve) | `security_architecture` section unavailable |
| Portfolio-level quality roll-up | `applications_quality_insights` | Single-application scope only |
| Inter-application dependency graph | `inter_applications_dependencies` | Replaced by narrative call graph, provenance-labeled |
| Structurally-verified call graphs | `pathfinder_hierarchy_details` | Replaced by `grep` + narrative, completeness not guaranteed |
| Multi-application comparison | `applications`, `applications_transactions` | Out of scope |

Gained in exchange: `z-operations` (JCL, scheduling, restart/recovery) has no CAST origin —
CAST's model is distributed-stack and had no equivalent.

---

## Limitations

| Limitation | Reason |
|---|---|
| Dependency completeness cannot be guaranteed | Without Z Understand's `get_project_*` tools, dependency and call-graph data is narrative-extracted. Every such artifact carries `narrative-per-program-not-tool-verified`. |
| Dynamic `CALL identifier` edges are unresolved | The target is only known at runtime. Reported as unresolved, never guessed. |
| DB2/IMS DDL, constraints, triggers out of scope | Requires DBA tooling external to Bob. |
| No runtime telemetry | SLA, uptime, SMF and live scheduler state have no source in the repository. |
| Two source templates are thin | `business_capabilities` and `architecture_decisions` are stubs in the origin service (223 and 104 characters). They are ported verbatim; expand them in `references/prompts/` if you want richer output. |

---

## Skill files

| File | Purpose |
|---|---|
| `SKILL.md` | The 10-step pipeline Bob follows at activation |
| `README.md` | This file |
| `references/document-catalog.md` | The 31 documents: level, plan, output path, template file |
| `references/grounding-contract.md` | Evidence, determinism, provenance and self-check rules |
| `references/evidence-plans.md` | The 9 Z Premium evidence plans + CAST→Z plan mapping |
| `references/z-substitutions.md` | Distributed-stack concept → Z equivalent table |
| `references/prompts/*.md` | 31 document templates, one per `prompt_type` |

Companion command skills (separate folders under `.bob/skills/`): `generate-docs`, `docs-status`.

---

## Version history

| Version | Change |
|---|---|
| 1.0.0 | Initial port of `services/cast-integration` documentation generation to Bob + Z Premium Package. 31 prompts, 9 evidence plans, grounding contract, evidence cache, document ledger. |
