# cobol-knowledge-extraction

A Bob skill that runs a disciplined, repeatable, resumable knowledge-extraction pipeline over a
mainframe codebase — COBOL, PL/I, JCL, REXX, or Assembler — and files every artifact into a
versioned `bob-z-knowledge-extract/` knowledge base.

**v2.0.0 — BobZ 3.x MCP-direct.** This skill calls the BobZ MCP server's tools directly:
`generate_data_dictionary`, `generate_documentation`, `explain_code`, `z_code_scan`,
`get_variables`, `get_control_flow`, `get_paragraphs`, `scan_program`, `get_expanded_source`,
`edit_data_dictionary`, and — when a Z Understand server is configured — `get_project_*`,
`impact_analysis`, `implementation_planning`, `sync_data_dictionary`. There is no UI-invocation
requirement and no "Autonomous Fallback Path": every capability below is a normal tool call the
agent makes itself, per program, per turn, with a structured JSON result. See `SKILL.md`'s
Version history for exactly what changed from v1.3.0.

---

## What it does

The skill drives BobZ MCP tools — Generate data dictionary, Generate documentation, Explain code,
Z Code Scan, and their structural/editor counterparts — and enforces consistent filing, naming, a
coverage ledger, and honest reporting of what could and could not run. It adds no extraction
capability of its own: the agent still makes every MCP call turn by turn (this is interactive, not
a fire-and-forget batch job), but three scripts under `scripts/` now do the inventory, ledger
verification, and coverage bookkeeping deterministically from disk state — never from memory, and
never by calling MCP themselves.

**Output tree produced:**

| Folder | Contents |
|---|---|
| `00-manifest/` | Machine-readable manifest, program inventory, coverage ledger, MCP capability probe, verification summary, run history |
| `01-application-architecture/` | System-level documentation from `generate_documentation` |
| `02-business-rules/by-program/` | Business rules and `explain_code` output per program |
| `03-data-structures/` | Data dictionary (by-program + master), copybook layouts, record layouts |
| `04-code-flow/` | Control flow graphs, paragraph indexes, dependency-derived call graphs |
| `05-dependencies/` | Provenance-labeled inter-program dependency map |
| `06-database/` | SQL usage per program (DDL is out of scope — requires DBA tooling); table usage map when `zUnderstandConfigured` |
| `07-file-structures/` | Physical file layout documentation |
| `08-jcl-batch/` | JCL job documentation, job-to-program map, batch/online classification |
| `09-cics-ims-transactions/` | CICS/IMS resource cross-walk (if checked-in source is present) |
| `10-error-handling/` | ABEND codes, exception paths, error-handling documentation |
| `11-code-quality/` | Z Code Scan findings, complexity metrics |
| `12-enterprise-standards/` | `AGENTS.md` copy, coding standards, custom skills |
| `13-impact-analysis/` | `impact_analysis` output when `zUnderstandConfigured`; out of scope otherwise |
| `14-implementation-plans/` | `implementation_planning` output when `zUnderstandConfigured`; downgrade-labeled reasoning otherwise |
| `15-modernization-mapping/` | Refactoring candidates and service-program slices |
| `16-cross-reference/` | Structural cross-reference (requires Z Understand server) |
| `17-qa-validation/` | DD review queue, SME sign-off log, validation report |

---

## Requirements

| Requirement | Notes |
|---|---|
| BobZ 3.x MCP server | Reachable from the agent's environment — probed first, every run (Gate G0) |
| IBM Bob IDE | Advanced mode must be enabled |
| Z Premium Package | Backs the MCP tools (`generate_data_dictionary`, `generate_documentation`, `explain_code`, `z_code_scan`, and the structural/editor tools) |
| Z Understand server | Optional — enables `get_project_*`, `impact_analysis`, `implementation_planning`, `sync_data_dictionary` as directly-callable tools. Without it, those tools are absent (never approximated) and the impact-analysis/implementation-plan/cross-reference folders stay `outOfScope`. |
| Mode | Z Code or Z Architect |
| Python 3, stdlib only | Runs `scripts/build_inventory.py`, `scripts/verify_extraction.py`, `scripts/build_report.py` — no third-party dependencies |

---

## How to invoke

