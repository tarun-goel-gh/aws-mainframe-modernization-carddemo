# modernization-pipeline — the end-to-end BobZ workflow

From a mainframe codebase to a 31-document application documentation suite and a shareable local
zip, driven entirely by IBM Bob IDE + Z Premium Package (the BobZ v3.x MCP server). No AWS, no
cloud job, no bucket — everything happens inside the local IDE workspace.

This is the reference for the *workflow*: what each phase does, why two of the nine phases cannot
be scripted, where the run can legitimately come back "partial," and how to resume it. For the
extraction model, read [`../cobol-knowledge-extraction/README.md`](../cobol-knowledge-extraction/README.md).
For the documentation model — the 31 documents, the grounding contract, the coverage matrix — read
[`../z-app-documentation/README.md`](../z-app-documentation/README.md).

---

## Why this is not one script

`atx-pipeline`, the AWS-Transform analog, wraps **one** shell script end to end because AWS
Transform's reverse-engineering step is an asynchronous cloud job: you start it once and poll for
completion. BobZ has no equivalent job. Every unit of extraction work — a data dictionary pass, a
docgen call, an explain, a Z Code Scan — is a single MCP tool call the agent makes on its own turn,
and the next call to make depends on the result of the last one. There is nothing to launch and
poll.

So `modernization-pipeline` is a **checklist orchestrator**, not a wrapper around one opaque
script. Seven of its nine phases *are* deterministic local file work and run through
`scripts/run_pipeline.sh` exactly like `atx-pipeline`'s phases 5-8. The other two — the extraction
loop itself, and the final publish copy — are marked in the script as `STOP - this phase requires
the agent, not this script`, printed with instructions and a distinct exit status, never faked.

---

## Prerequisites

| Requirement | Why |
|---|---|
| IBM Bob IDE, **Advanced mode** enabled | Required for `cobol-knowledge-extraction` and `z-app-documentation` to activate at all |
| **Z Premium Package** | Backs every MCP tool in §1a of `.bob/skills/_design/bobz-v3-foundations.md` (`generate_data_dictionary`, `generate_documentation`, `explain_code`, `z_code_scan`, `get_variables`, `get_paragraphs`, `get_control_flow`, `scan_program`, `get_expanded_source`, `edit_data_dictionary`) |
| A reachable **BobZ v3.x MCP server** | Phases 1 (probe) and 2 (extraction) only. Phases 3-6 are offline once `bob-z-knowledge-extract/` exists |
| **Z Understand server** (optional) | Unlocks `get_project_*`, `impact_analysis`, `implementation_planning`, `sync_data_dictionary` — §1b of the design doc. Without it, dependency data and the L8 modernization documents degrade to narrative, never silently upgrade |
| `python3`, `zip`, `unzip` | The deterministic phases; no third-party Python packages |
| bash | Written for bash 3.2 (macOS default): no associative arrays, no `${var,,}` |

If `bob-z-knowledge-extract/` does not exist yet and the MCP server is unreachable, this pipeline
cannot produce anything but a bare inventory. Run `cobol-knowledge-extraction`'s own preflight
first to find out why the server is unreachable — this skill does not diagnose that itself.

---

## The nine phases

Per `.bob/skills/_design/bobz-v3-foundations.md` §7a:

```
  1 preflight → 2 extract → 3 extract-verify → 4 reuse-snapshot → 5 coverage →
       (probe)   (AGENT)      (script, Gate B)    (script)          (script, Gate C)
  6 evidence → 7 generate → 8 package → 9 publish
     (script)    (script)     (script)   (AGENT)
```

| # | Phase | Reads | Writes | Runs via |
|---|---|---|---|---|
| 1 | `preflight` | MCP reachability (agent-probed), `program-inventory.csv` | `mcp-capability-probe.json` (agent), inventory (script) | `build_inventory.py` + agent probe |
| 2 | `extract` | resolved scope | `bob-z-knowledge-extract/**`, `extraction-status.csv` | the agent, calling `cobol-knowledge-extraction` batch after batch |
| 3 | `extract-verify` | `extraction-status.csv`, filed artifacts | `verification.json`, `validation-report.md` | `cobol-knowledge-extraction/scripts/verify_extraction.py` — Gate B |
| 4 | `reuse-snapshot` | `bob-z-knowledge-extract/**` | `reuse-snapshot.json` (sha256 fingerprints) | inline deterministic snapshot step in `run_pipeline.sh` |
| 5 | `coverage` | `program-inventory.csv`, the probe file | `coverage.md`, `evidence-index.json` | `z-app-documentation/scripts/build_coverage.py` — Gate C |
| 6 | `evidence` | `mcp-cache/`, `bob-z-knowledge-extract/` (if present) | `evidence-pack.json` | `z-app-documentation/scripts/extract_evidence.py` |
| 7 | `generate` | `evidence-pack.json` + 31 prompts | the 31 documents + ledger | `z-app-documentation/scripts/generate_docs.py` |
| 8 | `package` | `bob-z-app-docs/` | `bob-z-app-docs-<run-id>.zip` (after a clean disclosure scan) | zip + inline disclosure scan |
| 9 | `publish` | the zip | a copy at a path the user names | the agent, after Gate D and explicit confirmation |

