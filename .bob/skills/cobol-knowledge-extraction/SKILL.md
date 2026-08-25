---
name: cobol-knowledge-extraction
description: Use when extracting, documenting, or cataloging knowledge from a mainframe COBOL, PL/I, JCL, REXX, or Assembler codebase for modernization — builds a versioned bob-z-knowledge-extract knowledge base by calling the BobZ 3.x MCP server directly (generate_data_dictionary, generate_documentation, explain_code, z_code_scan, get_variables, get_control_flow, get_paragraphs, scan_program, get_expanded_source, edit_data_dictionary, and — when a Z Understand server is configured — get_project_*, impact_analysis, implementation_planning, sync_data_dictionary). Works against any project given as a folder path, a file list, an inventory CSV, a glob, or the open workspace. Activate when the user asks to extract knowledge, document a legacy application, catalog business rules, build a modernization knowledge base, run an extraction batch, or mentions "bob-z-knowledge-extract", "knowledge extraction", or "extraction ledger".
metadata:
  version: 2.0.0
  argument-hint: '[path|file-list|inventory.csv|glob] [--dry-run]'
---

# COBOL Knowledge Extraction

Runs a disciplined, repeatable, resumable knowledge-extraction process over a mainframe codebase and
files every artifact into a `bob-z-knowledge-extract/` tree. Project-agnostic: nothing about a
specific application, folder layout, or naming convention is assumed — scope and environment are
resolved at Steps 1 and 2 every run.

**This is v2.0.0 — the BobZ 3.x MCP-direct rewrite.** BobZ 3.x ships a real MCP server exposing
Bob IDE / Z Premium Package capabilities as directly-callable tools. There is now **one path**:
the agent calls the promoted MCP tools itself — `generate_data_dictionary`, `generate_documentation`
(three perspectives), `explain_code`, `z_code_scan`, `get_variables`, `get_control_flow`,
`get_paragraphs`, `scan_program`, `get_expanded_source`, `edit_data_dictionary`, and, when
`zUnderstandConfigured: true`, `get_project_inventory`, `get_project_tables`,
`get_project_resource_usage`, `impact_analysis`, `implementation_planning`, `sync_data_dictionary` —
gets a structured JSON result back, and files it. The old two-tier **Autonomous Fallback Path**
(`get_variables` + `start_subtask`, "§8a-alt"/"§8b-alt") and the "Primary path (IBM workflow,
UI-invoked)" framing it existed to work around are both **retired**. If you are looking for that
language because you read an older version of this file, it no longer applies: every workflow that
used to require "an interactive session available" is now a normal tool call.

**What did not change:** the domain knowledge this skill encodes about mainframe extraction —
the CMQ*/IMS*/DB2* system-copybook non-fatal-warning classification, the serial-execution
requirement for `get_variables` against a shared SQLite database, the ledger and manifest column
names, the folder structure under `bob-z-knowledge-extract/`, the batch ceilings, the
resumption-via-checkpoint-log rule, and the SME data-dictionary review gate. All of it is carried
forward below, updated only where the invocation mechanics changed.

**Deterministic vs. interactive, in one paragraph:** the coverage/ledger/manifest bookkeeping that
used to be entirely agent-narrated is now **partly deterministic** — three scripts under
`scripts/` (`build_inventory.py`, `verify_extraction.py`, `build_report.py`) do the inventory
scan, the artifact-vs-ledger reconciliation, and the coverage math, exactly and repeatably, from
files already on disk. **None of these scripts ever calls the BobZ MCP server.** Only the agent
calls MCP tools, one call at a time, per program, per turn — this remains an **interactive
loop**, not a fire-and-forget batch job. The scripts exist so the bookkeeping around those calls
stops depending on the agent remembering counting rules correctly; they do not remove the agent
from the per-program MCP call loop itself.

---

## Run modes

| Mode | When | Behavior |
|---|---|---|
| **PLAN** | User passes `--dry-run`, says "plan only", "what would you do", or Gate G0 fails | Produce the full plan and the manifest, write **no** artifacts, change **no** ledger rows |
| **EXECUTE** | Default — proceed autonomously as soon as Gate G0 passes | Run the batch, write artifacts, update the ledger. Do not wait for confirmation. |

Always state which mode you are in as the first line of your response.

---

## Gate structure (G0–G4)

This skill enforces five named gates, mirroring the gate discipline used elsewhere in this skill
suite. Each is described in full at the step where it fires; this table is the map.

| Gate | Fires at | Checks | On failure |
|---|---|---|---|
| **G0** | Step 2b, once per run | MCP reachable, workspace root unambiguous, Advanced mode on, `zUnderstandConfigured` determined, capability map derived | Drop to PLAN mode immediately — **no fallback path exists in v2.0.0**; report the exact transport/tool error |
| **G1** | Steps 3–5, once per run | Output folder scaffold exists, manifest written, `program-inventory.csv` + `extraction-status.csv` built/reconciled via `build_inventory.py` | Do not proceed to batch selection until resolved |
| **G2** | Step 7, per batch | Batch respects ceilings (≤100 programs per `generate_documentation` run; `get_variables` always serial), `batch_id` assigned and stamped on every touched row | Re-split the batch |
| **G3** | Step 8, per tool group, before the first call of that kind in a run | Preconditions for the specific MCP tool are met — `bobz/DD.json` exists before `get_variables`/`edit_data_dictionary`; the program is scanned (`scan_program`) before `get_variables`/`get_expanded_source` on a program not yet in the scanner DB; `databasePath` is resolved and passed explicitly | Fix the precondition, then call — never call blind |
| **G4** | Step 8, after every call (interactive half) + Step 15 batch close (deterministic half, `verify_extraction.py`) | Tool response is well-formed; ledger flag set to `Y`/`E`; checkpoint logged; every `Y` flag is backed by a real artifact on disk | Log the error, mark `E`, continue; a batch is not "closed" until `verify_extraction.py` exits `0` |

---

## Approval posture

**This skill is fully autonomous. No human approval is required at any point — not for tool calls,
not for skill activations, not for file writes, not for MCP tool invocations.**

All approvals are declared upfront in Step 2 and are irrevocable for the session. There are no
interactive gates in the human-approval sense (the G0–G4 gates above are automated correctness
checks, not approval prompts), and no per-step confirmation requests anywhere in the process.

One content gate survives — it is a **deferred review gate, not an interactive prompt**, and it
exists for a reason unrelated to how the tool was invoked:

- **Data dictionary business meanings** — entries are filed as `status: draft` and queued in
  `17-qa-validation/dd-review-queue.md`. They are excluded from the completeness count until a
  human signs them off asynchronously. The skill never pauses for this; it reports the queue size
  in Step 15 and continues. This gate exists because the **content is AI-generated** — that fact
  is independent of whether it arrived via a UI workflow or a direct MCP tool call, so the rewrite
  changes nothing about it.

