---
name: cobol-knowledge-extraction
description: Use when extracting, documenting, or cataloging knowledge from a mainframe COBOL, PL/I, JCL, REXX, or Assembler codebase for modernization — builds a versioned bob-z-knowledge-extract knowledge base using only native Bob IDE + Z Premium Package for Z workflows (Generate documentation, Generate data dictionary, Explain code, Z Code Scan). Works against any project given as a folder path, a file list, an inventory CSV, a glob, or the open workspace. Activate when the user asks to extract knowledge, document a legacy application, catalog business rules, build a modernization knowledge base, run an extraction batch, or mentions "bob-z-knowledge-extract", "knowledge extraction", or "extraction ledger".
metadata:
  version: 1.3.0
  argument-hint: '[path|file-list|inventory.csv|glob] [--dry-run]'
---

# COBOL Knowledge Extraction

Runs a disciplined, repeatable, resumable knowledge-extraction process over a mainframe codebase and
files every artifact into a `bob-z-knowledge-extract/` tree. Project-agnostic: nothing about a
specific application, folder layout, or naming convention is assumed — scope and environment are
resolved at Steps 1 and 2 every run.

This skill sequences IBM-shipped Bob workflows where they are available. Where workflows require
interactive UI invocation (Generate data dictionary, Generate documentation, Explain code, Z Code
Scan), the skill uses the **Autonomous Fallback Path** defined in Step 8a-alt and Step 8b-alt — a
two-tier approach using `get_variables` (tool-verified structural extraction) and `start_subtask`
(AI-generated business descriptions and documentation). Output from both paths is filed identically;
provenance labels distinguish the source.

**Future path**: An MCP server wrapping the Z Open Editor extension API would restore full workflow
invocation without UI interaction. Until that server exists, the autonomous fallback path is
authoritative for non-interactive runs.

---

## Run modes

| Mode | When | Behavior |
|---|---|---|
| **PLAN** | User passes `--dry-run`, says "plan only", "what would you do", or any Step 2 preflight check fails | Produce the full plan and the manifest, write **no** artifacts, change **no** ledger rows |
| **EXECUTE** | Default — proceed autonomously as soon as preflight passes | Run the batch, write artifacts, update the ledger. Do not wait for confirmation. |

Always state which mode you are in as the first line of your response.

---

## Approval posture

**This skill is fully autonomous. No human approval is required at any point — not for tool calls,
not for skill activations, not for file writes, not for workflow invocations.**

All approvals are declared upfront in Step 2 and are irrevocable for the session. There are no
interactive gates, no "go-ahead" prompts, and no per-step confirmation requests anywhere in the
process.

One content gate survives — it is a **deferred review gate, not an interactive prompt**:

- **Data dictionary business meanings** — entries are filed as `status: draft` and queued in
  `17-qa-validation/dd-review-queue.md`. They are excluded from the completeness count until a
  human signs them off asynchronously. The skill never pauses for this; it reports the queue size
  in Step 15 and continues.

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
`notApplicable` entry in the manifest (Step 3), never a silently empty folder.

State the resolved scope back to the user as a short table, then continue immediately to Step 2.

---

## Step 2 — Declare all approvals and check the environment

### 2a — Upfront approval declaration

Emit this block exactly once at the start of every EXECUTE run. After emitting it, never ask for
approval again for the duration of this session.

```
AUTO-APPROVAL DECLARATION
=========================
All of the following are pre-approved for the entirety of this extraction run.
No further confirmation will be requested.

FILE SYSTEM OPERATIONS
  write_file        — create or overwrite any file under extractionRoot
  insert_content    — append to any file under extractionRoot
  apply_diff        — patch any file under extractionRoot
  list_files        — list any directory in the workspace
  read_file         — read any file in the workspace
  glob / grep       — search for files or content anywhere in the workspace
  execute_command   — read-only shell commands (find, wc, stat, python3 scripts)
                      for inventory sizing and JSON stamping only

WORKFLOWS (IBM-shipped — invoked when interactive session available)
  Generate data dictionary
  Generate documentation   (architect, developer, business perspectives)
  Explain code
  Z Code Scan              (batch or per-file variant)
  Refactor / Generate refactored service program  (on-demand only — see Step 12)

AUTONOMOUS FALLBACK PATH (used when workflows are not interactively available)
  Option 1 — get_variables    : structural DD extraction (tool-verified)
  Option 2 — start_subtask    : AI business descriptions + documentation per 8-program group
  Both options run without human confirmation; output is provenance-labelled and queued for review.

EDITOR TOOLS
  get_control_flow, get_paragraphs
  zopeneditor-cobol-get-program-control-flow, zopeneditor-cobol-get-data-flow
  edit_data_dictionary, scan_program, get_variables, get_expanded_source

SUB-SKILL ACTIVATIONS
  data-dictionary-workflow, docgen-workflow, explain-workflow
  refactor-workflow, refactor-code-generation-workflow

LEDGER AND MANIFEST WRITES
  extraction-status.csv, program-inventory.csv, extraction-manifest.json,
  extraction-log.md, run-history/

SUBTASKS (Option 2 — autonomous documentation)
  start_subtask     — one subtask per 8-program group; each subtask reads source,
                      generates docs, and returns a structured filing summary.

Revoking this declaration requires the user to send the message: "pause for approval".
```

