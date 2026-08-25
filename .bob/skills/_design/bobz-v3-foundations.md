# BobZ v3 Foundations — Single Source of Truth

Design reference for rebuilding `.bob/skills/` around **BobZ version 3.x**, which ships a real
MCP server exposing IBM Bob / Z Premium Package capabilities as directly-callable tools. This
retires the "Autonomous Fallback Path" (`get_variables` + `start_subtask` two-tier workaround)
and the "UI-invocation-only workflow" framing that `cobol-knowledge-extraction` v1.3.0 and
`z-app-documentation` v1.0.0 were built against.

**Every agent building any piece of this suite (`cobol-knowledge-extraction` v2.0.0,
`z-app-documentation` v2.0.0, the new `modernization-pipeline` v1.0.0, `generate-docs` v2.0.0,
`docs-status` v2.0.0, and their companions) must treat this document as authoritative.** Where
this document gives an exact name, column list, JSON key, flag, or exit code, that is the name —
do not rename, reorder, or "improve" it independently. Where it explicitly reconciles a conflict
between two pre-existing files, the reconciliation here wins over either original.

This document is a **promotion of already-documented names into a directly-callable MCP
vocabulary — it invents no tool names.** Every tool in §1 is already named in
`cobol-knowledge-extraction/SKILL.md`'s `AUTO-APPROVAL DECLARATION` and "Derive the capability
map" sections, and in `z-app-documentation`'s evidence-plans.md capability inventory. The only
thing that changes is the invocation surface: these names now resolve to real MCP tool calls
made directly by the agent, on any turn, with no UI session and no `start_subtask` detour.

---

## 0. What changes, in one paragraph

BobZ 3.x's MCP server means every capability that used to require "an interactive session
available" or the two-tier `get_variables`/`start_subtask` fallback is now a normal tool call the
agent makes itself, per program, per turn, with a structured JSON result. There is no more
"Primary path (IBM workflow, UI-invoked)" vs. "Autonomous Fallback Path" split — there is one
path: call the MCP tool, get structured JSON back, file it. `doc_generated=P` (partial,
fallback-authored) as a status is retired along with the fallback it existed to label; documents
and dictionary entries the tool produces are now first-class, `Y`-flagged output straight away
(they still queue for SME review — that gate survives — but they no longer carry a "downgraded
autonomous narrative" caveat). Scripts do the deterministic bookkeeping (inventory, ledger
verification, coverage math, evidence aggregation, document composition); **only the agent calls
the MCP server, and only per turn** — no script in this suite ever makes an MCP call itself.

---

## 1. BobZ MCP tool vocabulary

