---
name: z-app-documentation
description: Use when generating the full application documentation suite for a mainframe application — the 31 documents across 9 levels (discovery, business context, business documentation, technical, design, data, integration, operations, modernization) — using BobZ v3's MCP server (Z Premium Package capabilities as directly-callable tools) plus the source members in the workspace. Produces a versioned bob-z-app-docs knowledge base built by three deterministic scripts (build_coverage.py, extract_evidence.py, generate_docs.py) over an evidence-grounded, resumable, ledger-tracked pipeline. Activate when the user asks to generate application documentation, produce a modernization document set, build an as-is assessment, document business rules or data lineage, generate an executive summary or migration roadmap, or mentions "bob-z-app-docs", "documentation suite", "9-level documentation", or "document ledger".
compatibility: Requires BobZ v3's MCP server reachable in the workspace (Advanced mode, Z Code or Z Architect). No CAST Imaging MCP server and no AWS Transform run are needed. A Z Understand server is optional — without it, the six `get_project_*`/`impact_analysis`/`implementation_planning`/`sync_data_dictionary` tools are unavailable and their sections read unavailable, never approximated.
metadata:
  version: "2.0.0"
  argument-hint: '[all|L0..L8|<prompt_type>] [path|inventory.csv|glob] [--dry-run] [--force]'
  upstream: cobol-knowledge-extraction
---

# Z Application Documentation Suite

Generates a complete, evidence-grounded application documentation set — **31 documents across
9 levels** — from a mainframe codebase, using BobZ v3's MCP server and the source members in the
workspace.

**Version 2.0.0 is script-driven, not prose-driven.** Three scripts —
`scripts/build_coverage.py`, `scripts/extract_evidence.py`, `scripts/generate_docs.py` — own the
prerequisite gate, the evidence aggregation and the compose/self-check/file loop. The agent's job
is to call the BobZ MCP tools per program per plan and hand the results to those scripts; it is
not to author a document freehand. See "Hand-composition is not permitted" below for why that
line is not negotiable.

This skill is a port of the CAST integration service's documentation generator
(`services/cast-integration`). The prompt catalog, grounding contract, determinism rules and
evidence-plan mechanism are carried over 1:1. The **evidence source is different**: the service
used a CAST Imaging MCP server; this skill uses the **BobZ MCP server tools named in
`.bob/skills/_design/bobz-v3-foundations.md` §1**, plus read-only file tools over the workspace.
There is no CAST MCP dependency anywhere.

Version 1.0.0 sequenced IBM-shipped UI workflows through a two-tier fallback because no
MCP server existed. BobZ v3 ships one: every capability in §1 of the foundations document is now
a normal tool call the agent makes itself, per program, per turn, with a structured JSON result.
There is no more "UI-invoked workflow vs. autonomous fallback" split, and `doc_generated=P`
(partial, fallback-authored) is retired along with the fallback it existed to label.

---

## Scope

**In scope** — probing MCP reachability; calling BobZ MCP tools per program per evidence plan;
reading workspace source read-only; running the three scripts to gate, aggregate and compose;
maintaining the program inventory, document ledger and evidence indices; reporting gaps.

**Out of scope** — modifying application source; modifying `bobz/DD.json` outside
`edit_data_dictionary`; hand-composing a document instead of running `generate_docs.py`; any
capability in `.bob/skills/_design/bobz-v3-foundations.md` §1b when `zUnderstandConfigured` is
`false`.

## Non-negotiable rules

1. **No evidence, no document.** Every claim traces to an MCP tool result or a source read
   obtained this run. Ungrounded fields read `Not available from Z Premium analysis`.
2. **MCP reachability is a hard gate, and there is no fallback behind it.** If the BobZ MCP
   server does not answer the reachability probe, this skill drops to PLAN mode. It does not
   degrade to a narrative substitute — that path was retired in this version.
3. **Templates are fixed.** Never add, drop or reorder a template's sections. Render every
   heading, even when its content is unavailable. `references/template-families.md` says how to
   read each template's section set.
