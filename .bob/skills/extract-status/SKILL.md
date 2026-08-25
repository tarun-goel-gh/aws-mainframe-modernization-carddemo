---
name: extract-status
description: >-
  Report knowledge-extraction coverage from the ledger without running any
  extraction
metadata:
  version: 2.0.0
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '[path-to-bob-z-knowledge-extract]'
---

Report the current state of the knowledge extraction. Do not run any extraction workflow, and do not
modify any file.

Locate `bob-z-knowledge-extract/` (at $1 if given, otherwise the open workspace root), then read
`00-manifest/program-inventory.csv`, `00-manifest/extraction-status.csv`, and
`00-manifest/extraction-manifest.json`, and report:

1. Coverage as `<complete>/<inventory total>` plus a percentage, where complete means
   `dd_generated=Y` and `doc_generated=Y`.
2. A named list of every program not yet complete, with which passes are outstanding for each.
3. Any program in the ledger but not the inventory, or in the inventory but not the ledger — these are
   reconciliation defects, report them explicitly.
4. Any ledger row marked `Y` whose corresponding artifact file is missing on disk.
5. Every `notApplicable` and `outOfScope` area recorded in the manifest, with its reason.
6. Whether the Step 12 Refactor question has been resolved in `00-manifest/extraction-log.md`.

Never report a bare percentage without the named list.
