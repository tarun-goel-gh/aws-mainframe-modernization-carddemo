---
name: z-app-documentation
description: Use when generating the full application documentation suite for a mainframe application — the 31 documents across 9 levels (discovery, business context, business documentation, technical, design, data, integration, operations, modernization) — using only native Bob IDE + Z Premium Package workflows (Generate documentation, Generate data dictionary, Explain code, Z Code Scan). Produces a versioned bob-z-app-docs knowledge base with an evidence-grounded, resumable, ledger-tracked pipeline. Activate when the user asks to generate application documentation, produce a modernization document set, build an as-is assessment, document business rules or data lineage, generate an executive summary or migration roadmap, or mentions "bob-z-app-docs", "documentation suite", "9-level documentation", or "document ledger".
metadata:
  version: 1.0.0
  argument-hint: '[all|L0..L8|<prompt_type>] [path|inventory.csv|glob] [--dry-run]'
---

# Z Application Documentation Suite

Generates a complete, evidence-grounded application documentation set — **31 documents across
9 levels** — from a mainframe codebase, using only IBM-shipped Bob capabilities.

This skill is a port of the CAST integration service's documentation generator
(`services/cast-integration`). The prompt catalog, grounding contract, determinism rules and
evidence-plan mechanism are carried over 1:1. The **evidence source is different**: the
service used a CAST Imaging MCP server; this skill uses the **Z Premium Package workflows and
the source members in the workspace**. There is no CAST MCP dependency anywhere.

This skill adds **no documentation capability**. Bob's workflows are IBM-shipped; this skill
sequences them, enforces grounding, caches evidence, files output, maintains the ledger, and
reports honestly what could not run. It must never substitute a capability that is unavailable.

---

## Reference files — read on demand, not upfront

| File | Read when |
|---|---|
| `references/grounding-contract.md` | **Always**, before writing any document. Non-negotiable. |
| `references/document-catalog.md` | Step 1 and Step 7 — the 31 documents, levels, plans and output paths. |
| `references/evidence-plans.md` | Step 8, before running a document's evidence pass. |
| `references/z-substitutions.md` | Step 8, whenever a template names a distributed-stack concept. |
| `references/prompts/<n>-<prompt_type>.md` | Step 8, one per document being generated. |

Never load all 31 prompt files at once. Load the one you are generating.

---

## Run modes

| Mode | When | Behavior |
|---|---|---|
| **PLAN** | User passes `--dry-run`, says "plan only", "what would you do", or any Step 2 preflight check fails | Produce the full plan, the manifest and the ledger preview; write **no** documents, change **no** ledger rows |
| **EXECUTE** | Default — proceed autonomously as soon as preflight passes | Run the batch, write documents, update the ledger. Do not wait for confirmation. |

Always state which mode you are in as the first line of your response.

---

## Approval posture

**This skill is fully autonomous. No human approval is required at any point** — not for tool
calls, not for skill activations, not for file writes under `docsRoot`, not for workflow
invocations.

All approvals are declared upfront in Step 2 and are irrevocable for the session. There are no
interactive gates and no per-step confirmation requests.

Two content gates survive. Both are **deferred review gates, not interactive prompts**:

- **Data dictionary business meanings** — filed `status: draft`, queued in
  `17-qa-validation/dd-review-queue.md`, excluded from the completeness count.
- **Business-level assertions** (capabilities, stakeholders, personas, requirements) — filed
  with an `Assumption — not tool-verified` label and queued in
  `17-qa-validation/business-review-queue.md`.

State `EXECUTE — auto-approved posture, content review deferred to queues` as the opening line
of every EXECUTE run. The only revocation trigger is a user message containing the phrase
**"pause for approval"**.

---

## Step 1 — Resolve scope and inputs

Never assume the scope. Resolve two things: **which source** and **which documents**.

### 1a — Source scope

