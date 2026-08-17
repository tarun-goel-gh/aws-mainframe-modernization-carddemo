# Extraction: per-business-function loop

Turns each selected business function into a verified spec bundle. Run **one function at a
time** and finish each completely — including download and verification — before starting the
next.

## Why strictly sequential

Selecting a new set of business functions **restarts the reimagine step** for the new
selection. The console then shows results only for the newest selection: earlier issue lists
and the S3 links for prior business logic and requirements stop being displayed. The earlier
outputs are not deleted — they remain in the artifacts tab and in S3 — but you can no longer
rely on the UI or the agent's latest message to hand them to you.

Consequence: **snapshot and verify each function's artifacts before triggering the next.**
A batch-collect-at-the-end design loses the mapping from artifact to function.

## Choosing a shape

| | Sequential | Batch |
|---|---|---|
| Functions per reimagine run | 1 | many |
| **Default** | **the default — use it unless the user accepts the depth tradeoff** | only on explicit request, or for a large estate where breadth beats depth |
| Attribution | direct — one zip, one function | requires splitting the combined zip |
| Wall clock | highest | much lower |
| **Specification depth** | **full** | **materially lower — measured, see below** |
| Partial failure | isolated by construction | whole batch can under-deliver silently |

Both shapes are supposed to end in the same place — one self-contained, verified bundle per
function — but **they do not produce equivalent content**, and earlier guidance in this file
wrongly claimed otherwise.

### Measured evidence that batch trades away depth

One measured job, same source, same connector, same job id, detailed functional
specification enabled in both cases:

| | 1 function, sequential | 9 functions, batched |
|---|---|---|
| Account Balance and Transaction Processing | **286** functional requirements | **14** |
| Programs referenced for that function | 9 | 1 |
| Rules for that function | 328 | 14 |
| Combined spec zip size | 64 KB (1 function) | 56 KB (9 functions) |
| Functions delivering any spec at all | 1 of 1 | **6 of 9** |

The batch produced 466 functional requirements across six delivered functions — barely more
than the single sequential run produced for one function, and a 20x regression on the
function common to both. Three functions emitted an empty folder while the job's worklog
reported `Pipeline complete: 9/9 passed, 0 failed, 0 skipped`.

Two conclusions, both load-bearing:

1. **Prefer sequential.** Batch only when the user has accepted shallower specifications, or
   when the goal is a broad first pass to prioritise, with depth to follow per function.
2. **Never trust the pipeline's own completion claim.** It reported 9/9 when 6 delivered.
   Only gate G4 over the unpacked bundle, with scope enforced, establishes what exists.

If you do batch, keep batches small — 3 or 4 — rather than one large one. Depth degrades
with batch size, and a timeout on a big batch costs visibility into every function in it.

## Sequential loop

```
for each function F in scope:
    if state.functions[F].status in (succeeded, skipped): continue      # idempotent resume
    1  readiness probe
    2  gate G3
    3  trigger reimagine
    4  poll within budget, servicing checkpoints
    5  locate spec zip
    6  download + unpack
    7  verify (gate G4)
    8  record + persist
```

## Batch loop

```
1  readiness probe for every function in the batch                      → gate G3 each
2  drop or flag functions that fail G3 under human-touch; under autonomous keep them
   and record the degradation
3  submit the whole batch in one business-function selection
4  poll to completion, servicing checkpoints (BRE config must list files for all
   selected functions)
5  locate the combined spec zip written after the batch started
6  download + unpack                    → scripts/fetch_artifact.sh
7  split into per-function bundles      → scripts/split_bundle.py --state <state.json>
8  verify with scope enforced           → scripts/verify_spec.py --state <state.json>  gate G4
9  record each function independently, then persist
```

**Steps 7 and 8 must be given the expected scope.** Both scripts otherwise infer the function
set from whatever is on disk, which cannot detect a function that produced nothing — the exact
failure that let a 9-function batch report "6 of 6 verified". Pass `--state` (reads
`autonomy.scope`) or `--expect "<A>,<B>"`. A batch verified without scope enforcement has not
been verified.

Expected batch poll budget: `maxPollMinutes` is defined per function, so for a batch use
`maxPollMinutes × functions`, capped at something you are willing to wait. On timeout the whole
batch is `timed_out`, which is why small batches are safer.

Batch sizing: keep a batch to a size whose combined run stays inside the poll budget. For very
large estates, run several batches sequentially rather than one enormous batch — a timeout on a
40-function batch loses visibility into all 40, while four 10-function batches lose one.

### Splitting is mandatory

