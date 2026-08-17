---
name: mainframe-reverse-engineering
description: Govern and execute AWS Transform mainframe reverse engineering end to end — verify connectivity and
  account setup, intake COBOL/JCL source from GitHub, an S3 zip, or the local workspace, run discovery
  (analyze code, analyze data, discover data paths, discover business functions), then extract
  business logic and generate modernization requirements for every discovered business function,
  producing one verified spec zip per function plus a status report. Use when reverse engineering,
  assessing, decomposing, or reimagining a mainframe, COBOL, JCL, CICS, or VSAM codebase with AWS
  Transform. Requirements: Requires the AWS Transform MCP server declared in `config.toml` with AWS credential or SSO auth, AWS CLI v2,
  an AWS Transform mainframe reimagine connector (S3 + Amazon Neptune), and unzip plus python3 on
  PATH.
license: Apache-2.0
metadata:
  author: tarun.goel
  version: "1.1.1"
  phase: reverse-engineering
---

# Mainframe Reverse Engineering (AWS Transform)

Governs Phase 1 of the Reimagine pattern: reverse-engineer a mainframe codebase into
per-business-function modernization requirements with full traceability. Forward
engineering (DDD, microservice specs, code generation) is **out of scope** — this skill
stops at verified spec artifacts on local disk plus a status report.

## Scope

**In scope**
- Connectivity and account-setup verification
- Source intake from GitHub, an existing S3 zip, or the local workspace
- Discovery: analyze code → analyze data → discover data paths → discover business functions
- Per-function: readiness probe → extract business logic → generate requirements → spec zip
- Verification of every produced artifact, then a consolidated report

**Out of scope** — stop and hand off if asked for these
- DDD / bounded contexts / microservice specs / code generation → `workload-mainframe-reimagine.md`
- COBOL→Java refactor (a different AWS Transform pattern entirely)
- Test planning, test data collection, IaC, deployment
- Provisioning AWS infrastructure (connector, Neptune, roles) — verified, never created

**Codebase-agnostic.** Nothing here is tuned to a particular application. Business functions,
programs, entry points, and exclusions are always derived from the run's own discovery output,
never from a built-in list. Any named example in the reference files is illustrative only —
if you find yourself matching a hardcoded application or function name, that is a bug.

## Non-negotiable rules

1. **Never fabricate status.** A function is `succeeded` only when gate G4 passes on a
   spec zip that exists on local disk. Never infer success from job state or an agent message.
   A run that logged `Pipeline complete: 9/9 passed, 0 failed, 0 skipped` had in fact produced
   specifications for six of nine — the pipeline's own completion claim is not evidence.
1a. **Verify against the requested scope, never against what is on disk.** Enumerating
   delivered functions cannot detect a function that delivered nothing. Always pass
   `--state` (or `--expect`) to `verify_spec.py` and `split_bundle.py`. Reporting "N of N
   verified" where N was discovered by scanning is a reporting error, not a shortcut.
1b. **Distinguish client-side from account-side before blaming the account.** MCP responses
   cannot tell the two apart. A non-MCP cross-check must fail too before you report an
   account as unconfigured (`references/preflight.md` §1.3).
2. **Answer checkpoints only from evidence, never from a guess.** Autonomous mode answers a
   checkpoint when the response is *derivable* from verified state or a documented policy, and
   logs the derivation. When it is not derivable, stop — see Hard stops. A guessed answer to
   "which connector" or "which functions" corrupts the whole run silently.
3. **Snapshot before moving on.** Download, split, and verify a run's artifacts before
   triggering the next run — per function when sequential, per batch when batched. AWS
   Transform resets the reimagine step's displayed results when a new set of business functions
   is selected; prior outputs survive in S3 but stop being surfaced. Persist as you go or you
   lose the artifact-to-function mapping.
4. **One failure never stops the run.** Classify it, record it, continue with the next function.
5. **Persist state after every stage transition**, before reporting anything to the user.
6. **Never hardcode agent names or transformation names.** Discover them.
7. **Always pass an explicit AWS profile to every shell command**, and the region resolved at
   preflight. Ambient env is frequently empty and silently falls back to an expired default
   profile, which surfaces as a confusing token error rather than "wrong profile".
7a. **Never export credentials into a shell you keep using.**
   `eval "$(aws configure export-credentials --format env)"` also exports
   `AWS_CREDENTIAL_EXPIRATION`; once it passes, every AWS call reports *"Credentials were
   refreshed, but the refreshed credentials are still expired"* even with a valid login and a
   correct clock. Use a subshell, or strip the set per command:
   `env -u AWS_CREDENTIAL_EXPIRATION -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN …`.
   Suspect this before suspecting expiry or clock skew — they are indistinguishable from the
   error text alone.
