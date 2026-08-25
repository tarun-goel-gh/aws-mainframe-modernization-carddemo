# Evidence Plans — Z Premium Package

Direct replacement for `CAST_TOOL_PLANS` in
`cast-integration/src/cast_integration_service/prompts/grounding.py`.

The service injected a named CAST MCP tool sequence into every prompt so the agent gathered
evidence in a cheap, ordered, repeatable way. This file does the same job with **BobZ v3 MCP
server tools, plus read-only file tools**. No CAST MCP server is used.

**Every capability below is directly callable — there is no UI session to invoke.** BobZ v3
ships an MCP server that exposes Z Premium Package capabilities (and the editor tools) as normal
tool calls: the agent calls the tool itself, on this turn, and gets a structured JSON result
back. There is no "launch the workflow and wait for the IDE" step and no `start_subtask` detour —
that two-tier path existed only because no MCP server did, and it is retired. Where a step below
says "Generate documentation (architect perspective)", read it as the direct call
`generate_documentation(programId, programPath, perspective=architect)`; "Explain code" is
`explain_code(...)`; "Z Code Scan" is `z_code_scan(...)`; and so on for every capability in the
inventory below. The exact tool names and argument shapes are the authoritative vocabulary in
`.bob/skills/_design/bobz-v3-foundations.md` §1 — this file names *when* to call each one, that
document names *how*.

Run the plan named by the document's reference file. Run steps **in order**. Stop when the
document's sections are satisfied.

---

## Capability inventory (what the plans are built from)

| Capability | Kind | Requires Z Understand? |
|---|---|---|
| `generate_documentation` (architect / developer / business perspectives) | BobZ MCP tool | No |
| `generate_data_dictionary` | BobZ MCP tool | No |
| `explain_code` | BobZ MCP tool | No |
| `z_code_scan` (single program or batch) | BobZ MCP tool | No |
| `refactor` / `generate_refactored_service` | BobZ MCP tool (reliability unverified with no Z Understand server) | Unverified |
| `get_control_flow`, `get_paragraphs`, `get_variables`, `get_expanded_source`, `scan_program`, `edit_data_dictionary` | BobZ MCP tool | No |
| `read_file`, `list_files`, `glob`, `grep`, read-only `execute_command` | File tool (local, not MCP) | No |
| `/init` (AGENTS.md), `/z-coding-standards-skill-builder` | Bob command (local, not MCP) | No |
| `get_project_inventory`, `get_project_tables`, `get_project_resource_usage`, `impact_analysis`, `implementation_planning`, `sync_data_dictionary` | BobZ MCP tool | **Yes** |

Anything in the last row is **unavailable** without a configured Z Understand server. Do not
approximate it — state the gap and mark the affected sections
`Not available from Z Premium analysis`. Every "BobZ MCP tool" row above is called directly by
the agent per `.bob/skills/_design/bobz-v3-foundations.md` §1; the rows still marked
"Bob command" / "File tool (local, not MCP)" are the capabilities that document does not promote
into the MCP vocabulary — call them exactly as before.

**Tool name correction (mirrors `cobol-knowledge-extraction/SKILL.md` F10):**
`zopeneditor-cobol-get-program-control-flow` and `zopeneditor-cobol-get-data-flow` are **not
valid tool names** and must never be called, in a plan step or otherwise. Use only
`get_control_flow` and `get_paragraphs` from the promoted MCP tool vocabulary — `get_variables`
already returns the WS/Linkage item detail (PIC, level, usage) that would otherwise be sought
from a "data flow" call.

---

## CAST plan → Z plan mapping

| Original CAST plan | Z replacement | What changed |
|---|---|---|
| `discovery` (`applications`, `stats`, `packages`, `api_inventory`, `application_database_explorer`, `applications_dependencies`, `quality_insights`) | `z-discovery` | Application listing replaced by source-root inventory; package listing by member/library classification; DB explorer by copybook + DCLGEN scan |
| `comprehensive` | *(not ported as a plan)* | The service used it for one mega-document; here every level runs its own plan and the manifest aggregates |
| `module` (`objects`, `object_profiles`, `object_details`, `source_files`, `pathfinder_hierarchy_details`) | `z-module` | Object model replaced by program → paragraph → variable structural tools plus Explain code |
| `api` (`api_inventory`, `transactions`, `transaction_profiles`, `transaction_details`) | `z-api` | CAST transactions replaced by CICS transaction IDs, BMS maps, program entry points and MQ interfaces |
| `data` (`application_database_explorer`, `data_graphs`, `data_graph_*`) | `z-data` | Replaced by Generate data dictionary, copybook record layouts and `EXEC SQL` extraction |
| `architecture` (`architectural_graph`, `package_interactions`, dependencies) | `z-structure` | Replaced by architect-perspective docgen, control-flow tools and narrative call graphs |
| `integration` (`inter_applications_dependencies`, `inter_app_detailed_dependencies`) | `z-integration` | Replaced by `EXEC CICS LINK/XCTL/START`, MQ calls, JCL dataset handoffs and called subprograms |
| `quality` (`applications_quality_insights`, `quality_insight_violations`, `advisors`, `application_iso_5055_explorer`) | `z-quality` | Replaced by Z Code Scan findings and complexity metrics |
| `business` (`transactions`, `data_graphs`, `packages`) | `z-business` | Replaced by business-perspective docgen plus Explain code on the highest-complexity programs |
| *(none — new)* | `z-operations` | JCL job flow, scheduling, return codes, ABEND and restart logic. The service had no equivalent because CAST's model is distributed-stack. |

