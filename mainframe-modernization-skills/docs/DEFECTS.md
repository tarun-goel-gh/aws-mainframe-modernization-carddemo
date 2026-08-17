# Defect log

Every defect found in the suite, its root cause, and how the fix was proven.

Kept because several of these are the *reason* a mechanism exists, and a future maintainer who does
not know that will remove the mechanism. The CI gates in `tools/` map almost one-to-one onto entries
here.

Entries marked **(summarised)** come from earlier in the working session, carried forward through a
context summary; the rest were found and verified directly, with the evidence given.

---

## Severity key

| | Meaning |
|---|---|
| **S1** | data disclosure, or silently wrong output a reader would trust |
| **S2** | silent data loss, or a check that fails to check |
| **S3** | wrong behaviour that is visible when it happens |
| **S4** | cosmetic or ergonomic |

---

## S1 — Disclosure and correctness

### D-01 · Internal scratch files published in an anonymously readable archive

**Severity** S1 · **Where** `run_pipeline.sh` phase ordering

The published zip contained eight `.phase-*.out` files. `.phase-preflight.out` held the preflight JSON
including the caller's account id and assumed-role ARN — which carries the SSO permission set name
(`AWSReservedSSO_AdministratorAccess_<id>`) and a corporate email address.

**Root cause.** Scratch files were deleted at the end of the script, but the archive is built in phase
8, before that cleanup. Not a race — a straightforward ordering error.

**Fix.** Phase output moved to a `mktemp` directory outside the run folder, with a trap for cleanup.
Packaging cannot include what was never in the folder. Plus two redundant guards — `ph_package` clears
stale scratch files for `--resume` against older run folders, and `zip -x` excludes the pattern — and
a **disclosure gate** that scans every archive entry for principal ARNs, `ASIA`/`AKIA` key ids,
`X-Amz-Security-Token=` and secret-key assignments, deleting the zip and failing the phase on a hit.

**Proven.** Gate run against the known-bad archive caught exactly the offending file. Live object
re-fetched with all credentials stripped: zero hits for scratch files, ARNs, keys, tokens or the email.

**Guard** `make check-secrets`, and the gate inside phase 8.

> The account id is deliberately excluded from the gate's patterns. It appears in 7 of 31 documents by
> design and is disclosed before publishing. A gate that fires on expected content gets disabled.

---

### D-02 · Application name hardcoded into every document header

**Severity** S1 · **Where** `generate_docs.py`

The header line was a literal: `**Application:** CardDemo`. Point the tool at any other codebase and
all 31 documents claim to be about CardDemo — the most visible possible way for a generic tool to lie
about its subject.

**Fix.** Derived with recorded provenance: `--app-name` / `ATX_APP_NAME`, else the upstream
`sourceOrigin` archive basename with extension and any trailing `-main`/`-master`/`-develop` stripped,
else the workspace name, else `Unnamed application`. The choice is written to `manifest.json` as
`application.nameSource` so a reader can distinguish a supplied name from a derived one.

**Proven.** Seven derivation cases unit-tested. Full run: 0 of 31 documents carry the old literal,
31 of 31 carry the derived name, both override paths reach every document, and coverage is unchanged
at 111/90/0.

**Guard** `make check-generic`.

---

### D-03 · Newest-wins bundle selection destroyed extracted requirements

**Severity** S1 · **Where** `run_pipeline.sh` phase 3

AWS Transform writes one zip per generation attempt. Processing them in timestamp order let a later,
worse attempt overwrite a better one: a function's requirements file went from **81,708 bytes / 294
requirements** to **8,576 bytes / 14 requirements**.

Two further measurements killed the alternative heuristic: the **largest** zip in the job contains
exactly one function, and the delivered estate is the union across zips, not any single one.

**Fix.** Stage every zip, split each into its own output, then select per function by requirement count
with bytes as tie-break. The existing `specs/` entry competes too, making a re-run **monotonic** — the
estate can improve or hold, never degrade. Decisions recorded in `00-manifest/bundle-selection.md`.

**Proven.** From-scratch rebuild with no prior tree selected the 294-requirement copy, and found a
function bundle the single-zip approach missed entirely — from the earliest zip, which largest-wins
could never have picked. Zero regressions across all functions.

---

### D-04 · Scope-blind verification reported success on incomplete delivery

**Severity** S1 · **(summarised)** · **Where** `verify_spec.py`, `split_bundle.py`

Verification counted what it found rather than comparing against what was *discovered*, so a bundle
missing three of nine business functions reported "6 of 6 verified" and exited 0.

**Fix.** `--expect` / `--state` flags supply the discovered scope; new `empty_function_folder` and
`function_missing_from_bundle` failures. Reporting "N of N verified" where N was obtained by scanning
is a reporting error, not a shortcut.

**Proven.** The nine-function bundle now fails, naming the three empty folders, and exits 1 — and still
fails on empty folders even without `--state`.

