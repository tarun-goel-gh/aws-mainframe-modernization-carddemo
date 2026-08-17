# CAST Integration Service → Bob Skill: Analysis and Porting Map

**Source analysed:** `ACE-Agents/services/cast-integration`
**Target:** `aws-mainframe-modernization-carddemo-main/.bob/skills/`
**Constraint set by requirement:** no CAST MCP server — evidence comes from the
IBM Bob Z Premium Package.
**Date:** 2026-08-05

---

## 1. What the service actually does

The service is a **prompt-orchestration layer**, not a documentation engine. Its value is in
four things, in descending order of importance:

1. **A catalog of 31 document templates** organised into 9 modernization levels
   (`prompts/all_prompts.py::PROMPT_REGISTRY`, ~2 600 lines). Each template fixes the
   section set of one deliverable.
2. **A grounding contract** (`prompts/grounding.py`) that forces every statement to trace to
   a tool result — evidence-only, no parametric recall, no fabrication, determinism rules,
   traceability tags, an Evidence Index, and a final self-check.
3. **Named tool plans** (`CAST_TOOL_PLANS`, 9 of them) that tell the agent which CAST tools to
   call, in what order, with token-efficiency rules — breadth before depth, profiles before
   details, resolve identifiers once, stop when satisfied.
4. **A composer** (`compose_prompt` / `get_prompt`) that assembles: grounding contract →
   determinism rules → token-efficiency + tool plan → runtime-specific rules → task banner →
   the document template → self-check footer.

### Runtime pipeline

```
FastAPI / CLI  →  Celery task  →  get_prompt(prompt_type, application_name, …)
                  (mcp_doc_tasks.py)         │
                                             ├── evidence_source = cast_mcp   → MultiProviderDocGenerator
                                             │      (LangChain agent + CAST MCP streamable_http)
                                             └── evidence_source = filesystem → FilesystemAnalyzer
                                                    (Claude Agent SDK / OpenAI Agents / Gemini)
                                             ↓
                                     db_storage + output_storage (S3/GCS/Azure)
                                     Redis progress → WebSocket
```

Key observation: the service **already** has two evidence sources and a
`normalize_evidence_source()` switch (`cast_mcp` vs `filesystem`), with different
"system-of-record" wording and different `generated_by` attribution injected into the same
templates. Porting to Bob is therefore adding a **third evidence source** — not rebuilding the
pipeline. That is exactly what this skill does.

### Component inventory

| Component | File | Lines | Role |
|---|---|---|---|
| Prompt registry | `prompts/all_prompts.py` | 2 600 | 31 templates + `get_prompt()` + `PROMPT_TOOL_PLANS` |
| Grounding | `prompts/grounding.py` | 570 | Contract, determinism, tool plans, composer |
| Standalone prompts | `prompts/comprehensive_doc.py`, `api_doc.py`, `hierarchy_doc.py`, `module_specific_doc.py` | 26 KB | Older single-document variants, superseded by `all_prompts` |
| Generator | `doc_generator.py` | 26 KB | `MultiProviderDocGenerator` — LangChain agent, MCP wiring, output normalisation |
| CAST tool specs | `utils/cast_mcp_tools.py` | 17 KB | 25 CAST tool schemas + allowed-tool list |
| CAST client | `utils/cast_mcp_client.py` | 12 KB | JSON-RPC / SSE MCP client |
| Task layer | `cast/tasks/mcp_doc_tasks.py` | 25 KB | Celery entry, source resolution, storage |
| Filesystem analyzer | `cast/services/filesystem_analyzer.py` | 38 KB | Provider-native SDK analysis, no CAST |
| Storage | `cast/utils/db_storage.py`, `output_storage.py` | 18 KB | DB + cloud persistence |

---

## 2. What survives the port, what changes, what is lost

### Survives 1:1

