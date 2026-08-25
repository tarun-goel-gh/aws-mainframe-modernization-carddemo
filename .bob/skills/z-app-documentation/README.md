# z-app-documentation

A Bob skill that generates the **full application documentation suite — 31 documents across
9 levels** — for a mainframe application, using BobZ v3's MCP server and the source members in
the workspace.

It is a port of the documentation generator in `ACE-Agents/services/cast-integration`.
The prompt catalog, grounding contract, determinism rules and evidence-plan mechanism are
carried over 1:1. **The evidence source is different**: the service queried a CAST Imaging
MCP server; this skill queries the **BobZ MCP server** (Z Premium Package capabilities,
promoted to directly-callable tools in v2.0.0) plus the source members in the workspace. There
is no CAST dependency.

`SKILL.md` is the governing document. This README is for humans.

---

## Version 2.0.0: script-driven, not prose-driven

Version 1.0.0 asked the agent to read a template, gather evidence, compose the document, run a
self-check, and file it — ten prose steps, freehand, once per document, 31 times. That worked,
but nothing forced two runs over the same evidence to produce the same output, and nothing
forced the self-check to actually block a bad document rather than just get read and nodded past.

Version 2.0.0 moves the composition, self-check and filing into three scripts:

```
scripts/build_coverage.py     the prerequisite gate + coverage matrix
scripts/extract_evidence.py   aggregates cached MCP tool output into evidence-pack.json
scripts/generate_docs.py      composes, self-checks, and files — or refuses to file
```

The agent still does exactly one thing scripts cannot: it **calls the BobZ MCP tools**, per
program, per evidence plan, and writes the raw results to `00-manifest/mcp-cache/`. Everything
downstream of that — aggregation, section-set selection, provenance labeling, the self-check, the
ledger update — is mechanised. See `SKILL.md`'s "Hand-composition is not permitted" section for
the two guarantees that only survive if the script runs: the self-check that actually blocks
filing, and the per-document staleness fingerprints in `document-evidence.json`.

### Why this is the determinism win, concretely

- **Byte-identical reruns.** Two runs of `generate_docs.py` against an unchanged
  `evidence-pack.json` produce identical documents — same ordering, same headings, same
  citations — because a script has no freedom to phrase a heading two different ways on two
  different days. A model composing freehand does.
- **sha256 staleness detection, not "does this look current."** `build_coverage.py` fingerprints
  every artifact feeding the evidence pack; `generate_docs.py` fingerprints every artifact an
  individual document actually read. A source member changing under a filed document is
  detectable by hash comparison, not by someone remembering to re-check it.
- **The self-check can actually refuse.** A script either finds a Coverage note, an Evidence
  Index and every template heading, or it doesn't file the document — there is no "I checked and
  it's fine" step for a model to talk itself through. `generate_docs.py` exits `1` and the batch
  continues with everything else.
- **The evidence/composition boundary is explicit.** MCP tool output is structured JSON now
  (§3 of `.bob/skills/_design/bobz-v3-foundations.md`), not narrative prose to be re-read and
  reinterpreted at document-writing time — so `extract_evidence.py` is a clean aggregation step,
  and the only text-mining left in the whole pipeline is over JCL, BMS maps and LINKAGE SECTION
  source, which never went through an MCP tool in the first place.

None of this changes what the documents say. It changes whether the same inputs reliably produce
the same output, and whether a bad document can reach `docsRoot` at all.

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
modernization document set, build an as-is assessment, document business rules or data lineage,
or produce an executive summary or migration roadmap.

### Slash commands

```
/generate-docs [all|L0..L8|<prompt_type>] [path|inventory.csv|glob] [--dry-run] [--force]
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
| `/generate-docs --dry-run` | PLAN mode: scope, capability map and coverage matrix, writes nothing |
| `/docs-status` | Coverage report from the ledger, no generation |

---

## Requirements

| Requirement | Notes |
|---|---|
| IBM Bob IDE | Advanced mode must be enabled |
| BobZ v3 MCP server | Required and reachable — preflight's first check. No fallback exists if it is not. |
| Z Understand server | Optional. Without it, the six §1b tools (`get_project_inventory`, `get_project_tables`, `get_project_resource_usage`, `impact_analysis`, `implementation_planning`, `sync_data_dictionary`) are unavailable and the sections that would use them are marked unavailable, not approximated. |
| Mode | Z Code or Z Architect |
| CAST Imaging | **Not required and not used.** |

---

## Execution flow

```
Step 0   Preflight — resolve/refresh program inventory, MCP reachability probe,
         mode checks, capability map                          [no fallback if MCP unreachable]
