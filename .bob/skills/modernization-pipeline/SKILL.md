---
name: modernization-pipeline
description: Guided end-to-end run from a mainframe codebase to the 31-document application documentation suite and a shareable local zip, using only IBM Bob IDE + Z Premium Package (BobZ v3.x MCP server) — no AWS anywhere. Walks nine phases with gates A-D at each decision point — scope, extraction coverage, thin-evidence generation, and disclosure before any copy — and resumes a failed run without redoing completed work. Activate when the user asks to run the whole modernization pipeline, go end to end on this codebase, extract knowledge and generate docs, package or share the documentation suite, or runs /modernization-pipeline.
compatibility: Needs .bob/skills/cobol-knowledge-extraction (interactive, MCP-driven) and .bob/skills/z-app-documentation (scripts). Needs a reachable BobZ v3.x MCP server for phase 2; --offline documents an existing bob-z-knowledge-extract/ with no MCP calls. bash 3.2 compatible (macOS default).
metadata:
  author: modernization-pipeline
  version: "1.0.0"
  argument-hint: '[--offline] [--resume <run-id>] [--from <phase>] [--dry-run] [--no-publish] [scope]'
  delegates-to: cobol-knowledge-extraction, z-app-documentation
---

# /modernization-pipeline

Unlike `atx-pipeline` — which wraps **one** opaque shell script because AWS Transform's
reverse-engineering job runs as an async cloud job you poll — BobZ extraction is **interactive**.
The agent calls MCP tools turn by turn, per program; there is no job id to poll and no bucket to
fetch from. So this skill is not a wrapper around one script. It is a **checklist orchestrator**:
it sequences skill and script invocations in a fixed order and stops at four named gates (A-D). The
underlying script, `.bob/skills/modernization-pipeline/scripts/run_pipeline.sh`, executes the
phases that *are* deterministic (1, 3, 4, 5, 6, 7, 8) and refuses to fake the two that are not
(2, 9) — it prints what the agent must do instead and stops with a distinct exit status.

Do not reimplement phases 3-8 in chat. Each of those phases is one call to an already-existing
script (or a small deterministic snapshot step) in this skill or a sibling skill's `scripts/`
folder; narrating the equivalent work by hand produces a run that is not recorded in
`pipeline-run-state.json` and therefore cannot be resumed, and it lets a coverage number or a
self-check drift from what the script would actually have computed.

There is **no AWS anywhere in this skill.** No S3, no presigned URLs, no IAM ARNs, no bucket
policies, no account id, no expiry concept. Everything lives inside the local IDE workspace.
"Publish" means a plain file copy to a path the user names, nothing more.

---

## The nine phases

Per `.bob/skills/_design/bobz-v3-foundations.md` §7a:

| # | Phase | Needs MCP | Agent-required | Runs via |
|---|---|---|---|---|
| 1 | `preflight` | yes | partially | delegates to `cobol-knowledge-extraction`'s Step 2 preflight (MCP reachability probe, mode checks, capability map) + `build_inventory.py` |
| 2 | `extract` | yes | **fully** | run the `cobol-knowledge-extraction` skill against the resolved scope, batch after batch, until target coverage or a user-named subset is reached |
| 3 | `extract-verify` | no | no | `cobol-knowledge-extraction/scripts/verify_extraction.py` — Gate B |
| 4 | `reuse-snapshot` | no | no | index `bob-z-knowledge-extract/` artifacts + sha256 fingerprints for `z-app-documentation` reuse |
| 5 | `coverage` | no | no | `z-app-documentation/scripts/build_coverage.py` — Gate C |
| 6 | `evidence` | no | no | `z-app-documentation/scripts/extract_evidence.py` |
| 7 | `generate` | no | no | `z-app-documentation/scripts/generate_docs.py` |
| 8 | `package` | no | no | zip `bob-z-app-docs/` + local disclosure scan (refuses to produce the zip on a hit) |
| 9 | `publish` | no | **fully** | OPTIONAL — copy the zip to a user-named local or network path, after explicit confirmation |

Phases 3-8 need no MCP call and no human judgment call; the script performs them exactly. Phases
2 and 9 need a human or an MCP-calling agent turn and **the script never attempts them** — it
prints `STOP - this phase requires the agent, not this script` and exits with status `3`, which
this skill recognizes as "your turn," not a failure.

When the MCP server is unreachable but `bob-z-knowledge-extract/` already exists from a previous
session, `--offline` is the fast, complete path: it skips phase 2 and documents whatever
extraction already landed, exactly as `atx-pipeline --offline` re-documents an existing
`.atx/mfre/` with no AWS calls.

### Phase 1 in more detail — do not duplicate it here

Phase 1 is `cobol-knowledge-extraction`'s own Step 2 preflight, called, not re-specified:

1. Resolve/build `program-inventory.csv` for the scope (`build_inventory.py` — deterministic,
   the script does this part).
