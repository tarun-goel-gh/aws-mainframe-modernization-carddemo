# atx-docs-status

Entry point. Reports the state of the documentation suite. Read-only — writes nothing, generates
nothing.

Invoke as `/docs-status`.

## What it answers

- Which of the 31 documents exist, and their status: `complete` / `partial` / `unavailable` / `blocked`
- Business-function coverage: delivered of discovered, and which functions have no specification
- Grounded versus absent sections, and the split between the two absence markers
- Degraded evidence plans
- **Stale** documents — where the evidence changed after the document was written
- The SME review queue depth

## Arguments

```
/docs-status              full report
/docs-status --gaps       only what is missing or absent
/docs-status --stale      only documents whose evidence has changed
```

## Where it reads from

`$ATX_DOCS_ROOT/00-manifest/`, falling back to `.atx/app-docs-latest/00-manifest/`. When several
`.atx/app-docs-*` folders exist it reports which run it read and notes that others are present.

If no suite exists it says documentation has not been generated yet and points at
[`/generate-docs`](../atx-generate-docs/README.md). It does not build the tree.

## How staleness is detected

`document-evidence.json` records the sha256 of every artifact each document actually consumed. A
document is stale when any of those fingerprints no longer matches what is on disk. Without this an
upstream re-run silently invalidates documents that still look current.

Pseudo-paths such as `workspace app/**` carry a fingerprint derived from measured values rather than
a file digest, so they participate in the comparison too.

## Interpreting the output

`unavailable` is not a defect. Two documents in a typical suite (`security_architecture`,
`modernization_strategy`) have zero grounded sections because AWS Transform genuinely produces no
evidence for them. The honest report is that they cannot be written, not a document padded with
inference.

Read the coverage denominator before the document count. 31 documents over 6 of 11 business functions
is a different thing from 31 documents over the whole estate, and only the denominator tells you
which you have.