Two groups: tools that work with no Z Understand server configured, and tools gated on
`zUnderstandConfigured: true` (read from `<workspaceRoot>/.bobz/local-settings.json`, exactly as
today's preflight already does).

### 1a. Always available (`zUnderstandConfigured` irrelevant)

| Tool | Purpose (one line) | Argument shape |
|---|---|---|
| `generate_data_dictionary` | Business-meaning data-dictionary entries for a program; writes into `bobz/DD.json` | `programId`, `programPath`, `databasePath` |
| `generate_documentation` | Narrative documentation from one of three perspectives | `programId`, `programPath`, `perspective: architect\|developer\|business` |
| `explain_code` | Plain-language explanation of a program or a named paragraph | `programId`, `programPath`, `paragraphName?` |
| `z_code_scan` | Static quality/complexity findings, single program or a batch | `programId` or `programIds[]`, `programPath`/`programPaths[]`, `databasePath` |
| `get_variables` | Tool-verified structural extraction: WS/Linkage items with PIC, level, usage; internally drives `edit_data_dictionary` | `programId`, `programPath`, `databasePath` (**always pass explicitly**) |
| `get_control_flow` | Control-flow graph metadata for one program | `programId`, `programPath` |
| `get_paragraphs` | Paragraph list with line ranges | `programId`, `programPath` |
| `scan_program` | Parses/indexes a program into the local scanner DB — prerequisite for `get_expanded_source`/`get_variables` on a program not yet scanned | `programId`, `programPath`, `databasePath` |
| `get_expanded_source` | Copybook-resolved source text (PIC clauses and conditions as the compiler would see them) | `programId`, `programPath`, `databasePath` |
| `edit_data_dictionary` | Directly write/update `DD.json` entries — no longer only reachable through `get_variables`'s internal 3-step workflow | `databasePath`, `entries[]` (`name`, `type`, `shortDescription`, `longDescription`, `status`, `scope[]`) |
| `refactor` | "Simple refactoring" of a single program | `programId`, `programPath` |
| `generate_refactored_service` | Extracts a candidate service-program slice and its report | `programId`, `programPath`, `serviceName` |

`refactor` and `generate_refactored_service` keep the same reliability caveat v1.3.0 recorded:
whether they work cleanly with `zUnderstandConfigured: false` is still unconfirmed IBM-side.
Probe once per workspace on first use, record the exact observed outcome — never assume clean.

### 1b. Requires `zUnderstandConfigured: true`

| Tool | Purpose (one line) | Argument shape |
|---|---|---|
| `get_project_inventory` | Authoritative full-project member inventory from the Z Understand index | `databasePath` |
| `get_project_tables` | DB2/IMS table usage map across the whole project | `databasePath`, `tableName?` |
| `get_project_resource_usage` | Cross-program resource usage (files, tables, copybooks) — the `get_project_*` tool that upgrades a dependency from narrative to structurally verified | `databasePath`, `resourceName?` |
| `impact_analysis` | Change-impact analysis across the project graph | `databasePath`, `targetMember`, `targetField?`, `changeDescription` |
| `implementation_planning` | Generates an implementation plan for a stated modernization goal | `databasePath`, `goal`, `scope[]` |
| `sync_data_dictionary` | Project-wide reconciliation/merge of `DD.json` entries — replaces the old "hand-assembled merge" the fallback needed | `databasePath` |

If `zUnderstandConfigured` is `false`, every tool in §1b is **unavailable** — call none of them,
approximate none of them, and say so plainly in every preflight report. This is unchanged from
v1.3.0's capability map; only §1a's invocation mechanics changed.

---

## 2. Capability probe

Preflight now has one more check than v1.3.0, and it comes first: **is the MCP server reachable
at all?** Everything else in the existing probe (Active mode, Advanced mode, Z Understand
config, local scanner metadata, existing state) is unchanged in substance — only its ordering
relative to the new check changes.

### 2a. Probe order

1. **Resolve/refresh the program inventory** (`build_inventory.py`, §4) if it does not exist yet
   for this scope. The reachability probe needs at least one real `programId`/`programPath` pair
   to call against.
2. **MCP reachability probe** — the agent makes one cheap, real tool call: `get_paragraphs` (or
   `get_control_flow`) against the first program in the freshly built inventory. A response
   (including a well-formed tool-level error about that specific program) proves the server is
   reachable. A connection/transport failure, timeout, or "tool not found" proves it is not.
   Record `mcpProbeMethod`, `mcpProbeLatencyMs`, and whatever server/version string the response
   surfaces (`mcpServerVersion`, or `"unknown"` if the tool result carries none — never invent
   one).
3. **Active mode** — Z Code or Z Architect (unchanged from v1.3.0).
4. **Advanced mode** — required for any skill in this suite to have activated (unchanged).
5. **Z Understand server** — read `<workspaceRoot>/.bobz/local-settings.json`; record
   `zUnderstandConfigured: true|false` (unchanged mechanism).
6. **Local scanner metadata** — does `.bobz/expanded/` or a `ScannerOutput.db` already exist
   (unchanged).
7. **Existing state** — do `AGENTS.md`, `bobz/DD.json`, `bob-z-knowledge-extract/`,
   `bob-z-app-docs/` already exist? Never overwrite blind (unchanged).

### 2b. Failure handling — no fallback path exists anymore

If step 2 fails (MCP unreachable): **drop to PLAN mode immediately.** Report the exact
transport/tool error. Do **not** invoke any per-program narrative fallback, `start_subtask`, or
downgraded output — that mechanism is retired in v2.0.0, not merely deprioritized. An
unreachable MCP server is a stop condition for EXECUTE mode, full stop, in every skill in this
suite.

### 2c. The probe result file

The probe is written by the **agent** (only the agent calls MCP tools) to
`00-manifest/mcp-capability-probe.json`, one per extraction/documentation root. Scripts (§4) read
this file; **no script ever performs the probe itself.**

```json
{
  "probedAt": "2026-08-24T00:00:00Z",
  "mcpReachable": true,
  "mcpProbeMethod": "get_paragraphs(programId=CBACT01C)",
  "mcpProbeLatencyMs": 184,
  "mcpServerVersion": "3.1.0",
  "activeMode": "Z Code",
  "advancedMode": true,
  "zUnderstandConfigured": false,
  "localScannerMetadata": "<databaseLocation from .bobz/local-settings.json>",
  "capabilityMap": {
    "generate_data_dictionary": "available",
    "generate_documentation": "available",
    "explain_code": "available",
    "z_code_scan": "available",
    "get_variables": "available",
    "get_control_flow": "available",
    "get_paragraphs": "available",
    "scan_program": "available",
    "get_expanded_source": "available",
    "edit_data_dictionary": "available",
    "refactor": "unverified",
    "generate_refactored_service": "unverified",
    "get_project_inventory": "unavailable",
    "get_project_tables": "unavailable",
    "get_project_resource_usage": "unavailable",
    "impact_analysis": "unavailable",
    "implementation_planning": "unavailable",
    "sync_data_dictionary": "unavailable"
  }
}
```

`build_coverage.py` in both `cobol-knowledge-extraction` and `z-app-documentation` treats a
missing or `mcpReachable: false` probe file as a hard prerequisite failure (§4).

---

## 3. `evidence-pack.json` schema

The single JSON file `z-app-documentation/scripts/extract_evidence.py` writes and
`generate_docs.py` reads. Because evidence now arrives as structured MCP tool output (DD
entries, docgen JSON, Z Code Scan findings) rather than freeform text, this is a **clean JSON
aggregation** — it does not regex-mine prose the way the AWS Transform-evidence version of this
script does. The only text-parsing this script performs is over artifacts that never went
through an MCP tool in the first place: JCL, BMS maps, and LINKAGE SECTION source, exactly as
today's `cobol-knowledge-extraction` Step 10 already does by hand.

Provenance vocabulary — use **exactly** these three string values anywhere a `provenance` field
appears in `evidence-pack.json` (this is a narrower set than the four-value grounding-contract
vocabulary `z-app-documentation` v1.0.0 inherited from the CAST port; MCP tool output and
read-only source reads are no longer meaningfully different levels of trust, so they collapse
into one value):

| Provenance | When |
|---|---|
| `tool-verified` | Content came from an MCP tool call this run (`get_variables`, `generate_data_dictionary`, `generate_documentation`, `explain_code`, `z_code_scan`, `get_paragraphs`, `get_control_flow`, `scan_program`, `get_expanded_source`) **or** a deterministic local read (`read_file`/`grep` over JCL, BMS, copybooks, LINKAGE SECTION) performed this run. |
| `narrative-per-program-not-tool-verified` | Content inferred from another tool's narrative output rather than read structurally — e.g. a call graph assembled from `generate_documentation`'s prose, or a dependency list assembled by `grep`-ing `CALL '...'` literals rather than resolved by `get_project_resource_usage`. |
| `z-understand-verified` | Content came from a `get_project_*` tool, `impact_analysis`, `implementation_planning`, or `sync_data_dictionary` — only possible when `zUnderstandConfigured: true`. |

### 3a. Top-level shape

```json
{
  "schemaVersion": "1.0",
  "skillVersion": "2.0.0",
  "generatedAt": "2026-08-24T00:00:00Z",
  "workspaceRoot": "…",
  "docsRoot": "…",
  "extractionRoot": "bob-z-knowledge-extract or null if not reused",
  "mcp": {
    "reachable": true,
    "serverVersion": "3.1.0",
    "zUnderstandConfigured": false,
    "probeFile": "00-manifest/mcp-capability-probe.json"
  },
  "programs": { "…": "see §3b, one entry per program_name in program-inventory.csv" },
  "application": { "…": "see §3c" }
}
```

### 3b. `programs.<PROGRAM_NAME>`

```json
{
  "filePath": "app/cbl/CBACT01C.cbl",
  "language": "COBOL",
  "sizeBytes": 4821,
  "dataDictionary": {
    "provenance": "tool-verified",
    "source": "get_variables + generate_data_dictionary",
    "entries": [
      {
        "name": "ACCT-BALANCE",
        "type": "PIC S9(9)V99",
        "shortDescription": "Current account balance",
        "longDescription": "Signed balance carried by the account master record.",
        "status": "draft",
        "scope": [{ "programName": "CBACT01C" }]
      }
    ]
  },
  "businessRules": {
    "provenance": "tool-verified",
    "source": "generate_documentation(perspective=business)",
    "text": "…markdown body, front-matter stripped…"
  },
  "architectureNotes": {
    "provenance": "tool-verified",
    "source": "generate_documentation(perspective=architect)",
    "text": "…"
  },
  "errorHandling": {
    "provenance": "tool-verified",
    "source": "generate_documentation(perspective=developer)",
    "text": "…"
  },
  "explain": {
    "provenance": "tool-verified",
    "source": "explain_code",
    "paragraphs": { "1000-MAIN-PARA": "…narrative…" }
  },
  "codeFlow": {
    "paragraphs": { "provenance": "tool-verified", "source": "get_paragraphs", "items": [] },
    "controlFlow": { "provenance": "tool-verified", "source": "get_control_flow", "graph": {} }
  },
  "dependencies": [
    { "target": "CBACT02C", "kind": "CALL", "provenance": "tool-verified",
      "source": "get_project_resource_usage" },
    { "target": "ACCTFILE-VSAM", "kind": "FILE", "provenance": "narrative-per-program-not-tool-verified",
      "source": "generate_documentation narrative" }
  ],
  "zCodeScan": {
    "provenance": "tool-verified",
    "source": "z_code_scan",
    "findings": [],
    "complexity": 14
  }
}
```

Every leaf object that came from a tool or a read carries its own `provenance` and `source` —
mirroring the "per-document Evidence Index built from artifacts actually read" discipline
`atx-app-documentation/scripts/generate_docs.py` already enforces. A field absent from a
program's entry means it was never produced this run — it must never be backfilled with an
invented value; `generate_docs.py` renders the corresponding heading as unavailable instead.

### 3c. `application` (aggregates)

```json
{
  "jclJobToProgramMap": [
    { "job": "CBACT01J", "step": "STEP010", "invokes": "CBACT01C",
      "provenance": "narrative-per-program-not-tool-verified", "source": "generate_documentation(JCL) + grep" }
  ],
  "complexityRanking": [
    { "programName": "CBACT01C", "complexity": 14, "source": "z_code_scan" }
  ],
  "zCodeScanSummary": {
    "provenance": "tool-verified",
    "programsScanned": 42,
    "findingsTotal": 187,
    "bySeverity": { "high": 6, "medium": 41, "low": 140 }
  },
  "dataDictionaryMaster": {
    "provenance": "tool-verified",
    "path": "bobz/DD.json",
    "entryCount": 512,
    "syncedViaZUnderstand": false
  }
}
```

`extract_evidence.py` never invents an aggregate: `jclJobToProgramMap` is empty (not omitted) if
no JCL is in scope, and its provenance never upgrades to `z-understand-verified` just because
`get_project_resource_usage` happened to answer a *different* program's dependency question.

---

## 4. Script CLI contracts

**No script in this suite ever calls the MCP server.** Only the agent does, once per tool call,
per turn. Scripts are deterministic local file I/O, verification, and reporting exactly like
`atx-app-documentation`'s three scripts — the division of labor is: agent gathers evidence via
MCP tool calls and writes it to a known cache path; scripts build inventories, verify ledger
claims against what actually landed on disk, aggregate the cache into `evidence-pack.json`, and
compose/self-check/file documents from that pack.

Flag/exit-code conventions below match `atx-app-documentation`'s scripts exactly (argparse-style
long flags, `0` success / `1` a real failure / `2` bad usage) so an agent that has only read this
document and the atx scripts can predict behavior correctly.