---

## S2 — Checks that failed to check, and silent loss

### D-05 · bash 4 expansion meant a missing required argument did not stop the script

**Severity** S2 · **Where** `snapshot_analysis.sh`

```bash
[[ -n "${!req}" ]] || { echo "ERROR: --${req,,} is required" >&2; usage; }
```

macOS ships bash 3.2, which has no `${var,,}`. The resulting `bad substitution` aborted the compound
command, so **`usage` never ran** and execution continued past the validation. The visible symptom was
a cosmetic message error; the actual effect was a validation that did not validate.

**Fix.** Lowercase via `tr`.

**Proven.** Missing `--bucket` now exits 2 with `ERROR: --bucket is required`; missing `--job-id`
likewise with the correct flag name.

**Guard** `make check-bash32`.

> `bash -n` parses `${var,,}` without complaint, so this class of defect only appears when the branch
> executes. A syntax check is not sufficient.

---

### D-06 · Preflight write probe reported a permission failure that did not exist

**Severity** S2 · **Where** `preflight.sh`

The upload-bucket write check used `aws s3api put-object --body /dev/null`. The AWS CLI rejects that
with `Blob values must be a path to a file`, which the script reported as a denied `PutObject`. A
false failure on a security check is worse than no check — it teaches the operator to ignore it.

**Fix.** Write a real `mktemp` file, then delete the probe object.

**Proven.** Against a live bucket: probe accepted, cleaned up, no objects left behind.

---

### D-07 · Publish emitted the share link into a file it then deleted

**Severity** S2 · **Where** `run_pipeline.sh` phase 9

`run_phase` captures each phase's stdout to compose the log, and the driver deletes those files at the
end. The presigned URL — the entire deliverable of phase 9 — was written to stdout and therefore
vanished. The phase reported `ok` while producing nothing usable.

**Fix.** The link is persisted to `00-manifest/publish.md` and reprinted in the closing summary.

**Proven.** Live run emitted the URL to the console and to disk.

---

### D-08 · Driver never exported its own AWS credentials

**Severity** S2 · **Where** `run_pipeline.sh`

Preflight passed, then `fetch-specs` failed with `ExpiredToken` 1.5 seconds later. It looked like a
race. It was two different credential sources: `preflight.sh` and `snapshot_analysis.sh` each fix their
own environment in their own subprocess, but the driver makes AWS calls directly in phases 2 and 9 and
those resolved against the caller's shell — typically the default profile, usually expired.

This is precisely the trap the skill's own reference documentation warns about.

**Fix.** The driver unsets the stale credential variables and exports `AWS_PROFILE` / `AWS_REGION` for
itself, deriving the region from the profile when not given.

**Proven.** `fetch-specs` went from `FAILED exit=1` to `ok 2.8s`.

---

### D-09 · No fail-fast: a doomed 102 MB download after a credential failure

**Severity** S2 · **Where** `run_pipeline.sh`

After `fetch-specs` failed fatally, the run continued into phase 4's full analysis download, which
could not succeed.

**Fix.** Phases are dependency-ordered, so a fatal failure stops the run and names the phase it
stopped before. `--keep-going` overrides. `partial` never stops anything.

---

### D-10 · Batch extraction lost requirement depth

**Severity** S2 · **(summarised)** · **Where** extraction strategy

Batched extraction produced **286 requirements → 14** for the same function, and a nine-function bundle
came back smaller than a single-function bundle.

**Fix.** Sequential extraction became the default, with the measured evidence recorded in the skill's
reference documentation so the decision is not silently reverted.

---

### D-11 · Skill install directories scanned as application source

**Severity** S2 · **Where** `verify_spec.py`

Source walks excluded `.git`, `node_modules`, `.atx` and `.kiro`, but not `.claude` or `.codex`. On
those runtimes the suite's own installed tree would be indexed as customer source, corrupting the
program-resolution check that verification depends on.

**Fix.** A named `EXCLUDED_SCAN_DIRS` constant covering every runtime dot-directory plus `.venv` and
`__pycache__`. `split_bundle.py` imports from `verify_spec`, so one fix covers both.

**Proven.** Planted `DECOYPGM.cbl` in `.claude/skills/demo/` and `REALPGM.cbl` in `app/`; only
`REALPGM` was indexed.

---

### D-12 · Stale publication record baked into a re-packaged archive

**Severity** S2 · **Where** `run_pipeline.sh` phase 8

`publish.md` is written by phase 9. Re-packaging a previously published run therefore embedded the
*previous* — possibly withdrawn — URL into the new archive.

**Fix.** `ph_package` removes it. An archive cannot contain a truthful record of its own publication;
one from a previous publish is worse than none.

---

## S3 — Visible wrong behaviour

### D-13 · Documentation claimed the suite used no MCP

**Severity** S3 · **Where** `MIGRATION.md`