Phases 3-8 need no MCP call. When the server is down but `bob-z-knowledge-extract/` is already
populated, `--offline` skips phase 2 and is a complete path on its own — the documents do not
depend on phase 2 having run in the same session.

---

## Quick start

```bash
S=.bob/skills/modernization-pipeline/scripts

# See the plan without touching anything
$S/run_pipeline.sh --offline --dry-run

# Documents only, from an existing bob-z-knowledge-extract/
$S/run_pipeline.sh --offline

# Full run: preflight, then stop for the agent to run extraction
$S/run_pipeline.sh --scope Cobol/ --app-name CardDemo

# After the agent has driven cobol-knowledge-extraction to acceptable coverage
$S/run_pipeline.sh --resume <run-id> --from extract-verify

# Stop before the (optional) publish copy
$S/run_pipeline.sh --resume <run-id> --from extract-verify --no-publish
```

In chat, `/modernization-pipeline` runs the same thing with a gate at each decision point.

---

## Flags

| Flag | Effect |
|---|---|
| `--offline` | skip phase 2 (`extract`); document whatever `bob-z-knowledge-extract/` already holds |
| `--from <phase>` | start here, skipping earlier phases |
| `--only <phase>` | run exactly one phase |
| `--resume <run-id>` | reuse this pipeline's own recorded run state (`pipeline-run-state.json`); phases already `ok` are skipped |
| `--no-publish` | run phases 1-8 and stop before the phase-9 marker |
| `--dry-run` | print the plan and exit |
| `--keep-going` | continue after a fatal failure instead of stopping |
| `--scope PATH\|@FILELIST\|CSV\|GLOB` | forwarded to `build_inventory.py` |
| `--workspace-root DIR` | default `.` |
| `--extraction-root DIR` | default `<workspace-root>/bob-z-knowledge-extract` |
| `--docs-root DIR` | default `<workspace-root>/bob-z-app-docs` |
| `--app-name NAME` | forwarded to `generate_docs.py`; default derived, never invented |
| `--force` | forwarded to `extract_evidence.py` / `generate_docs.py` |
| `--run-id TS` | use this stamp instead of the current time |

`--from` overrides the resume skip-list, so `--resume X --from generate` re-runs generation even
though it succeeded before. `--only` bypasses everything else.

---

## Why `extractionRoot` and `docsRoot` are not stamped per run

`atx-pipeline` stamps a fresh `app-docs-<timestamp>/` folder every run because AWS Transform's
evidence is a point-in-time snapshot pulled from a finished job — two runs over the same job
produce byte-identical output, so the timestamp is purely a container.

BobZ extraction and documentation are **cumulative and ledger-driven**: `extraction-status.csv`
and `document-ledger.csv` already track exactly which program or document is complete, partial, or
still pending, and re-running is designed to pick up where the ledger left off, not to start a
fresh copy. Stamping `bob-z-knowledge-extract/` or `bob-z-app-docs/` per run would break that —
every invocation would re-pay the MCP cost the cache exists to avoid.

So those two folders are persistent, one per workspace. What *is* stamped per run is this
pipeline's own bookkeeping: `pipeline-run-log.md` and `pipeline-run-state.json`, both written under
`<docs-root>/00-manifest/`. `--resume <run-id>` resumes *this pipeline's* record of which of the
nine phases it already ran clean against the current (persistent) `extractionRoot`/`docsRoot` —
it is not choosing between multiple snapshots the way `atx-pipeline --resume` is.

---

## Progress reporting

One line per phase, to stdout and to `<docs-root>/00-manifest/pipeline-run-log.md`:

```
[1/9] preflight          ok          1.1s  exit=0
[2/9] extract             AGENT       0.0s  exit=3
        STOP - this phase requires the agent, not this script. Run cobol-knowledge-extraction
        against the resolved scope, then resume: run_pipeline.sh --resume 20260824-101500 --from extract-verify
[3/9] extract-verify     ok          0.2s  exit=0
[4/9] reuse-snapshot     ok          0.1s  exit=0
[5/9] coverage           ok          0.4s  exit=0
[6/9] evidence           ok          0.6s  exit=0
[7/9] generate           partial     4.2s  exit=1
        18 of 31 documents filed; 13 rendered "Not available from Z Premium analysis"
[8/9] package             FAILED      0.1s  exit=1
        REFUSING TO PACKAGE — disclosure scan hit
```