### 4a. `cobol-knowledge-extraction/scripts/build_inventory.py`

```
build_inventory.py [--scope PATH|@FILELIST|INVENTORY.CSV|GLOB]
                    [--workspace-root DIR]      (default: cwd)
                    [--extraction-root DIR]     (default: <workspace-root>/bob-z-knowledge-extract)
                    [--out-dir DIR]             (default: <extraction-root>/00-manifest)
                    [--languages-config FILE]   (default: built-in extension map, §1 of SKILL.md)
                    [--dry-run]                 (print counts, write nothing)
                    [--json]                    (emit summary JSON to stdout)
```

Exit codes: `0` inventory/ledger written or reconciled · `1` no source files found in scope ·
`2` bad usage.

Behavior: resolves scope by the same precedence order as SKILL.md Step 1 (inventory CSV > file
list > glob > folder > workspace root), classifies by extension, and writes/reconciles
`00-manifest/program-inventory.csv` (§5) and `00-manifest/extraction-status.csv` (§5). Reconcile
means: add rows for programs newly in scope, never drop or reorder an existing row, never touch
an existing row's flag columns. Never calls MCP — pure filesystem walk and classification.

### 4b. `cobol-knowledge-extraction/scripts/verify_extraction.py`

```
verify_extraction.py --extraction-root DIR
                      [--batch-id ID]           (limit the check to rows carrying this batch_id)
                      [--json]
                      [--check-only]            (evaluate and print the verdict; write nothing)
```