| # | Input form | How to interpret |
|---|---|---|
| 1 | An inventory CSV path (`*.csv` with a `program_name` column) | Authoritative program list; use rows as-is |
| 2 | An explicit list of files, or `@`-referenced files | Exactly those programs |
| 3 | A glob (e.g. `LGA*.cbl`) | Expand within the resolved source roots |
| 4 | A folder path | All recognized source files under it, recursively |
| 5 | Nothing given | The currently open workspace root |

Then resolve and **record**:

1. **`workspaceRoot`** — the folder the IDE has open. If Bob artifacts (`.bob/`, `.bobz/`,
   `bobz/`, `docs/explain/`) appear at more than one level of the path, stop and ask which
   root to use. Do not guess — the ledger denominator depends on it.
2. **`docsRoot`** — `<workspaceRoot>/bob-z-app-docs`, unless the user names another.
3. **`applicationName`** — the name the documents are titled with. Take it from, in order:
   the user's words, `zapp.yaml`, the repository folder name. State which source you used.
4. **`sourceRoots`** — discover them; do not expect any particular folder name. If
   `zapp.yaml` or a `.zapp/` property group exists, read it: `libraries.locations` tells you
   where copybooks resolve from and hints where source lives.
5. **`languagesPresent` / `languagesAbsent`** — classify by extension, case-insensitively:
   COBOL `.cbl .cob .cobol` · copybook `.cpy .copy` · PL/I `.pli .pl1` · include `.inc` ·
   JCL `.jcl .prc .proc` · REXX `.rex .rexx` · HLASM `.asm .hlasm .mlc` · CICS `.csd` ·
   BMS `.bms`. Record every language found **and every one not found**.

### 1b — Document scope

Read `references/document-catalog.md`. Resolve the document argument:

| Argument | Meaning |
|---|---|
| *(none)* or `all` | All 31 documents, levels 0 → 8 in order |
| `L0` … `L8` | Every document at that level |
| `L0-L3` | A level range |
| A `prompt_type` (e.g. `data_lineage`) | Exactly that document |
| Several `prompt_type`s | Exactly those, generated in catalog order |

Three documents are **feature-scoped** (`business_features`, `feature_catalog`,
`business_rules`) — they need a `feature_name` and produce one file per feature. If no
features are known yet, run `business_features` first; its output becomes the feature list.

State the resolved scope back as a short table, then continue immediately to Step 2.

---

## Step 2 — Declare all approvals and check the environment

### 2a — Upfront approval declaration

Emit this block exactly once at the start of every EXECUTE run.

```
AUTO-APPROVAL DECLARATION
=========================
All of the following are pre-approved for the entirety of this documentation run.
No further confirmation will be requested.

FILE SYSTEM OPERATIONS
  write_file        — create or overwrite any file under docsRoot
  insert_content    — append to any file under docsRoot
  apply_diff        — patch any file under docsRoot
  list_files        — list any directory in the workspace
  read_file         — read any file in the workspace
  glob / grep       — search for files or content anywhere in the workspace
  execute_command   — read-only shell commands (find, wc, stat, python3)
                      for inventory sizing and JSON stamping only

WORKFLOWS (IBM-shipped, Z Premium Package)
  Generate documentation   (architect, developer, business perspectives)
  Generate data dictionary
  Explain code
  Z Code Scan              (batch or per-file variant)

EDITOR TOOLS
  get_control_flow, get_paragraphs, get_variables, get_expanded_source, scan_program
  zopeneditor-cobol-get-program-control-flow, zopeneditor-cobol-get-data-flow

SUB-SKILL ACTIVATIONS
  docgen-workflow, data-dictionary-workflow, explain-workflow

LEDGER AND MANIFEST WRITES
  document-ledger.csv, program-inventory.csv, documentation-manifest.json,
  generation-log.md, evidence-cache/, run-history/

NO application source file is ever modified. Writes are confined to docsRoot.
Revoking this declaration requires the user to send: "pause for approval".
```

### 2b — Preflight: probe the environment

Probe every run and report as a table with an explicit value for each row:

1. **Active mode** — Z Code or Z Architect.
2. **Advanced mode** — required for this skill to have activated at all.
3. **Z Understand server** — read `<workspaceRoot>/.bobz/local-settings.json`. A
   `databaseLocation` pointing at a local `ScannerOutput.db` with no server URL = local-scanner
   mode. Record `zUnderstandConfigured: true|false`.
4. **Local scanner metadata** — does `.bobz/expanded/` or a `ScannerOutput.db` already exist?
5. **Existing state** — do `AGENTS.md`, `bobz/DD.json`, `docs/explain/`,
   `bob-z-knowledge-extract/` or `docsRoot` already exist? Never overwrite them blind.
   If `bob-z-knowledge-extract/` exists, **reuse its artifacts as evidence** (see Step 5c) —
   that tree was produced by the `cobol-knowledge-extraction` skill and is already grounded.

Derive the capability map:

| Capability | If `zUnderstandConfigured` is false |
|---|---|
| `/init`, Generate documentation, Generate data dictionary, Explain code, Z Code Scan, control-/data-flow tools | available |
| `/impact-analysis`, `/implementation-planning`, `/sync-data-dictionary`, every `get_project_*` tool | **unavailable** — state plainly; never approximate |
| ISO-5055 scoring, CVE mapping, portfolio quality roll-up | **unavailable in all configurations** — these came from CAST in the original service and have no Z Premium equivalent |

**Preflight fails** — drop to PLAN mode — if the workspace root is ambiguous, no source files
were found in scope, the named input does not exist, or the requested `prompt_type` is not in
the catalog.

---

## Step 3 — Create the output tree

Idempotent: create what is missing, never overwrite or delete existing content.

```
bob-z-app-docs/
  00-manifest/                    run-history/, evidence-cache/
  L0-discovery/
  L1-business-context/
  L2-business-documentation/      business-features/, feature-catalog/
  L3-technical-documentation/
  L4-design/
  L5-data/
  L6-integration/
  L7-operations/
  L8-modernization/
  17-qa-validation/
```

For any folder that cannot receive content yet, create a placeholder `README.md`:

```
# <folder-name>
Pending — reason will be recorded after scope resolution.
```

Update these in Step 4. Never delete an existing README that carries real content.

---

## Step 4 — Write the manifest

Write `00-manifest/documentation-manifest.json`:

```json
{
  "schemaVersion": "1.0",
  "skillVersion": "1.0.0",
  "generatedAt": "<exact date from conversation context>",
  "workspaceRoot": "<resolved>",
  "docsRoot": "<resolved>",
  "applicationName": "<resolved>",
  "applicationNameSource": "user|zapp.yaml|folder-name",
  "inputMode": "workspace|folder|file-list|inventory-csv|glob",
  "documentScope": "all|L0-L8|<prompt_type list>",
  "scope": { "sourceRoots": [], "languagesPresent": [], "languagesAbsent": [] },
  "environment": {
    "activeMode": "", "advancedMode": true, "zUnderstandConfigured": false,
    "localScannerMetadata": "", "bobIdeVersion": "", "zPremiumVersion": ""
  },
  "capabilityMap": {},
  "evidenceCache": { "programsWithDocgen": 0, "programsWithExplain": 0,
                     "programsWithZCodeScan": 0, "ddGenerated": false },
  "batches": [],
  "coverage": {
    "documentsPlanned": 0, "documentsGenerated": 0, "documentsPartial": 0,
    "documentsFailed": 0, "documentsReviewed": 0,
    "ddEntriesQueued": 0, "businessAssumptionsQueued": 0
  },
  "approvalPosture": "auto-approved",
  "provenanceSummary": {},
  "notApplicable": [],
  "outOfScope": []
}
```

Seed these `outOfScope` entries every run — they hold in all environments:

- **ISO 5055 characteristic scoring, CVE mapping, portfolio quality insights** — supplied by
  CAST in the original service; no Z Premium equivalent.
- **DB2/IMS DDL, constraints, triggers, indexes, catalog statistics** — require DBA tooling
  outside Bob.
