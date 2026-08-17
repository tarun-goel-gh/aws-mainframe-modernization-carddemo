# State, resume, and reporting

## Layout

```
.atx/mfre/
├── state.json                  ← single source of truth
├── source.zip                  ← packaged source (local/github modes)
├── inventory.csv               ← per-file classification from packaging
├── discovery/                  ← business function catalog artifacts
│   ├── business_function.csv
│   └── business_function.json
├── analysis/                   ← analysis artifacts (scripts/snapshot_analysis.sh)
│   ├── code-analysis/              per-file type, LOC, complexity, dependencies, missing files
│   ├── data-analysis/              data lineage + field-level data dictionary
│   ├── business-function-discovery/
│   └── snapshot-manifest.json
├── specs/<FunctionSlug>/       ← one verified bundle per function
│   ├── <spec_gen_specs_*.zip>
│   ├── spec/<FunctionSlug>/{requirements.md,traceability.yaml,discovery/programs.yaml}
│   └── verification.json
├── report.md                   ← generated, never hand-edited
└── manifest.json               ← generated, machine-readable
```

Add `.atx/` to `.gitignore` unless the team wants artifacts committed. Say which you did.

## state.json

```json
{
  "schemaVersion": 1,
  "runId": "mfre-20260812-2115",
  "stage": "preflight|intake|job|discovery|extraction|report|done",
  "autonomy": {
    "level": "autonomous|human-touch",
    "maxPollMinutes": 90,
    "batchMode": true,
    "batchSize": 10,
    "scope": ["<function name>", "…"],
    "excludedInfrastructure": [
      { "name": "<function name>", "signals": ["build toolchain", "no business outcome"] }
    ]
  },
  "aws": { "profile": "…", "region": "…", "accountId": "…" },
  "workspace": { "id": "…", "name": "…" },
  "job": { "id": "…", "name": "…", "agent": "…", "createdAt": "…" },
  "connector": { "id": "…", "type": "…", "bucket": "…", "status": "ACTIVE" },
  "source": {
    "mode": "github|s3zip|local",
    "origin": "…", "commit": "…",
    "zipKey": "…", "zipSha256": "…",
    "fileCounts": { "cobol": 42, "jcl": 61, "copybooks": 88, "scheduler": 2 },
    "companions": { "data": 14, "docs": 3, "noiseDropped": 3 },
    "unknownShare": 0.03,
    "glossary": true,
    "glossaryProvenance": "user-supplied|auto-drafted-unverified|absent"
  },
  "discovery": {
    "completedAt": "…",
    "catalogPath": ".atx/mfre/discovery/business_function.csv",
    "functions": [
      { "name": "…", "slug": "…", "category": "batch|online|mixed",
        "dataPaths": 10, "entryPoints": 8, "loc": 8269, "missingFiles": 3,
        "entryPointList": ["…"], "isInfrastructure": false }
    ]
  },
  "gates": { "G0": "pass", "G1": "pass", "G2": "pass" },
  "answeredTasks": [
    { "taskId": "…", "title": "…", "at": "…", "derivation": "connector discovered at G0",
      "payload": { "connectorId": "…", "connectorType": "…" } }
  ],
  "awaitingUserTasks": [ { "taskId": "…", "title": "…", "reason": "severity CRITICAL" } ],
  "functions": {
    "<Function Name>": {
      "slug": "…",
      "status": "succeeded",
      "attempts": 1,
      "readiness": { "missing": [], "unsupported": ["AWS.M2.X.SYSTRAN"] },
      "specZip": "spec_gen_specs_20260806_145108.zip",
      "specKey": "transform-output/<jobId>/spec_gen/…",
      "localPath": ".atx/mfre/specs/<slug>",
      "metrics": { "reqF": 286, "reqN": 4, "openQuestions": 16,
                   "rulesTotal": 328, "captured": 286, "notApplicable": 42,
                   "programs": 9, "sections": 14 },
      "verification": { "gate": "pass", "warnings": ["discovery/programs.yaml is empty"] },
      "startedAt": "…", "finishedAt": "…", "durationMin": 42,
      "failure": null
    }
  },
  "report": { "markdown": ".atx/mfre/report.md", "manifest": ".atx/mfre/manifest.json", "generatedAt": "…" },
  "updatedAt": "…"
}
```

Write after **every** stage transition and after **every** function outcome — before telling
the user anything. If the session dies between the work and the write, the work is invisible.

## Resume rules