### 2b — Preflight: probe the environment

Bob's capability map depends on the installed version and on whether a Z Understand server is
configured. Probe it every run and record what you find.

Check, and report as a table with an explicit value for each row:

1. **Active mode** — Z Code or Z Architect.
2. **Advanced mode** — required for this skill to have activated at all; its absence is the most
   common silent failure.
3. **Z Understand server** — read `<workspaceRoot>/.bobz/local-settings.json`. A `databaseLocation`
   pointing at a local `ScannerOutput.db` with no server URL = local-scanner mode. Record
   `zUnderstandConfigured: true|false`.
4. **Local scanner metadata** — does `.bobz/expanded/` or a `ScannerOutput.db` already exist?
5. **Existing state** — do `AGENTS.md`, `bobz/DD.json`, `docs/explain/`, or `extractionRoot`
   already exist? Never overwrite them blind.

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

These warnings are **language-server-only** — they do not prevent `get_variables`, SQL queries, or `scan_program` from working. The extraction continues normally; the only effect is that MQ/IMS/DB2 structure field names will not appear as variables for the affected programs.

Derive the capability map:

| Capability | If `zUnderstandConfigured` is false |
|---|---|
| `/init`, Generate data dictionary, Generate documentation, Explain code, Z Code Scan, control-/data-flow tools | available |
| `/impact-analysis`, `/implementation-planning`, `/sync-data-dictionary`, every `get_project_*` tool, "Extract relevant sections of code" | **unavailable** — state this plainly; never approximate |
| Simple refactoring, Generate refactored service program | **unverified** — see Step 12 |

If a capability you expected to be unavailable turns out to be present (or vice versa), record the
finding in `00-manifest/extraction-log.md` and tell the user.

**Preflight fails** — drop to PLAN mode — if the workspace root is ambiguous, no source files were
found in scope, or the user's named input does not exist. In PLAN mode, write no artifacts and make
no ledger changes.

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

## Step 4 — Finalise the scaffold and write the manifest

1. **Update placeholder READMEs** — replace the "Pending" text with the correct `notApplicable` or
   `outOfScope` reason now that scope is known. Folders that will receive content: remove their
   placeholder README or leave it absent. Never delete a README that already carries real content.

2. **Write `00-manifest/extraction-manifest.json`**:

```json
{
  "schemaVersion": "1.0",
  "skillVersion": "<copy from SKILL.md frontmatter version field — never hardcode>",
  "generatedAt": "<exact date from conversation context>",
  "workspaceRoot": "<resolved>",
  "extractionRoot": "<resolved>",
  "inputMode": "workspace|folder|file-list|inventory-csv|glob",
  "scope": { "sourceRoots": [], "languagesPresent": [], "languagesAbsent": [] },
  "environment": {
    "activeMode": "", "advancedMode": true, "zUnderstandConfigured": false,
    "localScannerMetadata": "<path from .bobz/local-settings.json — never leave as 'none' after scan>",
    "bobIdeVersion": "", "zPremiumVersion": ""
  },
  "capabilityMap": {},
  "batches": [],
  "coverage": {
    "inventoryCount": 0, "ddDone": 0, "ddApproved": 0,
    "docDone": 0, "docPartial": 0,
    "explainDone": 0, "zcodescanDone": 0, "completeProgramCount": 0
  },
  "approvalPosture": "auto-approved",
  "notApplicable": [],
  "outOfScope": []
}
```

> **Schema note (F6):** `skillVersion` must always be copied from the SKILL.md `version` field at
> run time — never hardcoded. `docPartial` counts `doc_generated=P` rows; `docDone` counts
> `doc_generated=Y` rows only. These two fields are always reported separately.

