# Mainframe Reverse Engineering (AWS Transform)

Turns a mainframe codebase into per-business-function modernization requirements with full
traceability, using AWS Transform. Phase 1 of the Reimagine pattern: it stops at verified spec
artifacts on local disk plus a status report, and never forward-engineers.

`SKILL.md` is the governing document — the agent loads it and follows it. This README is for
humans: what the skill does, how to drive it, and what it produces.

---

## What it does

```
0 Resume      → re-enter a prior run from .atx/mfre/state.json
1 Preflight   → connectivity + existing account setup verified            [G0]
2 Intake      → source zip in S3, inventory recorded                      [G1]
3 Job         → workspace + job created, instructions loaded
4 Discovery   → business function catalog persisted                       [G2]
5 Extraction  → readiness → BRE → requirements → split → verify     [G3, G4]
6 Report      → table + manifest written                                  [G5]
```

Each stage has an exit gate. Gates are not advisory — a gate failure stops the stage.

**In scope:** connectivity and account-setup verification, source intake, the four discovery
capabilities, per-function business logic extraction and requirements generation, verification,
and reporting.

**Out of scope:** DDD, bounded contexts, microservice specs, code generation, COBOL→Java
refactoring, test planning, IaC, and provisioning any AWS infrastructure. Account setup is
*verified*, never created.

**Codebase-agnostic.** Business functions, entry points, and infrastructure exclusions are
always derived from the run's own discovery output. Any application or function name appearing
in the reference files is illustrative. If the skill ever matches a hardcoded application name,
that is a bug.

---

## Requirements

| Requirement | Notes |
|---|---|
| {{MCP_PREREQUISITE}} | AWS credential or SSO auth |
| AWS CLI v2 | plus `unzip`, `python3`, and `git` on PATH |
| AWS Transform enabled | in the target account **and region** |
| Mainframe **reimagine** connector, `ACTIVE` | S3 bucket + Amazon Neptune knowledge graph |
| Neptune Serverless 1.4.5.1+ | `available`, IAM auth, storage encryption |

A plain S3 connector is not sufficient. Per-function requirements generation is a reimagine
capability and needs the Neptune-backed connector.

PyYAML is used by `verify_spec.py` when importable; without it a targeted line parser reads the
fields the gate needs, so it is optional.

---

## How to Use

The skill activates from natural language in {{RUNTIME_NAME}}. You do not call the scripts yourself in
normal use — the agent runs them. Direct invocation is documented below for debugging and CI.

### Starting a run

```
reverse engineer this COBOL codebase with AWS Transform
```

The agent runs autonomously by default: it answers every derivable checkpoint from verified
state and documented policy, and pauses only at the hard stops. It states this at kickoff.

The only required input is an **AWS profile**. Region is derived from that profile's own
configuration.

```
reverse engineer this mainframe app using profile my-profile
```

### Supervised mode

Any of these phrasings switch to `human-touch`, which pauses at every checkpoint including
display-only reviews:

```
reverse engineer this codebase, but check with me at each step
--human-touch
run this supervised
review each step with me
```

### Choosing the source

Three intake modes. The agent asks if you have not said.

```
reverse engineer the COBOL in this workspace
reverse engineer https://github.com/org/repo at branch main
assess the source already at s3://my-bucket/legacy-app.zip
```

For an existing S3 zip the skill validates in place rather than repackaging — it will not
silently change what you believe you submitted.

### Controlling scope

Discovery typically finds more "functions" than you want to spend compute on, because
build/deploy JCL and sysadmin utilities appear as functions. Those are excluded by default with
the signals that classified them, and any can be added back:

```
include Application Build and Deployment in scope as well
extract only Payment Authorization Processing and Fraud Review
re-extract all functions including the ones already done
```

### Resuming

State is persisted after every stage transition and every function outcome, so a run survives
a lost session, an expired token, or a service outage.

```
resume the reverse engineering run
what's the status of the mainframe run?
```

`succeeded`, `skipped`, and twice-failed functions are skipped on resume. `timed_out`,
`readiness_blocked`, and `awaiting_user` are retried.

### Worked example