A batch run returns **one** `spec_gen_specs_<ts>.zip` containing `spec/<FunctionA>/`,
`spec/<FunctionB>/`, … Shipping that as-is fails the requirement that each function's zip carry
everything for that function.

```
scripts/split_bundle.py --dir <unpacked> --out-dir .atx/mfre/specs \
                        --state .atx/mfre/state.json --source-root <repo>
```

Each output bundle contains:

```
<Slug>.zip
├── spec/<Slug>/requirements.md
├── spec/<Slug>/traceability.yaml
├── spec/<Slug>/discovery/programs.yaml
├── function-metadata.json     ← provenance, metrics, verification, caveats
└── README.md                  ← human entry point
```

`function-metadata.json` is what makes a bundle independently useful: business function name,
slug, category, description; data paths, entry points, LOC, missing-file count; extraction
status, attempts, readiness lists, source zip key; requirement and rule counts; the list of
programs referenced; the verification verdict with failures and warnings; run/job/workspace,
region, account, source mode, commit and package sha256; and the glossary provenance note.

Anyone receiving one zip can answer "what is this, where did it come from, how far do I trust
it" without the run that produced it.

### 1 — Readiness probe (do this first, always)

Ask before spending compute. `send_message` scoped to the job:

> Check the readiness of the business function "<F>" for the Reimagine workflow. Report the
> missing files and unsupported files, and name the specific files. Do not start extraction
> yet — I want to review the readiness result first.

Expect a report separating:
- **Missing files** — referenced but absent. These degrade extraction. Blocking.
- **Unsupported files** — present but not processable, for example GDG bases and plain `.txt`.
  Usually safe to skip because they are infrastructure artifacts holding no business logic.

Record both lists verbatim in `state.functions[F].readiness`.

The explicit "do not start extraction yet" matters. Without it the agent may helpfully begin,
and you lose the gate.

#### When the probe cannot run

The readiness probe depends on the Business Function Discovery Agent, which can be
unavailable independently of everything else — observed returning internal errors on every
query while the job, connector, and API were all healthy. Do not block the run on it, and do
not let the agent invent an answer.

Fallback, in order:

1. Take the per-function missing-file **count** from the discovery catalog
   (`business_function.csv`, column `Number of potential missing files`). It is authoritative
   for counts, and it is already in `state.discovery.functions[].missingFiles`.
2. Record `readiness.probeStatus = "unavailable"` with the timestamp and the agent's own
   error, and state plainly that per-file **names** and the unsupported-file list could not be
   obtained.
3. Set gate G3 to `pass_degraded` and carry that into the function's `function-metadata.json`
   and the report.

A count without names is weaker than a real probe: you know fidelity is reduced but not which
rules are affected. That is a reportable limitation, not a silent one.

### 2 — Gate G3

| Readiness | `autonomous` | `human-touch` |
|---|---|---|
| No missing, no unsupported | proceed | proceed |
| No missing, some unsupported | proceed, record skipped list | proceed, record skipped list |
| Missing files present | proceed **degraded**, record loudly | ask: supply files, proceed degraded, or skip |

Under `autonomous`, missing files do not block. Real estates are rarely complete, and blocking
would defeat the point of an autonomous run. The cost is requirement fidelity for the affected
rules, so the degradation must be impossible to miss: it goes in
`state.functions[F].readiness.missing`, the function's `function-metadata.json`, its README
caveats, and the report. Mark the function `succeeded_degraded` in the report's status column
if it otherwise passes G4.

Never silently drop a function for missing files. Either run it degraded and say so, or skip it
and say so.

### 3 — Trigger reimagine

Prefer the HITL task when the business-function selection task is pending — that is the
supported path (see `references/hitl-tasks.md`, `MainframeAssessmentBusinessProcessDiscoveryComponent`).

If no such task is open, drive it through chat:

> Yes, proceed with the Reimagine workflow for the business function "<F>". Run business logic
> extraction and generate modernization requirements for it. The N unsupported files
> (<names>) are acceptable to skip.

Name the unsupported files explicitly. It confirms the intent and leaves an audit trail in the
message history.

Two sub-steps run server-side:
1. **Extract business logic** — results to S3 as JSON; per-file issues surfaced with file
   name, type, path, status, and detail.
2. **Generate requirements** — starts **automatically** after extraction with no further
   prompt. Do not wait for a task that will never appear.

Set `status: extracting`, stamp `startedAt`, persist.

### 4 — Poll

`get_job_status` on an increasing interval. Between polls, check
`list_resources resource="tasks"` for new HITL tasks and service them.