State `EXECUTE — auto-approved posture, dictionary review deferred to queue` as the opening line of
every run. Never ask the user to confirm the posture, approve a step, or give a go-ahead. The only
revocation trigger is an explicit user message containing the phrase **"pause for approval"**.

---

## Step 1 — Resolve scope and inputs

Never assume the scope. Determine it from whichever input the user actually gave, in this precedence
order:

| # | Input form | How to interpret |
|---|---|---|
| 1 | An inventory CSV path (`*.csv` with a `program_name` column) | Authoritative program list; use rows as-is, do not re-discover |
| 2 | An explicit list of files, or `@`-referenced files | Exactly those programs, nothing else |
| 3 | A glob or pattern (e.g. `LGA*.cbl`) | Expand within the resolved source roots |
| 4 | A folder path | All recognized source files under it, recursively |
| 5 | Nothing given | The currently open workspace root |

This is also exactly the precedence order `scripts/build_inventory.py --scope` implements — the
script performs the mechanical resolution; the agent still owns the multi-root ambiguity check
below, which requires judgment a script should not silently guess at.

Then resolve and **record** four things — every later step depends on them:

1. **`workspaceRoot`** — the folder the IDE has open. If Bob artifacts (`.bob/`, `.bobz/`, `bobz/`,
   `docs/explain/`) appear at *more than one* level of the path, the workspace has been opened at
   multiple roots. Stop and ask the user which root to use. Do not guess — the whole filing contract
   and the inventory denominator depend on this answer.
2. **`extractionRoot`** — `<workspaceRoot>/bob-z-knowledge-extract`, unless the user names another.
3. **`sourceRoots`** — the folders actually holding source. Discover them; do not expect any
   particular folder name. If `zapp.yaml` or a `.zapp/` property group exists, read it: its
   `libraries.locations` entries tell you where copybooks/includes resolve from, which is also a
   reliable hint for where source lives.
4. **`languagesPresent` / `languagesAbsent`** — classify by extension, case-insensitively:

| Language | Extensions |
|---|---|
| COBOL | `.cbl` `.cob` `.cobol` |
| COBOL copybook | `.cpy` `.copy` |
| PL/I | `.pli` `.pl1` |
| PL/I include | `.inc` |
| JCL | `.jcl` `.prc` `.proc` |
| REXX | `.rex` `.rexx` |
| Assembler (HLASM) | `.asm` `.hlasm` `.mlc` |
| CICS resources | `.csd` |
| BMS maps | `.bms` |

Record every language you found **and every one you did not**. A language that is absent is a
`notApplicable` entry in the manifest (Step 4), never a silently empty folder.

State the resolved scope back to the user as a short table, then continue immediately to Step 2.

---

## Step 2 — Declare all approvals and pass Gate G0

### 2a — Upfront approval declaration

Emit this block exactly once at the start of every EXECUTE run. After emitting it, never ask for
approval again for the duration of this session.

```
AUTO-APPROVAL DECLARATION
=========================
All of the following are pre-approved for the entirety of this extraction run.
No further confirmation will be requested.

FILE SYSTEM OPERATIONS
  write_file / insert_content / apply_diff   — any file under extractionRoot
  list_files / read_file / glob / grep        — anywhere in the workspace
  execute_command                             — running build_inventory.py, verify_extraction.py,
                                                 build_report.py, and other read-only shell commands
                                                 (find, wc, stat) for inventory sizing

BOBZ MCP TOOLS (called directly by the agent, per program, per turn — no UI session required)
  generate_data_dictionary    generate_documentation (architect / developer / business)
  explain_code                z_code_scan
  get_variables                get_control_flow            get_paragraphs
  scan_program                 get_expanded_source          edit_data_dictionary
  refactor                     generate_refactored_service  (on-demand only — Step 12)

BOBZ MCP TOOLS — gated on zUnderstandConfigured: true (called directly when available;
never approximated when it is false — see the capability map below)
  get_project_inventory       get_project_tables         get_project_resource_usage
  impact_analysis              implementation_planning    sync_data_dictionary

EDITOR / STRUCTURE READS (subset of the same MCP tool set, listed separately for clarity)
  get_control_flow, get_paragraphs, get_expanded_source, scan_program

SUB-SKILL ACTIVATIONS
  data-dictionary-workflow, docgen-workflow, explain-workflow
  refactor-workflow, refactor-code-generation-workflow

LEDGER, MANIFEST, AND SCRIPT WRITES
  extraction-status.csv, program-inventory.csv, extraction-manifest.json,
  extraction-log.md, run-history/, mcp-capability-probe.json, verification.json
  (produced by build_inventory.py, verify_extraction.py, build_report.py)

Revoking this declaration requires the user to send the message: "pause for approval".
```

### 2b — Gate G0: preflight

Bob's capability map depends on the installed BobZ version and on whether a Z Understand server
is configured. Probe it every run, in this order, and record what you find.

1. **Build/refresh the program inventory first.** Run `scripts/build_inventory.py` (§ Scripts)
   against the Step 1 scope if `program-inventory.csv` does not already exist for it. Gate G0's
   next check needs at least one real `programId`/`programPath` pair to call against — this is
   why inventory-building now happens *before* the MCP reachability probe rather than at the old
   Step 5.
2. **MCP reachability probe (new — the first live check).** Make one cheap, real tool call —
   `get_paragraphs` (or `get_control_flow`) — against the first program in the inventory just
   built. A response, including a well-formed tool-level error about that specific program,
   proves the server is reachable. A connection/transport failure, timeout, or "tool not found"
   proves it is not. Record `mcpProbeMethod`, `mcpProbeLatencyMs`, and whatever server/version
   string the response surfaces (`mcpServerVersion`, or `"unknown"` if the result carries
   none — never invent one).
3. **Active mode** — Z Code or Z Architect.
4. **Advanced mode** — required for this skill to have activated at all; its absence is the most
   common silent failure.
5. **Z Understand server** — read `<workspaceRoot>/.bobz/local-settings.json`. A `databaseLocation`
   pointing at a local `ScannerOutput.db` with no server URL = local-scanner mode. Record
   `zUnderstandConfigured: true|false`.
6. **Local scanner metadata** — does `.bobz/expanded/` or a `ScannerOutput.db` already exist?
7. **Existing state** — do `AGENTS.md`, `bobz/DD.json`, `docs/explain/`, or `extractionRoot`
   already exist? Never overwrite them blind.

Write the probe result to `00-manifest/mcp-capability-probe.json`:

```json
{
  "probedAt": "<exact timestamp from conversation context>",
  "mcpReachable": true,
  "mcpProbeMethod": "get_paragraphs(programId=<first inventory program>)",
  "mcpProbeLatencyMs": 0,
  "mcpServerVersion": "unknown",
  "activeMode": "",
  "advancedMode": true,
  "zUnderstandConfigured": false,
  "localScannerMetadata": "<databaseLocation from .bobz/local-settings.json>",
  "capabilityMap": {
    "generate_data_dictionary": "available", "generate_documentation": "available",
    "explain_code": "available", "z_code_scan": "available",
    "get_variables": "available", "get_control_flow": "available", "get_paragraphs": "available",
    "scan_program": "available", "get_expanded_source": "available",
    "edit_data_dictionary": "available",
    "refactor": "unverified", "generate_refactored_service": "unverified",
    "get_project_inventory": "unavailable", "get_project_tables": "unavailable",
    "get_project_resource_usage": "unavailable",
    "impact_analysis": "unavailable", "implementation_planning": "unavailable",
    "sync_data_dictionary": "unavailable"
  }
}
```

**Gate G0 fails — drop to PLAN mode immediately** — if the MCP server is unreachable, the
workspace root is ambiguous, Advanced mode is off, or no source files were found in scope. **No
fallback path exists in v2.0.0.** Do not invoke any per-program narrative substitute, do not
approximate a tool's output, do not degrade quietly — report the exact transport/tool error and
stop. In PLAN mode, write no artifacts and make no ledger changes.

**F2 — IBM system copybook warnings (CRRZG5307W and similar)**

When the COBOL language server emits warnings of the form:

```
CRRZG5307W The COBOL language server requested the include file "<NAME>", which was not found.
```

Apply the following classification before treating it as a failure:

| Copybook prefix | Classification | Action |
|---|---|---|
| `CMQ*` (e.g. CMQGMOV, CMQPMOV, CMQMDV, CMQV) | IBM MQ system copybook — ships with MQ product, never checked into source repos | Log once to `extraction-log.md`: `"MQ system copybooks not in repo — MQ structure fields will be absent from DD for: {PROGRAMS}"`. Add `"system-copybooks-missing: CMQxxxx"` to ledger `notes`. Do NOT mark `dd_generated=E`. |
| `IMS*`, `DLI*` | IMS/DL-I system copybook | Same treatment as CMQ* — log and note, do not fail. |
| `DB2*`, `SQL*` | DB2 system copybook | Same treatment. |
| Any other name | Genuine missing copybook | Investigate. If it is a project copybook (should be in repo), log as `dd_generated=E` and note the unresolved include in `17-qa-validation/validation-report.md`. |

These warnings are **language-server-only** — they do not prevent `get_variables`,
`generate_data_dictionary`, `scan_program`, or any other MCP tool call from working. The
extraction continues normally; the only effect is that MQ/IMS/DB2 structure field names will not
appear as variables for the affected programs.

**Capability map** — this is now a direct callability map, not an availability-of-UI-session map:

| Capability | If `zUnderstandConfigured` is false | If `zUnderstandConfigured` is true |
|---|---|---|
| `generate_data_dictionary`, `generate_documentation`, `explain_code`, `z_code_scan`, `get_variables`, `get_control_flow`, `get_paragraphs`, `scan_program`, `get_expanded_source`, `edit_data_dictionary` | **callable** — irrelevant to Z Understand | callable |
| `refactor`, `generate_refactored_service` | **unverified** — see Step 12 | unverified — same caveat |
| `get_project_inventory`, `get_project_tables`, `get_project_resource_usage`, `impact_analysis`, `implementation_planning`, `sync_data_dictionary` | **absent** — do not call, do not approximate, state this plainly | **callable** |

This replaces the old two-column "available / unavailable" table: these six tools used to be
flatly "unavailable" in the old model regardless of configuration; they are now directly-callable
MCP tools whose reachability is a runtime fact, gated only on `zUnderstandConfigured`. If a
capability you expected to be unavailable turns out to be present (or vice versa), record the
finding in `00-manifest/extraction-log.md` and tell the user.

---

## Step 3 — Create the output folder structure

Now that `workspaceRoot` and `extractionRoot` are resolved, create the full tree. This step is
**idempotent** — create what is missing, never overwrite or delete existing content.

```
00-manifest/                              run-history/ (sub-folder)
01-application-architecture/
02-business-rules/                        by-program/ (sub-folder)
03-data-structures/                       data-dictionary/, data-dictionary/by-program/,
                                          copybooks/, record-layouts/ (sub-folders)
04-code-flow/                             control-flow/, paragraph-index/, call-graphs/
05-dependencies/
06-database/                              sql-usage-by-program/
07-file-structures/
08-jcl-batch/                             jobs/
09-cics-ims-transactions/
10-error-handling/                        exception-paths-by-program/
11-code-quality/                          zcodescan-findings/
12-enterprise-standards/                  custom-skills/
13-impact-analysis/
14-implementation-plans/
15-modernization-mapping/
16-cross-reference/
17-qa-validation/
```

For any folder that cannot receive content yet, create a placeholder `README.md`:

```
# <folder-name>
Pending — reason will be recorded after scope resolution.
```

These placeholders are updated in Step 4. Never delete an existing README.

---

## Step 4 — Finalise the scaffold and write the manifest (Gate G1)

1. **Update placeholder READMEs** — replace the "Pending" text with the correct `notApplicable` or
   `outOfScope` reason now that scope is known. Folders that will receive content: remove their
   placeholder README or leave it absent. Never delete a README that already carries real content.

2. **Write `00-manifest/extraction-manifest.json`**:

```json
{
  "schemaVersion": "1.1",
  "skillVersion": "<copy from SKILL.md frontmatter version field — never hardcode>",
  "generatedAt": "<exact date from conversation context>",
  "workspaceRoot": "<resolved>",
  "extractionRoot": "<resolved>",
  "inputMode": "workspace|folder|file-list|inventory-csv|glob",
  "scope": { "sourceRoots": [], "languagesPresent": [], "languagesAbsent": [] },
  "mcp": {
    "reachable": false,
    "probeMethod": "",
    "probeLatencyMs": 0,
    "serverVersion": "unknown",
    "probeFile": "00-manifest/mcp-capability-probe.json"
  },
  "environment": {
    "activeMode": "", "advancedMode": true, "zUnderstandConfigured": false,
    "localScannerMetadata": "<path from .bobz/local-settings.json — never leave as 'none' after scan>",
    "bobIdeVersion": "", "zPremiumVersion": ""
  },
  "capabilityMap": {},
  "batches": [],
  "coverage": {
    "inventoryCount": 0, "ddDone": 0, "ddApproved": 0,
    "docDone": 0,
    "explainDone": 0, "zcodescanDone": 0, "completeProgramCount": 0
  },
  "approvalPosture": "auto-approved",
  "notApplicable": [],
  "outOfScope": []
}
```