- **Runtime telemetry, SLA/uptime metrics, live scheduler state, SMF data** — no runtime feed.
- **Container / cloud deployment configuration** — not present on Z unless checked in.
- **Impact analysis and implementation planning** — require a Z Understand server.

Every folder that will stay empty gets a `README.md` stating whether it is `notApplicable`
(nothing of this kind exists) or `outOfScope` (exists, but could not be extracted) and why.
An unexplained empty folder is a defect: it falsely implies "we looked and found nothing."

---

## Step 5 — Build the inventories (these are the denominators)

### 5a — Program inventory

Write `00-manifest/program-inventory.csv`, one row per source member:

```
program_name,file_path,language,size_bytes,line_count,in_scope
```

`program_name` = member name, **upper-case, no extension**. `file_path` relative to
`workspaceRoot`, forward slashes. Reconcile with an existing file rather than replacing it.

### 5b — Document ledger

Write `00-manifest/document-ledger.csv` — the single source of truth for completeness:

```
doc_key,level,scope,feature_name,z_plan,output_path,evidence_gathered,generated,self_check_passed,reviewed,batch_id,run_date,notes
```

One row per planned document (31 for `all`, plus one extra row per feature for each of the
three feature-scoped documents). All flag columns start `N`.

A document is **complete** when `evidence_gathered=Y` **AND** `generated=Y` **AND**
`self_check_passed=Y`. `reviewed` is a separate SME dimension and never blocks completeness.

Use `E` for a pass that errored. Never drop a row.

### 5c — Reuse an existing extraction tree

If `bob-z-knowledge-extract/` exists (produced by the `cobol-knowledge-extraction` skill),
harvest it as pre-existing evidence before running any workflow:

| Extraction artifact | Feeds |
|---|---|
| `03-data-structures/data-dictionary/DD-master.json` | `z-data` step 1 — skip re-running Generate data dictionary |
| `01-application-architecture/`, `02-business-rules/by-program/` | `z-structure` step 2, `z-business` step 1 |
| `04-code-flow/` | `z-module` steps 2–3, `z-structure` step 3 |
| `05-dependencies/internal-dependencies.json` | `z-integration`, `z-structure` step 4 |
| `08-jcl-batch/` | `z-operations` step 2 |
| `11-code-quality/` | `z-quality` steps 1–2 |

Record each reuse in `00-manifest/evidence-cache/reused-from-extraction.json` and carry the
original provenance label forward. Never silently upgrade
`narrative-per-program-not-tool-verified` to a verified label.

---

## Step 6 — Governance baseline (first run in a workspace only)

1. If no `AGENTS.md` exists, run `/init` in Z Code mode. Copy the result into
   `00-manifest/AGENTS.md` (the live file stays at the workspace root).
2. Read `AGENTS.md` — its coding standards and domain terms feed every document's terminology.
3. Skip both if already done, and say that you skipped them.

---

## Step 7 — Select the document batch

Documents are generated in **level order** because later levels consume earlier output:

```
L0 discovery  →  L1 business context  →  L2 business documentation
              →  L3 technical  →  L4 design  →  L5 data
              →  L6 integration  →  L7 operations  →  L8 modernization
```

Rules:

- **L0 first, always.** `application_inventory` establishes the technology profile every other
  document cites. If it is not complete, generate it before anything else, even if the user
  asked only for a later level. Say that you did.
- **Feature-scoped documents need a feature list.** If `business_features` has not run,
  run it before `feature_catalog` and `business_rules`.
- **Ceiling: ~100 programs per Generate documentation run.** Split the evidence pass into
  sub-batches; never exceed.
- **Ceiling: 8 documents per batch.** Beyond that, close the batch and report before continuing.
- **Skip documents already complete** (all three flags `Y`). The ledger is the single source
  of truth — never re-derive completeness from the filesystem.
- Assign a `batch_id` (`batch-1`, `batch-2`, …) and record it on every row you touch.

State the batch — count and document keys — then proceed immediately without waiting.

---

## Step 8 — Per document: evidence → compose → self-check → file