4. **Provenance on every derived artifact.** Rendered documents use
   `references/grounding-contract.md`'s four-value vocabulary. The `evidence-pack.json` the
   scripts build carries its own, narrower three-value vocabulary — `tool-verified`,
   `narrative-per-program-not-tool-verified`, `z-understand-verified` — because MCP tool output
   and a deterministic local read are no longer meaningfully different trust levels. Do not
   blend the two vocabularies in either direction.
5. **Resumable and idempotent.** A document already marked complete in `document-ledger.csv` is
   skipped, not regenerated, unless `--force`.
6. **Determinism.** Fixed ordering, verbatim identifiers, no synonym variety, no invented dates.
   Two runs over unchanged evidence produce byte-identical documents.
7. **Hand-composition is not permitted.** See below.
8. **Source is read-only.** Writes are confined to `docsRoot`. The one exception is
   `bobz/DD.json`, reachable only through `edit_data_dictionary` / `generate_data_dictionary`.

### Hand-composition is not permitted

**Run `scripts/generate_docs.py`. Do not write a document's markdown by hand, even to fix a
gap you can see.** Hand-composition cannot satisfy this skill's own determinism rules: identical
inputs must yield identical output, ordering must be stable, and every heading must come from the
family the template actually belongs to rather than from a guess at what a heading "should" look
like. Two guarantees a hand-written document cannot give you:

- **The self-check blocks filing.** `generate_docs.py` runs the grounding contract's §5 checklist
  before it writes a single byte, and a document that fails is **not filed** — it is reported and
  the batch continues. A document you composed by hand and then eyeballed against the checklist
  is an assertion of compliance, not compliance; the whole point of an enforced self-check is that
  it does not trust the thing that just wrote the document to grade itself.
- **`document-evidence.json`'s staleness fingerprints depend on the script actually having read
  the evidence.** Every document's per-artifact fingerprint entry is written by the same code path
  that composed the document, from the artifacts it actually opened this run. A hand-written
  document has no such trail — either the fingerprint file lies about what was read, or it is
  simply absent, and either way the next run cannot tell fresh evidence from stale.

If a document is wrong, the fix is: correct the evidence in `mcp-cache/` or the source, re-run
`extract_evidence.py`, then `generate_docs.py --force`. Never patch the rendered file directly.

---

## Reference files — read on demand, not upfront

| File | Read when |
|---|---|
| `.bob/skills/_design/bobz-v3-foundations.md` | Always, before the preflight probe — it is the authoritative MCP tool vocabulary, script contracts and schemas this skill runs against. |
| `references/grounding-contract.md` | Always, before composing or reviewing any document. Non-negotiable. |
| `references/document-catalog.md` | Step 1 and the generation step — the 31 documents, levels, plans and output paths. |
| `references/evidence-plans.md` | Before gathering evidence for a document — which MCP tools to call, in what order. |
| `references/template-families.md` | Before generating — how each template's section set is expressed and extracted. |
| `references/z-substitutions.md` | Whenever a template names a distributed-stack concept. |
| `references/prompts/<n>-<prompt_type>.md` | One per document being generated. |

Never load all 31 prompt files at once. Load the one you are generating.

| Script | Purpose |
|---|---|
| `scripts/build_coverage.py` | Prerequisite gate — probe file, inventory, coverage matrix |
| `scripts/extract_evidence.py` | Aggregate `mcp-cache/` (and any reused extraction tree) into `evidence-pack.json` |
| `scripts/generate_docs.py` | Compose, self-check and file the documents against the ledger |

No script in this suite ever calls the MCP server. Only the agent does, once per tool call, per
turn — scripts are deterministic local file I/O, verification and reporting.

---

## Run modes

| Mode | When | Behavior |
|---|---|---|
| **PLAN** | User passes `--dry-run`, says "plan only", "what would you do", or the MCP reachability probe fails | Produce the scope table, capability map and coverage matrix; run no MCP tool calls beyond the one-shot probe; write no documents; change no ledger rows |
| **EXECUTE** | Default — proceed autonomously as soon as preflight passes | Gather evidence, run the batch, write documents, update the ledger. Do not wait for confirmation. |

Always state which mode you are in as the first line of your response.

---

## Approval posture

**This skill is fully autonomous. No human approval is required at any point** — not for MCP
tool calls, not for skill activations, not for file writes under `docsRoot`, not for script
invocations.