```
You:   reverse engineer this COBOL codebase with AWS Transform, profile my-profile
Agent: [preflight] account 123456789012 / us-east-1, connector ACTIVE, Neptune available
       [intake]    44 COBOL, 62 copybooks, 55 JCL, 21 BMS — no glossary, will auto-draft
       [discovery] 11 business functions found; 2 classified infrastructure-only and excluded
                   → presents the catalog table and the computed scope of 9
       [extraction] sequential, one function at a time, verifying each before the next
       [report]    "7 of 9 business functions succeeded" + per-function table
```

---

## Scripts

Deterministic and independently runnable. Every one is read-only against your source and
account except the artifacts it writes under `.atx/mfre/`, and the one declared exception noted
under `preflight.sh`.

### `preflight.sh` — environment and account setup

```bash
# Minimum: profile only, region derived from it
scripts/preflight.sh --profile my-profile

# With bucket checks, and headroom judged against the expected run length
scripts/preflight.sh --profile my-profile \
  --bucket my-transform-bucket \
  --expected-run-min 120

# Also validate a destination bucket for a published deliverable
scripts/preflight.sh --profile my-profile \
  --bucket my-transform-bucket \
  --upload-bucket my-docs-bucket \
  --upload-prefix generated-zip \
  --intend-public
```

Emits JSON on stdout with an `ok` boolean, human-readable checks on stderr. Exit 0 pass, 1 a
required check failed, 2 bad usage.

`--bucket` is the bucket artifacts are **read** from. `--upload-bucket` is where a deliverable is
**written**. They are separate flags on purpose: publishing into the bucket that holds the raw source
analysis is how a narrow share turns into a broad exposure.

When `--upload-bucket` is supplied, five extra checks run:

| Check | Fails when |
|---|---|
| `upload_bucket_separation` | warns when the upload bucket is also the artifact bucket |
| `upload_bucket_region` | bucket missing; warns on a region mismatch, which breaks presigned URLs |
| `upload_bucket_write` | `PutObject` is denied — caught **before** the work, not after |
| `upload_bucket_public` | reports posture `blocked` / `unguarded` / `partial`; escalates under `--intend-public` |
| `upload_bucket_existing_policy` | warns when a `Principal: "*"` Allow already exists, so an upload is exposed on arrival |

The write check is the script's one exception to being read-only: it writes a small probe object and
immediately deletes it. A bucket policy granting `s3:PutObject` cannot be inferred from metadata, and
finding out after 31 documents have been generated is the expensive way to learn it.

`--intend-public` only *checks* whether a public-read policy could apply. It changes no policy.

### `snapshot_analysis.sh` — mirror the analysis artifacts

```bash
scripts/snapshot_analysis.sh --profile my-profile \
  --bucket my-transform-bucket \
  --job-id <job-id> --dest .atx/mfre/analysis
```

Syncs the job's analysis prefixes into `.atx/mfre/analysis/`, unpacks any zips, and writes
`snapshot-manifest.json`. Around 100 MB for a mid-sized estate, including one data-dictionary CSV per program. This is
what the documentation skill grounds most of its content in — the spec bundles alone cover far less.

Exit 0 when at least one prefix was captured, 1 when nothing was, 2 bad usage.

### `package_source.sh` — build the intake zip

```bash
scripts/package_source.sh \
  --src . --out .atx/mfre/source.zip --app legacy-app \
  --glossary glossary.csv \
  --upload s3://my-transform-bucket/ \
  --profile my-profile --region us-east-1
```

Enforces the artifact-type folder layout, classifies by extension, computes the unknown share,
and writes `inventory.csv` and a `.sha256` beside the zip. Refuses to produce a zip that would
fail gate G1 unless you pass `--force`.

### `fetch_artifact.sh` — download and unpack

```bash
scripts/fetch_artifact.sh \
  --profile my-profile --region us-east-1 \
  --bucket my-transform-bucket \
  --key "transform-output/<jobId>/spec_gen/spec_gen_specs_20260813_071942.zip" \
  --dest .atx/mfre/specs/MyFunction
```

Downloads through the S3 API deliberately. Reading connector-backed assets through the MCP layer
returns bytes as a text field, which corrupts binary zips.

### `verify_spec.py` — gate G4