Exit codes: `0` every claimed-complete row is backed by an artifact on disk · `1` at least one
ledger flag has no backing artifact, or the ledger/inventory program-name sets differ ·
`2` bad usage.

Checks (a defect in any of these is reported, never silently patched):

| Ledger flag | Required artifact |
|---|---|
| `dd_generated=Y` | `03-data-structures/data-dictionary/by-program/{PROGRAM}-DD.json` exists, non-empty `entries` |
| `doc_generated=Y` | `01-application-architecture/{PROGRAM}-arch.md` **and** `02-business-rules/by-program/{PROGRAM}.md` **and** `10-error-handling/exception-paths-by-program/{PROGRAM}.md` all exist |
| `explain_done=Y` | corresponding explain output filed under `02-business-rules/by-program/` or `01-application-architecture/` |
| `zcodescan_done=Y` | `11-code-quality/zcodescan-findings/{PROGRAM}.json` exists |

Also checks: every dependency entry in `05-dependencies/internal-dependencies.json` carries one
of the three provenance values from §3; `program-inventory.csv` and `extraction-status.csv`
carry identical `program_name` sets. Writes/append to `17-qa-validation/validation-report.md`;
never mutates ledger flags itself — flag correction is the agent's job after reading the report.

### 4c. `cobol-knowledge-extraction/scripts/build_report.py`

```
build_report.py --extraction-root DIR
                 --batch-id ID
                 [--date YYYY-MM-DD]            (default: today, from conversation context — never invented by the script)
                 [--json]
```

Exit codes: `0` report written and manifest coverage recomputed · `1` ledger or manifest missing
or unreadable · `2` bad usage.