Step 1   Resolve source scope + document scope
Step 2   scripts/build_coverage.py         — prerequisite gate, coverage.md, evidence-index.json
Step 3   Agent gathers evidence            — direct MCP tool calls per program per plan,
                                              written to 00-manifest/mcp-cache/
Step 4   scripts/extract_evidence.py       — aggregate mcp-cache/ into evidence-pack.json
Step 5   scripts/generate_docs.py          — compose, self-check, file (or refuse to file)
Step 6   Cross-document consistency        (names, counts, orphans, provenance)
Step 7   Close batch: report from coverage.md / document-ledger.csv, not from memory
```

Steps 2, 4 and 5 are scripts. Steps 0, 1, 3 and 6–7 are the agent's — the agent calls MCP tools
and resolves scope; it never calls MCP from inside a script and never composes a document by
hand.

---

## The MCP cache — why 31 documents is affordable

BobZ MCP tool calls are still the expensive part of this pipeline, so tool output is cached
**per program per tool** under `00-manifest/mcp-cache/` and reused across every document that
needs it. A run over 50 programs pays roughly 50 `generate_documentation` calls and 50
`z_code_scan` calls **once**, not once per document — `extract_evidence.py` aggregates the same
cache file into every document that cites that program.

Cache entries are invalidated when the source member's `mtime` or `size_bytes` changes, checked
against `program-inventory.csv`. `/docs-status` reports the hit rate and names any program whose
cached evidence has gone stale.

If a `bob-z-knowledge-extract/` tree already exists (from `cobol-knowledge-extraction`),
`extract_evidence.py` harvests it as pre-existing evidence, carrying its provenance labels
forward unchanged.

---

## Grounding

`references/grounding-contract.md` overrides every template and this skill file, and is
**unchanged from v1.0.0**:

- **Evidence-only** — every fact traces to an MCP tool result or a source read from this run.
- **No parametric recall** — no training knowledge about "typical" COBOL or this application.
- **No fabrication** — ungrounded fields read `Not available from Z Premium analysis`.
- **Traceability** — `[source: <tool> -> <MEMBER:lines>]` per claim, Evidence Index per document.
- **Determinism** — fixed ordering, verbatim identifiers, fixed section sets.
- **Provenance labels (rendered documents)** — `z-workflow-verified`, `source-read-verified`,
  `narrative-per-program-not-tool-verified`, `z-understand-verified`.

`evidence-pack.json` itself (the scripts' internal aggregate, not the rendered documents) uses a
**narrower, three-value** provenance vocabulary — `tool-verified`,
`narrative-per-program-not-tool-verified`, `z-understand-verified` — because an MCP tool result
and a deterministic local read are no longer meaningfully different trust levels. See
`.bob/skills/_design/bobz-v3-foundations.md` §3 for exactly where each value applies.

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

`reviewed=Y` is tracked separately and never blocks completeness. `generate_docs.py` computes
`n/31` from `document-ledger.csv` on every run — never from memory, and never from the previous
report.

---

## Output tree

```
bob-z-app-docs/
  00-manifest/
    documentation-manifest.json     run metadata, gaps, counts
    mcp-capability-probe.json       reachability probe result (Step 0)
    program-inventory.csv           7-column header, shared with cobol-knowledge-extraction
    coverage.md                     per-program coverage matrix (build_coverage.py)
    evidence-index.json             sha256 fingerprints of every artifact feeding the pack
    mcp-cache/{PROGRAM}/{tool}.json raw MCP tool results, one file per program per tool
    evidence-pack.json              aggregated evidence (extract_evidence.py)
    document-ledger.csv             31 rows, the completeness record
    document-evidence.json          per-document artifact fingerprints — staleness detection
    generation-log.md               append-only, one line per document / tool error
    run-history/                    one summary per batch
    AGENTS.md                       copied from the workspace-root file, first run only
  L0-discovery/ … L8-modernization/
  17-qa-validation/
    dd-review-queue.md
    business-review-queue.md
    validation-report.md
    sme-signoff-log.md
