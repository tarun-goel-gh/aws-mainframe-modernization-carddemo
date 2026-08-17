---
name: atx-pipeline
description: Guided end-to-end run from AWS Transform spec artifacts to the 31-document application documentation suite and a shareable zip. Walks the nine phases with a gate at each decision point — credentials, partial-delivery coverage, and the publish destination — and resumes a failed run without redoing completed work. Activate when the user asks to run the whole pipeline, go end to end, fetch specs and generate docs, publish or share the documentation, or runs /atx-pipeline.
compatibility: Needs .kiro/skills/mainframe-reverse-engineering (scripts) and .kiro/skills/atx-app-documentation. AWS phases need an AWS CLI v2 profile; --offline documents an existing .atx/mfre with no AWS access. macOS bash 3.2 compatible.
license: Apache-2.0
metadata:
  author: tarun.goel
  version: "1.0.0"
  argument-hint: '[--offline] [--resume <run-id>] [--from <phase>] [--dry-run]'
  delegates-to: atx-app-documentation
---

# /atx-pipeline

One command does the work: `.kiro/skills/atx-app-documentation/scripts/run_pipeline.sh`. This skill
is the guided wrapper around it — it decides what to ask before running, what to show after each
phase, and where to stop and wait for a human.

Do not reimplement the phases in chat. The script is the executable definition of the pipeline;
narrating equivalent commands by hand produces runs that are not recorded in `run-state.json` and
therefore cannot be resumed.

## The nine phases

| # | Phase | Needs AWS | Notes |
|---|---|---|---|
| 1 | `preflight` | yes | credentials, artifact bucket, upload bucket |
| 2 | `fetch-specs` | yes | downloads `spec_gen/*.zip` |
| 3 | `verify-split` | yes | scope check, then split per business function |
| 4 | `snapshot-analysis` | yes | mirrors the analysis artifacts the documents cite |
| 5 | `coverage` | no | prerequisite gate + coverage matrix |
| 6 | `evidence` | no | one pass over every shared artifact |
| 7 | `generate` | no | compose, self-check, file |
| 8 | `package` | no | zip the run folder |
| 9 | `publish` | yes | upload and emit a link |

Phases 5-8 need no network. When SSO has lapsed and `.atx/mfre/` is already populated, `--offline`
is the fast path and it is a complete path — the documents do not depend on phases 1-4 being run
in the same session.

## Gates

Stop at each gate and wait. These are the points where continuing on an assumption produces either
a misleading document set or an unintended disclosure.

**Gate A — before phase 1.** Confirm profile, region, artifact bucket and job id. If the user has
not named an upload bucket, say that phases 8 and 9 will be skipped and the zip stays local.
Run `--dry-run` first and show the plan.

**Gate B — after phase 3.** Report delivered-of-discovered business functions. Phase 3 exits 1 and
is recorded `partial` whenever AWS Transform returned fewer functions than were discovered; that is
a normal outcome, not a failure. Name the missing functions explicitly and confirm the user wants a
documentation suite that covers a subset of the estate. Never let a partial delivery pass silently
into phase 5, because every downstream document then describes a fraction of the application while
reading like it describes all of it.

**Gate C — after phase 5.** Show the coverage matrix before generating. Lead with
delivered-of-discovered, then degraded evidence plans. If coverage is low, ask whether to generate
at all — 31 thin documents are worse than an honest gap report.

**Gate D — before phase 9.** The security gate.

- Default to a presigned URL. Say the expiry.
- `--public` must be asked for, never inferred from "share it" or "upload it".
- Before any public publish, state plainly what becomes anonymously readable: the AWS account id
  appears in 7 of the 31 documents, alongside bucket names, program and JCL names, business rules
  and the data dictionary.
- The script refuses `--public` when the upload bucket is also the artifact bucket. Do not work
  around that by widening a policy manually; the artifact bucket holds the raw source analysis.
- A presigned URL cannot outlive the credentials that signed it. With a one-hour SSO session,
  `--expires-in 604800` still dies in an hour. Report the effective lifetime, not the requested one.

## Running it

Full run:

```
.kiro/skills/atx-app-documentation/scripts/run_pipeline.sh \
  --profile <profile> --region <region> \
  --bucket <artifact-bucket> --job-id <job-id> \
  --upload-bucket <docs-bucket>
```

Documents only, no AWS:

```
.kiro/skills/atx-app-documentation/scripts/run_pipeline.sh --offline
```

Resume after a failure, without redoing what already passed:

```
.kiro/skills/atx-app-documentation/scripts/run_pipeline.sh --resume <run-id> --from <phase>
```

## Reporting

Each phase prints one line: `[n/9] <phase> <status> <elapsed> exit=<code>`. The same rows land in
`<run-folder>/00-manifest/run-log.md`, and machine-readable state in `run-state.json`. Relay the
phase lines to the user as they appear rather than summarising at the end, then close with:

- run folder and run id
- documents written, and coverage as `grounded / absent / not-extracted`
- any phase recorded `partial` or `FAILED`, with the resume command
- the share link and its real expiry, from `00-manifest/publish.md`

## Rules

- One run, one folder. The script stamps `.atx/app-docs-<YYYYMMDD-HHMMSS>` once and exports
  `ATX_DOCS_ROOT`; never pass a different `--docs-root` to individual scripts mid-run.
- Output lives under `.atx/`, which is gitignored. The zip is the distribution channel, not the
  working tree.
- Never call AWS Transform to start new analysis. This pipeline consumes a finished job.
- Never modify `.atx/mfre/` or application source from this skill.
- A phase recorded `partial` is a reportable state, not something to retry until it turns green.
- Report the coverage number before the document count.