Every folder that will stay empty gets a `README.md` stating which case applies and why. An
unexplained empty folder is a defect: it falsely implies "we extracted this and found nothing."

Seed these `outOfScope` entries every run — they hold in all environments:

- `06-database/schema/`, `06-database/constraints-and-triggers.md` — DB2/IMS DDL; requires DBA tooling outside Bob.
- `06-database/table-usage-map.json` — requires `get_project_tables`; Z Understand unavailable.
- `13-impact-analysis/` — requires `/impact-analysis`.
- `14-implementation-plans/` — requires `/implementation-planning`; see Step 14 for the fallback.

---

## Step 5 — Build the inventory (this is the denominator)

Without a Z Understand project there is no `get_project_inventory`. The inventory is the only
denominator every completeness number is measured against. Build it from the Step 1 scope.

Write `00-manifest/program-inventory.csv`, one row per source file, header exactly:

```
program_name,file_path,language,size_bytes,status
```

- `program_name` — source member name, **upper-case, no extension**, exactly as the mainframe knows it.
- `file_path` — relative to `workspaceRoot`, forward slashes.
- `status` — `pending` initially.

Then write `00-manifest/extraction-status.csv` (the ledger):

```
program_name,file_path,language,dd_generated,dd_approved,doc_generated,explain_done,zcodescan_done,reviewed_by_sme,batch_id,notes
```

All flag columns start `N`. **The ledger must always have exactly the same `program_name` set as the
inventory.** If the inventory already exists, reconcile: add rows for new programs, never drop a row.

---

## Step 6 — Governance baseline (first run in a workspace only)

1. If no `AGENTS.md` exists, run `/init` in Z Code mode and copy the result into
   `12-enterprise-standards/AGENTS.md` (the live file stays at the workspace root).
2. Run `/z-coding-standards-skill-builder` against the highest-complexity program identified in
   **Step 11** (code quality). File derived standards into `12-enterprise-standards/coding-standards.md`
   and any generated skill into `12-enterprise-standards/custom-skills/`. Do not wait for the user
   to nominate a program — use complexity rank (highest paragraph count from `complexity-metrics.csv`)
   as the automatic selection criterion. If Step 11 has not yet run, defer this step and record it
   as pending in `extraction-log.md`.
3. Skip steps 1 and 2 if the targets already exist, and state that you skipped them.

---

## Step 7 — Select the batch

Choose the next batch from ledger rows not yet complete. A program is **complete** when
`dd_generated=Y` **AND** `dd_approved=Y` **AND** `doc_generated=Y` — all three flags, no exceptions.

- **Ceiling: ~100 programs per Generate documentation run.** Split into further batches; never exceed.
- Honor an explicit batch the user named (a list, folder, or glob) over your own selection.
- **Skip any program already complete** (all three flags above). The ledger is the single source of
  truth — never re-derive completeness from the filesystem.
- Assign a `batch_id` (`batch-1`, `batch-2`, …) and record it on every row you touch.

State the batch — count and program names — then proceed immediately without waiting.

---

## Step 8 — Per program: data dictionary → documentation → dependencies

**Execution level clarification (F12):** Step 8 operates at two levels simultaneously:

- **Tier 1 (`get_variables`)** — strictly per-program, one at a time, serial. This is the innermost loop.
- **Tier 2 (`start_subtask` documentation)** — per-group of ≤ 8 programs. After all Tier 1 calls for
  a group are complete, fire one `start_subtask` for that group. Never fire a subtask for a program
  before its Tier 1 `get_variables` call has completed (or been marked `E`).

The ordering rule *"for each program, run in this exact order"* means: complete Tier 1 for a group
first, then run Tier 2 for that same group. Do not interleave Tier 1 and Tier 2 across groups.

### 8a. Data dictionary — Primary path (IBM workflow)

**Detecting interactive session availability (F13):** The IBM Generate data dictionary workflow is
UI-invoked only. It cannot be triggered programmatically by the agent. Treat this path as
**unavailable** in all non-interactive (autonomous) runs. The test is simple:

- If the user has explicitly run the workflow in this session and confirmed output → primary path available.
- Otherwise → primary path unavailable; proceed directly to §8a-alt.

Do not attempt to call the workflow programmatically. Do not wait or retry. Fall through to §8a-alt immediately.