All approvals are declared upfront and are irrevocable for the session. There are no interactive
gates and no per-step confirmation requests.

Two content gates survive. Both are **deferred review gates, not interactive prompts**:

- **Data dictionary business meanings** — filed `status: draft`, queued in
  `17-qa-validation/dd-review-queue.md`, excluded from the completeness count.
- **Business-level assertions** (capabilities, stakeholders, personas, requirements) — filed
  with an `Assumption — not tool-verified` label and queued in
  `17-qa-validation/business-review-queue.md`.

State `EXECUTE — auto-approved posture, content review deferred to queues` as the opening line
of every EXECUTE run. The only revocation trigger is a user message containing the phrase
**"pause for approval"**.

Emit this block exactly once at the start of every EXECUTE run:

```
AUTO-APPROVAL DECLARATION
=========================
All of the following are pre-approved for the entirety of this documentation run.
No further confirmation will be requested.

FILE SYSTEM OPERATIONS
  write_file / apply_diff / insert_content   — any file under docsRoot
  list_files / read_file / glob / grep       — anywhere in the workspace
  execute_command                            — read-only shell commands only

BOBZ MCP TOOLS (v3 server — always available, §1a of the foundations doc)
  generate_data_dictionary, generate_documentation, explain_code, z_code_scan,
  get_variables, get_control_flow, get_paragraphs, scan_program,
  get_expanded_source, edit_data_dictionary, refactor, generate_refactored_service

BOBZ MCP TOOLS (v3 server — gated on zUnderstandConfigured, §1b)
  get_project_inventory, get_project_tables, get_project_resource_usage,
  impact_analysis, implementation_planning, sync_data_dictionary

SCRIPTS
  scripts/build_coverage.py, scripts/extract_evidence.py, scripts/generate_docs.py

SUB-SKILL ACTIVATIONS
  cobol-knowledge-extraction (for inventory/extraction reuse), docs-status, generate-docs

LEDGER AND MANIFEST WRITES
  document-ledger.csv, program-inventory.csv, documentation-manifest.json,
  mcp-capability-probe.json, evidence-pack.json, generation-log.md, mcp-cache/, run-history/

NO application source file is ever modified. Writes are confined to docsRoot, plus
bobz/DD.json solely through generate_data_dictionary / edit_data_dictionary.
Revoking this declaration requires the user to send: "pause for approval".
```

---

## Step 0 — Preflight

1. **Resolve/refresh the program inventory.** If `program-inventory.csv` does not exist yet for
   this scope (in `bob-z-knowledge-extract/00-manifest/` or under this skill's `docsRoot`), run
   `cobol-knowledge-extraction`'s `scripts/build_inventory.py` first. The reachability probe below
   needs at least one real `programId`/`programPath` pair to call against.
2. **MCP reachability probe.** Make one cheap, real tool call — `get_paragraphs` or
   `get_control_flow` — against the first inventoried program. A response, including a
   well-formed tool-level error about that specific program, proves the server is reachable. A
   connection/transport failure or timeout proves it is not. Write
   `00-manifest/mcp-capability-probe.json` (schema: `bobz-v3-foundations.md` §2c) recording
   `mcpReachable`, `mcpProbeMethod`, `mcpProbeLatencyMs`, `mcpServerVersion` (or `"unknown"` —
   never invented).
3. **Active mode** — Z Code or Z Architect.
4. **Advanced mode** — required for this skill to have activated at all.
5. **Z Understand server** — read `<workspaceRoot>/.bobz/local-settings.json`; record
   `zUnderstandConfigured: true|false`.
6. **Local scanner metadata** — does `.bobz/expanded/` or a `ScannerOutput.db` already exist?
7. **Existing state** — do `AGENTS.md`, `bobz/DD.json`, `bob-z-knowledge-extract/` or `docsRoot`
   already exist? Never overwrite them blind. If `bob-z-knowledge-extract/` exists, plan to reuse
   its artifacts as evidence (Step 3).

**If step 2 fails: drop to PLAN mode immediately and report the exact transport/tool error.**
There is no per-program narrative fallback in this version — an unreachable MCP server is a stop
condition for EXECUTE mode, full stop.

Derive the capability map from steps 3–5 exactly as `mcp-capability-probe.json`'s
`capabilityMap` block requires (§1 of the foundations doc): every §1a tool `available`; §1b tools
`unavailable` when `zUnderstandConfigured` is `false`; `refactor` and
`generate_refactored_service` `unverified` until probed once this workspace.

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
   `bobz/`, `docs/explain/`) appear at more than one level of the path, stop and ask which root
   to use. Do not guess — the ledger denominator depends on it.
