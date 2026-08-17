---
name: atx-app-documentation
description: Generate the full application documentation suite for a mainframe application — the 31 documents across 9 levels (discovery, business context, business documentation, technical, design, data, integration, operations, modernization) — grounded entirely in the artifacts produced by the mainframe-reverse-engineering skill (AWS Transform assess + reimagine). Produces a timestamped .atx/app-docs-<run-id> knowledge base with an evidence-grounded, resumable, ledger-tracked pipeline and an explicit business-function coverage matrix. Activate when the user asks to generate application documentation from an AWS Transform run, produce a modernization document set, build an as-is assessment, document business rules or data lineage, generate an executive summary or migration roadmap, or mentions "atx-app-docs", "documentation suite", "9-level documentation", or "document ledger".
compatibility: Requires a completed mainframe-reverse-engineering run in the workspace — .atx/mfre/state.json with gate G2 passed, at least one delivered spec bundle, and ideally .atx/mfre/analysis/ from scripts/snapshot_analysis.sh. Read-only with respect to source and .atx/mfre/. No AWS credentials, no MCP server and no AWS Transform API calls are needed at documentation time.
license: Apache-2.0
metadata:
  author: tarun.goel
  version: "1.0.0"
  phase: documentation
  argument-hint: '[all|L0..L8|<prompt_type>] [--dry-run]'
  upstream: mainframe-reverse-engineering
---

# Application Documentation Suite (AWS Transform evidence)

Generates a complete, evidence-grounded application documentation set — **31 documents across
9 levels** — from the artifacts a completed AWS Transform reverse-engineering run left on disk.

This skill is the third port of the same document catalog. The origin was the CAST integration
service (evidence: CAST Imaging MCP). The second was `z-app-documentation` (evidence: IBM Bob
Z Premium Package workflows). This one uses **`mainframe-reverse-engineering` output**. The
prompt catalog, grounding contract, determinism rules and evidence-plan mechanism carry over;
only the evidence source changes.

**This skill adds no analysis capability.** It does not call AWS Transform, does not run
discovery, and cannot create evidence. It reads what the upstream run produced, composes
documents against fixed templates, and refuses to fill a section it cannot ground.

## Scope

**In scope** — reading `.atx/mfre/` artifacts and workspace source; composing the 31 documents;
maintaining a document ledger, coverage matrix and evidence index; reporting gaps.

**Out of scope** — running or resuming an AWS Transform job (that is
`mainframe-reverse-engineering`), forward engineering, code generation, editing application
source, editing `.atx/mfre/`, and any live service call.

## Non-negotiable rules

1. **No evidence, no document.** Every claim traces to an artifact read this run or a source
   member read this run. Ungrounded fields read `Not available from AWS Transform analysis`.
2. **Coverage is stated, never implied.** AWS Transform produces requirements per business
   function and only for functions that succeeded. Never generalise from delivered functions to
   "the application". See Step 2.
3. **The upstream run is immutable.** `.atx/mfre/` is owned by `mainframe-reverse-engineering`.
   Read it; never write to it. All output goes under `docsRoot`.
4. **No live calls.** Do not use the AWS Transform chat or its Neptune knowledge graph as
   evidence — non-deterministic, unreproducible, and it breaks the determinism rules.
5. **Templates are fixed.** Never add, drop or reorder a template's sections. Render every
   heading, even when its content is unavailable.
6. **Provenance on every derived artifact**, using only this skill's vocabulary.
7. **Resumable and idempotent.** A document already marked complete in the ledger is skipped,
   not regenerated, unless `--force`.
8. **Determinism.** Fixed ordering, verbatim identifiers, no synonym variety, no invented dates.

## Reference files — read on demand, not upfront

| Need | File |
|---|---|
| The 31 documents, their levels, plans and output paths | `references/document-catalog.md` |
| Evidence contract, coverage honesty, provenance, determinism, self-check | `references/grounding-contract.md` |
| The nine `atx-*` evidence plans and the artifact inventory | `references/evidence-plans.md` |
| Distributed-stack concept → AWS Transform evidence mapping | `references/atx-substitutions.md` |
| How to read each template's section set, and the three stub section sets | `references/template-families.md` |
| One document's required section set | `references/prompts/<n>-<prompt_type>.md` |

| Script | Purpose |
|---|---|
| `scripts/build_coverage.py` | Step 2 — prerequisite gate and coverage matrix |
| `scripts/extract_evidence.py` | Step 5 — read every shared artifact once into an evidence pack |
| `scripts/generate_docs.py` | Step 7 — compose, self-check and file the documents |

Load a prompt template only when you are about to write that document.

## Run modes

