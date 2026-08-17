# atx-pipeline — the end-to-end workflow

From AWS Transform spec artifacts to 31 application documents and a shareable zip, in one command.

This is the reference for the workflow itself: what each phase does, what it reads and writes, where
it can legitimately come back "partial", and how to resume it. For the documentation model — the 31
documents, the grounding contract, the coverage matrix — read
[`../atx-app-documentation/README.md`](../atx-app-documentation/README.md).

---

## Prerequisites

| Requirement | Why |
|---|---|
| A **finished** AWS Transform reverse-engineering job | This pipeline consumes analysis; it never starts one |
| `.atx/mfre/state.json` with gate G2 passed | The coverage gate refuses to document an incomplete run |
| AWS CLI v2 + a profile | Phases 1-4 and 9 only. Phases 5-8 are offline |
| `python3`, `unzip`, `zip`, `shasum` | No third-party Python packages |
| bash | Written for macOS bash 3.2: no associative arrays, no `${var,,}` |

If `.atx/mfre/` does not exist, run the
[`mainframe-reverse-engineering`](../mainframe-reverse-engineering/README.md) skill first. This
pipeline cannot analyse a codebase.

---

## The nine phases

```
                    ┌──────────────── needs AWS ────────────────┐
  1 preflight  →  2 fetch-specs  →  3 verify-split  →  4 snapshot-analysis
                                                              │
                    ┌──────── offline, deterministic ──────────┘
                    5 coverage  →  6 evidence  →  7 generate  →  8 package
                                                              │
                                              9 publish ◄─────┘  needs AWS
```

| # | Phase | Reads | Writes |
|---|---|---|---|
| 1 | `preflight` | AWS credentials, both buckets | nothing (probe object is deleted) |
| 2 | `fetch-specs` | `s3://<bucket>/transform-output/<job>/spec_gen/*.zip` | `.atx/mfre/specs-raw/` |
| 3 | `verify-split` | `specs-raw/*.zip` | `.atx/mfre/specs/`, `00-manifest/bundle-selection.md` |
| 4 | `snapshot-analysis` | the job's analysis prefixes | `.atx/mfre/analysis/` (~102 MB) |
| 5 | `coverage` | `.atx/mfre/state.json`, discovery CSVs | `coverage.md`, `evidence-index.json` |
| 6 | `evidence` | every shared artifact, once | `evidence-pack.json` |
| 7 | `generate` | the evidence pack + 31 prompts | the 31 documents + 6 manifests |
| 8 | `package` | the run folder | `.atx/app-docs-<run-id>.zip` |
| 9 | `publish` | the zip | S3 object + `00-manifest/publish.md` |

Phases 5-8 need no network. When SSO has lapsed and `.atx/mfre/` is already populated, `--offline`
is both the fast path and a complete path — the documents do not depend on 1-4 running in the same
session.

---

## Quick start

```bash
S=.codex/skills/atx-app-documentation/scripts

# See the plan without touching anything
$S/run_pipeline.sh --offline --dry-run

# Documents only, from an existing .atx/mfre (~3 s)
$S/run_pipeline.sh --offline

# Everything, including publish
$S/run_pipeline.sh \
  --profile my-profile --region us-east-1 \
  --bucket <artifact-bucket> --job-id <job-id> \
  --upload-bucket <docs-bucket>
```

In chat, `/atx-pipeline` runs the same thing with a gate at each decision point.

---

## Flags

### Selection

| Flag | Effect |
|---|---|
| `--offline` | skip every phase needing AWS (1, 2, 3, 4, 9) |
| `--from <phase>` | start here, skipping earlier phases |
| `--only <phase>` | run exactly one phase |
| `--resume <run-id>` | reuse an existing run folder; phases already recorded `ok`/`partial` are skipped |
| `--no-upload` | run 1-8 and stop before publishing |
| `--dry-run` | print the plan and exit |
| `--keep-going` | continue after a fatal failure instead of stopping |

`--from` overrides the resume skip-list, so `--resume X --from generate` re-runs generation even
though it succeeded before. `--only` bypasses everything else.

### Inputs

| Flag | Default |
|---|---|
| `--profile` | required unless `--offline` |
| `--region` | the profile's configured region |
| `--bucket` | the AWS Transform job bucket, read-only |
| `--job-id` | the AWS Transform job id |
| `--mfre` | `.atx/mfre` |
| `--docs-root` | `.atx/app-docs-<YYYYMMDD-HHMMSS>` |
| `--run-id` | the current timestamp |
| `--app-name` | derived from the upstream run — see below |

### The application name

It appears in the header of all 31 documents, so it is derived rather than assumed, in this order:

1. `--app-name` (or `ATX_APP_NAME`)
2. the basename of the upstream run's `sourceOrigin`, with the archive extension and any trailing
   `-main` / `-master` / `-develop` branch suffix removed
3. the upstream workspace name
4. `Unnamed application`

Whichever applies is recorded in `00-manifest/manifest.json` as `application.nameSource`, so a reader
can tell a supplied name from a derived one without trusting the header. Pass `--app-name` when the
archive name is not the name the business uses.

### Publishing

| Flag | Default |
|---|---|
| `--upload-bucket` | none; phases 8-9 are skipped without it |
| `--upload-prefix` | `atx-app-docs` |
| `--public` | off. Opt-in only |
| `--expires-in` | `604800` (7 days, the SigV4 maximum) |

---

## Run folders

One run, one folder. The driver stamps the folder name **once** and exports `ATX_DOCS_ROOT`, so
every step of a run agrees even though each script can compute its own default:

```
.atx/app-docs-20260814-194447/       the run
.atx/app-docs-20260814-194447.zip    the deliverable, a sibling never inside the folder
.atx/app-docs-latest ──────────────► app-docs-20260814-194447
```

Invoked bare, the individual scripts resolve `$ATX_DOCS_ROOT`, then `.atx/app-docs-latest`. So an
ad-hoc `generate_docs.py` updates the most recent run instead of starting a stray one.

`.atx/` is gitignored. Runs accumulate side by side and the zip is the distribution channel, not the
working tree. Two runs over the same evidence produce byte-identical documents — only `generatedAt`,
`docsRoot`, `run-log.md` and `run-state.json` differ — so diffing two run folders shows evidence
drift rather than generator noise.

---

## Progress reporting

One line per phase, to stdout and to `00-manifest/run-log.md`:

```
[5/9] coverage           ok          0.2s  exit=0
[3/9] verify-split       partial     2.2s  exit=1
        5 bundle(s) staged, 7 function bundle(s) in specs/
[2/9] fetch-specs        FAILED      1.5s  exit=1
        ---- output ----
        fatal error: ExpiredToken ...
        ----------------
```

The in-progress redraw uses `\r` and is emitted only when stdout is a terminal, so a captured
transcript stays clean.

| Artifact | Purpose |
|---|---|
| `00-manifest/run-log.md` | markdown table: phase, status, elapsed, exit code, detail |
| `00-manifest/run-state.json` | machine-readable phase status, consumed by `--resume` |
| `00-manifest/publish.md` | the share link and its **real** expiry |
| `00-manifest/bundle-selection.md` | which extraction attempt each function came from |

Phase stdout is captured to a `mktemp` directory **outside** the run folder. That is a disclosure
boundary, not tidiness: phase 8 zips the run folder, and preflight's output contains the caller's
account id and assumed-role ARN.

---

## Statuses

| Status | Meaning | Stops the run? |
|---|---|---|
| `ok` | exit 0 | no |
| `partial` | non-zero, but a declared expected outcome | **no** |
| `skipped` | not selected; the reason is recorded | no |
| `FAILED` | unexpected non-zero | yes, unless `--keep-going` |

### `partial` is not a failure

Phase 3 exits 1 whenever AWS Transform delivered fewer business functions than were discovered. For
one measured estate that was the standing state: 11 discovered, 9 scoped, 6 delivered. Three scoped functions
came back with empty requirements, which is an AWS-side outcome, not a pipeline fault.

Treating that as failure would mean never documenting this estate. Treating it as success would mean
31 documents that describe six functions while reading as though they describe the application. So
it is recorded `partial`, the run continues, and the coverage matrix carries the `6 of 11`
denominator into every count.

### Fail-fast

The phases are dependency-ordered, so a fatal failure stops the run and names what it stopped
before. Without that, a credential failure in phase 2 leads straight into a 102 MB download in
phase 4 that cannot succeed.

---

## Two mechanisms worth understanding

### Richest-wins bundle merge (phase 3)

AWS Transform writes **one zip per generation attempt**, each containing only the functions that
attempt produced. The delivered estate is therefore the *union* across zips, and neither size nor
recency identifies the best copy:

- the largest zip in one measured job held exactly **one** function
- one function came back with **294** requirements on the first attempt and **14** on a later one

So phase 3 stages every zip, splits each into its own output, and then chooses per function by
requirement count (tie-break: bytes). The existing `specs/` entry competes too, which makes a re-run
monotonic: the estate can improve or hold, never degrade. Every decision lands in
`bundle-selection.md`:

```
| Business function | Kept from | Requirements | Bytes | Rejected |
| AccountBalance... | 20260806_145108 | 294 | 81708 | 20260813_071942 (14 reqs, 8576 B) |
```