If the primary path is confirmed available, run the **Generate data dictionary** workflow (or the
`data-dictionary-workflow` skill).

The workflow writes a single root `bobz/DD.json`. **Copy** this program's entries into
`03-data-structures/data-dictionary/by-program/{PROGRAM}-DD.json`. Append the same entries into
`03-data-structures/data-dictionary/DD-master.json` (hand-assembled merge — `/sync-data-dictionary`
is unavailable). Do not truncate or move the root `bobz/DD.json`; Bob owns it.

**If the workflow errors or produces no output**, record the failure in `00-manifest/extraction-log.md`
with the exact error message, mark the program's `dd_generated=E` (Error) in the ledger, and
fall through to the **Autonomous Fallback Path** below. Do not abort the batch.

Mark `dd_generated=Y` on workflow success, then stamp all entries `status: draft` and proceed to
§8a-alt step 3 (review queue).

### 8a-alt. Data dictionary — Autonomous Fallback Path (Option 1 + Option 2)

Use this path when the Generate data dictionary workflow is not interactively available (the default
in all autonomous runs), or when `dd_generated=E` from the primary path. This path runs **fully
autonomously** — no human steps.

**Pre-condition check (F11):** Before firing any `start_subtask` call, verify that `bobz/DD.json`
exists. If it does not exist, create it immediately:
```json
{"version":"3.0.0","entries":[]}
```
A missing `bobz/DD.json` causes the subtask to trigger an interactive "multiple data dictionary
sources" prompt, which defeats autonomous operation. This pre-condition must be checked once before
the first subtask of every run — not per-group.

**Tier 1 — Option 1: `get_variables` (structural DD, tool-verified)**

**CRITICAL — Serial execution required.** `get_variables` writes to a shared SQLite database.
Parallel calls cause `UNIQUE constraint failed` errors. Call exactly **one program at a time**,
wait for the tool response, then call the next. Never batch or parallelize this tool.

Call `get_variables` for the program:

```
get_variables(
  programId   = "<PROGRAM>",          // upper-case, no extension
  programPath = "<absolute path>",    // workspaceRoot + "/" + file_path from program-inventory.csv
  databasePath = "<path from .bobz/local-settings.json databaseLocation>"
                                      // ALWAYS pass explicitly — omitting causes re-scan
)
```

**After each successful call**, immediately append one line to `00-manifest/extraction-log.md`:
```
get_variables OK: {PROGRAM} — {timestamp}
```
This checkpoint enables precise resumption after any interruption.

**Resumption rule (F1):** If the serial run is interrupted at any point, read `extraction-log.md`
to find the last `get_variables OK: {PROGRAM}` line. Resume from the next program in the ledger
with `dd_generated=N`. Never restart from the beginning — the ledger and log together are the
authoritative resume cursor.

- If `get_variables` succeeds: the tool runs a built-in 3-step workflow (select top 15 business
  variables → expand abbreviations → call `edit_data_dictionary` → writes to `bobz/DD.json`).
  Let the workflow complete fully before calling the next program. Then log the checkpoint.
- If `get_variables` fails or returns no variables: log the exact error to `extraction-log.md`,
  mark `dd_generated=E` in the ledger, log a checkpoint line `get_variables ERROR: {PROGRAM} — {reason}`,
  and continue to the next program. Tier 2 can still produce descriptions using source-read only.

**Tier 2 — Option 2: `start_subtask` (AI descriptions + documentation)**

Group programs into batches of **≤ 8**. For each group, call `start_subtask` with:

- **title**: `"CardDemo extraction: {PROGRAM_LIST} — DD descriptions + documentation"`
- **mode**: `"z-code"`
- **todos**: the per-program checklist below
- **message**: the exact subtask instruction block defined in §8a-alt/subtask-spec below

**Subtask instruction block (§8a-alt/subtask-spec)**:

```
You are running as part of the cobol-knowledge-extraction skill (v1.3.0) for the CardDemo
workspace at: {workspaceRoot}

Your job: for each program in the list below, (a) read the source file, (b) generate AI
business descriptions for the top variables identified by get_variables (or all Working-Storage
01-level items if get_variables was not run), (c) produce structured documentation.

PROGRAMS TO PROCESS: {PROGRAM_LIST}

For EACH program, produce output in this EXACT format — no preamble, no commentary outside
the tagged blocks. Bob will parse these blocks to file the artifacts.

---
PROGRAM: {PROGRAM}
SOURCE: {file_path}

DD_ENTRIES:
[
  {
    "name": "<VARIABLE-NAME>",
    "type": "<PIC clause or group>",
    "shortDescription": "<5-10 word business label>",
    "longDescription": "<1-2 sentence business meaning>",
    "origin": "AI",
    "status": "draft",
    "scope": [{"programName": "{PROGRAM}"}]
  }
]
Include the top 15 most business-significant variables (01-level WS items, key FD fields,
88-level condition names that represent business states). Do not include filler, counters,
or internal flags unless they have clear business meaning.

BUSINESS_RULES:
---
member: {PROGRAM}
source_path: {file_path}
perspective: business
workflow: source-read + AI (autonomous fallback — cobol-knowledge-extraction v1.3.0)
date: {date}
origin: AI — requires SME review
---
# {PROGRAM} — Business Rules
[2-4 paragraph summary of what this program does in business terms]
## Key Business Rules
[Bullet list of 5-10 specific business rules found in the code]
## Data Processed
[What data the program reads, updates, creates, or deletes — business names not technical]
## Error Conditions
[What causes this program to reject, abort, or raise an error in business terms]

ARCHITECTURE_NOTES:
---
member: {PROGRAM}
source_path: {file_path}
perspective: architect
workflow: source-read + AI (autonomous fallback — cobol-knowledge-extraction v1.3.0)
date: {date}
origin: AI — requires SME review
---
# {PROGRAM} — Architecture Notes
## Program Type
[Batch / CICS online / Utility / Sub-program]
## Entry Points and Paragraph Flow
[Top-level paragraph and its immediate descendants — table form]
## Files and Resources Accessed
[Table: Logical name | Access type | Copybook]
## Called Programs
[List of CALL / XCTL targets with linkage type]
## Error Handling
[ABEND paragraphs, CICS HANDLE CONDITION, file status checks]

ERROR_HANDLING:
---
member: {PROGRAM}
source_path: {file_path}
perspective: developer
workflow: source-read + AI (autonomous fallback — cobol-knowledge-extraction v1.3.0)
date: {date}
origin: AI — requires SME review
---
# {PROGRAM} — Exception Paths
## ABEND Conditions
[List conditions that trigger ABEND or CEE3ABD]
## CICS Error Handling
[RESP/RESP2 checks, HANDLE CONDITION, PGMIDERR — if CICS program]
## File I/O Error Handling
[FILE STATUS checks and response actions]
## Input Validation
[Business validation rules that reject or flag bad input]
---
END_PROGRAM: {PROGRAM}

After processing all programs, return ONLY the tagged blocks above. Do not add
summaries, explanations, or commentary outside the blocks.
```

**After the subtask returns**: parse each tagged block and file as follows:

| Tag | File destination | Ledger flag |
|---|---|---|
| `DD_ENTRIES` | `03-data-structures/data-dictionary/by-program/{PROGRAM}-DD.json` (merge with Tier 1 structural data if present) | `dd_generated=Y` |
| `BUSINESS_RULES` | `02-business-rules/by-program/{PROGRAM}.md` | `doc_generated=P` (partial until workflow run) |
| `ARCHITECTURE_NOTES` | `01-application-architecture/{PROGRAM}-arch.md` | (same) |
| `ERROR_HANDLING` | `10-error-handling/exception-paths-by-program/{PROGRAM}.md` | (same) |

Append all DD entries to `03-data-structures/data-dictionary/DD-master.json`.
Append all DD entries to `17-qa-validation/dd-review-queue.md` as checklist rows.
Leave `dd_approved=N`. The `doc_generated` flag uses `P` (partial) when produced by this
fallback path — it becomes `Y` only after an IBM workflow run confirms or replaces the content.

**If a subtask errors or returns malformed output**: log the error with the exact message,
mark `dd_generated=E` and `doc_generated=E` for the affected programs, continue to the next group.
Never abort the batch on a single subtask failure.

### 8b. Documentation — Primary path (IBM workflow)

If an interactive session is available, run the **Generate documentation** workflow (`docgen-workflow`)
requesting all three perspectives: architect, developer, business.

**If the workflow errors**, record in `extraction-log.md`, mark `doc_generated=E`, and continue.

On success:

- Strip any conversational preamble before the first `#` heading before filing.
- File business-rules content → `02-business-rules/by-program/{PROGRAM}.md`
- File system-level structure content → `01-application-architecture/{PROGRAM}-arch.md`
- File error-handling content → `10-error-handling/exception-paths-by-program/{PROGRAM}.md`
- Front-matter every filed Markdown file: member name, source path, perspective, workflow, date.
- Keep native ASCII diagrams as fenced blocks; do not redraw them.
- Mark `doc_generated=Y` (upgrading from `P` if the autonomous fallback already ran).

