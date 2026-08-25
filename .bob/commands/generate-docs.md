---
description: Run the z-app-documentation skill to generate the application documentation suite — all 31 documents, a level, or a single document type
argument-hint: '[all|L0..L8|<prompt_type>] [path|inventory.csv|glob] [--dry-run]'
---
Run the `z-app-documentation` skill with this scope: $ARGUMENTS

Resolve the arguments per the skill's Step 1:

- **Document scope** — `all` (or nothing) for all 31 documents; `L0`…`L8` for a level;
  `L0-L3` for a level range; one or more `prompt_type` keys (e.g. `data_lineage`,
  `business_rules`) for specific documents. Validate every key against
  `references/document-catalog.md` and stop if one is unknown, listing the valid keys.
- **Source scope** — treat any path argument as an inventory CSV, an explicit file list, a
  glob, or a folder, in that precedence order. If none was given, use the open workspace root.

If `--dry-run` appears anywhere in the arguments, stay in PLAN mode: produce the resolved
scope table, the preflight table, the capability map, the document batch and the ledger
preview, and write nothing.

Per Step 1b — three documents are feature-scoped (`business_features`, `feature_catalog`,
`business_rules`); if no feature list is known yet, generate `business_features` first, even when
the user asked only for a later level, since its output becomes the feature list the other two
need. Say when you did this and why.

Finish with the skill's Step 7 report — coverage as complete/planned plus a percentage, a
named list of every document not yet complete, a named list of every section rendered
`Not available from Z Premium analysis`, and the mcp-cache hit rate. Never report a bare
percentage.