| Service asset | Where it lands in the skill |
|---|---|
| 31 templates, section sets verbatim | `references/prompts/*.md` (one file per `prompt_type`) |
| 9-level organisation | Output tree `L0-discovery/` … `L8-modernization/` |
| `CAST_MCP_GROUNDING_RULE` (7 rules) | `references/grounding-contract.md` §1 |
| `DETERMINISM_RULES` | `references/grounding-contract.md` §2 |
| `TOKEN_EFFICIENT_EXECUTION` | `references/grounding-contract.md` §4 |
| `SELF_CHECK_FOOTER` | `references/grounding-contract.md` §5 |
| `PROMPT_TOOL_PLANS` mapping | `references/document-catalog.md` (`Z plan` column) |
| `compose_prompt()` assembly order | SKILL.md Step 8a–8c |
| `evidence_source` / `generated_by` switch | Fixed to `IBM Bob — Z Premium Package workflows` |

### Changes

| Service mechanism | Bob replacement | Rationale |
|---|---|---|
| `CAST_TOOL_PLANS` (9 CAST tool sequences) | `references/evidence-plans.md` (9 Z plans) | No CAST server; Z Premium workflows + editor tools + read-only file tools |
| `MultiProviderDocGenerator` agent loop | Bob's own agent loop | Bob *is* the runtime; no LangChain layer needed |
| `RUNTIME_GROUNDING` (OpenAI Agents / Claude Agent SDK) | Single Bob runtime block | One host, so one runtime rule |
| Celery task + Redis progress + WebSocket | Skill steps + `generation-log.md` + Step 10 report | Interactive IDE, not a service |
| `db_storage` + S3/GCS/Azure output | `bob-z-app-docs/` in the workspace | Files in the repo, reviewable in PRs |
| Per-prompt CAST query | **Evidence cache** (`00-manifest/evidence-cache/`) | Z workflows are far more expensive than CAST REST queries; cache per program per workflow, amortise across all 31 documents |
| No completeness tracking | **Document ledger** + manifest coverage | Borrowed from the existing `cobol-knowledge-extraction` skill so both trees behave identically |
| Distributed-stack template vocabulary | `references/z-substitutions.md` | Templates say "pom.xml", "REST endpoint", "Docker" — the table maps each to its Z evidence, or marks it unavailable |

### Lost — and honestly declared

These were CAST capabilities with no Z Premium equivalent. The skill renders the heading and
writes `Not available from Z Premium analysis` rather than inventing content.

| Lost | CAST tool | Documents affected |
|---|---|---|
| ISO 5055 characteristic scoring | `application_iso_5055_explorer` | `as_is_assessment`, `security_architecture` |
| CVE / vulnerability mapping | `quality_insights` (`nature=cve`) | `security_architecture` |
| Portfolio-level quality roll-up | `applications_quality_insights` | `as_is_assessment` |
| Structurally-verified call graphs | `pathfinder_hierarchy_details` | `system_architecture`, `component_design` — replaced by narrative graph, provenance-labeled |
| Inter-application dependency graph | `inter_applications_dependencies` | `integration_architecture` — single-application scope only |
| Multi-application comparison | `applications`, `applications_transactions` | All — one application per run |

### Gained

`z-operations` — JCL job flow, scheduling, `COND=` logic, return codes, ABEND handling,
restart/recovery, PROC/PROCLIB configuration. CAST's model is distributed-stack and had no
equivalent; on Z this is where `build_deployment`, `operations_manual`, `monitoring_alerting`
and `disaster_recovery` get their evidence.

---

## 3. Evidence plan mapping (the core of the port)

