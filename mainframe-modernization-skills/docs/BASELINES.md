# Baselines

What the golden test asserts, and the distinction between a *reference* run and a *fixture* run.

---

## Two different baselines

**Reference baseline** — the numbers from a real AWS Transform job. Useful for sanity, useless for CI:
the evidence is a customer codebase and 102 MB of analysis artifacts.

**Fixture baseline** — the numbers from the committed synthetic fixture, recorded in
`tests/golden/baseline.txt`. This is what CI asserts. Its values will *not* match the reference
baseline and should not be made to.

Conflating the two is the trap here. A tool meant to be generic must not have one job's numbers baked
into its test suite.

---

## Reference baseline

From a full nine-phase run against a real job, from an empty local state.

| Measure | Value |
|---|---|
| documents | 31 |
| sections grounded | 111 |
| sections evidence-absent | 90 |
| sections not-extracted | 0 |
| grounded share | 55% |
| document statuses | 4 complete / 25 partial / 2 unavailable |
| business functions | 6 delivered / 9 scoped / 11 discovered |
| archive | ~0.27 MB, 54 files |

Phase timings, for order-of-magnitude only:

```
1  preflight          18.8s
2  fetch-specs         2.8s
3  verify-split        2.2s   partial, exit 1 — expected
4  snapshot-analysis  34.0s   102 MB
5  coverage            0.2s
6  evidence            0.6s
7  generate            0.4s
8  package             0.4s
9  publish             6.7s
```

Phases 5-8 total under two seconds, which is why `--offline` is a practical inner loop.

**`0` not-extracted is the meaningful figure.** It means every remaining gap is genuine evidence
absence rather than a generator shortfall. If a change pushes that above zero, a parser regressed.

---

## Determinism

Asserted over the 31 documents and the substantive manifest fields. Two consecutive runs must differ
only in:

- `generatedAt`
- `docsRoot`
- `run-log.md` (wall-clock timings)
- `run-state.json`

Verified as **0 substantive differences** in `manifest.json` and byte-identical documents.

The archive itself is *not* byte-reproducible — zip embeds mtimes. Its sha256 is recorded in
`run-log.md` for traceability, not for determinism.

```bash
diff -r runA runB -x run-log.md -x run-state.json
```

---

## Fixture baseline

**Built.** 19 files, 80 KB, at `tests/fixtures/mfre-synthetic/`. Recorded in
`tests/golden/baseline.txt`:

```
docs=31
grounded=90
absent=111
notextracted=0
statuses=complete:3,partial:24,unavailable:4
delivered=2/5
appName=legacy-billing
appNameSource=derived from upstream sourceOrigin
```

Note this grounds **fewer** sections than the reference run (90 against 111) and reports more
`unavailable` documents. That is the expected consequence of a small fixture and must not be "fixed" by
inflating it — the fixture exists to detect change, not to look impressive.

`appName=legacy-billing` is derived from `s3://synthetic-fixtures/legacy-billing-main.zip`, which
exercises both extension and branch-suffix stripping. `delivered=2/5` comes from a deliberately mixed
estate: two delivered, one scoped-but-no-spec, one excluded as infrastructure, one never scoped.

### Fixture layout

Two parts, because the pipeline reads from two places:

```
tests/fixtures/mfre-synthetic/
├── mfre/      -> staged to <work>/.atx/mfre    the upstream run
└── app/       -> staged to <work>/app          application source
```

`app/` is not optional. `extract_evidence` reads BMS maps, linkage and error-handling constructs
directly from the workspace, so a fixture without it silently understates coverage.

### Proven to fail

A golden test that cannot fail is decoration. Three mutations were run against this fixture, each
restoring itself afterwards:

| Mutation | Detected by |
|---|---|
| remove a function from `autonomy.scope` | `delivered=2/5` → `1/5` |
| change `source.origin` | `appName=legacy-billing` → `other-estate` |
| delete one data-dictionary CSV | `grounded` 90→85, `absent` 111→116, `statuses` complete 3→2, unavailable 4→6 |