| Mode | Behaviour |
|---|---|
| `--dry-run` | PLAN only: coverage matrix, scope table, capability map, batch preview. No writes outside `00-manifest/`. |
| `all` | Every document not already complete, level order L0 → L8. |
| `L0`..`L8` | One level. |
| `<prompt_type>` | One document, e.g. `business_rules`. |
| `--force` | Regenerate documents already marked complete. Off by default. |

Default when no argument is given: `--dry-run`. Spending a full suite of generations before the
user has seen the coverage matrix is the wrong default, because coverage determines whether the
output is worth generating at all.

---

## Step 1 — Locate the upstream run

Resolve `docsRoot` in this order:

1. `$ATX_DOCS_ROOT` when set. `run_pipeline.sh` stamps `.atx/app-docs-<YYYYMMDD-HHMMSS>` once per
   run and exports it, which is what keeps one run inside one folder.
2. `.atx/app-docs-latest`, a symlink the driver repoints at the newest run.
3. A path the user names explicitly.

Runs are kept side by side so two document sets can be diffed. `.atx/` is gitignored, so the
zip produced by the `package` phase is the distribution channel — do not tell the user to commit
the run folder.

Find the upstream run:

1. `.atx/mfre/state.json` — the expected location.
2. If absent, search for `state.json` with a `schemaVersion` and an `autonomy.scope` key.
3. If still absent, **stop**:

   > No AWS Transform reverse-engineering run found. This skill documents an existing run; it
   > cannot analyse the codebase itself. Run `mainframe-reverse-engineering` first, then return.

Do not offer to document from source alone. A suite built by reading COBOL directly is not this
skill's output and would carry none of the provenance the templates require.

---

## Step 2 — Prerequisite gate and coverage matrix

This step replaces the Bob skill's environment probe. It is the gate that makes the rest honest.

### 2a — Hard prerequisites

| Check | Requirement | On failure |
|---|---|---|
| `state.json` readable | valid JSON, `schemaVersion` present | stop |
| `gates.G2` | `pass` | stop — without a persisted catalog there is no decomposition to document |
| `autonomy.scope` | non-empty | stop |
| Delivered functions | ≥1 function with a `status` in `succeeded` / `succeeded_degraded` **and** a `localPath` containing `requirements.md` | stop — nothing to document |
| `discovery/business_function.csv` | present | stop |

A failed prerequisite is a stop, not a warning. Generating 31 documents from an incomplete run
produces 31 documents that mostly say "unavailable", which wastes the user's time and looks like
a defect in this skill rather than a gap in the input.

### 2b — Soft prerequisites (degrade, record, continue)

| Missing | Effect | Record as |
|---|---|---|
| `analysis/code-analysis/` | no complexity, no per-file metrics, no dependency graph | `atx-quality` and `atx-discovery` degraded |
| `analysis/data-analysis/` | no data dictionary, no lineage with direction | `atx-data` severely degraded |
| `analysis/business-function-discovery/` | no data-path graphs | `atx-structure` degraded |
| `discovery/business_function.json` | no `category`, no `interfaces` edges | `atx-integration` and `atx-structure` degraded |
| `glossaryProvenance` ≠ `user-supplied` | terminology unverified | caveat on every document |

If the whole `analysis/` tree is absent, say so plainly and name the fix:

> `.atx/mfre/analysis/` is missing. Data, quality and discovery documents will be substantially
> incomplete. Run `mainframe-reverse-engineering`'s `scripts/snapshot_analysis.sh` against the
> job to capture it, then re-run.

### 2c — Build the coverage matrix

For every function in the discovery catalog, classify:

| Class | Test | What can be documented |
|---|---|---|
| `delivered` | scoped, terminal success, `requirements.md` exists | everything — catalog, requirements, rules, workflow sections |
| `scoped-no-spec` | scoped, any other terminal status | catalog fields only: name, description, category, entry points, LOC, data paths |
| `excluded-infrastructure` | in `autonomy.excludedInfrastructure` | catalog fields only, plus the exclusion signals |

Write `00-manifest/coverage.md`:

```markdown
# Coverage

Discovered: 11 · scoped: 9 · delivered: 6

| Business function | Category | Class | Reqs (F/N) | Rules | LOC | Documentable |
|---|---|---|---|---|---|---|
| Account Balance and Transaction Processing | mixed | delivered | 286/4 | 286/328 | 8269 | full |
| …                                          |       |           |        |       |      |      |
| Master Data File Initialization | batch | scoped-no-spec | — | — | 703 | catalog only |
| Application Build and Deployment | batch | excluded-infrastructure | — | — | 256 | catalog only |

## Consequences
- Requirement- and rule-derived content covers 6 of 11 discovered functions.
- 3 scoped functions delivered no specification: <names>.
- 2 functions excluded as infrastructure-only: <names, with signals>.
```