> **Schema note (F6):** `skillVersion` must always be copied from the SKILL.md `version` field at
> run time — never hardcoded. `schemaVersion` moved to `"1.1"` in v2.0.0 to reflect the new `mcp`
> block and the retirement of `docPartial` from the coverage schema (see the "MCP server is the
> primary path now" note under Key Rules). `docPartial` no longer appears here: `doc_generated`
> only ever takes `Y`/`N`/`E` going forward, so there is nothing partial left to count separately.
> `build_report.py` still tracks a legacy `docPartialLegacy` counter internally for workspaces
> resumed from a pre-v2.0.0 run — see Step 15.

Every folder that will stay empty gets a `README.md` stating which case applies and why. An
unexplained empty folder is a defect: it falsely implies "we extracted this and found nothing."

Seed these `outOfScope` entries — two hold unconditionally, two are conditional on
`zUnderstandConfigured` (this is new in v2.0.0: these tools are no longer always unavailable):

- `06-database/schema/`, `06-database/constraints-and-triggers.md` — **always** out of scope: DB2/IMS DDL, constraints, and triggers require DBA tooling outside Bob regardless of Z Understand.
- `06-database/table-usage-map.json` — out of scope only when `zUnderstandConfigured: false` (requires `get_project_tables`). When `true`, populate it directly from that tool call instead of seeding a stub.
- `13-impact-analysis/` — out of scope only when `zUnderstandConfigured: false` (requires `impact_analysis`). When `true`, this folder receives real content at Step 14.
- `14-implementation-plans/` — out of scope only when `zUnderstandConfigured: false` (requires `implementation_planning`). When `true`, same as above.

---

## Step 5 — Build the inventory (Gate G1 continued — this is the denominator)

Without a Z Understand project there is no `get_project_inventory`. The inventory is the only
denominator every completeness number is measured against.

**This step is now scripted.** Run:

```
python3 scripts/build_inventory.py --scope <path|@filelist|inventory.csv|glob> \
    --workspace-root <workspaceRoot> --extraction-root <extractionRoot>
```

(If Step 2b's Gate G0 probe already ran this script once for this scope, re-running it here is
still safe and required — it reconciles, it never duplicates or drops rows.) See § Scripts for
the full CLI contract, exit codes, and reconciliation rules.

`00-manifest/program-inventory.csv`, one row per source file, header exactly (**7 columns — this
is the v2.0.0 reconciled header**, unioning the column set this skill used in v1.3.0 with the
column set `z-app-documentation` needs so both skills can read the same file):

```
program_name,file_path,language,size_bytes,line_count,status,in_scope
```

- `program_name` — source member name, **upper-case, no extension**, exactly as the mainframe knows it.
- `file_path` — relative to `workspaceRoot`, forward slashes.
- `size_bytes`, `line_count` — measured by the script, never estimated.
- `status` — free-form lifecycle marker (`pending`, etc.); never overwritten once set.
- `in_scope` — this skill always writes `true` for every row (it never scopes to a subset the way
  a partial documentation run can); the column exists so `program-inventory.csv` has one shape
  across the whole skill suite.

Then `00-manifest/extraction-status.csv` (the ledger) — **unchanged from v1.3.0**:

```
program_name,file_path,language,dd_generated,dd_approved,doc_generated,explain_done,zcodescan_done,reviewed_by_sme,batch_id,notes
```

All flag columns start `N`. **The ledger must always have exactly the same `program_name` set as
the inventory.** `build_inventory.py` reconciles both files together and never drops a row from
either; `verify_extraction.py` (Step 15) checks that the two sets stayed identical.

`doc_generated` retains only `Y`/`N`/`E` in v2.0.0 — the `P` (partial) value is retired along with
the Autonomous Fallback Path that produced it. Every `doc_generated=Y` row from here forward means
all three `generate_documentation` perspective calls succeeded for that program, full stop. See
Step 8c and Step 15 for how a workspace carrying legacy `P` rows from a v1.3.0 run is handled.

---

## Step 6 — Governance baseline (first run in a workspace only)

1. If no `AGENTS.md` exists, run `/init` in Z Code mode and copy the result into
   `12-enterprise-standards/AGENTS.md` (the live file stays at the workspace root). `/init` is a
   Bob IDE slash command, not part of the BobZ MCP tool vocabulary — it is invoked the same way it
   always was.
2. Run `/z-coding-standards-skill-builder` against the highest-complexity program identified in
   **Step 11** (code quality). File derived standards into `12-enterprise-standards/coding-standards.md`
   and any generated skill into `12-enterprise-standards/custom-skills/`. Do not wait for the user
   to nominate a program — use complexity rank (highest paragraph count from `complexity-metrics.csv`)
   as the automatic selection criterion. If Step 11 has not yet run, defer this step and record it
   as pending in `extraction-log.md`.
3. Skip steps 1 and 2 if the targets already exist, and state that you skipped them.

---

## Step 7 — Select the batch (Gate G2)

Choose the next batch from ledger rows not yet complete. A program is **complete** when
`dd_generated=Y` **AND** `dd_approved=Y` **AND** `doc_generated=Y` — all three flags, no exceptions.

- **Ceiling: ~100 programs per `generate_documentation` batch.** Split into further batches; never exceed.
- Honor an explicit batch the user named (a list, folder, or glob) over your own selection.
- **Skip any program already complete** (all three flags above). The ledger is the single source of
  truth — never re-derive completeness from the filesystem.
- Assign a `batch_id` (`batch-1`, `batch-2`, …) and record it on every row you touch.

State the batch — count and program names — then proceed immediately without waiting.

---

## Step 8 — Per program: data dictionary → documentation → dependencies

For every program in the batch, call BobZ MCP tools directly, in the order below. **This is an
interactive, turn-by-turn loop** — the agent calls each tool itself, waits for the structured JSON
result, files it, and updates the ledger before moving to the next tool or program. There is no
subtask boundary, no 8-program grouping requirement for documentation, and no distinction anymore
between "the tool ran" and "the agent narrated a plausible substitute" — every call in this step is
the real tool.

### 8a. Pre-call checks — Gate G3

Before the first MCP call of a batch, check once (not once per program):

1. **`bobz/DD.json` must exist.** If it does not, create it immediately:
   ```json
   {"version":"3.0.0","entries":[]}
   ```
   A missing file can cause `get_variables` / `edit_data_dictionary` to raise an interactive
   "multiple data dictionary sources" condition that has no autonomous resolution. This is the
   same precondition v1.3.0 called out before its `start_subtask` calls (its old F11); it now
   applies before the direct `get_variables`/`edit_data_dictionary` calls instead.
2. **The program must be scanned.** If `.bobz/expanded/` or the scanner DB has no entry yet for a
   program, call `scan_program(programId, programPath, databasePath)` first — `get_variables` and
   `get_expanded_source` depend on it.
3. **`databasePath` is always passed explicitly** to every tool that takes it (read from
   `.bobz/local-settings.json` `databaseLocation`) — never omit it; omitting it causes a full
   re-scan.

### 8b. Data dictionary — `get_variables` + `generate_data_dictionary`

**CRITICAL — serial execution required (F1, unchanged).** `get_variables` — and, because both
write into the same SQLite-backed `bobz/DD.json`, `generate_data_dictionary` as well — must be
called **one program at a time, waited-for, then the next.** Parallel calls produce
`UNIQUE constraint failed` errors. This is a hard MCP-server-side constraint, not an artifact of
the retired fallback design — it survives the rewrite unchanged.

For each program, in order:

```
get_variables(
  programId    = "<PROGRAM>",          // upper-case, no extension
  programPath  = "<absolute path>",    // workspaceRoot + "/" + file_path from program-inventory.csv
  databasePath = "<path from .bobz/local-settings.json databaseLocation>"
)
```

`get_variables` returns tool-verified structural entries (WS/Linkage items with PIC, level, usage).

```
generate_data_dictionary(
  programId    = "<PROGRAM>",
  programPath  = "<absolute path>",
  databasePath = "<same path>"
)
```

`generate_data_dictionary` returns business-meaning entries and writes them into `bobz/DD.json`.

**After each successful pair of calls for a program**, immediately append to
`00-manifest/extraction-log.md`:
```
get_variables OK: {PROGRAM} — {timestamp}
generate_data_dictionary OK: {PROGRAM} — {timestamp}
```
This checkpoint is the resumption cursor.

**Resumption rule (F1, unchanged):** If the serial run is interrupted at any point, read
`extraction-log.md` to find the last `... OK: {PROGRAM}` line. Resume from the next program in the
ledger with `dd_generated=N`. Never restart from the beginning — the ledger and log together are
the authoritative resume cursor.

- Copy this program's entries from `bobz/DD.json` into
  `03-data-structures/data-dictionary/by-program/{PROGRAM}-DD.json`.
- Append the same entries into `03-data-structures/data-dictionary/DD-master.json`. If
  `zUnderstandConfigured: true`, call `sync_data_dictionary(databasePath)` to do this
  project-wide reconciliation — it replaces the old hand-assembled merge entirely. If
  `zUnderstandConfigured: false`, merge by hand exactly as before (the tool is absent, not
  degraded — do not approximate it).
- Stamp every entry `status: draft`, mark `dd_generated=Y` on the ledger, and append the entries
  to `17-qa-validation/dd-review-queue.md` as checklist rows (`- [ ] {PROGRAM}.{VARIABLE}`). The
  review gate is completely unaffected by this rewrite — see Approval posture above.
- If either call fails or returns no variables/entries: log the exact error to
  `extraction-log.md`, mark `dd_generated=E`, log a checkpoint line
  `... ERROR: {PROGRAM} — {reason}`, and continue to the next program. Never abort the batch on
  one program's failure.

### 8c. Documentation — `generate_documentation`, three perspectives

For each program, call `generate_documentation` three times, one per perspective. These calls are
independent of the serial `get_variables` constraint, but keep them per-program rather than
batched across programs so one failure never taints the whole batch:

```
generate_documentation(programId, programPath, perspective="business")
generate_documentation(programId, programPath, perspective="architect")
generate_documentation(programId, programPath, perspective="developer")
```

- Strip any conversational preamble before the first `#` heading before filing.
- `business` → `02-business-rules/by-program/{PROGRAM}.md`
- `architect` → `01-application-architecture/{PROGRAM}-arch.md`
- `developer` → `10-error-handling/exception-paths-by-program/{PROGRAM}.md`
- Front-matter every filed file: member name, source path, perspective, workflow
  (`generate_documentation` MCP tool), date.
- Keep native ASCII diagrams as fenced blocks; do not redraw them.
- Mark `doc_generated=Y` only once **all three** perspectives have filed successfully for that
  program. **`doc_generated=P` (partial) is retired in v2.0.0** — there is no fallback path left
  that produces partial documentation, so a program with only some perspectives filed stays
  `doc_generated=N` and is reported as a named incomplete program at Step 15, never silently
  rounded up.
  > **Legacy note — do not delete this paragraph when tidying the file.** A workspace previously
  > extracted under v1.3.0 may still carry `doc_generated=P` rows in its ledger — that value meant
  > "the Autonomous Fallback Path's `start_subtask` narrative ran, but no IBM workflow had
  > confirmed it yet." There is no more automatic P→Y upgrade path, because the mechanism that
  > used to perform that upgrade (a subsequent workflow run superseding the fallback output) no
  > longer exists in this form — `generate_documentation` is now the *only* path, run directly.
  > Treat any `P` row as not-yet-complete and re-run all three `generate_documentation` calls for
  > that program to file it as `Y` directly. `build_report.py` surfaces any such rows separately
  > as `docPartialLegacy` so they are never silently counted as done nor silently lost.
- If any perspective's call errors: log to `extraction-log.md`, mark `doc_generated=E`, continue.

### 8d. Dependencies — provenance label required

Extract the program's dependency list (called programs, copybooks, tables, files, interfaces) from
the `generate_documentation` output and — when `zUnderstandConfigured: true` — from
`get_project_resource_usage` for structurally-verified cross-program usage. Append to
`05-dependencies/internal-dependencies.json`.

**Provenance vocabulary — exactly these three values, never a fourth, never mixed on one entry:**

| Provenance | When |
|---|---|
| `tool-verified` | Content came from an MCP tool call this run, or a deterministic local read (`read_file`/`grep` over JCL, BMS, copybooks, LINKAGE SECTION) performed this run. |
| `narrative-per-program-not-tool-verified` | Content inferred from another tool's narrative output rather than read structurally — e.g. a call graph assembled from `generate_documentation`'s prose, or a dependency list assembled by grepping `CALL '...'` literals rather than resolved by `get_project_resource_usage`. |
| `z-understand-verified` | Content came from a `get_project_*` tool, `impact_analysis`, `implementation_planning`, or `sync_data_dictionary` — only possible when `zUnderstandConfigured: true`. |

This is a narrower, reconciled vocabulary versus v1.3.0's two-value scheme (`tool-verified` /
`narrative-per-program-not-tool-verified`) — the new middle value distinguishes Z
Understand-grounded structural verification from the older "any tool call" bucket. `verify_extraction.py`
(Step 15) checks every entry's provenance against this exact set and flags any entry carrying more
than one value.