2. **MCP reachability probe** — the agent's job, not the script's. One cheap real tool call
   (`get_paragraphs` or `get_control_flow`) against the first inventoried program. The script
   cannot make this call itself; it only checks afterward whether
   `00-manifest/mcp-capability-probe.json` exists and is well-formed. If it is missing and
   `--offline` was not passed, phase 1 reports `STOP - this phase requires the agent` too: run
   `cobol-knowledge-extraction`'s preflight first, then re-run this phase.
3. Active mode, Advanced mode, `zUnderstandConfigured`, local scanner metadata, existing state —
   all read from the probe file the agent wrote. Report the full capability map (see
   `cobol-knowledge-extraction/SKILL.md` §1 / the design note at
   `.bob/skills/_design/bobz-v3-foundations.md` §1-2 for the exact tool vocabulary and probe
   schema — this skill does not repeat that table).

### Phase 2 in more detail — why it cannot be a script call

There is no AWS Transform-style batch job to launch and poll. Each `generate_data_dictionary`,
`generate_documentation`, `explain_code`, `z_code_scan`, `get_variables`, `get_paragraphs`,
`get_control_flow` call is a single MCP round-trip the agent makes on its own turn, one program (or
one small group) at a time, writing the raw result to
`bob-z-knowledge-extract/00-manifest/mcp-cache/{PROGRAM}/{tool}.json` and updating
`extraction-status.csv` as it goes. Run the `cobol-knowledge-extraction` skill — directly, or via
its `extract-batch` command — repeatedly against the resolved scope until either:

- every in-scope program is `dd_generated=Y AND dd_approved=Y AND doc_generated=Y`, or
- the user has named a subset and that subset is complete, or
- the user says to stop short and accept partial coverage.

This phase has no fixed number of turns and no script can drive it, because each turn's tool
result determines what the next turn should call.

---

## Gates

Stop at each gate and wait. These are the points where continuing on an assumption produces a
misleading document set or an unwanted disclosure.

**Gate A — before phase 2.** Confirm the scope (path, file list, inventory CSV, or glob) and that
`workspaceRoot` is unambiguous, per `cobol-knowledge-extraction` Step 1's multi-root check. State
that Advanced mode is required and that the MCP reachability probe (phase 1) must have passed.
Run `--dry-run` first and show the plan.