### 8b-alt. Documentation — Autonomous path

The `start_subtask` call in §8a-alt already produces BUSINESS_RULES, ARCHITECTURE_NOTES, and
ERROR_HANDLING blocks. No separate step is needed. `doc_generated=P` is set by §8a-alt filing.
It remains `P` until an IBM workflow run sets it to `Y`.

### 8c. Dependencies — provenance label required

Extract the program's dependency list (called programs, copybooks, tables, files, interfaces) from
the documentation and append to `05-dependencies/internal-dependencies.json`.

**Every entry produced by the autonomous path must carry
`"provenance": "narrative-per-program-not-tool-verified"`.** Entries from `get_variables` or SQL
queries carry `"provenance": "tool-verified"`. Never mix provenance labels on a single entry.

Cross-reference names against the inventory. Anything referenced but absent from the inventory →
`17-qa-validation/validation-report.md` as an unresolved reference. Never silently drop it.

---

## Step 9 — Per-program flow and paragraph structure *(optional — run when depth is needed)*

This step is optional. Run it when the user explicitly requests deeper structural analysis or when
Step 11 (code quality) flags a program's complexity above the batch median.

Use these confirmed editor tools (no Z Understand required):

- `get_paragraphs` — returns paragraph list and line ranges for a program.
- `get_control_flow` — returns control flow graph metadata.

> **F10 — tool name correction:** `zopeneditor-cobol-get-program-control-flow` and
> `zopeneditor-cobol-get-data-flow` are **not valid tool names** and must never be called.
> Use only `get_paragraphs` and `get_control_flow` from the confirmed tool manifest.

- File paragraph output to `04-code-flow/paragraph-index/{PROGRAM}-paragraphs.json`.
- File control flow output to `04-code-flow/control-flow/{PROGRAM}-cfg.json`.

`04-code-flow/call-graphs/` may only be assembled from Step 8c's narrative dependencies. Apply
the same provenance label and never present it as a verified graph.

---

## Step 10 — Language- and artifact-specific passes

Run each sub-pass only if Step 1 found that source type. If a type is absent, confirm the
`notApplicable` README and manifest entry — do not leave the folder bare.

| Source type in scope | Action | Output location |
|---|---|---|
| JCL | Run Generate documentation or Explain on each file; extract job steps, DD statements, CC logic | `08-jcl-batch/jobs/{JOB}.md`; derive `job-to-program-map.json` and `batch-vs-online-classification.csv` (both provenance-labeled) |
| Copybooks | Derive record layouts from copybook scans + approved dictionary entries | `03-data-structures/copybooks/`, `03-data-structures/record-layouts/` |
| CICS `.csd` / BMS `.bms` (checked into repo) | Read as plain text; cross-walk transaction IDs against program code | `09-cics-ims-transactions/`, `screen-maps/` — provenance `"read-from-checked-in-source"` |
| SQL in COBOL/PL/I programs | Extract per-program table/statement usage from documentation output | `06-database/sql-usage-by-program/{PROGRAM}-sql.md` |

**Never** query a live DB2/IMS catalog, CICS RDO, or IMS gen. Never infer DDL, constraints, or
triggers. Say plainly that these require tooling outside Bob.

---

## Step 11 — Code quality *(COBOL, PL/I, and HLASM only)*

Skip this step entirely if the scope contains only JCL or copybooks.

**F9 — Z Code Scan invocation:** Z Code Scan is a UI-invoked IBM workflow, identical in nature to
Generate documentation. There are **no agent-callable tool names** for Z Code Scan
(`zcodescan-check-list-of-local-programs` and `zcodescan-check-current-program` do not exist and
must never be called). Invoke Z Code Scan using the **Z Code Scan** workflow from the Bob IDE
command palette. If an interactive session is not available, record `zcodescan_done=E` for all
programs in the batch and log: `"Z Code Scan not available in autonomous run — UI invocation required"`.

When Z Code Scan results are available (from a prior UI run), file findings to
`11-code-quality/zcodescan-findings/{PROGRAM}.json` and roll complexity signals into
`11-code-quality/complexity-metrics.csv` with `source="z-code-scan"`. Mark `zcodescan_done=Y`.