```bash
# Single function bundle
scripts/verify_spec.py --dir .atx/mfre/specs/UserSecurityProfileManagement \
  --source-root . --json

# Batch bundle WITH SCOPE ENFORCED — always do this for a batch
scripts/verify_spec.py --dir .atx/mfre/newrun \
  --state .atx/mfre/state.json --source-root .

# Scope from an explicit list instead of state
scripts/verify_spec.py --dir .atx/mfre/newrun \
  --expect "Credit Card Record Management,Online Transaction Entry"

# Write verification.json beside each bundle
scripts/verify_spec.py --dir .atx/mfre/newrun --state .atx/mfre/state.json --write
```

Exit 0 pass (warnings allowed), 1 fail, 2 bad usage.

**Always pass `--state` or `--expect` for a multi-function bundle.** Without it the script can
only report on functions it can find, which cannot detect a function that produced nothing. See
Scope enforcement below.

### `split_bundle.py` — one self-contained zip per function

```bash
scripts/split_bundle.py \
  --dir .atx/mfre/newrun \
  --out-dir .atx/mfre/specs \
  --state .atx/mfre/state.json \
  --source-root .
```

A batch run returns one zip holding every selected function. Splitting is mandatory: each
function must end up with a zip that stands alone — requirements, traceability, program
inventory, `function-metadata.json`, and a README — so it can be handed to a team without the
rest of the run.

### `build_report.py` — gate G5

```bash
scripts/build_report.py --state .atx/mfre/state.json --out-dir .atx/mfre
```

Generates `report.md` and `manifest.json` from state. Never hand-write the report; generated
output cannot drift from what actually happened.

---

## Outputs

```
.atx/mfre/
├── state.json                  ← single source of truth
├── source.zip / inventory.csv  ← local and github intake modes
├── discovery/
│   └── business_function.csv    ← the authoritative catalog
├── specs/<FunctionSlug>/
│   ├── spec/<FunctionSlug>/{requirements.md,traceability.yaml,discovery/programs.yaml}
│   ├── function-metadata.json   ← provenance, metrics, verification, caveats
│   └── README.md
├── specs/<FunctionSlug>.zip     ← the deliverable
├── report.md                    ← generated
└── manifest.json                ← generated, machine-readable
```

Add `.atx/` to `.gitignore` unless you want artifacts committed.

Every bundle stands alone by design. Anyone receiving one zip can answer "what is this, where
did it come from, and how far do I trust it" without access to the run that produced it.

---

## Scope enforcement

The single most important behaviour to understand.

Discovering functions by scanning for `requirements.md` makes a function that produced **no**
specification invisible. On a real 9-function batch, three functions emitted only an empty
`discovery/programs.yaml`, and verification reported:

```
gate: pass   functionCount: 6   passed: 6
```

A clean pass over two thirds of the requested scope, while the job's own worklog claimed
`Pipeline complete: 9/9 passed, 0 failed, 0 skipped`.

The gate now reconciles three sets, and any shortfall **fails**:

| Set | Meaning |
|---|---|
| `expected` | what was asked for (`--expect`, or `--state` → `autonomy.scope`) |
| `delivered` | `spec/<Slug>/` with a substantive `requirements.md` |
| `empty` | `spec/<Slug>/` present but carrying no `requirements.md` |

Same bundle, current behaviour:

```
G4 overall: FAIL — 6 passed, 3 failed of 9 function(s)
EMPTY function folders (3): MasterDataFileInitialization, OnlineTransactionEntry,
                            TransactionReportingandStatementGeneration
Scope: 6 delivered of 9 expected (source: state)
```

An empty function folder fails with or without an expected list — a folder the generator created
but never filled is a defect on its own evidence. Supplying the expected list additionally
catches functions that produced no folder at all.

---

## Sequential versus batch

**Sequential is the default.** Batching measurably reduces specification depth. From one job,
same source, same connector, detailed functional specification enabled in both cases:

| | 1 function, sequential | 9 functions, batched |
|---|---|---|
| Account Balance and Transaction Processing | **286** functional requirements | **14** |
| Programs referenced | 9 | 1 |
| Rules | 328 | 14 |
| Spec zip size | 64 KB (1 function) | 56 KB (9 functions) |
| Functions delivering any spec | 1 of 1 | **6 of 9** |