Behavior: recomputes `extraction-manifest.json`'s `coverage` block **from
`extraction-status.csv`**, never from memory or from a prior manifest value — same counting rules
SKILL.md Step 15 already specifies (`docPartial` retired along with the fallback path it existed
for; see §0). Writes `00-manifest/run-history/{date}-{batch_id}-summary.md`, appends one line to
`extraction-log.md`, and prints the named list of incomplete programs with their outstanding
flags — the same "never a bare percentage" requirement as today's Step 15.

### 4d. `z-app-documentation/scripts/build_coverage.py`

```
build_coverage.py --workspace-root DIR
                   [--extraction-root DIR]      (default: <workspace-root>/bob-z-knowledge-extract, if present)
                   [--docs-root DIR]            (default: <workspace-root>/bob-z-app-docs)
                   [--probe-file FILE]          (default: <docs-root>/00-manifest/mcp-capability-probe.json)
                   [--out-dir DIR]              (default: <docs-root>/00-manifest)
                   [--json]
                   [--check-only]
```

Exit codes: `0` prerequisites met, `coverage.md` + `evidence-index.json` written · `1` a hard
prerequisite failed · `2` bad usage.

Hard prerequisites (any failure stops, per §2b — no partial run past this gate):

| Check | Requirement |
|---|---|
| Probe file readable | valid JSON, `mcpReachable: true` |
| `program-inventory.csv` | present, ≥1 row |
| Advanced mode | `true` in the probe file |

