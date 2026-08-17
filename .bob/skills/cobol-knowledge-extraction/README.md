# cobol-knowledge-extraction

A Bob skill that runs a disciplined, repeatable, resumable knowledge-extraction pipeline over a
mainframe codebase — COBOL, PL/I, JCL, REXX, or Assembler — and files every artifact into a
versioned `bob-z-knowledge-extract/` knowledge base.

---

## What it does

The skill sequences IBM-shipped Bob workflows — Generate data dictionary, Generate documentation,
Explain code, Z Code Scan — and enforces consistent filing, naming, a coverage ledger, and honest
reporting of what could and could not run. It adds no extraction capability of its own.

**Output tree produced:**

| Folder | Contents |
|---|---|
| `00-manifest/` | Machine-readable manifest, program inventory, coverage ledger, run history |
| `01-application-architecture/` | System-level documentation from the docgen workflow |
| `02-business-rules/by-program/` | Business rules and explain-workflow output per program |
| `03-data-structures/` | Data dictionary (by-program + master), copybook layouts, record layouts |
| `04-code-flow/` | Control flow graphs, paragraph indexes, narrative call graphs |
| `05-dependencies/` | Provenance-labeled inter-program dependency map |
| `06-database/` | SQL usage per program (DDL is out of scope — requires DBA tooling) |
| `07-file-structures/` | Physical file layout documentation |
| `08-jcl-batch/` | JCL job documentation, job-to-program map, batch/online classification |
| `09-cics-ims-transactions/` | CICS/IMS resource cross-walk (if checked-in source is present) |
| `10-error-handling/` | ABEND codes, exception paths, error-handling documentation |
| `11-code-quality/` | Z Code Scan findings, complexity metrics |
| `12-enterprise-standards/` | `AGENTS.md` copy, coding standards, custom skills |
| `13-impact-analysis/` | Out of scope without Z Understand server |
| `14-implementation-plans/` | Downgrade-labeled plans (general reasoning, not Z Understand) |
| `15-modernization-mapping/` | Refactoring candidates and service-program slices |
| `16-cross-reference/` | Structural cross-reference (requires Z Understand server) |
| `17-qa-validation/` | DD review queue, SME sign-off log, validation report |

---

## Requirements

| Requirement | Notes |
|---|---|
| IBM Bob IDE | Advanced mode must be enabled |
| Z Premium Package | Required for all Z workflows (docgen, DD, explain, Z Code Scan) |
| Z Understand server | Optional — enables `/impact-analysis`, `/implementation-planning`, `get_project_*` tools. Without it, impact analysis and cross-reference folders are `outOfScope`. |
| Mode | Z Code or Z Architect |

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
Step  2  Declare approvals + preflight environment check
Step  3  Create output folder structure (idempotent)
Step  4  Finalise scaffold + write extraction-manifest.json
Step  5  Build program inventory and coverage ledger
Step  6  Governance baseline (AGENTS.md + coding standards) — first run only
Step  7  Select batch (≤100 programs)
Step  8  Per-program loop: data dictionary → documentation → dependencies
Step  9  Per-program flow and paragraph structure (optional / on-demand)
Step 10  Language-specific passes: JCL, copybooks, CICS/BMS, SQL
Step 11  Code quality: Z Code Scan + explain-workflow (COBOL/PL/I/HLASM only)
Step 12  Refactoring (on-demand only — not part of a standard batch)
Step 14  Impact analysis / implementation plan (on-demand, downgrade-labeled)
Step 15  Close batch: update ledger, recompute coverage, report
```

---

## Autonomy and approvals

The skill is **fully autonomous**. At Step 2 it emits a single AUTO-APPROVAL DECLARATION that
pre-approves all file system operations, workflows, editor tools, and sub-skill activations for the
entire session. It never pauses for per-step confirmation.

To suspend autonomy mid-session, send the message: **"pause for approval"**

---

## Data dictionary review gate

Even in fully autonomous mode, data dictionary **content** is not auto-approved. All AI-proposed
business meanings are filed as `status: draft` in `17-qa-validation/dd-review-queue.md`. A program
is not counted as complete until an SME reviews and signs off the entries in that queue.

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

The Step 15 report always shows `complete/total (%)` plus a named list of every incomplete program
and which specific flags are still pending.

---

## Resumability

The skill is designed to resume after interruption. Re-running against the same workspace will:
- Skip programs already complete (all three flags = `Y`).
- Retry programs with `E` (error) flags.
- Pick up where the batch left off using the coverage ledger as the single source of truth.

---

## Limitations

| Limitation | Reason |
|---|---|
| Dependency completeness cannot be guaranteed | Without Z Understand's `get_project_resource_usage`, dependency lists are narrative-extracted — they may miss calls not mentioned in documentation. Every dependency artifact carries `"provenance": "narrative-per-program-not-tool-verified"`. |
| DB2/IMS DDL, constraints, triggers out of scope | Requires DBA tooling external to Bob. |
| Impact analysis and cross-reference require Z Understand | `/impact-analysis`, `/implementation-planning`, and structural cross-reference tools are unavailable without a configured Z Understand server. |
| Simple refactoring without Z Understand is unconfirmed | IBM's prerequisites are self-contradictory. The skill probes it automatically on first request and records the outcome. |

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

---

## Version history

| Version | Change |
|---|---|
| 1.1.0 | Folder structure created before scope resolution (Step 3). Approval declaration merged into Step 2. Step 9 (flow/paragraph) made explicitly optional. Z Code Scan scoped to COBOL/PL/I/HLASM only. Error handling (`E` flag) added for workflow failures. Batch-complete definition corrected to require all three flags. Step 15 report requirements made exhaustive. Key Rules converted to table. `argument-hint` added to frontmatter. |
| 1.0.0 | Initial release |