The first two moved *only* their own measurement, which is the evidence that the assertions are
independent rather than redundant. The third is the one that proves section counts respond to evidence
at all.

### Sizing

Measured against the reference run:

| | Files | Size |
|---|---|---|
| analysis artifacts present | 2,430 | 95 MB |
| analysis artifacts **cited by documents** | 4 | 479 KB |

So the fixture does not need the full analysis tree. A synthetic fixture needs:

```
tests/fixtures/mfre-synthetic/
├── state.json                    discovered scope, gates, source origin
├── manifest.json
├── discovery/
│   ├── business_function.csv
│   └── business_function.json
├── specs/<Function>/spec/<Function>/
│   ├── requirements.md
│   ├── traceability.yaml
│   └── discovery/programs.yaml
└── analysis/                     a thin slice: code-analysis, data dictionary, data lineage
```

Estimated 1-2 MB.

### It must exercise the interesting cases

A fixture that only contains happy-path evidence tests almost nothing. It needs, at minimum:

| Case | Why |
|---|---|
| a **delivered** function with requirements and rules | the normal path |
| a **scoped-no-spec** function (empty requirements) | the partial-delivery path, and the `6 of 11` denominator |
| an **excluded-infrastructure** function | the classifier |
| **two competing bundles** for one function, differing in requirement count | the richest-wins merge (D-03) |
| at least one genuinely **absent** evidence class | the `unavailable` document status |
| a `sourceOrigin` that is **not** the workspace name | the application-name derivation (D-02) |

### Constraints

- **Synthetic, not derived from a customer codebase.** No real account ids, bucket names, profile
  names, program names or ARNs. `make check-secrets` and `make check-generic` run over
  `tests/fixtures/` too.
- Program names should be obviously fictional — `SYNTHPGM01`, `FIXTPGM02` — so a fixture artifact
  appearing in real output is immediately recognisable.
- Small enough to diff by hand when the golden test fails.

### Recording the baseline

Once built, run twice and record the values here:

```bash
tests/run_golden.sh --record
```

The recorded values become the assertion. They are expected to be *lower* than the reference baseline —
a small fixture grounds fewer sections. That is correct, not a regression.

---

## What the golden test asserts

Implemented in `tests/run_golden.sh`. It builds the Kiro variant, stages the fixture into a `mktemp`
workspace — a test run must never write into the repository — and runs the pipeline twice.

Asserted today:

| # | Assertion | Mechanism |
|---|---|---|
| 1 | pipeline completes; no phase `FAILED` | non-zero exit from the driver fails the run |
| 2 | document count matches the baseline | `docs=` measurement |
| 3 | grounded / absent / not-extracted match | `grounded= absent= notextracted=` |
| 4 | document statuses match | `statuses=` |
| 5 | `delivered of discovered` matches | `delivered=` from `manifest.json` |
| 6 | two runs produce byte-identical documents | `diff -r` excluding `00-manifest` |
| 7 | the application name is **derived**, not supplied | `appNameSource=` must not be `operator-supplied` |
| 8 | the archive passes the disclosure gate | a missing zip means packaging refused |

Assertions 5 and 7 exist because they are the regressions that would otherwise be invisible — the
output would still look like a complete, plausible document set.

Not yet asserted: that `bundle-selection.md` shows the richest attempt winning where bundles compete.
That needs the fixture to actually contain two competing bundles, which is why it is on the required-cases
list above.

### Recording and re-recording

```bash
tests/run_golden.sh --record     # write tests/golden/baseline.txt
tests/run_golden.sh              # assert against it
```

Exit 3 means "no fixture, skipped", and `make test` reports that as success. A missing fixture and a
failing assertion must not look the same, or the target gets ignored.

When a change moves the baseline legitimately, re-record **and** state the movement in `CHANGELOG.md`.
Per [`VERSIONING.md`](VERSIONING.md), a document-content change without an evidence change is
indistinguishable from a regression otherwise.