Soft prerequisites (degrade named plans, continue — mirrors `atx-app-documentation`'s SOFT list):

| Missing | Effect |
|---|---|
| `bob-z-knowledge-extract/` tree | no reuse; every program's evidence pass starts cold |
| `zUnderstandConfigured: false` | `z-integration`/`z-structure` dependency data stays narrative; `get_project_*`-backed plans degrade |

Writes `coverage.md` — one row per program (not per business function; BobZ has no
business-function discovery step) classified `reused-from-extraction` /
`needs-evidence-pass` / `no-source-in-scope` — and `evidence-index.json` with sha256 fingerprints
of every artifact that will feed the evidence pack, exactly as `atx-app-documentation`'s version
does for its own artifacts.

### 4e. `z-app-documentation/scripts/extract_evidence.py`

```
extract_evidence.py --workspace-root DIR
                     [--extraction-root DIR]    (default: <workspace-root>/bob-z-knowledge-extract, if present)
                     --docs-root DIR
                     [--force]                  (re-aggregate even if evidence-pack.json is newer than every input)
```

Exit codes: `0` `evidence-pack.json` written · `1` no `program-inventory.csv` and no cached
evidence of any kind to aggregate · `2` bad usage.

Behavior — **aggregation, not parsing**, for anything that already came from an MCP tool:

1. Read `program-inventory.csv`.
2. For each program, read `00-manifest/mcp-cache/{PROGRAM}/{tool}.json` — the raw MCP tool
   results the **agent** wrote this run (filenames: `docgen-architect.json`,
   `docgen-developer.json`, `docgen-business.json`, `explain.json`, `zcodescan.json`,
   `control-flow.json`, `paragraphs.json`, `variables.json`, `data-dictionary.json` — unchanged
   from `z-app-documentation` v1.0.0's `evidence-cache/{PROGRAM}/…` convention, renamed only from
   `evidence-cache` to `mcp-cache` to reflect that every file in it now comes from a direct tool
   call rather than a mixed workflow/fallback source). A program with no cache file for a given
   tool simply has that field absent from its `evidence-pack.json` entry — never invented.
3. If `bob-z-knowledge-extract/` exists, harvest its already-filed artifacts (`DD-master.json`,
   `02-business-rules/by-program/`, `01-application-architecture/`, `10-error-handling/`,
   `05-dependencies/internal-dependencies.json`, `08-jcl-batch/`, `11-code-quality/`) and carry
   their existing provenance labels forward **unchanged** — never silently upgrade a
   `narrative-per-program-not-tool-verified` entry to `tool-verified` just because it was reused.
4. Parse JCL/BMS/LINKAGE SECTION directly from workspace source with deterministic regex — the
   one legitimate text-mining step, because these artifact types never go through an MCP tool.
5. Write `<docs-root>/00-manifest/evidence-pack.json` per §3.

The script never calls MCP itself; step 2 only ever reads files the agent already wrote.

### 4f. `z-app-documentation/scripts/generate_docs.py`

```
generate_docs.py [--levels 0,1,2]
                  [--only PROMPT_TYPE]
                  [--force]                     (regenerate documents already ledgered complete)
                  [--docs-root DIR]             (default: $BOBZ_DOCS_ROOT or <workspace-root>/bob-z-app-docs)
                  [--app-name NAME]             (default: derived from zapp.yaml / folder name, never invented)
```

Exit codes: `0` every requested document filed · `1` at least one document failed its self-check
(and was **not** filed) · `2` bad usage.

Resolves each heading through the fixed order every builder agent must implement identically:

1. **Hard-unavailable list** — headings matching a fixed set of out-of-scope topics (target-state
   design, ownership/stakeholders, security/CVE, cost, SLA/telemetry, data classification, test
   coverage, RPO/RTO, monitoring dashboards — the BobZ equivalents of
   `atx-app-documentation/scripts/generate_docs.py`'s `HARD_NA` table) are marked unavailable
   before any generic builder gets a chance to answer them.
2. **Scoped builders** — each builder declares the heading topics it owns (data dictionary,
   business rules, architecture/dependencies, JCL/operations, error handling, complexity/quality,
   entry points, etc.), reading from `evidence-pack.json`. A builder may only answer headings in
   its own declared scope.
3. **Substitutions table** (`references/z-substitutions.md`, carried forward unchanged from
   v1.0.0) — for any heading naming a distributed-stack concept with no Z equivalent.
4. **Fallback** — nothing claims the heading: render it with
   `Not available from Z Premium analysis`.

Self-check (blocks filing on failure, exactly like `atx-app-documentation`'s enforced self-check):
Coverage note present, Evidence Index present, every template heading rendered, no dropped
section, every derived artifact provenance-labeled from the exact §3 vocabulary, at least one
artifact recorded as read. A document that fails is reported and **not written**; the batch
continues with the next document. Updates `document-ledger.csv` (§5) and
`00-manifest/generation-log.md` for every document actually filed.

---

## 5. Ledger / manifest field names — identical across both skills

These are the three files whose column names must never diverge between
`cobol-knowledge-extraction` and `z-app-documentation`. Two of the three already exist verbatim
in the current SKILL.md files; carry every existing column name forward **unchanged**. One of
the three (`program-inventory.csv`) exists today with **two different, conflicting column sets**
in the two skills' SKILL.md files — that conflict is reconciled below by unioning every existing
column name from both, in the order given. Do not drop any column that existed in either
original file.

### 5a. `program-inventory.csv` — reconciled, used by both skills

v1.3.0 (`cobol-knowledge-extraction`) had: `program_name,file_path,language,size_bytes,status`
v1.0.0 (`z-app-documentation`) had: `program_name,file_path,language,size_bytes,line_count,in_scope`

**Canonical header, going forward, for both skills:**

```
program_name,file_path,language,size_bytes,line_count,status,in_scope
```

- `program_name` — upper-case, no extension, exactly as the mainframe knows it.
- `file_path` — relative to `workspaceRoot`, forward slashes.
- `size_bytes`, `line_count` — measured, never estimated.
- `status` — free-form lifecycle marker used by `cobol-knowledge-extraction` (`pending`, etc.).
- `in_scope` — boolean marker used by `z-app-documentation` to note whether a discovered member
  is inside the resolved document-generation scope for the current run (a member can be in the
  inventory but out of scope for a partial `L5`-only run, for instance).

Both skills' `build_inventory.py` / inventory-building step must emit and reconcile against this
exact 7-column header. Neither skill drops the other's column even when it never populates it
meaningfully (`cobol-knowledge-extraction` still writes `in_scope=true` for every row it creates,
since it never scopes to a subset the way `z-app-documentation`'s `L0`-only runs can).

### 5b. `extraction-status.csv` — `cobol-knowledge-extraction`'s ledger, carried forward unchanged

```
program_name,file_path,language,dd_generated,dd_approved,doc_generated,explain_done,zcodescan_done,reviewed_by_sme,batch_id,notes
```

Unchanged from v1.3.0. `z-app-documentation`'s Step 5c reuse logic reads this file when
`bob-z-knowledge-extract/` exists, so both skills must agree on these exact column names for that
reuse to work at all. `doc_generated` retains only `Y`/`N`/`E` values in v2.0.0 — the `P`
(partial) value is retired along with the Autonomous Fallback Path that produced it (§0); every
`doc_generated=Y` row from here forward means a direct `generate_documentation` MCP call
succeeded, full stop.

### 5c. `document-ledger.csv` — `z-app-documentation`'s ledger, carried forward unchanged

```
doc_key,level,scope,feature_name,z_plan,output_path,evidence_gathered,generated,self_check_passed,reviewed,batch_id,run_date,notes
```

Unchanged from v1.0.0. A document is complete when `evidence_gathered=Y` AND `generated=Y` AND
`self_check_passed=Y` — `reviewed` stays a separate, non-blocking SME dimension, exactly as
today.

---

## 6. `template-families.md` format (new file for `z-app-documentation`)

`z-app-documentation/references/prompts/*.md` are the **same 31 templates**, ported verbatim from
the same origin CAST service that `atx-app-documentation`'s prompts came from — they are byte-for-
byte the same section-set shapes, just living in a different skill folder. This means the family
classification `atx-app-documentation/references/template-families.md` already worked out does
not need to be rediscovered by reading the AWS original; it can be **rederived directly from
`z-app-documentation`'s own existing `references/prompts/*.md` files**, because those files carry
the exact same `OUTPUT STRUCTURE` blocks, bold-label lines, or absence thereof.

Build `z-app-documentation/references/template-families.md` with this exact structure so
`generate_docs.py`'s parser and the reference-file author agree on format without either reading
the other's output:

### 6a. Required structure

1. **A "The three families" table**, exactly these three rows, in this column order:
   `Family | Count | How the section set is expressed | How to extract`.
   - **Family A — output structure** (4 templates): section set is an `OUTPUT STRUCTURE` block of
     markdown `##` headings. Extraction rule: take the `##` headings after the literal string
     `OUTPUT STRUCTURE`, strip any leading `N.` numbering, drop any heading that is a
     `{placeholder}`.
   - **Family B — bold labels** (24 templates): section set is bold labels at line start.
     Extraction rule: regex `^\*\*(.+)\*\*$`, strip a trailing `:`, reject any match containing a
     second `**` (inline `Label:** value` fragments) or longer than 70 characters.
   - **Family C — stub** (3 templates): the origin template supplies no output structure at all.
     Extraction rule: use a fixed, declared section set (below) rather than parsing anything.
2. **A "Family A members" section** naming the 4 templates in this family (verify against the
   actual prompt files rather than assuming the AWS original's list transfers unchanged — but as
   ported, they are: `application_inventory`, `as_is_assessment`, `executive_summary`,
   `stakeholder_analysis`).
3. **A "Family B members" section** — "the remaining 24" — with a one-sentence note that a
   template can contain bold strings that are *not* section headings (inline value labels), and
   that Family A must be tested before Family B for exactly this reason.
4. **A "Family C members and their declared section sets" section.** For each of the 3 stub
   templates (`business_capabilities`, `business_features`, `architecture_decisions`), declare a
   fixed, numbered section list. These are editorial decisions, carried forward **verbatim** from
   `atx-app-documentation/references/template-families.md` (§39–62 of that file) since they exist
   to restore determinism to the same underlying stub templates, not to reinterpret them for Z:

   **`business_capabilities`**: Capability Inventory · Capability to Business Function Mapping ·
   Current State Assessment · Capability Gaps · Modernization Impact per Capability · Open
   Questions

   **`business_features`**: Feature Inventory · Feature to Entry Point Mapping · Feature
   Ownership · Feature Dependencies · Open Questions

   **`architecture_decisions`**: Decision Log · Context and Drivers · Decisions Evidenced by the
   Codebase · Consequences · Decisions Deferred to Forward Engineering · Open Questions

5. **A "Duplicate headings within one template" section** — same rule as the AWS-evidence
   version: when two headings in one template legitimately resolve to the same evidence, emit it
   once and cross-reference with: `See **<heading>** above — the same evidence answers this
   heading. Repeating it here would add no information.` The heading still renders; only the body
   is deduplicated.

### 6b. Parser contract this file must satisfy

`generate_docs.py`'s `fixed_sets()` equivalent parses Family C section lists by regex against
this file: a bold `**`prompt_type`**` line immediately followed by a numbered list. Whoever
writes `template-families.md` must format the three Family C entries exactly that way — a bold
inline-code prompt-type name as its own line, then `1.`, `2.`, `3.`… on the following lines with
no blank line in between — or the parser finds nothing and every stub document silently gets an
empty section set instead of the declared one.

---

## 7. Package/publish design — `modernization-pipeline` (new orchestrator skill)

No AWS anywhere in this skill: no S3, no presigned URLs, no IAM ARNs, no bucket policies. The
`modernization-pipeline` skill is the BobZ analog of `atx-pipeline` — a guided wrapper that walks
nine phases with a gate at each decision point, driving `cobol-knowledge-extraction` and
`z-app-documentation` end to end inside the local IDE workspace only.

### 7a. The nine phases

| # | Phase | Needs MCP | What it does |
|---|---|---|---|
| 1 | `preflight` | yes | MCP reachability probe, mode checks, capability map (§2) |
| 2 | `extract` | yes | Run `cobol-knowledge-extraction` batch(es): DD, docgen, dependencies, per program, via direct MCP calls |
| 3 | `extract-verify` | no | `verify_extraction.py` gate (§4b) over the extraction ledger |
| 4 | `reuse-snapshot` | no | Index `bob-z-knowledge-extract/` artifacts + sha256 fingerprints for `z-app-documentation` reuse |
| 5 | `coverage` | no | `build_coverage.py` (§4d) — prerequisite gate + per-program coverage matrix |
| 6 | `evidence` | no | `extract_evidence.py` (§4e) — one pass, aggregate `evidence-pack.json` |
| 7 | `generate` | no | `generate_docs.py` (§4f) — compose, self-check, file |
| 8 | `package` | no | Zip the run folder + disclosure scan (§7c); refuse to produce the zip on a hit |
| 9 | `publish` | no | Optional copy to a user-named local or network path — no expiry, no signing |

Phases 5–9 need no MCP call at all. When the MCP server is down but a
`bob-z-knowledge-extract/` tree already exists, `--offline-docs` (documenting an existing
extraction without touching MCP again) is the fast path, exactly as `atx-pipeline --offline`
skips its AWS-only phases when `.atx/mfre/` is already populated.

### 7b. Gates (A–D, adapted from `atx-pipeline`)

**Gate A — before phase 1.** Confirm scope (path, file list, inventory CSV, or glob) and that
`workspaceRoot` is unambiguous (per `cobol-knowledge-extraction` Step 1's multi-root check). State
that Advanced mode is required. Run `--dry-run` first and show the plan before touching anything.

**Gate B — after phase 3 (`extract-verify`).** Report complete-of-inventory programs — the
per-program analog of `atx-pipeline`'s "delivered-of-discovered business functions". Name every
program that is not `dd_generated=Y AND dd_approved=Y AND doc_generated=Y`, and which flag is
still outstanding. A partial extraction is a normal, reportable outcome — never let it pass
silently into phase 5, because every downstream document would then describe a fraction of the
codebase while reading like it describes all of it.

**Gate C — after phase 5 (`coverage`).** Show the per-program coverage matrix before generating.
If coverage is low, ask whether to generate the documentation suite at all — 31 thin,
mostly-unavailable documents are a worse outcome than an honest gap report and a recommendation
to run more extraction batches first.

**Gate D — before phase 9 (`publish`).** The disclosure gate — always runs, whether or not the
user asked to publish anywhere:

- Zip the run folder (`bob-z-knowledge-extract/` and/or `bob-z-app-docs/`, per what the user
  scoped) only after the disclosure scan (§7c) passes clean.
- There is no "public" concept and no expiry concept: `publish` is always a copy to a path the
  user names explicitly — a local folder or a network share the IDE's filesystem can already
  reach. There is no bucket, no ACL, no signing key, and therefore nothing to default to public by
  accident.
- State plainly, before copying, what the archive contains: business rules, the data dictionary
  (including `status: draft` entries not yet SME-approved), program and JCL names, and any
  complexity/quality findings — the same class of disclosure `atx-pipeline`'s Gate D calls out for
  its own documents, minus anything AWS-specific.

### 7c. Disclosure scan (replaces the AWS-ARN/access-key scan)

`modernization-pipeline`'s package phase runs a local pattern scan over every file about to enter
the zip and **refuses to produce the archive** if any pattern hits — the same refuse-don't-warn
posture `atx-app-documentation/scripts/run_pipeline.sh`'s package phase already takes, with AWS
identity patterns swapped for generic secret/credential patterns (there are no AWS ARNs to catch
in a local-IDE artifact tree):

| Pattern | Catches |
|---|---|
| `(?i)password\s*[:=]\s*\S+` | Hard-coded passwords |
| `(?i)(api[_-]?key\|secret)\s*[:=]\s*\S+` | API keys, secrets |
| `-----BEGIN (RSA\|EC\|OPENSSH )?PRIVATE KEY-----` | Embedded private keys |
| `(?i)(user\s*id\|uid)\s*=.*password\s*=` | DB2/ODBC-style connection strings carrying credentials |
| `(?i)bearer\s+[A-Za-z0-9\-_.]{20,}` | Bearer tokens |
| `(?i)jdbc:[a-z0-9]+://[^;]*password=` | JDBC connection strings with an embedded password |

On a hit: print every match (`file: pattern-label`), delete any partially-written zip, and stop —
same as `atx-app-documentation`'s package phase refusing on an IAM ARN or access-key hit. Never
downgrade a hit to a warning.

---

## 8. Skill version numbers

| Skill | Was | Becomes | Why |
|---|---|---|---|
| `cobol-knowledge-extraction` | 1.3.0 | **2.0.0** | Breaking behavioral rewrite — the Autonomous Fallback Path (`get_variables` + `start_subtask`, §8a-alt/§8b-alt) is retired; every workflow tool is now called directly per §1 |
| `z-app-documentation` | 1.0.0 | **2.0.0** | Breaking behavioral rewrite — converts from prose-driven generation to script-driven (`build_coverage.py`/`extract_evidence.py`/`generate_docs.py`, §4d–4f); evidence source changes from mixed workflow/narrative to structured MCP JSON |
| `modernization-pipeline` | *(new)* | **1.0.0** | New orchestrator skill, first release |
| `generate-docs` | 1.0.0 | **2.0.0** | Companion command to `z-app-documentation`; bump in lockstep since its behavior depends entirely on the skill it wraps |
| `docs-status` | 1.0.0 | **2.0.0** | Same reason — reports against the v2.0.0 ledger/manifest shape |

`extract-batch` and `extract-status` (the companion command skills for
`cobol-knowledge-extraction`, currently unversioned in their frontmatter) should gain
`metadata.version: 2.0.0` alongside `cobol-knowledge-extraction` for the same lockstep reason,
even though this was not explicitly called out — leaving them unversioned while their underlying
skill jumps a major version is the kind of drift this document exists to prevent.

Every manifest's `skillVersion` field must be copied from its own `SKILL.md` frontmatter at run
time, exactly as the existing `F6` schema note in `cobol-knowledge-extraction/SKILL.md` already
requires — never hardcoded, never left stale after a version bump.