**Gate B — after phase 3 (`extract-verify`).** Run `verify_extraction.py` (from
`cobol-knowledge-extraction`'s `scripts/`) and report complete-of-inventory programs explicitly —
the BobZ analog of `atx-pipeline`'s "delivered-of-discovered business functions." Name every
program that is not `dd_generated=Y AND dd_approved=Y AND doc_generated=Y`, and which flag is
still outstanding. A partial extraction is a normal, reportable outcome. **Never let it pass
silently into phase 5**, because every downstream document then describes a fraction of the
codebase while reading as though it describes all of it.

**Gate C — after phase 5 (`coverage`).** Show the coverage matrix `build_coverage.py` (phase 5)
just wrote — lead with reused-from-extraction vs. needs-evidence-pass vs. no-source-in-scope. If
coverage is low, ask whether to generate the documentation suite at all. 31 thin, mostly
"Not available from Z Premium analysis" documents are a worse outcome than an honest gap report
and a recommendation to run more extraction batches first.

**Gate D — before phase 9 (`publish`).** The disclosure gate. It always runs at the end of phase 8
whether or not the user has asked to publish anywhere yet:

- The zip is not produced at all if the disclosure scan (patterns below) finds a hit. There is no
  "publish anyway" override.
- There is no public/private concept and no expiry concept here — `publish` is always an explicit
  file copy to a path the user names, a local folder or a network share the IDE's filesystem can
  already reach. Nothing defaults to shared by accident because there is no bucket, no ACL, and no
  signing key to misconfigure.
- Before copying, state plainly what the archive contains and therefore what becomes readable at
  the destination: business rules, the full data dictionary (**including `status: draft` entries
  not yet SME-approved**), program and JCL names, and any Z Code Scan complexity/quality findings.
  Unlike `atx-pipeline`'s Gate D, there is no AWS account id to disclose — but the draft dictionary
  entries are exactly the analog: content nobody has signed off on yet, about to leave the IDE.

---

## Package phase — disclosure scan (no AWS ARNs here; different secrets, same posture)

`atx-app-documentation`'s package phase scans for IAM/STS identity and AWS access keys because
those are the credentials that can leak from an AWS-Transform-fed run. Nothing in this skill ever
touches AWS, so those patterns do not apply. What can leak from a local IDE workspace is different:
passwords, API keys, private key material, and DB2/JDBC-style connection strings that happen to be
sitting in a copybook comment, a JCL parameter card, or a stray note filed alongside the evidence.

The scan runs over every file about to enter the zip, case-insensitively where noted:

| Pattern | Catches |
|---|---|
| `(?i)password\s*[:=]\s*\S+` | Hard-coded passwords |
| `(?i)(api[_-]?key\|secret)\s*[:=]\s*\S+` | API keys, secrets |
| `-----BEGIN (RSA\|EC\|OPENSSH )?PRIVATE KEY-----` | Embedded private keys |
| `(?i)(user\s*id\|uid)\s*=.*password\s*=` | DB2/ODBC-style connection strings carrying credentials |
| `(?i)bearer\s+[A-Za-z0-9\-_.]{20,}` | Bearer tokens |
| `(?i)jdbc:[a-z0-9]+://[^;]*password=` | JDBC connection strings with an embedded password |

A hit **refuses the zip**, not warns: print every match as `file: pattern-label`, delete any
partially-written zip, and stop the phase. Never downgrade a hit to a warning and never let the
user override it from chat — fix the offending file and re-run phase 8.

---

## Running it

Full run, MCP reachable:

```
.bob/skills/modernization-pipeline/scripts/run_pipeline.sh \
  --workspace-root . --scope Cobol/ --app-name CardDemo
```

The script runs phase 1, then stops at phase 2 with an agent-required marker. Run
`cobol-knowledge-extraction` (directly or via `/extract-batch`) until Gate B's coverage is
acceptable, then continue:

```
.bob/skills/modernization-pipeline/scripts/run_pipeline.sh \
  --resume <run-id> --from extract-verify
```

The script runs phases 3-8, then stops at phase 9 with an agent-required marker. After Gate D
passes and the user names a destination:

```
cp "bob-z-app-docs-<run-id>.zip" "/path/the/user/named/"
```

Documents only, no new extraction, from an existing `bob-z-knowledge-extract/`:

```
.bob/skills/modernization-pipeline/scripts/run_pipeline.sh --offline
```

Plan only, nothing touched:

```
.bob/skills/modernization-pipeline/scripts/run_pipeline.sh --offline --dry-run
```

### Flags

| Flag | Effect |
|---|---|
| `--offline` | skip phase 2 (`extract`); document whatever `bob-z-knowledge-extract/` already holds |
| `--resume <run-id>` | reuse this pipeline's own recorded run state; phases already `ok` are skipped |
| `--from <phase>` | start at this phase, skipping earlier ones |
| `--only <phase>` | run exactly one phase |
| `--dry-run` | print the plan and exit without touching anything |
| `--no-publish` | run phases 1-8 and stop before the phase-9 marker |
| `--keep-going` | continue after a fatal failure instead of stopping |
| `--scope PATH\|@FILELIST\|CSV\|GLOB` | forwarded to `build_inventory.py` — see Step 1 precedence in `cobol-knowledge-extraction/SKILL.md` |
| `--workspace-root DIR` | default `.` |
| `--extraction-root DIR` | default `<workspace-root>/bob-z-knowledge-extract` |
| `--docs-root DIR` | default `<workspace-root>/bob-z-app-docs` |
| `--app-name NAME` | forwarded to `generate_docs.py`; default derived, never invented |
| `--force` | forwarded to `extract_evidence.py` / `generate_docs.py` — re-aggregate/regenerate |
| `--run-id TS` | use this stamp instead of the current time |

---

## Reporting

Each phase prints one line: `[n/9] <phase> <status> <elapsed> exit=<code>`. `status` is one of
`ok`, `partial`, `skipped`, `FAILED`, or `AGENT` (phases 2 and 9's stop marker). The same rows land
in `<docs-root>/00-manifest/pipeline-run-log.md`, and machine-readable state in
`pipeline-run-state.json`. Relay the phase lines to the user as they appear, then close with:

- run id and the two persistent roots (`extractionRoot`, `docsRoot` — neither is stamped per run;
  only this pipeline's own run-log and run-state are)
- coverage as `complete / inventory-total` from Gate B, and `documents-generated / 31-planned` from
  phase 7, whichever ran this session
- any phase recorded `partial` or `FAILED`, with the resume command
- whether the zip exists and passed the disclosure scan; the destination, only if phase 9 actually
  ran after explicit confirmation

## Rules

- The script never calls the MCP server — only the agent does, and only phases 2 and 9 involve the
  agent doing work the script could not do deterministically. Every other phase is the named
  script (or, for phase 4, a small deterministic snapshot step in the pipeline script itself),
  unmodified, with the flags in `.bob/skills/_design/bobz-v3-foundations.md` §4.
- `extractionRoot` and `docsRoot` are persistent, not stamped per run — BobZ's own ledgers
  (`extraction-status.csv`, `document-ledger.csv`) are what makes a re-run resumable, not a new
  folder. Only this pipeline's own bookkeeping (`pipeline-run-state.json`,
  `pipeline-run-log.md`, both under `<docs-root>/00-manifest/`) is per invocation.
- Never call any MCP tool from this skill directly. This skill sequences `cobol-knowledge-extraction`
  and `z-app-documentation`; it has no MCP vocabulary of its own.
- Never modify application source. All writes are confined to `extractionRoot`, `docsRoot`, and the
  final zip.
- A phase recorded `partial` is a reportable state, not something to retry silently until it turns
  green. Report the coverage number before the document count, and the document count before the
  zip.
- `--offline` documents an existing extraction honestly; it never pretends phase 2 ran.