### Auto-activation
Bob activates this skill automatically when you ask to extract knowledge, document a legacy
application, catalog business rules, or build a modernization knowledge base.

### Slash command
```
/cobol-knowledge-extraction [path|file-list|inventory.csv|glob] [--dry-run]
```

| Argument | Meaning |
|---|---|
| *(none)* | Use the open workspace root |
| `path/to/folder` | All recognized source files under that folder |
| `PROG1.CBL PROG2.CBL` | Exactly those files |
| `path/inventory.csv` | CSV with a `program_name` column — authoritative list |
| `LGA*.cbl` | Glob expanded within source roots |
| `--dry-run` | PLAN mode: produce the scope table and capability map, write nothing |

### Examples
```
/cobol-knowledge-extraction
/cobol-knowledge-extraction Cobol/
/cobol-knowledge-extraction inventory.csv
/cobol-knowledge-extraction --dry-run
/cobol-knowledge-extraction Cobol/CUSTVAL.CBL Cobol/CUSTADD.CBL
```

---

## Execution flow

```
Step  1  Resolve scope and inputs
Step  2  Declare approvals + pass Gate G0 (MCP reachable, workspace root, Advanced mode,
         zUnderstandConfigured)
Step  3  Create output folder structure (idempotent)
Step  4  Finalise scaffold + write extraction-manifest.json                     — Gate G1
Step  5  Build program inventory and coverage ledger via build_inventory.py     — Gate G1
Step  6  Governance baseline (AGENTS.md + coding standards) — first run only
Step  7  Select batch (≤100 programs)                                          — Gate G2
Step  8  Per-program loop: data dictionary → documentation → dependencies       — Gates G3/G4
Step  9  Per-program flow and paragraph structure (optional / on-demand)
Step 10  Language-specific passes: JCL, copybooks, CICS/BMS, SQL
Step 11  Code quality: z_code_scan + explain_code (COBOL/PL/I/HLASM only)
Step 12  Refactoring (on-demand only — not part of a standard batch)
Step 14  Impact analysis / implementation plan (callable directly if zUnderstandConfigured)
Step 15  Close batch: verify_extraction.py (Gate G4) + build_report.py, report
```

---

## Autonomy and approvals

The skill is **fully autonomous**. At Step 2 it emits a single AUTO-APPROVAL DECLARATION that
pre-approves all file system operations, MCP tool calls, editor/structure reads, and sub-skill
activations for the entire session. It never pauses for per-step confirmation. The G0–G4 gates
described in `SKILL.md` are automated correctness checks (is the server reachable, is the scaffold
built, does the artifact back the ledger claim) — they are not human approval prompts.

To suspend autonomy mid-session, send the message: **"pause for approval"**

---

## Data dictionary review gate

Even in fully autonomous mode, data dictionary **content** is not auto-approved — this is
unchanged by the MCP-direct rewrite, because the gate exists due to the content being
AI-generated, not due to how the tool that generated it was invoked. All AI-proposed business
meanings are filed as `status: draft` in `17-qa-validation/dd-review-queue.md`. A program is not
counted as complete until an SME reviews and signs off the entries in that queue.

Sign-off procedure:
1. Open `17-qa-validation/dd-review-queue.md` and review each row.
2. Correct any wrong meanings; delete any wrong entries.
3. Tell Bob: *"Approve CUSTADD dictionary"* (or name the programs).
4. Bob flips `status` to `approved`, sets `dd_approved=Y`, and logs the sign-off.

---

## Coverage definition

A program is **complete** when all three flags are `Y` in `extraction-status.csv`:

```
dd_generated=Y  AND  dd_approved=Y  AND  doc_generated=Y
```

`doc_generated=P` (partial) is retired in v2.0.0 — `generate_documentation` success is first-class
`Y` the moment all three perspectives file successfully. A `P` row can still appear only if this
ledger was carried over from a pre-v2.0.0 (v1.3.0) run; `build_report.py` surfaces any such rows
separately as `docPartialLegacy` and never counts them toward completeness.

`scripts/build_report.py` recomputes coverage from `extraction-status.csv` deterministically and
renders the Step 15 report — always `complete/total (%)` plus a named list of every incomplete
program and which specific flags are still pending. `scripts/verify_extraction.py` proves every
`Y` flag is backed by a real artifact on disk before a batch is considered closed.