### Disclosure gate (phase 8)

The archive is what leaves the machine, so it is where the pipeline asserts what may not leave.
Before recording the zip, phase 8 scans every entry for:

- IAM/STS principal ARNs (`assumed-role/`, `user/`)
- `ASIA…` / `AKIA…` access key ids
- `X-Amz-Security-Token=` (a presigned URL pasted into a file)
- `aws_secret_access_key` assignments

A hit deletes the zip and fails the phase. The AWS **account id** is deliberately not on that list:
it appears in 7 of the 31 documents by design, and the user is told so before publishing.

---

## Publishing

Default is a presigned URL: no policy change, one object exposed, self-expiring.

```
[9/9] publish  ok
  ## Share link
  Presigned, expires in 604800 s from generation.
  > The signing credentials expire in 3404s, before the requested 604800 s.
```

A presigned URL **cannot outlive the credentials that signed it**. With a one-hour SSO session,
`--expires-in 604800` still dies in an hour, so the phase compares the two and reports the real
lifetime. For a genuinely long-lived link, sign with an IAM user's long-term key or use `--public`.

### `--public`

Opt-in. Writes a prefix-scoped statement and **merges** it into any existing bucket policy rather
than replacing it, because `put-bucket-policy` replaces the whole document:

```json
{
  "Sid": "AtxAppDocsPublicRead",
  "Effect": "Allow",
  "Principal": "*",
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::<bucket>/<prefix>/*"
}
```

Scoped to the prefix, so other prefixes in the same bucket stay private and the bucket cannot be
listed anonymously. Re-running replaces the statement by `Sid` rather than appending a duplicate.

**`--public` is refused when the upload bucket is also the artifact bucket.** That bucket holds
`transform-output/` — the raw source analysis, spec bundles and data dictionary — and a policy there
is one careless edit from exposing all of it. Give the deliverable its own bucket.

Before publishing publicly, know what becomes anonymously readable: the AWS account id in 7 of the
31 documents, plus bucket names, program and JCL names, business rules and the data dictionary.

To revoke:

```bash
aws s3api delete-bucket-policy --bucket <bucket>    # if AtxAppDocsPublicRead is the only statement
```

---

## Expected result

For one measured job, a clean run produced:

```
31 documents
111 grounded / 90 evidence-absent / 0 not-extracted  (55%)
4 complete / 25 partial / 2 unavailable
6 of 11 discovered business functions covered
```

The two `unavailable` documents (`security_architecture`, `modernization_strategy`) have zero
grounded sections because the evidence genuinely does not exist. That is a reported outcome, not a
gap to paper over.

Use those numbers as the regression baseline. A change in document count or grounded sections
without a change in upstream evidence means the generator moved.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Credentials were refreshed, but the refreshed credentials are still expired` | stale `AWS_CREDENTIAL_EXPIRATION` in the shell | the driver unsets it; for manual commands prefix `env -u AWS_CREDENTIAL_EXPIRATION -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN` |
| Preflight passes, next phase gets `ExpiredToken` | two different credential sources | pass `--profile` to the driver, not just to preflight |
| `zsh: command not found: env -u ...` | zsh does not word-split unquoted variables | use a function: `atx() { env -u ... aws "$@"; }` |
| Phase 3 exits 1 | fewer functions delivered than discovered | expected; read `coverage.md` |
| `BLOCKED: no upstream run at .atx/mfre/state.json` | no MFRE run | run `mainframe-reverse-engineering` first |
| `REFUSING TO PACKAGE` | credential material in the run folder | remove the named files; report it, the generator should not have written them |
| Presigned link dies early | session shorter than `--expires-in` | expected; use `--public` or an IAM user key |
| `SignatureDoesNotMatch` on a presigned URL | signed against the wrong region | pass the bucket's own region |

Resume after any failure without redoing what passed:

```bash
$S/run_pipeline.sh --resume <run-id> --from <phase>
```

---

## Design notes

**Why a script and not chat steps.** Narrating equivalent commands produces runs that are not
recorded in `run-state.json` and therefore cannot be resumed, and it makes determinism
unverifiable. The script is the executable definition; the skill is the guided wrapper.

**Why the stamp is computed once.** Each script can derive its own default root. If two steps
computed their own timestamps, one run would straddle two folders. The driver stamps once and
exports it.

**Why scratch files live outside the run folder.** Phase 8 archives that folder. Anything scratch
inside it becomes archive content, and the archive may be published anonymously. This was a real
leak, not a hypothetical one.

**Why `partial` exists at all.** A binary pass/fail forces a choice between refusing to document a
partial estate and silently overstating coverage. Neither is acceptable, so partial delivery is a
first-class state that flows into the coverage denominator.