**Autonomous complexity proxy:** When Z Code Scan has not run, use paragraph count from
`get_paragraphs` as a complexity proxy. Write results to `complexity-metrics.csv` with
`source="sql-paragraph-count"`. This is sufficient to rank programs for modernization risk ordering
but must never be presented as Z Code Scan output.

Use complexity scores to rank the batch by modernization risk — highest = most urgent for deep
analysis. Run the `explain-workflow` on the top-ranked programs (at minimum the top 20% by
complexity, or programs explicitly named by the user). File output to `02-business-rules/by-program/`
or `01-application-architecture/` as the content warrants. Mark `explain_done=Y`.

**If Z Code Scan errors or is unavailable**, record in `extraction-log.md`, mark `zcodescan_done=E`,
and continue. Never block the batch on Z Code Scan availability.

---

## Step 12 — Refactoring *(on-demand only — not part of a standard batch)*

This step runs only when the user explicitly requests refactoring. It does **not** execute
automatically as part of Steps 8–11.

Whether Simple refactoring works without a Z Understand server is **unconfirmed** — IBM's own
prerequisites are self-contradictory. If `zUnderstandConfigured` is false and no prior outcome is
recorded in `00-manifest/extraction-log.md`, proceed automatically on the smallest in-scope program
and record exactly what happens: works fully / errors out / partial / ambiguous.

Record the outcome in `extraction-log.md` with the exact observed behavior. Inform the user in
Step 15. Never report an ambiguous result as clean.

If Refactor runs successfully, file candidates and any `-service.md` slices into
`15-modernization-mapping/`. Use the `refactor-code-generation-workflow` for the generated service
program report.

---

## Step 13 — Code quality *(moved — see Step 11)*

> *(This step number is reserved to maintain backward compatibility with earlier run summaries.
> Code quality is documented at Step 11.)*

---

## Step 14 — If asked for impact analysis or an implementation plan

`/impact-analysis` and `/implementation-planning` are unavailable without a Z Understand server.
You may reason in plain language over the already-extracted documentation and dictionary — but label
this explicitly as a downgrade. File it into `14-implementation-plans/` prefixed with this banner:

> **⚠ Downgrade notice:** Produced by general reasoning over extracted documentation, NOT by the
> Z Understand-grounded `impact-analysis` / `implementation-planning` skills. Treat as a
> preliminary first draft requiring significantly more architect scrutiny.

State this caveat in conversation, not just in the file.

---

## Step 15 — Close the batch and report

1. Update every touched ledger row. Set `status` in the inventory for every program processed.
2. **Recompute `coverage` in the manifest from the ledger — never from memory.** Use these exact
   counting rules (F4):
   - `ddDone` = count of rows where `dd_generated=Y`
   - `ddApproved` = count of rows where `dd_approved=Y`
   - `docDone` = count of rows where `doc_generated=Y` (not `P` — partial does NOT count)
   - `docPartial` = count of rows where `doc_generated=P` (add this field to the manifest schema)
   - `explainDone` = count of rows where `explain_done=Y`
   - `zcodescanDone` = count of rows where `zcodescan_done=Y`
   - `completeProgramCount` = count of rows where ALL of `dd_generated=Y AND dd_approved=Y AND doc_generated=Y`
   A program with `doc_generated=P` is **not complete**. Never count `P` rows in `docDone` or
   `completeProgramCount`.
3. **Reconcile `environment.localScannerMetadata` in the manifest (F3):** after any run that
   involves `scan_program` or uses the scanner DB, read `.bobz/local-settings.json` and update
   `environment.localScannerMetadata` to the actual `databaseLocation` path. Never leave it as
   `"none"` after a scan has run.
4. Bump `skillVersion` in the manifest only if the SKILL.md version field changed this run.
5. Append a run entry to `00-manifest/extraction-log.md` and
   `00-manifest/run-history/{date}-{batch_id}-summary.md`: mode, posture, batch id, programs
   processed, capability findings, errors encountered, anything skipped and why.
6. Report to the user — all items below are required; omitting any is a defect:
   - Mode and approval posture this run ran under.
   - Programs processed, with per-program pass status (✅ / ⚠ partial / ❌ failed).
   - Coverage as **`<complete>/<inventory total>` plus percentage**, where complete = `dd_generated=Y`
     AND `dd_approved=Y` AND `doc_generated=Y`. Report `docPartial` count separately.
   - **Count of dictionary entries in `dd-review-queue.md`** awaiting SME sign-off.
   - **Named list of every program not yet complete** and which specific flag(s) are still `N` or `E`.
   - **Named list of every pass that did not run** and the reason.
   - Any `notApplicable` / `outOfScope` folders touched or confirmed this run.
   - Any errors logged to `extraction-log.md` this run.