---

## `z-discovery`

Scope, size and technology inventory. Call in this order:

1. `list_files` / `glob` across the resolved source roots → enumerate every member.
   Classify by extension (COBOL `.cbl .cob .cobol`, copybook `.cpy .copy`, PL/I `.pli .pl1`,
   include `.inc`, JCL `.jcl .prc .proc`, REXX `.rex .rexx`, HLASM `.asm .hlasm .mlc`,
   CICS `.csd`, BMS `.bms`). Record every language **found and not found**.
2. `read_file` on `zapp.yaml` / `.zapp/` property groups → library concatenations and where
   copybooks resolve from. This is the build-configuration evidence.
3. Read-only `execute_command` (`wc -l`, `find`, `stat`) → member counts, line counts,
   last-modified stamps. These are the only size metrics you may state.
4. `grep` for entry-point and interface markers: `PROCEDURE DIVISION USING`,
   `EXEC CICS`, `EXEC SQL`, `CALL '`, `MQOPEN`/`MQPUT`/`MQGET`.
5. Generate documentation (architect perspective) on the top-level driver programs only →
   application purpose and high-level shape.

**Stop condition:** the inventory table and technology profile are filled.
**Never:** state a line count, member count or date you did not measure in step 3.

---

## `z-structure`

Architecture, layering and modernization framing. Call in this order:

1. `z-discovery` results (reuse — do not re-run).
2. Generate documentation (**architect** perspective) across the batch → subsystem and layer
   narrative.
3. `get_control_flow` on each documented program → intra-program structure.
4. `grep` for `CALL '`, `EXEC CICS LINK|XCTL|START`, `COPY ` → inter-program edges.
   Assemble the call graph from these plus step 2's narrative.
   Label it `narrative-per-program-not-tool-verified`.
5. JCL job-to-program map from `z-operations` step 2 → batch-side structure.
6. Group members into subsystems using: JCL job grouping first, then naming convention,
   then copybook sharing. State which criterion you used.

**Never:** present the call graph as structurally complete without Z Understand.

---

## `z-module`

Program-, paragraph- and rule-level depth. Call in this order:

1. `scan_program` / `get_expanded_source` → resolve copybooks so PIC clauses and conditions
   are the expanded ones.
2. `get_paragraphs` → paragraph index with line ranges.
3. `get_variables` → working-storage and linkage items with PIC, level, usage.
4. Generate documentation (**developer** perspective) → per-program behaviour narrative.
5. Explain code → paragraph-level intent for the paragraphs the document details.
6. `get_variables` output already gathered in step 3 → variable lifecycle (declaration, PIC,
   level, usage) for the fields the document details. There is no separate "data flow" MCP
   tool; do not call `zopeneditor-cobol-get-data-flow` — it is not a valid tool name.
7. `grep` for `IF `, `EVALUATE `, `WHEN `, `88 ` condition names → candidate business rules;
   quote the condition verbatim with `member:line`.

**Stop condition:** every documented paragraph, field and rule has a `member:line` citation.

---

## `z-data`

Data dictionary, record layouts and lineage. Call in this order:

1. Generate data dictionary → business meanings. File as `status: draft`; queue every entry
   for SME review (see the review gate in `SKILL.md`).
2. `get_variables` + `get_expanded_source` per program → authoritative PIC, level, OCCURS,
   REDEFINES, usage.
3. `read_file` on each copybook → record layouts. Derive field offsets and lengths only by
   computation from PIC clauses; show the computation basis.
4. `grep` for `EXEC SQL` → DB2 statement inventory per program; `DECLARE ... CURSOR`,
   `SELECT`, `INSERT`, `UPDATE`, `DELETE` and the tables each touches.
5. `grep` for `SELECT ... ASSIGN TO`, `FD `, `RECORD KEY` → VSAM/QSAM file definitions and
   dataset DDNAMEs; cross-reference DDNAMEs against JCL from `z-operations`.
6. Lineage: chain `read → transform → write` per field using step 2 data-flow output and
   step 5 dataset mapping. Label `narrative-per-program-not-tool-verified`.

**Out of scope — state plainly, never infer:** DB2/IMS DDL, constraints, triggers, indexes,
catalog statistics. These require DBA tooling outside Bob.