Stop conditions:
- Requirements-generation step reports `SUCCEEDED`, or a spec zip newer than `startedAt` appears
- Budget (`state.autonomy.maxPollMinutes`, default 90) exhausted → `timed_out`
- Job enters `FAILED` / `STOPPED` → `failed`

`list_resources resource="worklogs" stepId=<step>` is the most informative progress signal
during a long run — it reports incremental counts ("50/64 files processed"), the rules
extracted, per-function `START`/`DONE` lines, and any Knowledge Graph ingestion failure. Use it
to distinguish real progress from a stall.

**A completion claim in the worklogs is not evidence of completion.** `Pipeline complete: 9/9
passed, 0 failed, 0 skipped` and a `DONE <Function>` line for each function were all emitted by
a run that delivered specifications for six of nine. Stop conditions tell you when to *look*;
only G4 over the unpacked bundle, with scope enforced, tells you what you *got*.

`timed_out` is not `failed`. The run is usually still progressing server-side and is resumable
in a later session; say that plainly rather than implying loss.

### 5 — Locate the spec zip

```
list_resources resource="artifacts" workspaceId=… jobId=… \
  pathPrefix="transform-output/<jobId>/spec_gen/"
```

Pick the asset with the **greatest `createdTimestamp` that is newer than this function's
`startedAt`**. Never assume "the newest zip overall" — a job accumulates one zip per reimagine
run, including cancelled attempts, and a stale or aborted run's zip looks superficially valid.

Record `specZip` (basename) and `specKey` (full key).

### 6 — Download and unpack

```
scripts/fetch_artifact.sh \
  --profile <p> --region <r> \
  --bucket <connector-bucket> \
  --key "<specKey>" \
  --dest ".atx/mfre/specs/<slug>"
```

Download via the S3 API, not by round-tripping asset content through the MCP layer — asset
reads return the bytes as a text field, which corrupts binary zips.

Expected bundle:

```
spec/<FunctionSlug>/
├── requirements.md                 ← the deliverable
├── traceability.yaml               ← rule → requirement mapping
└── discovery/programs.yaml         ← program inventory for the function
```

### 7 — Gate G4: verification

```
scripts/verify_spec.py --dir .atx/mfre/specs/<slug> --json                  # single function
scripts/verify_spec.py --dir <unpacked-batch> --state .atx/mfre/state.json  # batch, scope enforced
```

Checks, all deterministic:

| Check | Rule | Severity |
|---|---|---|
| `empty_function_folder` | `spec/<Slug>/` exists but has no `requirements.md` | fail |
| `function_missing_from_bundle` | an expected function has no `spec/` folder at all | fail |
| `bundle_shape` | `requirements.md` + `traceability.yaml` present and non-empty | fail |
| `reconciliation` | `summary.reconciliation.expected == written`, `shortfall == 0` | fail |
| `disposition_math` | `captured + not_applicable + unreachable + delegated == total_rules` | fail |
| `rules_accounted` | `not_accounted_for == 0` | fail |
| `req_dangling` | no REQ id is traced without being defined in `requirements.md` | fail |
| `requirements_substance` | ≥1 numbered section and ≥1 `REQ-F-*` | fail |
| `requirements_unique_ids` | no duplicate REQ definitions | fail |
| `req_provenance` | every defined requirement maps to ≥1 rule | warn |
| `req_empty_mapping` | no requirement index entry has an empty rule list | warn |
| `requirements_truncation` | last line is a finished sentence | warn |
| `program_resolution` | every `program:` resolves to a real source file (needs `--source-root`) | warn |
| `program_inventory` | `discovery/programs.yaml` lists ≥1 program | warn |
| `open_questions` | count of `OQ-*` | info |

**Fail** → `failed_verification`. Keep the artifacts; they are still useful evidence. Report
which check failed and why.
**Warn** → still `succeeded`, but warnings must appear in the report.

### Two things that will bite a naive verifier

**`traceability.yaml` carries two indices, not one.** A real bundle has both:

```yaml
rules:          # forward: 328 entries, rule_id -> req_id / req_ids, disposition, program
  - rule_id: …
    disposition: captured
    req_id: REQ-F-042
requirements:   # reverse: 290 entries, req_id -> rule_ids
  - req_id: REQ-F-250
    rule_ids: [ … ]
```

A requirement can be absent from the forward index yet fully mapped in the reverse one.
Reading only `rules:` produces a **false negative** on requirement coverage. The reverse index
is authoritative for "does this requirement have provenance".

**Severity is deliberately asymmetric.** A REQ id traced but never defined is a dangling
reference and a genuine artifact defect → fail. A REQ id defined but never traced is a
requirement lacking source provenance → warn, because the bundle is still usable and the rules
side may reconcile perfectly.

