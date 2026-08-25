---
description: Report application-documentation coverage from the document ledger without generating anything
argument-hint: '[path-to-bob-z-app-docs]'
---
Report the current state of the application documentation suite. Do not run any workflow, and
do not modify any file.

Locate `bob-z-app-docs/` (at $1 if given, otherwise the open workspace root), then read
`00-manifest/document-ledger.csv`, `00-manifest/program-inventory.csv` and
`00-manifest/documentation-manifest.json`, and report:

1. Coverage as `<complete>/<planned>` plus a percentage, where complete means
   `evidence_gathered=Y` AND `generated=Y` AND `self_check_passed=Y`. Break it down by level
   (L0–L8) as well as overall.
2. A named list of every document not yet complete, with which of `evidence_gathered`,
   `generated`, `self_check_passed` is still `N` for each (these ledger columns only ever take
   `Y`/`N` in `document-ledger.csv` — there is no `P`/`E` value).
3. Any ledger row whose `output_path` file is missing on disk — these are ledger defects,
   report them explicitly.
4. Any document file present under `docsRoot` with no matching ledger row — the reverse defect.
5. Every section across all documents rendered `Not available from Z Premium analysis`,
   grouped by document, with the recorded reason. Cross-check these against the manifest's
   `notApplicable` and `outOfScope` lists and report any that appear in one but not the other.
6. Review queue sizes: `17-qa-validation/dd-review-queue.md` and
   `17-qa-validation/business-review-queue.md`, plus any unresolved references in
   `validation-report.md`.
7. `mcp-cache` state from `00-manifest/mcp-cache/` (every file in it comes from a direct MCP
   tool call, per `.bob/skills/_design/bobz-v3-foundations.md` §4e): how many programs have a
   cached `generate_documentation` / `explain_code` / `z_code_scan` result, and how many
   in-scope programs have none — those are the ones a future run will pay for.
8. **Staleness.** Recompute the sha256 of every path recorded in
   `00-manifest/evidence-index.json` and name any whose digest no longer matches — that evidence
   is stale and any document citing it needs regeneration. If `evidence-index.json` does not
   exist yet, say so plainly instead of reporting zero stale documents.

Never report a bare percentage without the named lists.