Use batch only when you have accepted shallower specifications, or for a broad first pass to
prioritise with depth to follow. Keep batches to 3 or 4 rather than one large one: depth
degrades with batch size, and a timeout on a big batch costs visibility into every function in
it.

G4 measures internal consistency, so a thin-but-coherent bundle passes cleanly. **Depth
regression is invisible to the gate** and is checked separately — when re-extracting a function
that already has a bundle, the richer one is kept and both numbers are reported.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Credentials were refreshed, but the refreshed credentials are still expired` | stale `AWS_CREDENTIAL_EXPIRATION` in the environment — **not** an expired login, **not** clock skew | `env -u AWS_CREDENTIAL_EXPIRATION -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN …` |
| Same error, environment clean | genuinely expired SSO, or real skew | `aws sso login --profile <p>`; check the clock against an `s3.<region>.amazonaws.com` `Date` header before blaming skew |
| `NOT_CONFIGURED` / `sigv4AwsTransformAPI.available: false` | usually the MCP client, which probes once at startup and caches | reconnect `aws-transform-mcp` from the MCP Server view; pin its `env`; cross-check before blaming the account |
| `NO_PROFILES` from SSO `configure` | no Transform profile for that IdC instance, or the wrong start URL | the Transform **Start URL for IDE** is not the IdC portal start URL |
| Signed request returns 404 `UnknownOperationException` | wrong path, signature accepted | access **works** — fix the path, do not re-auth |
| `HTTP 400 A message is already being processed for this conversation` | `send_message` is not concurrent-safe per job | back off 60–150s and resend; use `skipPolling` for long triggers |
| Agent reports a sub-agent unreachable on every query | upstream service outage, not your source or account | back off with escalating waits inside the poll budget; it does not consume per-function attempts |
| Connector stuck `PENDING` | needs admin approval | share the verification link and wait |

### Never conclude "the account is not set up" from MCP evidence alone

Both `get_status` and `list_resources` ride the same MCP client, so a stale client is
indistinguishable from an unconfigured account. Cross-check with something else first:

```bash
# Does the account have Transform API access at all?
atx custom def list

# 403 = denied. 404 UnknownOperationException = signature accepted, access works.
curl -s -o /dev/null -w '%{http_code}\n' \
  --aws-sigv4 "aws:amz:us-east-1:transform" \
  -u "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" \
  -H "x-amz-security-token: $AWS_SESSION_TOKEN" \
  https://transform.us-east-1.api.aws/workspaces
```

Do not build that request with `eval "$(aws configure export-credentials --format env)"` in a
shell you keep using — that is what poisons the environment in the first row of the table above.

### Long runs and short SSO sessions

Extraction executes server-side and survives a local credential lapse. Local credentials are
only needed for MCP calls and S3 downloads, so re-authenticate before each download rather than
trying to hold one session across the whole run.

To extend sessions, from the Identity Center management account:

```bash
aws sso-admin update-permission-set \
  --instance-arn arn:aws:sso:::instance/<id> \
  --permission-set-arn <arn> \
  --session-duration PT8H          # max PT12H, also bounded by the role's MaxSessionDuration