2. **`docsRoot`** — `<workspaceRoot>/bob-z-app-docs`, unless the user names another.
3. **`applicationName`** — take it from, in order: the user's words, `zapp.yaml`, the repository
   folder name. State which source you used.
4. **`sourceRoots`** — discover them; do not expect any particular folder name. If `zapp.yaml`
   or a `.zapp/` property group exists, read it: `libraries.locations` tells you where copybooks
   resolve from.
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
`business_rules`) — they need a `feature_name` and produce one file per feature. If no features
are known yet, generate `business_features` first; its output becomes the feature list.

State the resolved scope back as a short table, then continue immediately to Step 2.

---

## Step 2 — Run the coverage gate

```
scripts/build_coverage.py --workspace-root <workspaceRoot>
                           [--extraction-root <bob-z-knowledge-extract>]
                           --docs-root <docsRoot>
                           [--probe-file <docsRoot>/00-manifest/mcp-capability-probe.json]
                           [--out-dir <docsRoot>/00-manifest]
                           [--json] [--check-only]
```

Exit `0`: prerequisites met, `coverage.md` and `evidence-index.json` written. Exit `1`: a hard
prerequisite failed — **stop** (probe unreadable or `mcpReachable: false`; no
`program-inventory.csv`; Advanced mode not `true` in the probe file). Exit `2`: bad usage.

`coverage.md` classifies every program `reused-from-extraction` / `needs-evidence-pass` /
`no-source-in-scope`. **Under `--dry-run`, stop here** and present it — this is the cheapest point
to decide the run is not worth doing, or to fix the upstream extraction first.

Soft prerequisites degrade named plans rather than stopping: no `bob-z-knowledge-extract/` tree
means every program's evidence pass starts cold; `zUnderstandConfigured: false` means
`z-integration`/`z-structure` dependency data stays narrative.

---

## Step 3 — Gather evidence: the one step scripts do not do

**This is the agent's step, not a script's.** For every program `build_coverage.py` classified
`needs-evidence-pass`, run the evidence plan named by each in-scope document's row in
`references/document-catalog.md` (full steps in `references/evidence-plans.md`). Each plan step
is now a direct BobZ MCP tool call — `generate_documentation(programId, programPath,
perspective=...)`, `explain_code(...)`, `z_code_scan(...)`, `get_variables(...)`, and so on, per
§1 of the foundations doc — made by the agent, on this turn, with no UI session.

Write every raw result to `00-manifest/mcp-cache/{PROGRAM}/{tool}.json` (`docgen-architect.json`,
`docgen-developer.json`, `docgen-business.json`, `explain.json`, `zcodescan.json`,
`control-flow.json`, `paragraphs.json`, `variables.json`, `data-dictionary.json`). Never re-run a
tool whose cache file exists and whose source member's `mtime`/`size_bytes` is unchanged —
compare against `program-inventory.csv`.

If a tool call errors: record the exact error in `00-manifest/generation-log.md`, mark that
program's contribution missing, and continue. Never abort the batch on a single tool failure.
Parse JCL, BMS maps and LINKAGE SECTION source directly with `read_file`/`grep` — these artifact
types never go through an MCP tool, so this is the one legitimate text-mining step left in the
pipeline.

If `bob-z-knowledge-extract/` exists, its already-filed artifacts (`DD-master.json`,
`02-business-rules/by-program/`, `01-application-architecture/`, `10-error-handling/`,
`05-dependencies/internal-dependencies.json`, `08-jcl-batch/`, `11-code-quality/`) count as
pre-gathered evidence — do not re-run a tool that tree already answered. Carry its provenance
labels forward unchanged; never silently upgrade `narrative-per-program-not-tool-verified` to
`tool-verified` just because it was reused.