Cross-reference names against the inventory. Anything referenced but absent from the inventory →
`17-qa-validation/validation-report.md` as an unresolved reference. Never silently drop it.

### 8e. Post-call verification — Gate G4 (interactive half)

After every MCP call, before moving on:

1. Confirm the tool returned a well-formed structured result, not a transport error.
2. File the artifact immediately — never hold several programs' results in memory before filing.
3. Set the ledger flag for that specific capability (`dd_generated`, `doc_generated`, …) to `Y` or
   `E` — never leave it `N` after a call has actually been made.
4. Log the checkpoint line to `extraction-log.md`.

This is the per-call half of Gate G4. The deterministic half — confirming every `Y` flag is
backed by a real artifact on disk — runs once per batch at Step 15 via `verify_extraction.py`.

---

## Step 9 — Per-program flow and paragraph structure *(optional — run when depth is needed)*

This step is optional. Run it when the user explicitly requests deeper structural analysis or when
Step 11 (code quality) flags a program's complexity above the batch median.

Call these MCP tools directly (no Z Understand required):

- `get_paragraphs(programId, programPath)` — returns paragraph list and line ranges for a program.
- `get_control_flow(programId, programPath)` — returns control flow graph metadata.

> **F10 — tool name correction (unchanged, still enforced):** `zopeneditor-cobol-get-program-control-flow`
> and `zopeneditor-cobol-get-data-flow` are **not valid tool names** and must never be called.
> Use only `get_paragraphs` and `get_control_flow` from the promoted MCP tool vocabulary.