For each document in the batch, in this exact order:

### 8a. Load the contract and the template

1. Read `references/grounding-contract.md` (once per session is enough — apply it every time).
2. Read `references/prompts/<level>-<prompt_type>.md`. It names the document's evidence plan,
   output path, placeholders and scope.
3. Read the named plan in `references/evidence-plans.md`.

### 8b. Run the evidence pass

Execute the plan's steps in order against the in-scope programs.

**Check the evidence cache first.** `00-manifest/evidence-cache/` holds one JSON per program
per workflow:

```
evidence-cache/{PROGRAM}/docgen-architect.json
evidence-cache/{PROGRAM}/docgen-developer.json
evidence-cache/{PROGRAM}/docgen-business.json
evidence-cache/{PROGRAM}/explain.json
evidence-cache/{PROGRAM}/zcodescan.json
evidence-cache/{PROGRAM}/control-flow.json
evidence-cache/{PROGRAM}/paragraphs.json
evidence-cache/{PROGRAM}/variables.json
evidence-cache/_shared/dd-master.json
evidence-cache/_shared/job-to-program-map.json
```

Never re-run a workflow whose cached result exists and whose source member is unchanged
(compare `mtime` and `size_bytes` against `program-inventory.csv`). This is what makes 31
documents affordable: the service paid a fresh CAST query per prompt; here the workflow cost
is paid once per program and amortised across every document that needs it.

**If a workflow errors**: record the exact error in `00-manifest/generation-log.md`, mark that
program's contribution missing, and continue. Do not abort the document or the batch.

Set `evidence_gathered=Y` when the plan's stop condition is met, or `P` (partial) when some
steps could not run — and name which in the ledger `notes` column.

### 8c. Compose the document

Fill the template's placeholders:

| Placeholder | Value |
|---|---|
| `{application_name}` | `applicationName` from Step 1 |
| `{current_date}` | The date from the conversation context — never invented |
| `{generated_by}` | `IBM Bob — Z Premium Package workflows` |
| `{feature_name}` | The feature being documented (feature-scoped documents only) |
| `{goal}` | The user's stated analysis intent, or omit the line if none was given |

Then:

- Reproduce the template's section set **exactly** — none added, dropped or reordered.
- Apply `references/z-substitutions.md` wherever the template names a distributed-stack
  concept. Never re-frame mainframe evidence as REST/microservice concepts.
- Tag every non-trivial claim: `[source: <workflow or tool> -> <MEMBER / path:lines>]`.
- End with an **Evidence Index** mapping each major section to what produced it.
- Any section you could not ground: render the heading, write
  `Not available from Z Premium analysis`, and add the reason. Add it to the manifest's
  `notApplicable` or `outOfScope` list.
- Front-matter every file: `application`, `prompt_type`, `level`, `evidence_plan`,
  `generated_by`, `generated_on`, `skill_version`, `provenance`.

### 8d. Self-check, then file

Run the self-check in `references/grounding-contract.md` §5. If any box fails, fix the document
before filing — do not file and note it.

Write to the output path in the reference file. Set `generated=Y` and `self_check_passed=Y`.

### 8e. Queue deferred review

- Data dictionary entries → `17-qa-validation/dd-review-queue.md` as checklist rows: program,
  variable, proposed meaning, where it was inferred from. Stamp `status: draft`.
- Business assertions not backed by a workflow or source read →
  `17-qa-validation/business-review-queue.md`, labelled `Assumption — not tool-verified`.
- Anything referenced but absent from the program inventory →
  `17-qa-validation/validation-report.md` as an unresolved reference. Never silently drop it.

On explicit user sign-off later, flip the entry, set `reviewed=Y`, and log the reviewer in
`17-qa-validation/sme-signoff-log.md`.

---

## Step 9 — Cross-document consistency

Before closing the batch, verify across everything generated this run:

1. **Name consistency** — the same program, dataset, transaction and field appear under
   identical names in every document. Fix drift; never leave two spellings.