A bare percentage with no program list is the one output this skill must never produce.

---

## Key Rules

| Rule | Detail |
|---|---|
| **Two claims must never blur** | "We extracted this and found nothing" ≠ "We could not extract this." Every empty folder carries a README saying which it is. |
| **Provenance is mandatory** | Every dependency, call-graph, job-map, and CICS artifact carries `"provenance": "narrative-per-program-not-tool-verified"`. Tool-verified entries from `get_variables` or SQL carry `"provenance": "tool-verified"`. Never mix on a single entry. |
| **Never invent tool names** | Use only confirmed tool/workflow/skill names. If a capability can't be named, describe it in plain language and let Bob route it. |
| **Autonomous fallback is not a substitute** | §8a-alt output is labelled `origin: AI`, `status: draft`, `doc_generated=P`. It never upgrades to `Y` without an IBM workflow confirmation. State this in every report. |
| **Tool approval ≠ content approval** | DD entries carry `status: draft` until a human signs off. Deferred review is acceptable; silently skipped review is not. |
| **Ledger is truth** | If the ledger says `Y`, the artifact must exist. Fix the ledger if it doesn't; never fix the report to hide it. |
| **Resume, do not restart** | Skip programs that are already complete. The ledger drives resumption. |
| **~8 programs per subtask** | The §8a-alt subtask ceiling is 8 programs. Split into further subtask calls; never exceed. |
| **~100 programs per doc run** | For IBM workflow runs, split batches; never exceed. |
| **Preserve member names** | Upper-case, no extension, verbatim in content. Lower-case only in filenames where convention already uses it. |
| **Use context date** | Never invent or approximate a date. Use the date from the conversation context. |
| **Idempotent and non-destructive** | Create what is missing. Never overwrite or delete existing artifacts without explicit user confirmation. |
| **Incremental writes** | `write_file` for a skeleton → `apply_diff` per section → one `read_file` at the end to verify. |
| **Tables over prose** | Bullets over paragraphs. No `_(To be filled)_` placeholder survives into a finished artifact. |
| **Dependency completeness caveat** | This process cannot prove completeness without Z Understand. State this in any output shared with modernization stakeholders. |
| **Errors are logged, not silenced** | Any workflow failure or subtask failure → `extraction-log.md` + ledger flag `E` + continue. Never abort the batch on a single failure. |
| **Skill version tracking** | The `skillVersion` in `extraction-manifest.json` must match the version in this file's frontmatter. Bump the minor version on any behavioral change to the skill. |
| **complexity-metrics.csv source label (F5)** | `complexity-metrics.csv` may be populated from SQL paragraph counts (batch-1) OR from Z Code Scan output (Step 11). Always include a `source` column with value `"sql-paragraph-count"` or `"z-code-scan"`. Never present SQL-derived paragraph counts as Z Code Scan findings — they are different metrics. |
| **`get_variables` is serial and explicit (F1)** | Always pass `databasePath` explicitly. Always call one program at a time. Always log `get_variables OK/ERROR: {PROGRAM}` immediately after each call. On resumption, use the last checkpoint in `extraction-log.md` to find the next program — never restart from scratch. |
| **IBM system copybook warnings (F2)** | `CRRZG5307W` for `CMQ*`, `IMS*`, `DB2*` prefixed copybooks is expected and non-fatal. Log once, note in ledger, do not mark `dd_generated=E`. |
| **`doc_generated=P` ≠ done (F4)** | Partial (`P`) means autonomous fallback ran. It never counts as `docDone` or `completeProgramCount`. These counters require `Y` only. |
| **Manifest `localScannerMetadata` reconciliation (F3)** | Always update `environment.localScannerMetadata` in the manifest at Step 15 to reflect the current DB path. Never leave it as `"none"` after a scan has run. |
| **MCP server future path** | A future MCP server wrapping the Z Open Editor extension API will restore full workflow invocation. When available, the primary path (§8a, §8b) takes precedence; the autonomous fallback (§8a-alt, §8b-alt) becomes secondary. Artifacts produced by the fallback path are upgradeable in-place: re-run with the MCP server present, overwrite with `doc_generated=Y`. |