- File paragraph output to `04-code-flow/paragraph-index/{PROGRAM}-paragraphs.json`.
- File control flow output to `04-code-flow/control-flow/{PROGRAM}-cfg.json`.

`04-code-flow/call-graphs/` may only be assembled from Step 8d's dependency data, and only carries
the provenance label that data already has. Never present a narrative call graph as verified.

---

## Step 10 — Language- and artifact-specific passes

Run each sub-pass only if Step 1 found that source type. If a type is absent, confirm the
`notApplicable` README and manifest entry — do not leave the folder bare.

| Source type in scope | Action | Output location |
|---|---|---|
| JCL | Call `generate_documentation` or `explain_code` directly on each file; extract job steps, DD statements, CC logic | `08-jcl-batch/jobs/{JOB}.md`; derive `job-to-program-map.json` and `batch-vs-online-classification.csv` (both provenance-labeled) |
| Copybooks | Derive record layouts from `scan_program`/`get_expanded_source` output + approved dictionary entries | `03-data-structures/copybooks/`, `03-data-structures/record-layouts/` |
| CICS `.csd` / BMS `.bms` (checked into repo) | Read as plain text; cross-walk transaction IDs against program code | `09-cics-ims-transactions/`, `screen-maps/` — provenance `"tool-verified"` (deterministic local read) |
| SQL in COBOL/PL/I programs | Extract per-program table/statement usage from `generate_documentation` output, or from `get_project_tables` when `zUnderstandConfigured: true` | `06-database/sql-usage-by-program/{PROGRAM}-sql.md` |

**Never** query a live DB2/IMS catalog, CICS RDO, or IMS gen. Never infer DDL, constraints, or
triggers. Say plainly that these require tooling outside Bob.

---

## Step 11 — Code quality *(COBOL, PL/I, and HLASM only)*

Skip this step entirely if the scope contains only JCL or copybooks.

**Z Code Scan is now a directly-callable MCP tool: `z_code_scan`.** Call it per-program or as a
batch:

```
z_code_scan(programId="<PROGRAM>", programPath="<path>", databasePath="<path>")
z_code_scan(programIds=[...], programPaths=[...], databasePath="<path>")
```

There is no more UI-invocation requirement and no more agent-callable-tool-name ambiguity — the
old fake names `zcodescan-check-list-of-local-programs` and `zcodescan-check-current-program`
still do not exist and must never be called, but that is now moot since the real tool has a real
name.

File findings to `11-code-quality/zcodescan-findings/{PROGRAM}.json` and roll complexity signals
into `11-code-quality/complexity-metrics.csv` with `source="z-code-scan"`. Mark
`zcodescan_done=Y`.

**Complexity proxy (F5, unchanged trigger logic, updated framing):** if `z_code_scan` itself
errors for a specific program (a real tool-level error now, not a "the UI wasn't available"
condition), fall back to paragraph count from `get_paragraphs` as a complexity proxy **for that
program only** — write it to `complexity-metrics.csv` with `source="sql-paragraph-count"`. Never
present a paragraph-count proxy as `z_code_scan` output; always carry the `source` column so the
two are never confused downstream. Mark `zcodescan_done=E` for that program and log the exact
error.

Use complexity scores to rank the batch by modernization risk — highest = most urgent for deep
analysis. Call `explain_code` directly on the top-ranked programs (at minimum the top 20% by
complexity, or programs explicitly named by the user). File output to `02-business-rules/by-program/`
or `01-application-architecture/` as the content warrants. Mark `explain_done=Y`.

**If `z_code_scan` errors for the whole batch** (not just one program — e.g. the databasePath is
unreachable), record in `extraction-log.md`, mark `zcodescan_done=E` for the affected programs,
and continue. Never block the whole batch on one tool's failure.

---

## Step 12 — Refactoring *(on-demand only — not part of a standard batch)*

This step runs only when the user explicitly requests refactoring. It does **not** execute
automatically as part of Steps 8–11.

`refactor(programId, programPath)` and `generate_refactored_service(programId, programPath, serviceName)`
are directly-callable MCP tools, but whether they work cleanly with `zUnderstandConfigured: false`
is still **unconfirmed** — IBM's own prerequisites are self-contradictory, and the MCP-direct
rewrite does not resolve that ambiguity by itself. If no prior outcome is recorded in
`00-manifest/extraction-log.md`, probe once per workspace on the smallest in-scope program and
record exactly what happens: works fully / errors out / partial / ambiguous.

Record the outcome in `extraction-log.md` with the exact observed behavior. Inform the user in
Step 15. Never report an ambiguous result as clean.

If `refactor` runs successfully, file candidates and any `-service.md` slices into
`15-modernization-mapping/`. Use `generate_refactored_service` for the generated service program
report.

---

## Step 13 — Code quality *(moved — see Step 11)*

> *(This step number is reserved to maintain backward compatibility with earlier run summaries.
> Code quality is documented at Step 11.)*

---

## Step 14 — If asked for impact analysis or an implementation plan

`impact_analysis` and `implementation_planning` are now **directly-callable MCP tools** — but only
when `zUnderstandConfigured: true`. This is the item that changed most under the capability map:
in v1.3.0 they were flatly "unavailable without a Z Understand server"; in v2.0.0 they are
**callable if `zUnderstandConfigured`, else absent** — call them directly:

```
impact_analysis(databasePath, targetMember, targetField?, changeDescription)
implementation_planning(databasePath, goal, scope[])
```

File the returned plan into `14-implementation-plans/` with `provenance: "z-understand-verified"` —
**no downgrade banner needed.** This is first-class, Z Understand-grounded output straight from
the tool, not a reasoning substitute.

If `zUnderstandConfigured: false`, these tools are **absent, not degraded** — do not call them and
do not approximate them with general reasoning framed as if it were their output. Say so plainly.
You may still reason in plain language over the already-extracted documentation and dictionary if
the user explicitly wants a best-effort artifact anyway — but label it explicitly as a downgrade,
exactly as before:

> **⚠ Downgrade notice:** Produced by general reasoning over extracted documentation, NOT by the
> Z Understand-grounded `impact_analysis` / `implementation_planning` MCP tools (unavailable —
> `zUnderstandConfigured: false`). Treat as a preliminary first draft requiring significantly more
> architect scrutiny.

State this caveat in conversation, not just in the file.

---

## Step 15 — Close the batch and report

1. Update every touched ledger row. Set `status` in the inventory for every program processed.