8. **Read-only against the customer's source and account.** Never edit mainframe code, never
   provision infrastructure.
9. **Every delivered function bundle stands alone.** Requirements, traceability, program
   inventory, metadata, and caveats travel together, so one zip is useful without the run that
   produced it.

## Autonomy contract

**Default: `autonomous`.** Run the whole pipeline without check-ins, deriving every answer
from state and policy. Do not ask the user to opt in — just state at kickoff that you are
running autonomously and that `--human-touch` is available.

| Mode | Behaviour |
|---|---|
| `autonomous` *(default)* | answer every derivable checkpoint; pause only at the hard stops below |
| `human-touch` | pause at every checkpoint, including display-only reviews |

Invoke `human-touch` when the user asks for it in any form — "supervised", "check with me",
"review each step", "human in the loop".

### Hard stops — pause even when autonomous

These are safety boundaries, not conveniences. Do not route around them.

1. **`severity: CRITICAL` tasks** — a non-admin cannot approve one anyway
   (`SEND_FOR_APPROVAL` is required), and auto-approving as admin discards the review the
   severity exists to force.
2. **`category: TOOL_APPROVAL` tasks** — an agent asking permission to run a tool.
3. **Destructive or scope-expanding requests** — deleting a workspace or job, provisioning
   infrastructure, widening scope beyond what was agreed.
4. **Ambiguity a rule cannot settle** — two equally valid connectors, an unresolvable
   business-function name, contradictory catalog data.

Everything else is derivable and gets answered without asking. See
`references/hitl-tasks.md` for the per-component derivation rules.

### Autonomous defaults

| Decision | Default |
|---|---|
| Function scope | all discovered functions minus infrastructure-only ones (gate G2 heuristics) |
| Extraction shape | **sequential** — batch only on explicit request, because batching measurably reduces specification depth (`references/extraction.md`) |
| Poll budget | 90 minutes per function, then `timed_out` and move on; for a batch, budget × functions |
| Re-extraction that regresses | keep the richer existing bundle, retain the new one beside it, report both numbers |
| Missing files at readiness | proceed degraded, record prominently — do not block the run |
| Glossary | auto-draft if absent, label `auto-drafted-unverified` everywhere |
| Review checkpoints | read, extract signals to state, acknowledge, log |

Record the whole contract in `state.autonomy`. The poll budget doubles as standing approval
for waits, so `adaptive_poll` needs no per-call prompt.

Proceeding degraded on missing files is deliberate: real estates are rarely complete, and
blocking would defeat autonomy. The cost is fidelity, so it must be loud — the affected
function's readiness list, its metadata file, and the report's failure section all carry it.

## Pipeline

Seven stages, each with an exit gate. Never skip a gate. On resume, re-enter at
`state.stage` (see `references/state-and-reporting.md`).

```
0 Resume        → read .atx/mfre/state.json, re-enter mid-pipeline
1 Preflight     → connectivity + existing account setup verified   [G0]
2 Intake        → source zip in S3, inventory recorded             [G1]
3 Job           → workspace + job created, instructions loaded
4 Discovery     → business function catalog persisted              [G2]
5 Extraction    → readiness → BRE → requirements → split → verify  [G3, G4]
6 Report        → table + manifest written                         [G5]
```

### Stage 0 — Resume

Read `.atx/mfre/state.json`. If absent, this is a fresh run: create it and continue to
Stage 1. If present, tell the user what run you found (stage, job name, functions already
done) and offer resume vs fresh start. Never silently reuse or silently discard prior state.

### Stage 1 — Preflight

Follow `references/preflight.md`. The **AWS profile is the only required input**; region is
derived from that profile's own configuration. Ask for a profile if none was given, then
discover everything else.

Two distinct checks the user often conflates:

- **Connectivity** — is the Transform API reachable and authenticated?
- **Service setup** — does the account actually have what a mainframe *reimagine* job needs?
  A live API connection proves nothing about the connector, the Neptune knowledge graph, or
  the bucket.

```
scripts/preflight.sh --profile <p> [--bucket <connector-bucket>]
```

**Account setup is a precondition, not something this skill provisions.** Transform
onboarding, the reimagine connector, Neptune, IAM roles, and the bucket are expected to exist
already. Discover and verify them; if something is missing, name it precisely and stop.
Never create infrastructure to make a run possible — that is a hard stop.