Also emit `00-manifest/evidence-index.json` — the artifact paths, their sha256, and which plans
they feed. That index is what makes a later run able to tell stale evidence from fresh.

**Under `--dry-run`, stop here** and present the coverage matrix. This is the user's cheapest
opportunity to decide the run is not worth doing, or to go fix the upstream run first.

---

## Step 3 — Create the output tree

```
.atx/app-docs-<YYYYMMDD-HHMMSS>/
├── 00-manifest/
│   ├── manifest.json          run metadata, gaps, counts
│   ├── coverage.md            Step 2c
│   ├── evidence-index.json    artifact paths + sha256 + plan mapping
│   ├── document-evidence.json per-document artifact index + sha256
│   ├── ledger.md              31 rows, one per document
│   ├── generation-log.md      append-only, one line per document
│   ├── review-queue.md        sections needing an SME
│   ├── run-log.md             one row per pipeline phase (run_pipeline.sh)
│   ├── run-state.json         phase status, for --resume
│   └── publish.md             share link and its real expiry, when published
├── L0-discovery/
├── L1-business-context/
├── L2-business-documentation/
├── L3-technical-documentation/
├── L4-design/
├── L5-data/
├── L6-integration/
├── L7-operations/
└── L8-modernization/
```

The run folder sits under `.atx/`, which is gitignored, so runs accumulate side by side without
touching the working tree. Two runs over the same evidence produce byte-identical documents — only
`generatedAt`, `docsRoot`, `run-log.md` and `run-state.json` differ — so a diff between run folders
shows evidence changes, not generator noise.

To review documents in git, copy a run folder to a tracked path deliberately. Do not commit it by
default: 7 of the 31 documents carry the AWS account id, and `.atx/` being ignored is the only thing
currently keeping them out of a commit.

---

## Step 4 — Write the ledger

31 rows from `references/document-catalog.md`, each with: `#`, level, `prompt_type`, ATX plan,
output path, status (`pending` / `complete` / `partial` / `blocked`), grounded-section count,
unavailable-section count, and the generation timestamp.

The ledger is the resumability mechanism and the completeness denominator. Four statuses, and the
last two are deliberately distinct:

| Status | Meaning |
|---|---|
| `complete` | every template heading grounded |
| `partial` | written, some headings unavailable |
| `unavailable` | written, but **no** heading could be grounded — even though the document's plan *did* have evidence. The template asks for things this evidence set cannot answer. |
| `blocked` | the document's evidence plan has no evidence at all |

Collapsing the last two hides the difference between "we have data but this template wants
something else" and "we have no data" — and those call for different fixes.

**The suite record is `00-manifest/suite-state.json`, and a batch merges into it.** A `--only` or
`--levels` run must not reduce the record to the documents it touched; the ledger and manifest are
built from all 31 rows, not from the last command.

Every derived manifest is regenerated on every run — `ledger.md`, `manifest.json`,
`review-queue.md`, `generation-log.md` and `document-evidence.json`. `coverage.md` belongs to
`build_coverage.py`; the generator warns when it is older than the evidence pack rather than
letting it drift silently.

---

## Step 5 — Load shared evidence once

Run `atx-preflight` from `references/evidence-plans.md`, then load into memory once:

- the catalog (CSV + JSON), the coverage matrix
- `state.json` scope, exclusions, gates, per-function metrics
- the analysis index (not the full contents)
- per delivered function: the `traceability.yaml` summary block and the REQ id set

Do **not** load every `traceability.yaml` in full up front. A single function's file can carry
hundreds of rules; load the rules for a function when a document actually details it.

---

## Step 6 — Select the batch

Resolve the requested scope to a document list, filtered by the ledger. Order by level, then by
catalog `#`. Report the batch before generating: which documents, which plans, and which plans
are degraded per Step 2b.

Bound the batch. A full 31-document run in one pass produces a large diff and a long window in
which a failure loses work; prefer level-sized batches.

---

## Step 7 — Per document: evidence → compose → self-check → file

**Run `scripts/generate_docs.py`. Do not hand-compose the documents.**

```
scripts/extract_evidence.py                      # once per batch: Step 5
scripts/generate_docs.py [--levels 0,1] [--only <prompt_type>] [--force]
```

Hand-composition cannot satisfy this skill's own determinism rules: identical inputs must yield
identical output, ordering must be stable, and identifiers must be reproduced verbatim. A model
writing 31 documents freehand produces none of that. The generator mechanises 7a–7d below, and
the steps are documented so its behaviour is reviewable rather than opaque.