---

## Step 4 — Aggregate the evidence pack

```
scripts/extract_evidence.py --workspace-root <workspaceRoot>
                             [--extraction-root <bob-z-knowledge-extract>]
                             --docs-root <docsRoot>
                             [--force]
```

Exit `0`: `evidence-pack.json` written. Exit `1`: no `program-inventory.csv` and no cached
evidence of any kind to aggregate. Exit `2`: bad usage.

This script reads `mcp-cache/` and any reused extraction tree — it never calls MCP itself, and it
never invents a field. A program with no cache file for a tool simply has that field absent from
its `evidence-pack.json` entry.

---

## Step 5 — Compose, self-check, file

```
scripts/generate_docs.py [--levels 0,1,2] [--only <prompt_type>] [--force]
                          [--docs-root <docsRoot>] [--app-name "<override>"]
```

Exit `0`: every requested document filed. Exit `1`: at least one document failed its self-check
and was **not** filed — the batch continues with the others. Exit `2`: bad usage.

Section sets come from `references/template-families.md`; out-of-scope distributed-stack
headings resolve through `references/z-substitutions.md`; anything left over renders
`Not available from Z Premium analysis`. The self-check enforces: a Coverage note, an Evidence
Index, every template heading rendered, every derived artifact provenance-labeled, at least one
artifact recorded as read. Updates `document-ledger.csv` and `generation-log.md` for every
document actually filed. See "Hand-composition is not permitted" above — this script is not
optional, and its verdict is not something to talk yourself past.

Generated data-dictionary entries and unverified business assertions still queue to
`17-qa-validation/dd-review-queue.md` and `17-qa-validation/business-review-queue.md`
respectively — that gate is unchanged from v1.0.0.

---

## Step 6 — Cross-document consistency

Before closing the batch, verify across everything generated this run: the same program, dataset,
transaction and field appear under identical names in every document; program/job/table counts
agree with `program-inventory.csv`; no orphan references; the same fact never carries a stronger
provenance label in one document than another — the weaker label wins. Record every fix in
`generation-log.md`.

---

## Step 7 — Close the batch and report

**Report from the scripts' own output, not from what you remember generating.** Read
`coverage.md` and `document-ledger.csv` (or `generate_docs.py --json`) and report:

- Mode and approval posture this run ran under.
- Coverage as `<complete>/<planned>` plus percentage, where complete = `evidence_gathered=Y` AND
  `generated=Y` AND `self_check_passed=Y` — computed by the script, not restated from memory.
- **Named list of every document not yet complete**, and which of `evidence_gathered`,
  `generated`, `self_check_passed` is still `N` (these `document-ledger.csv` flags only ever take
  `Y`/`N` — there is no `P`/`E` value the way `extraction-status.csv`'s `doc_generated` has).
- **Named list of every section rendered `Not available from Z Premium analysis`**, grouped by
  document.
- Review-queue depth in `dd-review-queue.md` and `business-review-queue.md`.
- MCP tool calls that errored this run, with the program and the exact error.
- Cache hit rate: tool calls reused from `mcp-cache/` vs. run fresh this batch.

A bare percentage with no named list is the one output this skill must never produce.

---

## Failure policy

| Class | Example | Action |
|---|---|---|
| `mcp-unreachable` | reachability probe fails | drop to PLAN, report the transport error, no fallback |
| `prerequisite` | no inventory, Advanced mode off | stop; name the fix |
| `evidence-missing` | a plan's tools returned nothing for a program | mark that program's contribution missing, continue |
| `evidence-partial` | some programs lack a cache entry | generate, mark `partial`, state coverage |
| `template-gap` | a stub template (Family C) | use `template-families.md`'s fixed section set |
| `self-check-fail` | ungrounded field, missing Evidence Index | fix the evidence, re-run the script; never hand-file |

One document failing never stops the batch. Record it and continue.

## Communication

Progress, not process. Do not name plan ids, tool names or cache paths in prose to the user
unless they asked. Report which documents exist, what they cover, and what is missing. When
coverage is partial, say so first.