```

---

## Known gaps vs. the CAST-backed service

These sections existed in the service because CAST supplied them. There is no BobZ equivalent,
so the skill renders the heading and marks it unavailable rather than inventing it.

| Lost capability | CAST source | Effect |
|---|---|---|
| ISO 5055 characteristic scoring | `application_iso_5055_explorer` | `security_architecture`, `as_is_assessment` sections unavailable |
| CVE / vulnerability mapping | `quality_insights` (nature=cve) | `security_architecture` section unavailable |
| Portfolio-level quality roll-up | `applications_quality_insights` | Single-application scope only |
| Inter-application dependency graph | `inter_applications_dependencies` | Replaced by narrative call graph, provenance-labeled |
| Structurally-verified call graphs (without Z Understand) | `pathfinder_hierarchy_details` | Replaced by `grep` + narrative, completeness not guaranteed |
| Multi-application comparison | `applications`, `applications_transactions` | Out of scope |

Gained in exchange: `z-operations` (JCL, scheduling, restart/recovery) has no CAST origin —
CAST's model is distributed-stack and had no equivalent. And, new in v2.0.0: dependency and
resource-usage data is **structurally verified**, not narrative, whenever
`zUnderstandConfigured: true` — `get_project_resource_usage` is a real upgrade over the v1.0.0
`grep`-and-narrative approach, not just a faster way to reach the same guess.

---

## Limitations

| Limitation | Reason |
|---|---|
| Dependency completeness cannot be guaranteed without Z Understand | Without `get_project_*` tools, dependency and call-graph data stays narrative-extracted, labelled `narrative-per-program-not-tool-verified`. |
| Dynamic `CALL identifier` edges are unresolved | The target is only known at runtime. Reported as unresolved, never guessed. |
| DB2/IMS DDL, constraints, triggers out of scope | Requires DBA tooling external to Bob. |
| No runtime telemetry | SLA, uptime, SMF and live scheduler state have no source in the repository. |
| Three source templates are thin | `business_capabilities`, `business_features` and `architecture_decisions` are stubs in the origin service and carry no `OUTPUT STRUCTURE` block. `references/template-families.md` gives each a fixed, declared section set instead of leaving it to vary run to run. |
| No fallback if the MCP server is unreachable | v1.0.0's two-tier fallback path is retired. An unreachable server drops the whole run to PLAN mode. |

---

## Skill files

| File | Purpose |
|---|---|
| `SKILL.md` | The script-driven pipeline Bob follows at activation |
| `README.md` | This file |
| `PORTING-ANALYSIS.md` | The original CAST → Bob port analysis (v1.0.0; still historically accurate) |
| `references/document-catalog.md` | The 31 documents: level, plan, output path, template file |
| `references/grounding-contract.md` | Evidence, determinism, provenance and self-check rules (unchanged) |
| `references/evidence-plans.md` | The 9 Z evidence plans — now direct BobZ MCP tool call sequences |
| `references/template-families.md` | How each template's section set is expressed and extracted — new in v2.0.0 |
| `references/z-substitutions.md` | Distributed-stack concept → Z equivalent table |
| `references/prompts/*.md` | 31 document templates, one per `prompt_type` |
| `scripts/build_coverage.py` | Prerequisite gate + coverage matrix |
| `scripts/extract_evidence.py` | Aggregates `mcp-cache/` into `evidence-pack.json` |
| `scripts/generate_docs.py` | Composes, self-checks, files |

Companion command skills (separate folders under `.bob/skills/`): `generate-docs`, `docs-status`.
Companion orchestrator: `modernization-pipeline`, the no-AWS BobZ analog of `atx-pipeline`, which
drives `cobol-knowledge-extraction` and this skill end to end through nine phases and gates A–D.

---

## Version history

| Version | Change |
|---|---|
| 2.0.0 | Script-driven rewrite. Composition, self-check and filing move into `scripts/build_coverage.py` / `extract_evidence.py` / `generate_docs.py`; evidence source promoted from mixed UI-workflow/narrative-fallback to BobZ v3's MCP server (direct tool calls, structured JSON); new `references/template-families.md`; new preflight MCP-reachability probe with no fallback path; provenance vocabulary in `evidence-pack.json` narrows to three values. See `.bob/skills/_design/bobz-v3-foundations.md`. |
| 1.0.0 | Initial port of `services/cast-integration` documentation generation to Bob + Z Premium Package UI workflows. 31 prompts, 9 evidence plans, grounding contract, evidence cache, document ledger. |
