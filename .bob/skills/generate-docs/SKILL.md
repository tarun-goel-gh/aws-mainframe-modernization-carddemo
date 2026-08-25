---
name: generate-docs
description: >-
  Run the z-app-documentation skill to generate the application documentation
  suite — all 31 documents, a level, or a single document type
metadata:
  version: 2.0.0
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '[all|L0..L8|<prompt_type>] [path|inventory.csv|glob] [--dry-run]'
---

Thin entry point. All behaviour lives in the `z-app-documentation` skill — read that skill's
`SKILL.md` and follow its pipeline. Do not reimplement its steps here; this file exists so the
action has a name the user can invoke, and so the two script calls below happen with the right
flags.

Run the `z-app-documentation` skill with this scope: $ARGUMENTS

## 1. Resolve the arguments

- **Document scope** — `all` (or nothing) for all 31 documents; `L0`…`L8` for a level; `L0-L3`
  for a level range; one or more `prompt_type` keys (e.g. `data_lineage`, `business_rules`) for
  specific documents. Validate every key against `references/document-catalog.md` and stop if one
  is unknown, listing the valid keys.
- **Source scope** — treat any path argument as an inventory CSV, an explicit file list, a glob,
  or a folder, in that precedence order. If none was given, use the open workspace root. This
  resolved location is the `--workspace-root` passed to `build_coverage.py` below.
- **Docs root** — `$BOBZ_DOCS_ROOT` if set, else `<workspace-root>/bob-z-app-docs`. Pass this same
  value as `--docs-root` to both scripts so they read and write the same run folder.

If `--dry-run` appears anywhere in the arguments, stay in PLAN mode: run step 2 only, present its
output as the plan (resolved scope, coverage, capability map), and write nothing — never reach
step 3.

## 2. Pre-check — coverage gate

Invoke:

```
z-app-documentation/scripts/build_coverage.py \
  --workspace-root <resolved-workspace-root> \
  --docs-root <resolved-docs-root> \
  --check-only --json
```

- **Exit 2** — bad usage. Fix the invocation and retry.
- **Exit 1** — a hard prerequisite failed (unreadable/unreachable-MCP probe file,
  `program-inventory.csv` missing or empty, or Advanced mode not `true` in the probe). Report the
  blocker verbatim from the script's output and stop. The fix is upstream — re-run the probe or
  the extraction that populates `program-inventory.csv` — not something this command can patch.
- **Exit 0** — prerequisites met. Its `--json` output is the coverage numbers for this turn; carry
  them into the final report in step 4 rather than re-deriving them.

Stop here if `--dry-run` was requested.

## 3. Generate

Map the resolved document scope onto `generate_docs.py`'s flags and invoke it:

```
z-app-documentation/scripts/generate_docs.py \
  --docs-root <resolved-docs-root> \
  [--levels <n>[,<n>...]] \
  [--only <prompt_type>]
```

- `all` / no document scope given → pass neither `--levels` nor `--only` (every incomplete
  document, per the script's own default).
- A single level or a range → `--levels`, comma-separated (`L0-L3` → `--levels 0,1,2,3`).
- One or more `prompt_type` keys → `--only <prompt_type>`, once per key.
- Never pass `--force` from this command — a document already ledgered complete
  (`evidence_gathered=Y` AND `generated=Y` AND `self_check_passed=Y` in `document-ledger.csv`)
  stays complete. Forcing regeneration of complete documents is not part of this command's
  argument surface; invoke `z-app-documentation` directly for that.
- `generate_docs.py` reads `evidence-pack.json`. If the evidence-aggregation step
  (`extract_evidence.py`) that produces it hasn't run yet for this scope, follow
  `z-app-documentation/SKILL.md`'s own pipeline ordering to produce it first — that is the main
  skill's step, not reimplemented here.

Exit codes: `0` every requested document filed · `1` at least one document failed its self-check
and was not filed (the batch still continues past it — see the script's own output for which) ·
`2` bad usage.

`generate_docs.py` enforces its own document-generation ordering internally (e.g. producing a
prerequisite document ahead of one explicitly requested). If it did so, say so, citing its own
`00-manifest/generation-log.md` entry — do not narrate an ordering decision the script didn't
actually make.

## 4. Report

Finish with a report built from the two scripts' own output and exit status, not agent narration:

- Coverage as complete/planned plus a percentage, taken from step 2's `build_coverage.py --json`
  output. Never report a bare percentage.
- A named list of every document not yet complete, read from `document-ledger.csv` after step 3.
- A named list of every section rendered `Not available from Z Premium analysis`, read from
  `generate_docs.py`'s self-check output / `00-manifest/generation-log.md`.
- The `mcp-cache` hit rate (evidence reused from `00-manifest/mcp-cache/` versus gathered cold this
  run) — read from `build_coverage.py`'s coverage output, not estimated.