| Observed state | Re-enter at |
|---|---|
| no `state.json` | Stage 1 Preflight (fresh run) |
| `stage: preflight`, G0 not pass | Stage 1 |
| `stage: intake`, no `source.zipKey` | Stage 2 |
| `stage: job`, no `job.id` | Stage 3 |
| `job.id` present, `discovery.functions` empty | Stage 4 |
| `discovery.functions` present, functions with non-terminal status | Stage 5, skipping terminal ones |
| all scoped functions terminal, no `report.generatedAt` | Stage 6 |
| report generated | done — offer forward engineering |

Always re-verify auth on resume; credentials expire between sessions. Do **not** re-verify
completed gates.

Two different notions of "done" — do not conflate them:

- **Skip on resume**: `succeeded`, `skipped`, and — after 2 attempts — `failed`,
  `failed_verification`. `timed_out`, `readiness_blocked`, and `awaiting_user` are resumable
  and should be retried in a new session.
- **Publishable in a report**: all of the above. Only `pending`, `extracting`, and `verifying`
  block report generation, because they mean the run is still in flight. A run that ends with
  timeouts or blocked functions must still be reportable — that is the whole point of
  continuing past a failure.

## Report

`scripts/build_report.py` generates both outputs from state. Never hand-write the report;
generated output cannot drift from what actually happened.

### Headline

Lead with `N of M business functions succeeded`, then total requirements produced and total
rules captured. If anything failed, name it in the first two sentences.

### Main table

| Business function | Status | Spec zip | Reqs (F/N) | Open Qs | Rules captured | Programs | LOC | Data paths | Verification |
|---|---|---|---|---|---|---|---|---|---|

- **Status** — display label from the vocabulary in `references/extraction.md`
- **Spec zip** — basename; full key and local path go in the manifest
- **Reqs (F/N)** — functional / non-functional counts
- **Rules captured** — `captured/total` with the not-applicable count noted
- **Verification** — `pass`, `pass (N warnings)`, or `FAIL: <check>`

### Supporting sections

1. **Run context** — account, region, workspace name, job name, source mode + commit/sha256,
   glossary present, autonomy level used.
2. **Coverage** — functions discovered vs scoped vs succeeded; excluded infrastructure with
   rationale.
3. **Warnings** — grouped by type across functions, each naming the affected function.
4. **Failures** — one block per failure: class, reason, attempts, retained artifacts, and the
   specific next action.
5. **Readiness exceptions** — skipped unsupported files and any missing files accepted, per function.
6. **Checkpoints answered autonomously** — every task answered without the user, with the
   derivation used. Plus any parked at a hard stop and why.
7. **Open questions rollup** — total `OQ-*` across functions, which are architectural decisions
   (atomicity, rollback, reference-data placement) versus clarifications. These are the real
   handoff items for the forward-engineering team.
8. **Next step** — forward engineering entry point, named but not started.

### manifest.json

Machine-readable sibling for pipelines and later automation:

```json
{
  "runId": "…", "generatedAt": "…",
  "job": { "workspaceName": "…", "jobName": "…" },
  "summary": { "discovered": 11, "scoped": 9, "succeeded": 8, "failed": 1,
               "totalReqF": 1420, "totalReqN": 22, "totalOpenQuestions": 63 },
  "functions": [
    { "name": "…", "slug": "…", "status": "succeeded",
      "specZip": "…", "specKey": "…", "localPath": "…",
      "metrics": { }, "warnings": [ ], "failure": null }
  ]
}
```

### Gate G5

- [ ] No scoped function is still in flight (`pending`, `extracting`, `verifying`)
- [ ] Every status is one of the documented values
- [ ] Every `succeeded` row's `localPath` exists on disk and contains `requirements.md`
- [ ] Every `succeeded` row's verification gate is `pass`
- [ ] Aggregate counts reconcile with the per-function breakdown — totals aggregate
      **succeeded functions only**, so any breakdown list must be filtered the same way
- [ ] Every failure has a class and a next action
- [ ] Warnings are attributed to specific functions

Fail → fix state or re-verify; do not publish a report that cannot be reconciled.

## Reporting honesty

- Never mark `succeeded` without a passing G4 on a file that exists locally.
- Distinguish `timed_out` (probably still running server-side, resumable) from `failed`.
- Quote real numbers from artifacts; never estimate a count you did not compute.
- State what was **not** covered as prominently as what was: excluded functions, skipped
  unsupported files, and warnings are part of the result.
- No pricing, no duration estimates for future runs. Elapsed times already measured are fine.
