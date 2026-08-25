---
name: docs-status
description: >-
  Report application-documentation coverage from the document ledger without
  generating anything
metadata:
  version: 2.0.0
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '[path-to-bob-z-app-docs]'
---

Report the current state of the application documentation suite. Do not run any workflow, and
do not modify any file. All behaviour otherwise lives in the `z-app-documentation` skill; this
file only resolves where to look and which script call refreshes the coverage numbers.

## 1. Locate the run

`bob-z-app-docs/` at `$1` if given, else `$BOBZ_DOCS_ROOT` if set, else
`<workspace-root>/bob-z-app-docs`. If it doesn't exist, say documentation has not been generated
yet and point at `/generate-docs`. Do not build the tree here.

## 2. Refresh coverage without writing

Invoke:

```
z-app-documentation/scripts/build_coverage.py \
  --workspace-root <resolved-workspace-root> \
  --docs-root <resolved-docs-root> \
  --check-only --json
```

`--check-only` evaluates and prints the verdict; it writes nothing, matching this command's
read-only contract. Exit `1` means a hard prerequisite failed (probe unreadable/unreachable,
`program-inventory.csv` missing, Advanced mode false) — report that blocker verbatim instead of a
coverage number. Exit `0` means its `--json` output is this turn's coverage; use it, not a stale
value out of the manifest.

## 3. Read the ledger, inventory and manifest

Read `00-manifest/document-ledger.csv`, `00-manifest/program-inventory.csv` and
`00-manifest/documentation-manifest.json`.

## 4. Report, in this order

1. **Coverage** as `<complete>/<planned>` plus a percentage, from step 2's output — where
   complete means `evidence_gathered=Y` AND `generated=Y` AND `self_check_passed=Y`. Break it down
   by level (L0–L8) as well as overall.
2. A named list of every document not yet complete, with which specific flag(s) —
   `evidence_gathered`, `generated`, `self_check_passed` — are still `N` for each (these three
   ledger columns only ever take `Y`/`N` in `document-ledger.csv`; there is no `P`/`E` value the
   way `cobol-knowledge-extraction`'s `extraction-status.csv` has).
3. Any ledger row whose `output_path` file is missing on disk — these are ledger defects, report
   them explicitly.
4. Any document file present under the docs root with no matching ledger row — the reverse
   defect.
5. Every section across all documents rendered `Not available from Z Premium analysis`, grouped
   by document, with the recorded reason. Cross-check these against the manifest's
   `notApplicable` and `outOfScope` lists and report any that appear in one but not the other.
6. Review queue sizes: `17-qa-validation/dd-review-queue.md` and
   `17-qa-validation/business-review-queue.md`, plus any unresolved references in
   `validation-report.md`.
7. `mcp-cache` state from `00-manifest/mcp-cache/` (renamed from `evidence-cache` — every file in
   it now comes from a direct MCP tool call rather than a mixed workflow/fallback source): how
   many programs have a cached `generate_documentation` / `explain_code` / `z_code_scan` result,
   and how many in-scope programs have none — those are the ones a future run will pay for.
8. **Staleness.** `00-manifest/evidence-index.json` (written by a prior, non-`--check-only` run of
   `build_coverage.py`) carries the same `{doc-or-program key: {path: sha256}}` shape
   `atx-app-documentation`'s `document-evidence.json` used — same role, new name, per the design
   reconciliation. Recompute the sha256 of every path it records and name any whose digest no
   longer matches; those are stale and any document citing them needs regeneration. Mirror
   `atx-docs-status`'s inline check:

   ```python
   import json, hashlib, os
   root = "<resolved-docs-root>"
   idx = json.load(open(f"{root}/00-manifest/evidence-index.json"))
   entries = idx.get("documents", idx)  # tolerate either a top-level or a nested "documents" key
   def sha256(p):
       h = hashlib.sha256()
       with open(p, "rb") as f:
           for chunk in iter(lambda: f.read(65536), b""):
               h.update(chunk)
       return h.hexdigest()
   for key, artifacts in sorted(entries.items()):
       bad = [p for p, was in artifacts.items() if os.path.isfile(p) and sha256(p) != was]
       if bad:
           print(key, "STALE via", bad[:3])
   ```

   If `evidence-index.json` does not exist yet (no non-`--check-only` `build_coverage.py` run has
   happened for this scope), say so plainly instead of reporting zero stale documents — an absent
   fingerprint file is not the same as a clean one.

## Rules

- Freshness: state whether coverage was recomputed this turn (step 2 succeeded) or could not be
  refreshed (step 2 failed and you are reporting the manifest's last recorded value instead). If
  reporting a stale value, say so in past tense and offer to re-run once the blocker is fixed.
- Never estimate a count you did not read. If the ledger disagrees with what is on disk, report
  the disagreement rather than picking one.
- Never write, never generate, never modify source or the extraction root.
- Never report a bare percentage without the named lists.
