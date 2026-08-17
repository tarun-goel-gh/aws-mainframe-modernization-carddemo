---
name: atx-generate-docs
description: Generate application documentation from a completed AWS Transform reverse-engineering run. Entry point for the atx-app-documentation suite — checks prerequisites, builds the business-function coverage matrix, then generates the requested documents (all, a level L0-L8, or a single prompt_type). Activate when the user asks to generate docs, generate documentation, produce the documentation suite, or run /generate-docs.
compatibility: Requires a completed mainframe-reverse-engineering run (.atx/mfre/ with gate G2 passed and at least one delivered spec bundle). Read-only with respect to source and .atx/mfre/.
license: Apache-2.0
metadata:
  author: tarun.goel
  version: "1.0.0"
  argument-hint: '[all|L0..L8|<prompt_type>] [--dry-run] [--force]'
  delegates-to: atx-app-documentation
---

# /generate-docs

Thin entry point. All behaviour lives in the `atx-app-documentation` skill — read that skill's
`SKILL.md` and follow its pipeline. This file exists so the action has a name the user can invoke.

## What to do

1. **Load the suite skill.** Read `.kiro/skills/atx-app-documentation/SKILL.md`. Do not
   reimplement its steps here, and do not generate a document without its grounding contract
   loaded.

2. **Run the gate.** Execute:

   ```
   .kiro/skills/atx-app-documentation/scripts/build_coverage.py --mfre .atx/mfre
   ```

   The output directory defaults to `$ATX_DOCS_ROOT/00-manifest`, falling back to
   `.atx/app-docs-latest/00-manifest`. For a fresh timestamped run folder, or to fetch artifacts
   from AWS first, use `/atx-pipeline` instead of driving the scripts individually.

   Exit 1 means a hard prerequisite failed. Report the blocker verbatim and stop — the fix is
   upstream, in `mainframe-reverse-engineering`, not here.

3. **Parse the argument.**

   | Argument | Scope |
   |---|---|
   | *(none)* | `--dry-run` — coverage matrix only |
   | `all` | every incomplete document, L0 → L8 |
   | `L0`..`L8` | that level |
   | `<prompt_type>` | that one document |
   | `--dry-run` | plan and coverage, no writes outside `00-manifest/` |
   | `--force` | include documents already marked complete |

   No argument means dry run. Present the coverage matrix and stop. Generating a full suite
   before the user has seen coverage is the wrong default, because coverage decides whether the
   output is worth producing.

4. **Present coverage before generating.** Lead with delivered-of-discovered, name the functions
   with no specification, and name any degraded plans. Then proceed with the requested scope.

5. **Generate** per the suite skill's Step 7, one document at a time: load template → run the
   document's `atx-*` evidence plan → compose → self-check → file → update the ledger.

6. **Close** per Step 9. Report documents written, ledger coverage `n/31`, unavailable-section
   counts with reasons, and the review queue depth.

## Rules

- Never generate a document whose plan's evidence is missing — mark it `blocked` and continue.
- Never write outside the resolved run folder (`$ATX_DOCS_ROOT`, else `.atx/app-docs-latest`).
- Never modify `.atx/mfre/` or application source.
- Never call AWS Transform. This consumes a finished run.
- Lead every report with coverage, not with document count.