| CAST plan | CAST tools | Z plan | Z capabilities |
|---|---|---|---|
| `discovery` | `applications`, `stats`, `packages`, `api_inventory`, `application_database_explorer`, `applications_dependencies`, `quality_insights` | `z-discovery` | `list_files`/`glob` inventory, `zapp.yaml` read, `wc`/`stat` sizing, entry-point `grep`, architect-perspective docgen |
| `architecture` | `architectural_graph`, `architectural_graph_focus`, `package_interactions` | `z-structure` | Architect docgen, `get_control_flow`, `CALL`/`EXEC CICS` grep, JCL job grouping |
| `module` | `objects`, `object_profiles`, `object_details`, `source_files`, `pathfinder_hierarchy_details` | `z-module` | `scan_program`, `get_expanded_source`, `get_paragraphs`, `get_variables`, developer docgen, Explain code, `get-data-flow` |
| `data` | `application_database_explorer`, `data_graphs`, `data_graph_*` | `z-data` | Generate data dictionary, copybook layouts, `EXEC SQL` grep, `FD`/`SELECT ASSIGN` grep |
| `api` | `api_inventory`, `transactions`, `transaction_*` | `z-api` | `EXEC CICS` verbs, `.csd` resources, `.bms` maps, LINKAGE SECTION, MQ calls |
| `integration` | `inter_applications_dependencies`, `inter_app_detailed_dependencies` | `z-integration` | `CALL` grep (static/dynamic split), CICS LINK/XCTL/START, JCL DD handoffs, MQ, copybook sharing |
| `quality` | `applications_quality_insights`, `quality_insight_violations`, `advisors`, `application_iso_5055_explorer` | `z-quality` | Z Code Scan, complexity ranking, Explain code on top 20%, security/error-handling grep |
| `business` | `transactions`, `data_graphs`, `packages` | `z-business` | Business docgen, transaction IDs + BMS titles as feature names, Explain code, `88`/`EVALUATE` grep |
| `comprehensive` | (all of the above) | *not ported* | Each level runs its own plan; the manifest aggregates |
| — | — | `z-operations` | JCL inventory, job-to-program map, `COND=`/`RESTART=`, ABEND/return codes, PROC reads |

---

## 4. Design decisions worth flagging

**Evidence cache is the load-bearing addition.** Naively re-running every plan for every
document means ~31 × N workflow invocations. Caching per program per workflow makes it
~N invocations total. Cache invalidation is by source-member `mtime` + `size_bytes` against
`program-inventory.csv`; `/docs-status` names stale entries.

**Reuse of `bob-z-knowledge-extract/`.** The existing `cobol-knowledge-extraction` skill
already produces data dictionaries, per-program documentation, dependency maps, code-flow
artifacts and Z Code Scan findings. Step 5c harvests that tree as pre-existing evidence and
carries its provenance labels forward — the two skills compose rather than duplicate.

**Templates ported verbatim, not rewritten for Z.** Rewriting the section sets would break
comparability with documents the service already produced and would be a large, error-prone
edit across 2 600 lines. Instead the section set is fixed and `z-substitutions.md` handles
vocabulary. The tradeoff: some sections will legitimately read
`Not available from Z Premium analysis` on a mainframe codebase. That is the honest outcome —
and the skill counts and reports them rather than hiding them.

**Two source templates are stubs.** `business_capabilities` (223 chars) and
`architecture_decisions` (104 chars) supply no OUTPUT STRUCTURE in the origin service, so
model output would vary run to run. Both reference files add a **fixed section set** to
restore determinism, flagged as a template gap.

**Provenance is stricter than the service's.** The service tagged sources per claim; the skill
adds four explicit provenance values so a reader can tell a workflow-verified fact from a
narrative inference. This matters more on Z, where no structural verifier exists without a
Z Understand server.

---

## 5. Paths — what to create and update

All paths are relative to the connected folder root:
`/Users/manoj.sharma1/Private/IBM/aws-mainframe-modernization-carddemo-main/`

### Create