**Gate G0** — all of: environment not poisoned by a stale `AWS_CREDENTIAL_EXPIRATION`; auth
valid with headroom measured against the expected run length; region resolved and supported for
mainframe; a mainframe orchestrator agent discoverable; a workspace available; an `ACTIVE`
reimagine connector identified; its S3 bucket readable. Any failure → report the specific
missing item with the remediation from `references/preflight.md` and stop. Do not create a
job that will fail at step one.

**Before attributing a G0 failure to the account, a non-MCP cross-check must also fail**
(`atx custom def list`, or a SigV4 request where 403 means denied and 404
`UnknownOperationException` means access works). MCP evidence alone cannot separate a stale
client from an unconfigured account, and getting this wrong sends the user to provision
infrastructure they already own.

### Stage 2 — Intake

Follow `references/code-intake.md`. Three modes — ask which if not stated:

| Mode | Input | Action |
|---|---|---|
| `github` | repo URL + ref | clone shallow, package, upload |
| `s3zip` | existing `s3://…/x.zip` | validate in place, do not repackage |
| `local` | workspace path | package, upload |

For `github` and `local`, run `scripts/package_source.sh`. It enforces the documented
layout (artifact-type subfolders), classifies by extension, flags unknown extensions, and
warns when `glossary.csv` is absent — that file measurably improves extraction quality, so
offer to generate a starter from detected abbreviations.

**Gate G1** — zip exists in the connector bucket; ≥1 COBOL or JCL file present; unknown-
extension share ≤ 10% (or user accepted); inventory + sha256 recorded in state.

### Stage 3 — Job

Create the workspace if needed, then create the job. `create_job` also starts it.

```
list_resources resource="agents" agentType="ORCHESTRATOR_AGENT"   # discover, never hardcode
create_job workspaceId=… jobName="mfre-<app>-<YYYYMMDD-HHMM>" objective=… intent=…
load_instructions workspaceId=… jobId=…                            # REQUIRED before any job work
```

Objective template — state the full reverse-engineering arc so the agent plans discovery
*and* per-function reimagine:

> Assess and reimagine the mainframe application at `<s3 zip>`. Analyze code and data,
> discover data paths, and produce a business function catalog. Then, for each business
> function I select, extract business logic and generate modernization requirements with
> traceability. Do not refactor code.

Confirm the generated plan with the user before letting it run. Persist `job.id` immediately
— without it, nothing later is recoverable.

### Stage 4 — Discovery

Follow `references/discovery.md`. Drive the four capabilities, servicing HITL tasks per
`references/hitl-tasks.md`. Expect review checkpoints for code analysis, data analysis, data
path discovery, and business function discovery results.

Persist the catalog to `state.discovery.functions` and snapshot the discovery artifacts
(`business_function_outputs.zip` → `business_function.csv` is the authoritative catalog).

**Gate G2** — catalog persisted; every function has ≥1 data path and ≥1 entry point;
code-analysis quality signals triaged (missing files, duplicate program IDs, identically
named files, unclassified files); infrastructure-only functions flagged. Present the catalog
as a table and confirm the extraction scope before spending compute.

### Stage 5 — Extraction

Follow `references/extraction.md`. Two shapes, same gates. Default to **batch** above 4
functions in scope; sequential below that.

**Sequential** — one function per reimagine run. Cleanest attribution, highest wall-clock cost.

```
for each function F:
  1 readiness probe   → missing + unsupported                     [G3]
  2 trigger reimagine → extract business logic → generate requirements
  3 poll within budget, servicing checkpoints
  4 locate spec zip   → newest key under spec_gen/ after F started
  5 download + unpack → scripts/fetch_artifact.sh
  6 verify            → scripts/verify_spec.py                     [G4]
  7 persist, then next F
```

**Batch** — many functions per run, for large estates.

```
1 readiness probe every function in the batch                      [G3]
2 select the whole batch in one reimagine trigger
3 poll to completion, servicing checkpoints
4 download the combined spec zip (contains spec/<Function>/ per function)
5 split      → scripts/split_bundle.py  (per-function zip + metadata + README)
6 verify all → scripts/verify_spec.py enumerates every function    [G4]
7 persist per-function outcomes independently
```

A batch run returns **one** zip holding every selected function. Splitting is mandatory, not
cosmetic: each function must end up with a zip that stands alone — its requirements,
traceability, program inventory, `function-metadata.json`, and README — so it can be handed to
a team without the rest of the run. A partial batch failure is recorded per function; the
functions that verified still ship.