---

## Resumability

The skill is designed to resume after interruption. Re-running against the same workspace will:
- Reconcile the inventory/ledger via `build_inventory.py` — add newly-in-scope programs, never
  drop or reorder an existing row, never touch an existing row's status or flags.
- Skip programs already complete (all three flags = `Y`).
- Retry programs with `E` (error) flags.
- Resume the serial `get_variables`/`generate_data_dictionary` loop from the last
  `... OK: {PROGRAM}` checkpoint in `extraction-log.md` — never restart from scratch.

---

## Limitations

| Limitation | Reason |
|---|---|
| No fallback path if the MCP server is unreachable | This is a deliberate v2.0.0 design decision, not an oversight — Gate G0 drops to PLAN mode immediately rather than degrading to a narrative substitute. |
| Dependency completeness cannot be guaranteed without Z Understand | Without `get_project_resource_usage`, dependency lists are narrative-extracted (`narrative-per-program-not-tool-verified`) — they may miss calls not mentioned in documentation. |
| DB2/IMS DDL, constraints, triggers out of scope | Requires DBA tooling external to Bob, regardless of Z Understand configuration. |
| Impact analysis, implementation planning, and cross-reference require Z Understand | `impact_analysis`, `implementation_planning`, `sync_data_dictionary`, and every `get_project_*` tool are absent (not degraded) when `zUnderstandConfigured: false`. |
| `refactor`/`generate_refactored_service` without Z Understand is unconfirmed | IBM's prerequisites are self-contradictory. The skill probes it automatically on first request and records the outcome. |

---

## Output file ownership

| File | Owner | Notes |
|---|---|---|
| `bobz/DD.json` | Bob IDE | Never move or truncate. The skill copies entries; it does not modify the root. |
| `bob-z-knowledge-extract/` | This skill | All artifacts under this tree are managed by the skill. |
| `AGENTS.md` | Workspace root | The skill copies it to `12-enterprise-standards/`; the live file stays at the root. |

---

## Skill files

| File | Purpose |
|---|---|
| `SKILL.md` | Full step-by-step instructions followed by Bob at activation |
| `SKILL.md.bak-*` | Backup of a prior version — safe to delete once the current version is verified |
| `README.md` | This file — human-readable summary for sharing and onboarding |
| `scripts/build_inventory.py` | Scans a resolved source scope and writes/reconciles `program-inventory.csv` + `extraction-status.csv`. Never calls MCP. |
| `scripts/verify_extraction.py` | Gate G4 (deterministic half): checks every `Y` ledger flag is backed by an artifact on disk; reconciles inventory vs. ledger; validates dependency provenance labels. Never calls MCP. |
| `scripts/build_report.py` | Recomputes manifest coverage from the ledger and renders the Step 15 report deterministically. Never calls MCP. |

---

## Version history

| Version | Change |
|---|---|
| **2.0.0** | **BobZ 3.x MCP-direct rewrite.** Retires the "Primary path (IBM workflow, UI-invoked)" + "Autonomous Fallback Path" (`get_variables`/`start_subtask`) two-tier model — every promoted tool is now called directly by the agent, per program, per turn. Adds Gate G0–G4 discipline, the MCP reachability probe, and the `get_project_*`/`impact_analysis`/`implementation_planning`/`sync_data_dictionary` "callable if `zUnderstandConfigured`, else absent" capability map. Retires `doc_generated=P`. Reconciles `program-inventory.csv` to a 7-column header shared with `z-app-documentation`. Adds `scripts/build_inventory.py`, `scripts/verify_extraction.py`, `scripts/build_report.py` for deterministic bookkeeping — none of which ever calls MCP. The data-dictionary SME review gate is unchanged. |
| 1.1.0 | Folder structure created before scope resolution (Step 3). Approval declaration merged into Step 2. Step 9 (flow/paragraph) made explicitly optional. Z Code Scan scoped to COBOL/PL/I/HLASM only. Error handling (`E` flag) added for workflow failures. Batch-complete definition corrected to require all three flags. Step 15 report requirements made exhaustive. Key Rules converted to table. `argument-hint` added to frontmatter. |
| 1.0.0 | Initial release |