What the generator guarantees, each because its absence was a defect:

| Guarantee | Why |
|---|---|
| Per-document Evidence Index, built from artifacts actually read | a shared boilerplate table asserts provenance a document does not have |
| Two distinct unavailable markers | `Not available from AWS Transform analysis` (evidence absent) versus `Not extracted by this run` (exists, not parsed) — conflating them blames the evidence source for generator gaps |
| Citations use the full chain | `REQ-F-001 -> rule <id> -> COUSR02C`, from traceability's reverse index |
| The self-check is enforced | a document that fails is **not filed**; asserting compliance is not compliance |
| The ledger is honoured | `complete` documents are skipped unless `--force` |
| Section sets come from `references/template-families.md` | templates have three different shapes; guessing produces sub-labels as headings |

### 7a. Load the contract and the template

The generator reads `references/grounding-contract.md`, the document's row in
`references/document-catalog.md`, its `references/prompts/*.md` template, and the section-set
rules in `references/template-families.md`. Composition order matches the origin service's
`compose_prompt()`: grounding contract, determinism rules, coverage statement, task banner,
template, self-check.

### 7b. Run the evidence pass

Execute the document's ATX plan from `references/evidence-plans.md`, in order, stopping when the
template's sections are satisfied. Consult `references/atx-substitutions.md` whenever the
template names a distributed-stack concept.

Record every artifact read into the document's evidence index entry.

### 7c. Compose

- Render every template heading. No additions, no omissions, no reordering.
- Open with the **Coverage** note for this document: which functions its content covers.
- Tag non-trivial claims. Prefer `[source: REQ-F-042 -> rule <id> -> CBTRN02C]`; fall back to
  `[source: <artifact> -> <member:line>]`.
- Label every derived artifact with a provenance value from the contract's §1 table.
- An unavailable field takes **one of two markers**, and the distinction is not cosmetic:
  - `Not available from AWS Transform analysis` — the evidence does not exist. Say why, e.g.
    `— no specification delivered for this function`.
  - `Not extracted by this run` — the evidence exists in the codebase and was not parsed. This
    is a generator limitation and must not be dressed up as an evidence gap.
- Where two headings resolve to the same evidence, emit it once and cross-reference. Repeating a
  table is padding.
- Close with the **Evidence Index** — only the artifacts this document read.

### 7d. Self-check, then file

`self_check()` runs the contract's §5 checklist and **blocks filing on failure**. It rejects: a
missing Coverage note, a coverage figure without its denominator, a dropped template heading, a
missing Evidence Index, leaked Bob provenance vocabulary, a document that recorded no artifact,
and a bare total stated without its denominator.

A blocked document is reported and the batch continues. Then write the file, update the ledger
row, and append to `generation-log.md`.

### 7e. Queue deferred review

Generated data-dictionary business descriptions are `status: draft` and go to
`00-manifest/review-queue.md` for SME confirmation. They are the highest-risk content in the
suite because they read as authoritative and were machine-authored.

---

## Step 8 — Cross-document consistency

After a batch, check that shared facts agree across documents: function names and counts,
program attributions, entry-point lists, rule totals, LOC. A disagreement means one document
read a different artifact version — reconcile against `evidence-index.json`, not by picking the
nicer number.

---

## Step 9 — Close the batch and report

Update `manifest.json` and report:

- documents written this batch, and ledger coverage as `n/31`
- grounded versus unavailable section counts, and the top reasons for unavailable
- coverage headline: functions represented out of functions discovered
- degraded plans and what would fix them
- the review queue depth
- what to run next

Lead with coverage, not with document count. "18 of 31 documents, covering 6 of 11 business
functions" is the honest headline; "18 of 31 documents" alone invites the wrong conclusion.

---

## Failure policy

| Class | Example | Action |
|---|---|---|
| `prerequisite` | no upstream run, G2 not passed, no delivered spec | stop; name the fix |
| `evidence-missing` | plan's artifacts absent | mark documents `blocked`, continue with others |
| `evidence-partial` | some functions lack specs | generate, mark `partial`, state coverage |
| `template-gap` | template supplies no section set | use the reference file's fixed section set; flag it |
| `self-check-fail` | ungrounded field, missing Evidence Index | fix and re-run the check; never file |

One document failing never stops the batch. Record it and continue.

## Communication

Progress, not process. Do not name plan ids, step numbers or artifact paths in prose to the user
unless they asked. Report which documents exist, what they cover, and what is missing. When
coverage is partial, say so first — it is the single most decision-relevant fact about this
output.