**Gate G3 (per function, pre-run)** — readiness known. Unsupported files (GDG bases, plain
text) are recorded and skipped. Missing files do not block under `autonomous`: proceed
degraded and record loudly. Under `human-touch`, ask.

**Gate G4 (per function, post-run)** — the quality gate that makes output trustworthy.
`verify_spec.py --state .atx/mfre/state.json` must report `pass`: every expected function is
present with a substantive `requirements.md`, traceability reconciles with zero shortfall,
dispositions sum to `total_rules`, and no REQ id is referenced without being defined. A
function folder that exists but holds no `requirements.md`, or an expected function with no
folder at all, **fails** the gate. Warnings — an untraced requirement, an empty
`discovery/programs.yaml`, a truncated trailing line — do not fail the gate but must surface in
the report.

G4 measures internal consistency only. It cannot see a **depth regression**: a re-extraction
that drops from 286 requirements to 14 passes cleanly. Compare `reqF`, `rulesTotal`, and
`programs` against any prior bundle for the same function before promoting it.

Retry once on infrastructure-class failure. Never retry a readiness-blocked function without
new input.

### Stage 6 — Report

Run `scripts/build_report.py`. Emits `.atx/mfre/report.md` and `.atx/mfre/manifest.json`
from state — never hand-written, so the report cannot drift from reality. Required columns
and the metadata set are specified in `references/state-and-reporting.md`.

**Gate G5** — every selected function appears with a terminal status; every `succeeded` row
has a local path that exists; counts reconcile. Then present the table inline, lead with
the headline (`N of M succeeded`), and name the next step (forward engineering) without
starting it.

## Failure policy

| Class | Examples | Action |
|---|---|---|
| `auth` | expired token, wrong profile | fix and resume; never loop |
| `env` | stale `AWS_CREDENTIAL_EXPIRATION` poisoning every call | strip the inherited credential set; do not re-auth or chase the clock |
| `setup` | connector `PENDING`/`FAILED`, Neptune unreachable | stop at G0, remediate with user |
| `input` | missing files, bad zip layout, unclassified source | record; ask; skip function |
| `infrastructure` | transient API error, timeout | retry once, then `failed` |
| `service_unavailable` | a dependent agent returning internal errors for every request | back off and retry within the poll budget; do **not** spend per-function attempts |
| `quality` | G4 fail, or a function folder with no specification in it | keep artifacts, mark `failed_verification` / `failed`, report why |
| `blocked` | decision HITL task, user unavailable | park as `awaiting_user`, continue others |

Timed-out functions are `timed_out`, not `failed` — they are usually still running
server-side and resumable.

## Reference index

| Need | File |
|---|---|
| Connectivity + account setup checks, Neptune connector, remediation | `references/preflight.md` |
| GitHub / S3 / local intake, zip layout, glossary | `references/code-intake.md` |
| Discovery capabilities, quality signals, catalog handling | `references/discovery.md` |
| Per-function loop, readiness probe, retries | `references/extraction.md` |
| HITL task catalog, payload shapes, observed sequence | `references/hitl-tasks.md` |
| State schema, resume rules, report spec | `references/state-and-reporting.md` |

| Script | Purpose |
|---|---|
| `scripts/preflight.sh` | Environment, region derivation, bucket and Neptune discovery → JSON |
| `scripts/package_source.sh` | Build and validate the source zip, inventory, sha256 |
| `scripts/fetch_artifact.sh` | Download, unpack, integrity-check an S3 artifact |
| `scripts/snapshot_analysis.sh` | Code analysis + data analysis + BFD artifacts → `.atx/mfre/analysis/` |
| `scripts/verify_spec.py` | Gate G4 across every function in a bundle |
| `scripts/split_bundle.py` | Batch bundle → one self-contained zip + metadata per function |
| `scripts/build_report.py` | State → `report.md` + `manifest.json` |

**Downstream consumer.** The `atx-app-documentation` skill generates a 31-document application
documentation suite from this skill's outputs. It requires `.atx/mfre/analysis/` and the spec
bundles, so treat the analysis snapshot at Stage 4 as a deliverable, not a debug aid.

## Communication

Progress, not process. Do not name MCP tools, gate ids, or stage numbers to the user — those
are internal. Report what was found and what is next. Refer to workspaces, jobs, and
functions by name, never by raw UUID. When state is cached rather than freshly fetched, say
so in past tense and offer to refresh. Never promise background monitoring you are not doing.