2. **Run `scripts/verify_extraction.py --extraction-root <extractionRoot> --batch-id <batch_id>`
   (Gate G4, deterministic half) before declaring the batch closed.** Exit `0` means every `Y`
   flag in this batch is backed by a real artifact on disk and the inventory/ledger program-name
   sets match; exit `1` means at least one defect was found — fix the ledger or the filing before
   reporting success. **A batch is not closed until this script exits `0`.**

3. **Run `scripts/build_report.py --extraction-root <extractionRoot> --batch-id <batch_id> --date <date>`**
   (pass the exact date from conversation context — never let the script's own system-clock
   fallback stand in for it). This deterministically recomputes `extraction-manifest.json`'s
   `coverage` block **from `extraction-status.csv`**, never from memory or a prior manifest value,
   using these exact counting rules (F4, updated — `docPartial` retired):
   - `ddDone` = count of rows where `dd_generated=Y`
   - `ddApproved` = count of rows where `dd_approved=Y`
   - `docDone` = count of rows where `doc_generated=Y` (there is no more `P` value to exclude —
     `Y` already means all three perspectives filed)
   - `explainDone` = count of rows where `explain_done=Y`
   - `zcodescanDone` = count of rows where `zcodescan_done=Y`
   - `completeProgramCount` = count of rows where ALL of `dd_generated=Y AND dd_approved=Y AND doc_generated=Y`
   - `docPartialLegacy` (informational only, not part of the schema's primary coverage story) =
     count of any residual `doc_generated=P` rows carried over from a pre-v2.0.0 run — reported
     separately so they are visible without being counted as done.
   The script writes `00-manifest/run-history/{date}-{batch_id}-summary.md`, appends to
   `extraction-log.md`, and prints/writes the named list of incomplete programs — the same "never
   a bare percentage" requirement as before.

4. **Reconcile `environment.localScannerMetadata` in the manifest (F3, unchanged):** after any run
   that involves `scan_program` or uses the scanner DB, read `.bobz/local-settings.json` and
   update `environment.localScannerMetadata` to the actual `databaseLocation` path. Never leave it
   as `"none"` after a scan has run.

5. Bump `skillVersion` in the manifest only if the SKILL.md version field changed this run.

6. Report to the user — all items below are required; omitting any is a defect:
   - Mode and approval posture this run ran under.
   - `mcpReachable` and `mcpServerVersion` from the probe file.
   - Programs processed, with per-program pass status (✅ / ⚠ partial / ❌ failed).
   - Coverage as **`<complete>/<inventory total>` plus percentage**, where complete =
     `dd_generated=Y AND dd_approved=Y AND doc_generated=Y`. Report any `docPartialLegacy` count
     separately if non-zero.
   - **Count of dictionary entries in `dd-review-queue.md`** awaiting SME sign-off.
   - **Named list of every program not yet complete** and which specific flag(s) are still `N` or `E`.
   - **Named list of every pass that did not run** and the reason.
   - Any `notApplicable` / `outOfScope` folders touched or confirmed this run.
   - Any errors logged to `extraction-log.md` this run.
   - `verify_extraction.py`'s exit code and defect count for this batch.

A bare percentage with no program list is the one output this skill must never produce.

---

## Scripts

Three scripts under `scripts/` do the skill's deterministic bookkeeping. **None of them ever
calls the BobZ MCP server** — only the agent does that, per Step 8. All three are Python 3,
stdlib only, argparse-based, with the exit-code convention `0` success / `1` a real failure / `2`
bad usage.

### `scripts/build_inventory.py`

```
build_inventory.py [--scope PATH|@FILELIST|INVENTORY.CSV|GLOB]
                    [--workspace-root DIR]      (default: cwd)
                    [--extraction-root DIR]     (default: <workspace-root>/bob-z-knowledge-extract)
                    [--out-dir DIR]             (default: <extraction-root>/00-manifest)
                    [--languages-config FILE]   (default: built-in extension map, Step 1)
                    [--dry-run]                 (print counts, write nothing)
                    [--json]                    (emit summary JSON to stdout)
```

Exit codes: `0` inventory/ledger written or reconciled · `1` no source files found in scope ·
`2` bad usage.

Resolves scope by the same precedence order as Step 1, classifies by extension, and
writes/reconciles `program-inventory.csv` (7-column header, § Step 5) and `extraction-status.csv`
(11-column ledger, unchanged). Reconciling means: add rows for programs newly in scope, never drop
or reorder an existing row, never touch an existing row's `status` or ledger flag columns.

### `scripts/verify_extraction.py`

```
verify_extraction.py --extraction-root DIR
                      [--batch-id ID]           (limit the check to rows carrying this batch_id)
                      [--json]
                      [--check-only]            (evaluate and print the verdict; write nothing)
```

Exit codes: `0` every claimed-complete row is backed by an artifact on disk · `1` at least one
ledger flag has no backing artifact, or the ledger/inventory program-name sets differ · `2` bad
usage.

Checks, per ledger flag:

| Ledger flag | Required artifact |
|---|---|
| `dd_generated=Y` | `03-data-structures/data-dictionary/by-program/{PROGRAM}-DD.json` exists, non-empty `entries` |
| `doc_generated=Y` | `01-application-architecture/{PROGRAM}-arch.md` **and** `02-business-rules/by-program/{PROGRAM}.md` **and** `10-error-handling/exception-paths-by-program/{PROGRAM}.md` all exist |
| `explain_done=Y` | corresponding output filed under `02-business-rules/by-program/` or `01-application-architecture/` |
| `zcodescan_done=Y` | `11-code-quality/zcodescan-findings/{PROGRAM}.json` exists |

Also checks: every dependency entry in `05-dependencies/internal-dependencies.json` carries one of
the three allowed provenance values (Step 8d) and never more than one; `program-inventory.csv`
and `extraction-status.csv` carry identical `program_name` sets. Writes/appends to
`17-qa-validation/validation-report.md` and `00-manifest/verification.json`; never mutates a
ledger flag itself.

### `scripts/build_report.py`

```
build_report.py --extraction-root DIR
                 --batch-id ID
                 [--date YYYY-MM-DD]            (default: today — pass explicitly from
                                                  conversation context; the script's own
                                                  fallback is the system clock, not context)
                 [--json]
                 [--out-file FILE]              (write the rendered report here instead of stdout)
```

Exit codes: `0` report written and manifest coverage recomputed · `1` ledger or manifest missing
or unreadable · `2` bad usage.

Recomputes `extraction-manifest.json`'s `coverage` block **from `extraction-status.csv`**, never
from memory or a prior manifest value, using the exact counting rules in Step 15. Writes
`00-manifest/run-history/{date}-{batch_id}-summary.md`, appends one line to
`extraction-log.md`, and renders the Step 15 report to stdout (or `--out-file`) — always including
the named list of incomplete programs, per-batch pass/fail table, and the dd-review-queue count.

---

## Key Rules

| Rule | Detail |
|---|---|
| **No fallback path exists in v2.0.0** | An unreachable MCP server is a hard stop into PLAN mode at Gate G0, full stop, for every capability in this skill. There is no narrative substitute to fall back to — that mechanism was retired, not deprioritized. |
| **Two claims must never blur** | "We extracted this and found nothing" ≠ "We could not extract this." Every empty folder carries a README saying which it is. |
| **Provenance is mandatory** | Every dependency, call-graph, job-map, and CICS artifact carries exactly one of `tool-verified`, `narrative-per-program-not-tool-verified`, or `z-understand-verified` (Step 8d). Never mix on a single entry. |
| **Never invent tool names** | Use only confirmed MCP tool / sub-skill names from the promoted vocabulary (Step 2a). If a capability can't be named, describe it in plain language and let Bob route it. |
| **MCP output is first-class, not a downgrade** | A `generate_data_dictionary` or `generate_documentation` result is `Y`-flagged the moment it succeeds — there is no more "autonomous fallback, awaiting IBM workflow confirmation" intermediate state. The SME content-review gate (data dictionary `status: draft`) is the only deferral left, and it exists for a reason unrelated to invocation mechanics (see Approval posture). |
| **Tool approval ≠ content approval** | DD entries carry `status: draft` until a human signs off. Deferred review is acceptable; silently skipped review is not. |
| **Ledger is truth** | If the ledger says `Y`, the artifact must exist — `verify_extraction.py` proves it at Step 15. Fix the ledger if it doesn't; never fix the report to hide it. |
| **Resume, do not restart** | Skip programs that are already complete. The ledger drives resumption. |
| **~100 programs per doc batch** | `generate_documentation` batches are capped at ~100 programs (Step 7 / Gate G2). Split into further batches; never exceed. |
| **Preserve member names** | Upper-case, no extension, verbatim in content. Lower-case only in filenames where convention already uses it. |
| **Use context date** | Never invent or approximate a date. Use the date from the conversation context — including when calling `build_report.py --date`. |
| **Idempotent and non-destructive** | Create what is missing. Never overwrite or delete existing artifacts without explicit user confirmation. |
| **Incremental writes** | `write_file` for a skeleton → `apply_diff` per section → one `read_file` at the end to verify. |
| **Tables over prose** | Bullets over paragraphs. No `_(To be filled)_` placeholder survives into a finished artifact. |
| **Dependency completeness caveat** | Narrative-provenance dependency lists cannot be proven complete without Z Understand's `get_project_resource_usage`. State this in any output shared with modernization stakeholders when `zUnderstandConfigured: false`. |
| **Errors are logged, not silenced** | Any MCP tool call failure → `extraction-log.md` + ledger flag `E` + continue. Never abort the batch on a single failure. |
| **Skill version tracking** | The `skillVersion` in `extraction-manifest.json` must match the version in this file's frontmatter. Bump the minor version on any behavioral change; bump major on a breaking rewrite (this v2.0.0 rewrite is exactly that case). |
| **complexity-metrics.csv source label (F5)** | May be populated from paragraph counts (`source="sql-paragraph-count"`) when `z_code_scan` errors for a specific program, OR from `z_code_scan` itself (`source="z-code-scan"`). Always include the `source` column. Never present a paragraph-count proxy as Z Code Scan findings. |
| **`get_variables` is serial and explicit (F1)** | Always pass `databasePath` explicitly. Always call one program at a time. Always log `... OK/ERROR: {PROGRAM}` immediately after each call. On resumption, use the last checkpoint in `extraction-log.md` to find the next program — never restart from scratch. |
| **IBM system copybook warnings (F2)** | `CRRZG5307W` for `CMQ*`, `IMS*`, `DB2*` prefixed copybooks is expected and non-fatal. Log once, note in ledger, do not mark `dd_generated=E`. |
| **`doc_generated=P` is retired, not deleted from history** | `P` is never written by v2.0.0. A `P` row surfacing from a resumed pre-v2.0.0 workspace is not complete, is never counted in `docDone`/`completeProgramCount`, and is surfaced separately as `docPartialLegacy` by `build_report.py` — see Step 8c and Step 15. |
| **Manifest `localScannerMetadata` reconciliation (F3)** | Always update `environment.localScannerMetadata` in the manifest at Step 15 to reflect the current DB path. Never leave it as `"none"` after a scan has run. |
| **Gates are automated checks, not approval prompts** | G0–G4 gate the *correctness* of the run (reachability, scaffold, batch bounds, preconditions, artifact-vs-ledger truth) — they never ask the human for a go-ahead. Only the "pause for approval" phrase and the SME dictionary sign-off are human-in-the-loop by design. |
| **Scripts never call MCP** | `build_inventory.py`, `verify_extraction.py`, and `build_report.py` are pure local file I/O. Only the agent calls MCP tools, one call at a time, per turn. |

---

## Version history

| Version | Change |
|---|---|
| **2.0.0** | **BobZ 3.x MCP-direct rewrite.** Retires the two-tier "Primary path (IBM workflow, UI-invoked)" + "Autonomous Fallback Path" (`get_variables`/`start_subtask`, §8a-alt/§8b-alt) model entirely — every promoted tool (`generate_data_dictionary`, `generate_documentation`, `explain_code`, `z_code_scan`, `get_variables`, `get_control_flow`, `get_paragraphs`, `scan_program`, `get_expanded_source`, `edit_data_dictionary`) is now called directly by the agent, per program, per turn, against a real MCP server. Introduces Gate G0–G4 discipline; adds the MCP reachability probe (`00-manifest/mcp-capability-probe.json`) as the first preflight check. `get_project_*`, `impact_analysis`, `implementation_planning`, `sync_data_dictionary` move from flatly "unavailable" to "callable if `zUnderstandConfigured`, else absent." Retires `doc_generated=P` (partial) — `generate_documentation` success is first-class `Y` immediately; legacy `P` rows from a resumed v1.3.0 workspace are handled explicitly, never silently upgraded or dropped. Reconciles `program-inventory.csv` to a 7-column header (`+line_count,+in_scope`) shared with `z-app-documentation`. Adds three deterministic scripts (`build_inventory.py`, `verify_extraction.py`, `build_report.py`) that do inventory/ledger/coverage bookkeeping from disk state — none of them ever calls MCP. The data-dictionary SME review gate is unchanged: it exists because the content is AI-generated, independent of invocation mechanics. |
| 1.3.0 | Last release under the UI-invocation-only model. Two-tier Autonomous Fallback Path (`get_variables` + `start_subtask`) for Generate data dictionary / Generate documentation when no interactive session is available. |
| 1.1.0 | Folder structure created before scope resolution (Step 3). Approval declaration merged into Step 2. Step 9 (flow/paragraph) made explicitly optional. Z Code Scan scoped to COBOL/PL/I/HLASM only. Error handling (`E` flag) added for workflow failures. Batch-complete definition corrected to require all three flags. Step 15 report requirements made exhaustive. Key Rules converted to table. `argument-hint` added to frontmatter. |
| 1.0.0 | Initial release |
