# Workflow reference

The nine-phase pipeline reference ships **with the skill**, not here, so it cannot drift from the
script it documents:

```
src/skills/atx-pipeline/README.md          after step 2
dist/<runtime>/…/atx-pipeline/README.md    in every built variant
```

Deliberately a pointer rather than a copy. A duplicated 340-line reference is a duplicate that goes
stale, and this one describes flags and exit codes that change with the script.

## What it covers

- All nine phases: what each reads, writes, and how long it takes
- Full flag reference: selection, inputs, publishing
- Run folders, `ATX_DOCS_ROOT`, and the `latest` symlink
- The four statuses, and why `partial` is not a failure
- Richest-wins bundle merge and the disclosure gate
- Publishing: presigned versus `--public`, and why a presigned URL cannot outlive its session
- A troubleshooting table keyed on real error strings

## Quick reference

```bash
S=<skills-root>/atx-app-documentation/scripts

$S/run_pipeline.sh --offline --dry-run     # plan only
$S/run_pipeline.sh --offline               # documents only, ~3 s, no AWS
$S/run_pipeline.sh --profile P --region R \
  --bucket B --job-id J --upload-bucket U  # everything
$S/run_pipeline.sh --resume <id> --from <phase>
```

Phases 5-8 need no network. When SSO has lapsed and `.atx/mfre/` is populated, `--offline` is both the
fast path and a complete path to all 31 documents.

## Related

- [`BASELINES.md`](BASELINES.md) — what a correct run produces
- [`MIGRATION.md`](MIGRATION.md) — running the suite on Claude Code or Codex
- [`EXAMPLES.md`](EXAMPLES.md) — a real run, with output
- [`DEFECTS.md`](DEFECTS.md) — why the mechanisms exist
