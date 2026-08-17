---
name: extract-batch
description: >-
  Run the cobol-knowledge-extraction skill against a project, folder, file list,
  inventory CSV, or glob
metadata:
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '<path|file-list|inventory.csv|glob> [--dry-run]'
---

Run the `cobol-knowledge-extraction` skill against this scope: $1

Resolve the scope per the skill's Step 0 — treat the argument as an inventory CSV, an explicit file
list, a glob, or a folder path, in that precedence order. If no argument was given, use the open
workspace root.

If `--dry-run` appears anywhere in the arguments, stay in PLAN mode: produce the resolved scope, the
preflight table, the capability map, and the proposed batch, and write nothing.

Finish with the skill's Step 12 report — coverage as done/total plus a percentage, and a named list of
every program not yet complete and every pass that did not run. Never report a bare percentage.
