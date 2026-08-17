# atx-generate-docs

Entry point. Generates application documentation from an AWS Transform run that already exists
locally.

All behaviour lives in [`atx-app-documentation`](../atx-app-documentation/README.md). This skill
exists so the action has a name a user can invoke: `/generate-docs`.

## When to use this instead of `/atx-pipeline`

| Situation | Use |
|---|---|
| `.atx/mfre/` is already populated and you want documents | `/generate-docs` |
| You need to fetch artifacts from AWS first, or publish a zip | [`/atx-pipeline`](../atx-pipeline/README.md) |
| You only want to know what *could* be documented | [`/docs-status`](../atx-docs-status/README.md) |

`/generate-docs` covers phases 5-7 of the pipeline. It does not fetch, package or publish.

## Arguments

```
/generate-docs                      dry run — coverage matrix only, then stop
/generate-docs all                  every incomplete document, L0 → L8
/generate-docs L5                   one level
/generate-docs business_rules       one document
/generate-docs all --force          include documents already marked complete
```

**No argument means dry run.** Generating a full suite before the user has seen coverage is the
wrong default, because coverage decides whether the output is worth producing.

## Behaviour worth knowing

The gate runs first. `build_coverage.py` exits 1 when a hard prerequisite fails, and the fix is
upstream in [`mainframe-reverse-engineering`](../mainframe-reverse-engineering/README.md), not here.

Coverage is presented before anything is generated: delivered-of-discovered first, then functions
with no specification, then degraded evidence plans.

Output goes to `$ATX_DOCS_ROOT`, falling back to `.atx/app-docs-latest`. Invoked bare it updates the
most recent run rather than starting a new one — use `/atx-pipeline` for a fresh timestamped run.

A document whose evidence plan has no evidence is marked `blocked` and skipped, not invented. A
document that fails its self-check is reported and **not filed**; the batch continues.

## Rules

- Never calls AWS Transform. This consumes a finished run.
- Never modifies `.atx/mfre/` or application source.
- Never writes outside the resolved run folder.
- Reports coverage before document count.