An audit for MCP usage searched for the wrong terms and concluded the suite shelled out to the AWS CLI
exclusively. True for `atx-app-documentation`; false for `mainframe-reverse-engineering`, whose entire
control plane is MCP tool calls. A migration performed against that document would have produced a
non-functional reverse-engineering skill.

**Fix.** Corrected, with the surface measured: 55 server-generic tool references port unchanged, 5
host-specific references do not. Added per-runtime configuration for both targets and the credential
pinning requirement.

---

### D-14 · Generator gaps reported as evidence gaps

**Severity** S3 · **(summarised)** · **Where** `generate_docs.py`, prompts

Sections the generator had not implemented were marked with the same "evidence unavailable" marker as
sections where evidence genuinely did not exist — blaming AWS Transform for the tool's own shortfall.

**Fix.** Two distinct markers: `Not available from AWS Transform analysis` versus `Not extracted by
this run`. A single marker was considered and rejected. All 16 `not-extracted` sections were later
closed by writing the missing parsers, so the count is now 0 and every remaining gap is genuine.

---

### D-15 · Per-document evidence index asserted provenance it did not have

**Severity** S3 · **(summarised)** · **Where** `generate_docs.py`

Every document carried the same boilerplate evidence table, asserting sources that specific document
had never read.

**Fix.** Content builders record the artifacts they actually read; `document-evidence.json` holds
per-document fingerprints. This is also what makes staleness detection possible.

---

### D-16 · Account-setup conclusions drawn from MCP evidence alone

**Severity** S3 · **(summarised)** · **Where** `preflight.md`, gate G0

`get_status` and `list_resources` ride the same MCP client. When that client is stale, its failure is
indistinguishable from an unconfigured AWS account. This produced a real, expensive misdiagnosis: a
user was told to enable a service that was already running.

**Fix.** A non-MCP cross-check must also fail before any account-setup conclusion may be reported —
Transform CLI, a SigV4 request where 403 means denied and 404 `UnknownOperationException` means access
works, or the console. Reporting otherwise is a gate violation, not a judgement call.

---

## S4 — Ergonomic

### D-17 · Progress redraw corrupted captured output

`\r` redraw left `...[5/9] coverage ok` fragments when stdout was not a terminal, which is how a chat
transcript captures it. Now TTY-gated.

### D-19 · The drift gate passed while verifying nothing

**Severity** S2 · **Where** `Makefile`, `check-drift`

`git diff --exit-code -- dist/` exits 0 on **untracked** files. Before `dist/` was committed, the gate
that exists to make committed generated output safe reported success without comparing anything — and
`make check` reported "all checks passed".

A gate that cannot check must fail, not pass. It now verifies git is present and `dist/` is tracked
before diffing, and refuses with a message naming the fix. It also grew a git-independent determinism
check: build twice over a snapshot and compare, which answers "is the build reproducible" separately
from "does the committed output match".

**Proven.** In an untracked tree the target now exits 1 with the tracking error, having first confirmed
determinism.

---

### D-20 · `make help` hid a security gate

**Severity** S4 · **Where** `Makefile`

The help target matched `^[a-z-]+:`, which excludes digits, so `check-bash32` never appeared in
`make help`. A gate nobody can discover is a gate nobody runs. Pattern now `^[a-z0-9-]+:`.

---

### D-21 · `make test` failed identically whether the fixture was missing or the test broke

**Severity** S3 · **Where** `Makefile`, `tests/run_golden.sh`

`tests/run_golden.sh` did not exist, so `make test` died with `No such file or directory` — and once
written, its "no fixture, skipped" exit was treated by make as a failure. Absence of a fixture and a
failing assertion produced the same red result, which is the kind of ambiguity that gets a test target
ignored.

Exit 3 now means skipped and `make test` reports `test: skipped` with exit 0. A real assertion failure
still fails.

---

### D-18 · bash-3.2 lint false-positived on its own documentation

The first version of `check_bash32.sh` matched three comments that *explained* the constraint. A lint
that cries wolf gets ignored, so comments are stripped before matching:

```python
code = line.split('#', 1)[0]
```

Comment-aware, it reports 0 genuine constructs. Fixed before the gate shipped.

---

## Defect-to-guard map

| Guard | Catches |
|---|---|
| `make check-secrets` | D-01 |
| `make check-generic` | D-02 |
| `make check-bash32` | D-05, D-18 |
| `make check-drift` | hand-edited variants, non-deterministic builds, D-19 |
| `make check-frontmatter` | Kiro-only keys leaking into other runtimes |
| `make test` (golden run) | D-02, D-03, D-14, D-15 regressions |
| disclosure gate in phase 8 | D-01, recurrence by any route |

Four defects have no automated guard and rely on review: D-08 and D-09 (driver credential and
control flow), D-13 (documentation accuracy), D-16 (diagnostic discipline). These are the ones most
likely to come back.