| Artifact | Purpose |
|---|---|
| `<docs-root>/00-manifest/pipeline-run-log.md` | markdown table: phase, status, elapsed, exit code, detail |
| `<docs-root>/00-manifest/pipeline-run-state.json` | machine-readable phase status, consumed by `--resume` |
| `<extraction-root>/00-manifest/verification.json` | written by phase 3 |
| `<docs-root>/00-manifest/reuse-snapshot.json` | written by phase 4 |
| `<docs-root>/00-manifest/coverage.md`, `evidence-index.json` | written by phase 5 |
| `<docs-root>/00-manifest/evidence-pack.json` | written by phase 6 |
| `<docs-root>/00-manifest/mcp-capability-probe.json` | written by the **agent** in phase 1, read by every later phase |

---

## Statuses

| Status | Meaning | Stops the run? |
|---|---|---|
| `ok` | exit 0 | no |
| `partial` | non-zero, but a declared expected outcome (e.g. low coverage, some documents thin) | no |
| `skipped` | not selected this run; the reason is recorded | no |
| `AGENT` | this phase (2 or 9) needs the agent, not the script; exit code `3` | yes — by design, until the agent has done the work |
| `FAILED` | unexpected non-zero, including a disclosure-scan hit | yes, unless `--keep-going` |

---

## Package phase — disclosure scan

Before the zip is recorded, phase 8 scans every entry for hard-coded passwords, API keys/secrets,
private key headers, DB2/ODBC-style connection strings carrying credentials, bearer tokens, and
JDBC connection strings with an embedded password. **A hit deletes the zip and fails the phase —
it is never downgraded to a warning.** There is no AWS account id or ARN pattern here, because this
skill never touches AWS; see `SKILL.md`'s "Package phase" section for the exact six patterns.

---

## Publishing

There is no upload, no presigned URL, and no public/private bucket policy anywhere in this skill.
"Publish" is Gate D followed by a plain file copy:

1. Gate D states what is in the zip — business rules, the **entire** data dictionary including
   `status: draft` entries no SME has reviewed yet, program and JCL names, Z Code Scan findings —
   and confirms the destination path with the user.
2. The agent (not the script) copies the zip to the named local folder or reachable network share.
3. There is nothing to revoke and nothing that expires: whoever has filesystem access to the
   destination has the file, indefinitely, the same as any other file copy.

---

## Known, real limitations

This skill ships with no BobZ MCP server and no pre-existing extraction artifacts in this
repository, so a fresh run of `run_pipeline.sh` will legitimately fail or stop early:

- **Phase 1** cannot produce a passing `mcp-capability-probe.json` on its own — that file is
  written by the *agent* after a live MCP round-trip. Without a reachable BobZ v3.x server this
  repository's checkout has none, this phase reports the probe missing and stops, exactly as
  designed. This is not a bug to work around; it is the honest result of not having a server to
  reach.
- **Phase 2** never runs inside the script at all, by design — see "Why this is not one script"
  above.
- **Phases 3, 5, 6, 7** call scripts that live in `../cobol-knowledge-extraction/scripts/` and
  `../z-app-documentation/scripts/` (phase 4 is a small snapshot step inline in this skill's own
  script). At the time this skill was written those sibling skills were being rewritten to the
  v2.0.0 contracts in `.bob/skills/_design/bobz-v3-foundations.md` in parallel; if their `scripts/`
  folders have not landed yet, `run_pipeline.sh` reports the missing script by name and fails that
  phase rather than silently skipping it or fabricating output.
- **Phase 9** is always a manual, confirmed copy — there is intentionally no way to make it
  unattended.

None of this is faked to look like success. Run it against a real BobZ-enabled workspace, with the
sibling skills' scripts present, to see phases 1 and 3-8 actually complete.

---

## Skill files

| File | Purpose |
|---|---|
| `SKILL.md` | Full phase/gate instructions followed by Bob at activation |
| `README.md` | This file — human-readable summary |
| `scripts/run_pipeline.sh` | The deterministic driver for phases 1, 3, 4, 5, 6, 7, 8; prints and exits `3` for phases 2 and 9 |

---

## Version history

| Version | Change |
|---|---|
| 1.0.0 | Initial release — nine-phase orchestrator over `cobol-knowledge-extraction` v2.0.0 and `z-app-documentation` v2.0.0, per `.bob/skills/_design/bobz-v3-foundations.md` §7 |
