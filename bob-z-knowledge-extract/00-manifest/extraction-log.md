# Extraction Log — CardDemo

## Run: 2025-07-15 | batch-1

- Mode: EXECUTE — auto-approved posture, dictionary review deferred to queue
- Programs in scope: 46 (44 COBOL + 2 HLASM)
- Z Understand: Not configured
- Local scanner: Created — ScannerOutput.db at `/Users/tarun.goel/Library/Application Support/IBM Bob/User/workspaceStorage/e32e70681dc2246916f77c4fd8bd857e/IBM.bob-z-extension/.tmi/WCA4ZTMIOutput/ScannerOutput.db`
- `.bobz/local-settings.json` written by scan_program tool

### Steps completed this run

| Step | Result |
|---|---|
| scan_program | ✅ Scanned 44 source files |
| get_paragraphs — groups 1-5 | ✅ 610 paragraphs extracted across 31 core programs |
| SQL: copybook dependencies | ✅ Written to internal-dependencies.json |
| SQL: program calls | ✅ Written to internal-dependencies.json |
| SQL: file access | ✅ Written to internal-dependencies.json |
| SQL: complexity by paragraph count | ✅ Written to complexity-metrics.csv |
| Application architecture doc | ✅ bob-z-knowledge-extract/01-application-architecture/CardDemo-architecture.md |
| Paragraph index | ✅ bob-z-knowledge-extract/04-code-flow/paragraph-index/core-programs-paragraphs.md |
| Internal dependencies | ✅ bob-z-knowledge-extract/05-dependencies/internal-dependencies.json |
| CICS/BMS cross-walk | ✅ bob-z-knowledge-extract/09-cics-ims-transactions/cics-transactions-bms-maps.md |
| VSAM file structures | ✅ bob-z-knowledge-extract/07-file-structures/vsam-file-structures.md |
| JCL job-to-program map | ✅ bob-z-knowledge-extract/08-jcl-batch/job-to-program-map.md |
| Complexity metrics | ✅ bob-z-knowledge-extract/11-code-quality/complexity-metrics.csv |
| Quality summary | ✅ bob-z-knowledge-extract/11-code-quality/quality-summary.md |
| Enterprise coding standards | ✅ bob-z-knowledge-extract/12-enterprise-standards/coding-standards.md |

### Steps pending (next run — batch-2)

| Step | Detail |
|---|---|
| Generate data dictionary | Run for all 44 COBOL programs via data-dictionary-workflow |
| Generate documentation | Run for all 44 COBOL programs (architect + developer + business perspectives) |
| Explain code | Run for top 5 complexity programs: COACTUPC, COCRDUPC, COCRDLIC, CBTRN02C, CBSTM03A |
| Z Code Scan | Run for all 44 COBOL + 2 HLASM programs |
| Optional module programs | 13 programs (IMS/DB2/MQ modules) need DD + documentation |
| AGENTS.md | Run /init in Z Code mode and copy to 12-enterprise-standards/ |

### Errors this run
None.

### Programs not yet complete (all 46)
All programs have `dd_generated=N` (Generate data dictionary not yet run).
Core COBOL programs (31) have `doc_generated=P` (partial — structural docs generated; Generate documentation workflow pending).
Optional module programs (13) have `doc_generated=N` (not started).
HLASM programs (2) have `doc_generated=N` (HLASM workflows pending).

## Run: 2026-08-13 | skill-validation + artifact-fix

- Mode: EXECUTE — auto-approved posture, dictionary review deferred to queue
- Trigger: Full end-to-end skill validation audit — 13 defects found and fixed
- Skill version bumped: 1.2.0 → 1.3.0

### Fixes applied this run

| Fix | Detail |
|---|---|
| F1 | get_variables serial rule + checkpoint logging + resumption rule added to SKILL.md §8a-alt |
| F2 | CRRZG5307W classification table added to §2b — CMQ*/IMS*/DB2* = non-fatal system copybooks |
| F3 | Manifest localScannerMetadata reconciliation rule added to Step 15 |
| F4 | docDone/docPartial/completeProgramCount counting rules clarified in Step 15 |
| F5 | complexity-metrics.csv source column rule added to Key Rules |
| F6 | Manifest schema: skillVersion placeholder + docPartial field added |
| F7 | Subtask front-matter workflow stamps corrected from v1.2.0 → v1.3.0 (×3 blocks) |
| F8 | Step 6 cross-reference corrected: Step 13 (tombstone) → Step 11 |
| F9 | Step 11: invented zcodescan-check-* tool names removed; correct UI-invocation + autonomous proxy documented |
| F10 | Step 9: invented zopeneditor-cobol-get-* tool names removed; only get_paragraphs + get_control_flow remain |
| F11 | §8a-alt pre-condition: bobz/DD.json must exist before start_subtask; create empty if missing |
| F12 | Step 8 execution levels clarified: Tier 1 per-program serial; Tier 2 per-group after Tier 1 done |
| F13 | Steps 8a/8b interactive session test defined: agent skips primary path unless user confirms workflow output |

### Artifacts corrected to match new skill rules

| Artifact | Change |
|---|---|
| extraction-manifest.json | skillVersion 1.2.0→1.3.0; localScannerMetadata reconciled to actual DB path; docDone 31→0; docPartial 0→31; capabilityMap entries corrected (ui-only labels); knownLimitations section added; lastUpdated added |
| complexity-metrics.csv | source column added to all 31 rows with value "sql-paragraph-count" |

### MQ system copybook warning — logged per F2

MQ system copybooks (CMQGMOV, CMQPMOV, CMQMDV, CMQODV, CMQV, CMQTML) not in repo.
CRRZG5307W warnings from language server are non-fatal — extraction continues normally.
Affected programs: COACCT01, CODATE01, COPAUA0C.
MQ structure field names will be absent from DD for these three programs.
Ledger notes updated accordingly.

### Next step
get_variables serial run — batch-2 starting now (CBACT01C first).
get_variables OK: CBACT01C — 2026-08-13
get_variables OK: CBACT02C — 2026-08-13