---

## `z-api`

Interfaces and entry points — the Z equivalent of CAST's `api_inventory` / `transactions`.
Call in this order:

1. `grep` for `EXEC CICS` verbs → `RECEIVE MAP`, `SEND MAP`, `LINK`, `XCTL`, `START`,
   `RETURN TRANSID` → online entry points.
2. `read_file` on `.csd` resource definitions → transaction ID → program bindings.
3. `read_file` on `.bms` maps → screen fields, lengths, attributes; this is the online
   request/response contract.
4. `grep` for `PROCEDURE DIVISION USING` + read the LINKAGE SECTION → called-program
   interface signature (the Z equivalent of a request/response schema).
5. `grep` for `MQOPEN|MQPUT|MQGET|MQCLOSE` and web-service stubs → asynchronous and
   service interfaces.
6. Generate documentation (developer perspective) on each entry-point program → behaviour
   behind each interface.

**Mapping note:** where the template asks for HTTP method, path, status code, rate limiting
or versioning, use `references/z-substitutions.md`. If a concept has no Z equivalent, render
the heading with `Not available from Z Premium analysis` — do not invent a REST framing.

---

## `z-integration`

Inbound and outbound coupling. Call in this order:

1. `z-api` results (reuse).
2. `grep` for `CALL '` (static and dynamic) → called subprograms; distinguish literal from
   `CALL identifier` and flag dynamic calls as unresolved edges.
3. `EXEC CICS LINK|XCTL|START` targets → online inter-program integration.
4. JCL `DD` statements → dataset handoffs between jobs; `//*` scheduler comments, `SYSOUT`,
   FTP/NDM steps → external file transfer integration.
5. MQ queue names from step 1 of `z-api` → messaging contracts.
6. Copybook sharing across programs → shared-contract coupling.

Every edge carries provenance. Dynamic `CALL identifier` edges are reported as
**unresolved** — never guessed.

---

## `z-quality`

Quality, risk and security. Call in this order:

1. `z_code_scan` across the batch (`programIds[]`/`programPaths[]`, `databasePath`), or per
   program (`programId`, `programPath`, `databasePath`) → findings per program. The old fake
   names `zcodescan-check-list-of-local-programs` and `zcodescan-check-current-program` do not
   exist and must never be called.
2. Roll complexity signals into a complexity metrics table; rank the batch by
   modernization risk.
3. Explain code on the top 20% by complexity → why each is risky.
4. `grep` for security-relevant patterns actually present in the source: `EXEC CICS
   VERIFY PASSWORD`, RACF calls, hard-coded literals in `VALUE` clauses, `ACCEPT` from
   console, unencrypted dataset writes.
5. `grep` for error handling: `ON SIZE ERROR`, `INVALID KEY`, `AT END`, `EXEC CICS HANDLE`,
   `ABEND`, `RESP` checks → error-handling coverage.

**Not available without Z Understand:** ISO-5055 characteristic scoring, CVE mapping and
portfolio-level roll-up. The service got these from CAST `application_iso_5055_explorer`
and `quality_insights`; there is no Z Premium equivalent. Mark those sections unavailable.

---

## `z-business`

Business capability, feature and requirement content. Call in this order:

1. Generate documentation (**business** perspective) across the batch → business narrative
   per program.
2. JCL job names, CICS transaction IDs and screen titles from BMS maps → user-facing
   feature names. These are the closest Z equivalent of CAST transactions.
3. Explain code on the programs that carry the most conditional logic → the rules behind
   each feature.
4. Group programs into capabilities using: shared copybooks, shared datasets, and job
   grouping. State the grouping criterion used in the document.
5. `grep` for `88 ` condition names and `EVALUATE` blocks → policy and eligibility rules.

Business-level items not evidenced by a workflow or a source read must be labelled
`Assumption — not tool-verified` per the grounding contract, or omitted.

---

## `z-operations`

Batch operations, scheduling and recovery. **New plan — no CAST origin.** Call in this order:

1. `list_files` over JCL source roots → job inventory.
2. Generate documentation or Explain code on each JCL member → job steps, `EXEC PGM=`,
   `DD` statements, dataset dispositions. Build the job-to-program map.
   Label `narrative-per-program-not-tool-verified`.
3. `grep` for `COND=`, `IF `, `RESTART=`, `TYPRUN=` → conditional execution, restart points.
4. `grep` for `ABEND`, `RETURN-CODE`, `SET RETURN-CODE`, `EXEC CICS ABEND` → failure modes
   and return-code contracts.
5. `read_file` on PROC members and PROCLIB references → build/compile and runtime
   configuration. This is the Z answer to the template's "build & deployment" sections.
6. Scheduler metadata **only if checked into the repository** (control cards, scheduler
   comments). Never assume a scheduler product.

**Out of scope:** live scheduler state, SMF data, runtime monitoring feeds, production
console logs. State this rather than inferring.