```

Pinning the MCP server's environment removes the most common false negative entirely:

```json
"aws-transform-mcp": {
  "command": "uvx",
  "args": ["awslabs.aws-transform-mcp-server@latest"],
  "env": { "AWS_PROFILE": "<profile>", "AWS_REGION": "<region>" }
}
```

---

## Reference index

| Need | File |
|---|---|
| Connectivity, account setup, client-vs-account cross-check, env hygiene | `references/preflight.md` |
| GitHub / S3 / local intake, zip layout, glossary provenance | `references/code-intake.md` |
| Discovery capabilities, quality signals, infrastructure detection | `references/discovery.md` |
| Per-function loop, readiness, batch vs sequential, retries, G4 checks | `references/extraction.md` |
| HITL task catalog, payload shapes, derivation rules | `references/hitl-tasks.md` |
| State schema, resume rules, report specification | `references/state-and-reporting.md` |

---

## Downstream: turning a run into documentation

This skill produces evidence. It does not write application documentation. Once gate G2 has passed
and at least one spec bundle is delivered, `.atx/mfre/` is the input to a separate suite:

| Skill | Role |
|---|---|
| [`atx-pipeline`](../atx-pipeline/README.md) | end-to-end driver: fetch → verify → snapshot → 31 documents → published zip |
| [`atx-app-documentation`](../atx-app-documentation/README.md) | the documentation model and grounding contract |

Two things that skill depends on from this one:

1. **`snapshot_analysis.sh` must have run.** Without `.atx/mfre/analysis/`, coverage drops sharply
   because most grounded content comes from the analysis artifacts rather than the spec bundles.
2. **Partial delivery must be visible in `state.json`.** The coverage matrix reads the discovered
   scope from it to compute the `delivered of discovered` denominator. Overstating delivery here
   silently overstates every document downstream.

See [`../README.md`](../README.md) for the whole suite.

---

## Changelog

### 1.1.1

**`snapshot_analysis.sh` argument validation was silently broken on macOS.** Line 44 used bash 4's
`${req,,}` for a lowercase flag name; macOS ships bash 3.2. The resulting `bad substitution` aborted
the compound command, so `usage` never ran and a **missing required argument did not stop the
script** — it fell through to the next check. Now lowercased with `tr`, and it exits 2 with the
correct flag name. The lesson generalises: `bash -n` parses `${var,,}` without complaint, so this
class of bug only appears when the branch executes.

**`preflight.sh` gained upload-destination validation.** New `--upload-bucket`, `--upload-prefix` and
`--intend-public` flags with five checks, including a real `PutObject` probe. A first attempt used
`--body /dev/null`, which the AWS CLI rejects (`Blob values must be a path to a file`) and which
therefore reported a permission failure that did not exist; it now writes a `mktemp` file.

### 1.1.0

Corrections from a full production run. Every change is backed by observed behaviour, not
speculation.

**Scope enforcement in verification (correctness fix).** `verify_spec.py` and
`split_bundle.py` took the function set from whatever was on disk, so a batch that dropped
three of nine functions reported "6 of 6 verified" and passed. Both now accept `--state` /
`--expect` and fail on `empty_function_folder` and `function_missing_from_bundle`. Empty
folders fail even without an expected list.

**Sequential is now the default extraction shape.** Batch was the default above four
functions, and the reference claimed both shapes produced equivalent output. Measured: a
function yielding 286 functional requirements sequentially yielded 14 in a 9-function batch,
and the 9-function zip was smaller than the 1-function zip. The tradeoff table now names depth
loss.

**Re-extraction guard.** A re-run can produce a worse bundle than the one it replaces. The
richer bundle is kept as the deliverable, the new one is retained under a labelled path, and
both numbers appear in the report. G4 cannot detect this, since a thin bundle can be perfectly
self-consistent.

**G0 cannot blame the account on MCP evidence alone.** A stale MCP client reporting
`NOT_CONFIGURED` was indistinguishable from an unconfigured account, which led to a
recommendation to enable a service that was already running with an ACTIVE connector. A non-MCP
cross-check must now also fail, with the 403-versus-404 discriminator documented.

**Environment poisoning detected and prevented.** A stale `AWS_CREDENTIAL_EXPIRATION` makes
valid credentials report *"refreshed credentials are still expired"*, mimicking both an expired
login and clock skew. `preflight.sh` detects it, names it, and self-heals for its own checks;
the skill now forbids `eval "$(aws configure export-credentials --format env)"` in a persistent
shell.

**Pipeline completion claims are no longer trusted.** A run logging `Pipeline complete: 9/9
passed, 0 failed, 0 skipped` had delivered six of nine. Only G4 over the unpacked bundle
establishes what exists.

**Readiness fallback.** When the Business Function Discovery Agent is unavailable, missing-file
counts come from the discovery catalog, G3 becomes `pass_degraded`, and the loss of per-file
detail is recorded rather than papered over.

**Service-wide outages no longer consume per-function attempts.** A new `service_unavailable`
class backs off with escalating waits inside the poll budget. Previously one retry would have
failed nine functions in four minutes for an outage that cleared in fourteen.

**Also:** `--expected-run-min` judges credential headroom against the work rather than a flat 15
minutes; batch poll budget defined as per-function budget × functions; `send_message`
concurrency limit and its `HTTP 400` documented; `env` and `service_unavailable` added to the
failure policy.

### 1.0.0

Initial release.
