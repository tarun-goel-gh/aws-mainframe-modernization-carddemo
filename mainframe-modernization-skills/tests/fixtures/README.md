# tests/fixtures/

Synthetic evidence for the golden run. **Built** — `mfre-synthetic/`, 19 files, 80 KB. The recorded
baseline and the mutations that prove it can fail are in
[`../../docs/BASELINES.md`](../../docs/BASELINES.md#fixture-baseline).

```
mfre-synthetic/
├── mfre/      -> staged to <work>/.atx/mfre    the upstream run
└── app/       -> staged to <work>/app          application source
```

`app/` is not optional: `extract_evidence` reads BMS maps, linkage and error-handling constructs from
the workspace, so a fixture without it silently understates coverage.

Re-record with `tests/run_golden.sh --record` after an intended change, and state the movement in
`CHANGELOG.md`.

## Rules

**Synthetic, never derived from a customer codebase.** No real account ids, bucket names, profile
names, ARNs or program names. `make check-secrets` and `make check-generic` run over this directory too.

**Obviously fictional identifiers.** `SYNTHPGM01`, `FIXTJOB02`, `s3://synthetic-bucket/…`. If a fixture
artifact ever turns up in real output, it should be recognisable at a glance.

**Small enough to diff by hand.** Target 1-2 MB. The reference job carried 95 MB of analysis artifacts
but documents cited only 4 files totalling 479 KB, so the full tree is unnecessary.

**Must exercise the failure modes, not just the happy path.** A fixture containing only complete,
well-formed evidence would pass while the interesting regressions went undetected:

- a delivered function, a scoped-no-spec function, and an excluded-infrastructure function — so the
  `delivered of discovered` denominator is non-trivial
- two competing bundles for one function with different requirement counts — so the richest-wins merge
  is actually tested
- at least one genuinely absent evidence class — so an `unavailable` document status is produced
- a `sourceOrigin` that differs from the workspace name — so application-name derivation is exercised

## Why the baseline will not match the reference run

A small fixture grounds fewer sections than a real job. The recorded fixture numbers are the assertion;
the reference numbers in `BASELINES.md` are context. Making the two agree would mean either bloating
the fixture or weakening the assertion, and a generic tool should not have one job's numbers in its
test suite.