Also: do not treat a REQ numbering gap as a failure. Sequences legitimately skip ids. And note
that grepping the whole YAML for `REQ-\d+` overstates coverage, because `reason:` prose quotes
REQ ids in explanatory text — count only structural `req_id` / `req_ids` fields.

Two warnings observed on real output, worth surfacing rather than hiding: an empty
`discovery/programs.yaml` (inventory not populated even though traceability knows the
programs), and a final open question truncated mid-sentence with a trailing ellipsis.

### Re-extraction guard — never silently replace a richer bundle

A re-run can produce a **worse** specification than the one it replaces. Observed: re-extracting
a function that previously yielded 286 functional requirements produced 14.

So when a function already has a verified bundle and you extract it again, treat promotion as a
decision, not a default:

1. Verify the new bundle independently. Passing G4 says it is internally consistent, **not**
   that it is better.
2. Compare against the existing bundle on `reqF`, `rulesTotal`, and `programs`.
3. If any of those drops materially, **keep the existing bundle as the delivered artifact** and
   retain the new one beside it under a clearly labelled path, for example
   `specs/<Slug>-rerun-<YYYYMMDD>/`.
4. Record the regression as a warning on the function and name both numbers in the report.
   `state.functions[F].rerun` holds the alternate's metrics and verdict.
5. Tell the user, and let them choose which to ship.

G4 measures internal consistency, so a thin-but-coherent bundle passes cleanly. Depth
regression is invisible to the gate and must be checked separately.

### 8 — Record

Write metrics into `state.functions[F].metrics`: `reqF`, `reqN`, `openQuestions`,
`rulesTotal`, `captured`, `notApplicable`, `programs`, `sections`. Set terminal status, stamp
`finishedAt` and `durationMin`, persist. Then next function.

Under `autonomous`, stay quiet during the loop — one short progress line per function at most,
and speak up only when something fails. Under `human-touch`, summarise each function as it
completes.

## Retry policy

| Class | Retry | Detail |
|---|---|---|
| `infrastructure` (transient API, dropped poll) | once | fresh trigger, fresh budget |
| `service_unavailable` (a dependent agent is down) | **not counted as an attempt** | see below |
| `quality` (G4 fail) | once | only if a partial/aborted zip was picked — re-locate first |
| `quality` (empty function folder) | once, **sequentially** | batching is the likely cause; do not re-batch it |
| `input` (missing files) | never | needs new source |
| `blocked` (decision task) | never | needs the user |
| `auth` / `setup` | never | fix globally, then resume the loop |

Cap at 2 attempts per function. Record `attempts`. A function that fails twice is reported as
failed with its reason — that is a legitimate, honest outcome, not something to keep grinding.

### Service-wide unavailability is not a per-function failure

A dependent agent being down affects every function equally, so spending per-function attempts
on it is wrong: one retry would have marked nine functions `failed` inside four minutes for an
outage that cleared in fourteen.

When the agent reports it cannot reach a sub-agent — for example "the Business Function
Discovery Agent remains unavailable", or repeated internal errors on every query — treat it as
`service_unavailable`:

- Back off and retry with escalating waits (roughly 2, 5, 5+ minutes) inside the poll budget.
- Do **not** increment `attempts`; nothing about the function was tested.
- Keep the wait bounded by `maxPollMinutes`; on exhaustion record `timed_out`, which is
  resumable, rather than `failed`.
- Say plainly that this is an upstream outage, not a problem with the source or the account.

Distinguish it from a per-function infrastructure error: a service outage fails *identically*
for every function, and the agent's own message usually names the unreachable component.

## Status vocabulary

| Status | Meaning | Reportable |
|---|---|---|
| `pending` | not started | no — run unfinished |
| `readiness_ok` | probe passed, not yet triggered | no — run unfinished |
| `extracting` | reimagine running | no — run unfinished |
| `verifying` | artifacts downloaded, G4 running | no — run unfinished |
| `succeeded` | G4 passed, complete source | yes |
| `succeeded_degraded` | G4 passed, but ran with missing files | yes |
| `failed_verification` | artifacts exist, G4 failed | yes |
| `failed` | run failed after retries | yes |
| `timed_out` | poll budget exhausted, likely still running server-side | yes |
| `readiness_blocked` | missing files, skipped under `human-touch` | yes |
| `awaiting_user` | parked at a hard stop | yes |
| `skipped` | deliberately excluded | yes |

Use exactly these strings. `build_report.py` maps them to display labels and decides which
block report generation. `succeeded_degraded` counts toward the success total but is displayed
distinctly, so degraded fidelity is never hidden behind a clean number.