```
.bob/skills/z-app-documentation/SKILL.md                       ← main skill, 10-step pipeline
.bob/skills/z-app-documentation/README.md                      ← human-facing summary
.bob/skills/z-app-documentation/PORTING-ANALYSIS.md            ← this document
.bob/skills/z-app-documentation/references/document-catalog.md ← the 31 documents
.bob/skills/z-app-documentation/references/grounding-contract.md
.bob/skills/z-app-documentation/references/evidence-plans.md   ← the 9 Z plans
.bob/skills/z-app-documentation/references/z-substitutions.md
.bob/skills/z-app-documentation/references/prompts/0-application_inventory.md
.bob/skills/z-app-documentation/references/prompts/0-as_is_assessment.md
.bob/skills/z-app-documentation/references/prompts/1-executive_summary.md
.bob/skills/z-app-documentation/references/prompts/1-stakeholder_analysis.md
.bob/skills/z-app-documentation/references/prompts/1-business_capabilities.md
.bob/skills/z-app-documentation/references/prompts/1-business_features.md
.bob/skills/z-app-documentation/references/prompts/2-business_requirements.md
.bob/skills/z-app-documentation/references/prompts/2-user_stories.md
.bob/skills/z-app-documentation/references/prompts/2-business_process.md
.bob/skills/z-app-documentation/references/prompts/2-feature_catalog.md
.bob/skills/z-app-documentation/references/prompts/2-business_rules.md
.bob/skills/z-app-documentation/references/prompts/3-system_architecture.md
.bob/skills/z-app-documentation/references/prompts/3-technical_specs.md
.bob/skills/z-app-documentation/references/prompts/3-code_structure.md
.bob/skills/z-app-documentation/references/prompts/3-build_deployment.md
.bob/skills/z-app-documentation/references/prompts/4-architecture_decisions.md
.bob/skills/z-app-documentation/references/prompts/4-component_design.md
.bob/skills/z-app-documentation/references/prompts/4-security_architecture.md
.bob/skills/z-app-documentation/references/prompts/5-data_dictionary.md
.bob/skills/z-app-documentation/references/prompts/5-database_schema_full.md
.bob/skills/z-app-documentation/references/prompts/5-data_lineage.md
.bob/skills/z-app-documentation/references/prompts/6-integration_architecture.md
.bob/skills/z-app-documentation/references/prompts/6-api_documentation.md
.bob/skills/z-app-documentation/references/prompts/6-message_specs.md
.bob/skills/z-app-documentation/references/prompts/7-operations_manual.md
.bob/skills/z-app-documentation/references/prompts/7-monitoring_alerting.md
.bob/skills/z-app-documentation/references/prompts/7-disaster_recovery.md
.bob/skills/z-app-documentation/references/prompts/8-modernization_strategy.md
.bob/skills/z-app-documentation/references/prompts/8-target_architecture.md
.bob/skills/z-app-documentation/references/prompts/8-gap_analysis.md
.bob/skills/z-app-documentation/references/prompts/8-migration_roadmap.md
.bob/skills/generate-docs/SKILL.md                             ← /generate-docs command
.bob/skills/docs-status/SKILL.md                               ← /docs-status command
```

### Update (existing files — optional, recommended)

| Path | Change | Why |
|---|---|---|
| `.bob/skills/cobol-knowledge-extraction/SKILL.md` | In Step 15's report list, add a line pointing at `/generate-docs` as the next step once coverage is adequate | The two skills form a pipeline: extraction builds the evidence base, documentation consumes it |
| `.bob/skills/cobol-knowledge-extraction/README.md` | Add a "Companion skills" section naming `z-app-documentation` | Discoverability |
| `AGENTS.md` (workspace root) | If absent, `/init` creates it in Step 6 | Coding standards and domain terms feed document terminology |

### Runtime output (created by the skill, not by you)

```
bob-z-app-docs/          ← generated documentation tree; add to .gitignore only if you
                            do not want the docs versioned. Recommendation: version them.
```

### No changes required

`services/cast-integration` is untouched. The port copies content out of it; nothing in the
Python service needs to change for the Bob skill to work.

---

## 6. Verification checklist after installing

1. `/generate-docs --dry-run` → PLAN mode, scope table, capability map, batch preview, no writes.
2. `/generate-docs L0` → two documents in `bob-z-app-docs/L0-discovery/`, ledger rows flipped.
3. Open `L0-discovery/application-inventory.md` → confirm an Evidence Index is present and
   every table cell is either grounded with a `[source: …]` tag or reads
   `Not available from Z Premium analysis`.
4. `/docs-status` → coverage `2/31`, named list of the 29 outstanding documents.
5. Re-run `/generate-docs L0` → both documents skipped as complete (resumability check).
6. `/generate-docs L5` → confirm the evidence cache is hit for programs already processed in
   step 2 rather than re-running Generate data dictionary.