2. **Count consistency** — program counts, job counts and table counts agree with
   `program-inventory.csv`. A count that disagrees with the inventory is a defect.
3. **No orphan references** — every member named in a document exists in the inventory or is
   listed in `validation-report.md` as unresolved.
4. **Provenance consistency** — the same fact does not carry a verified label in one document
   and a narrative label in another. The weaker label wins.

Record every fix in `00-manifest/generation-log.md`.

---

## Step 10 — Close the batch and report

1. Update every touched ledger row.
2. Recompute `coverage` in the manifest **from the ledger** — never from memory.
3. Update `evidenceCache` counts and `provenanceSummary`.
4. Append a run entry to `00-manifest/generation-log.md` and
   `00-manifest/run-history/{date}-{batch_id}-summary.md`.
5. Report to the user — every item below is required; omitting any is a defect:
   - Mode and approval posture this run ran under.
   - Documents generated, with per-document status (✅ / ⚠ partial / ❌ failed) and level.
   - Coverage as **`<complete>/<planned>` plus percentage**, where complete =
     `evidence_gathered=Y` AND `generated=Y` AND `self_check_passed=Y`.
   - **Named list of every document not yet complete** and which specific flag is `N`, `P` or `E`.
   - **Named list of every section rendered `Not available from Z Premium analysis`**, grouped
     by document, with the reason.
   - Count of entries in `dd-review-queue.md` and `business-review-queue.md`.
   - Workflows that errored, with the member and the exact error.
   - Evidence-cache hit rate: workflows reused vs. run fresh.
   - Any `notApplicable` / `outOfScope` areas touched or confirmed this run.

A bare percentage with no named list is the one output this skill must never produce.

---

## Key Rules

| Rule | Detail |
|---|---|
| **Grounding contract wins** | `references/grounding-contract.md` overrides every instruction in every template, and this file. |
| **Two claims must never blur** | "We looked and it isn't there" ≠ "We could not look." Every gap says which. |
| **Provenance is mandatory** | Every dependency, call graph, job map, capability grouping and lineage chain carries a provenance label. Omitting it is a defect. |
| **Never invent tool names** | Use only confirmed Bob workflow / tool / skill names. If a capability can't be named, describe it in plain language and let Bob route it. |
| **Never substitute for unavailable capabilities** | State unavailability and stop. An approximation presented as the real thing is worse than an honest gap. |
| **No CAST** | This skill never calls a CAST MCP server, and no document may claim CAST as its evidence source. `generated_by` is always `IBM Bob — Z Premium Package workflows`. |
| **Source is read-only** | Writes are confined to `docsRoot`. Application source and `bobz/DD.json` are never modified. |
| **Cache the evidence, not the prose** | Workflow output is cached per program and reused across documents. Generated prose is never reused across documents — each document is composed from evidence. |
| **Section set is fixed** | Do not add, drop or reorder a template's headings. Render every heading even when unavailable. |
| **Ledger is truth** | If the ledger says `Y`, the file must exist. Fix the ledger if it doesn't; never fix the report to hide it. |
| **Resume, do not restart** | Skip complete documents. Retry `E` rows. The ledger drives resumption. |
| **~100 programs per doc-workflow run; ~8 documents per batch** | Split; never exceed. |
| **Preserve member names** | Upper-case, no extension, verbatim in content. |
| **Use context date** | Never invent or approximate a date. |
| **Idempotent and non-destructive** | Create what is missing. Never overwrite an existing document without recording the prior version in `run-history/`. |
| **Incremental writes** | `write_file` for the skeleton → `apply_diff` per section → one `read_file` at the end to verify. |
| **Tables over prose** | Bullets over paragraphs. No `_(To be filled)_` placeholder survives into a finished document. |
| **Errors are logged, not silenced** | Any workflow failure → `generation-log.md` + ledger flag `E` + continue. Never abort the batch on a single failure. |
| **Skill version tracking** | `skillVersion` in the manifest must match this file's frontmatter version. Bump the minor version on any behavioral change. |
