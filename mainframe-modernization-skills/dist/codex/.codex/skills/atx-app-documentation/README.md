# Application Documentation Suite (AWS Transform evidence)

Generates **31 documents across 9 levels** for a mainframe application, grounded entirely in the
artifacts a completed `mainframe-reverse-engineering` run left on disk.

`SKILL.md` is the governing document. This README is for humans.

---

## What it is, and what it is not

**Is:** a composition layer. It reads AWS Transform artifacts, fills fixed document templates,
and refuses to fill a section it cannot ground.

**Is not:** an analyser. It never calls AWS Transform, never runs discovery, never reads the
knowledge graph, and cannot create evidence. If the upstream run didn't produce something, the
document says so.

This is the third port of the same document catalog:

| Port | Evidence source | Runtime |
|---|---|---|
| origin | CAST Imaging MCP server | CAST integration service |
| `z-app-documentation` | IBM Bob Z Premium Package workflows | Bob IDE |
| **`atx-app-documentation`** | **`mainframe-reverse-engineering` output** | **Codex** |

The prompt catalog, grounding contract and determinism rules are shared. Only the evidence
source changes.

---

## Prerequisites

A completed upstream run in the workspace. Hard requirements — any failure stops the run:

- `.atx/mfre/state.json` present and valid
- `gates.G2 == "pass"` (business function catalog persisted)
- `autonomy.scope` non-empty
- at least one function delivered a `requirements.md`
- `.atx/mfre/discovery/business_function.csv` present

Strongly recommended — absence degrades specific plans rather than stopping:

- `.atx/mfre/analysis/` from `mainframe-reverse-engineering`'s `scripts/snapshot_analysis.sh`.
  Without it, data, quality and discovery documents are substantially incomplete.

No AWS credentials, no MCP server and no network access are needed at documentation time.

---

## How to Use

The skill activates from natural language. Coverage is checked before anything is generated.

### Check what is documentable first

```
what can be documented from the AWS Transform run?
generate application documentation --dry-run
```

Dry run is the default when no scope is given. It writes only the coverage matrix and stops. That
is deliberate: coverage determines whether generating 31 documents is worth doing at all.

### Generate

```
generate the full application documentation suite
generate L0 and L1 documentation
generate the business rules document
regenerate the data dictionary --force
```

| Scope | Meaning |
|---|---|
| `all` | every document not already complete, L0 → L8 |
| `L0`..`L8` | one level |
| `<prompt_type>` | one document, e.g. `business_rules`, `data_lineage` |
| `--dry-run` | coverage and plan only, no documents |
| `--force` | regenerate documents already marked complete |

### Check progress

```
documentation status
what's missing from the docs?
```

Reports ledger coverage `n/31`, grounded versus unavailable sections, and which plans are
degraded.

### Worked example

```
You:   generate application documentation from the transform run
Skill: [gate]     upstream run mfre-20260813-0550, G2 pass, 6 delivered specs
       [coverage] 6 delivered of 11 discovered (9 scoped)
                  3 scoped functions have no spec; 2 excluded as infrastructure
                  degraded: analysis/ absent -> data + quality documents thin
       → presents the coverage matrix and stops, because no scope was given
You:   go ahead with L2
Skill: [L2] 5 documents written, business_rules grounded from 466 rules across 6 functions
```

---

## Scripts

One driver, three workers. The documents are **generated, not hand-written** — identical inputs
must produce identical output, which freehand composition cannot guarantee.

### `run_pipeline.sh` — the driver

Nine phases from AWS artifacts to a shareable zip, with one progress line each. Use this rather
than chaining the workers by hand: it stamps the run folder once, records phase status in
`run-state.json`, and can resume.

```bash
# Everything: fetch from AWS, document, zip, publish
scripts/run_pipeline.sh --profile <p> --region <r> \
  --bucket <artifact-bucket> --job-id <job-id> --upload-bucket <docs-bucket>

# Documents only, no AWS needed (fast path when SSO has lapsed)
scripts/run_pipeline.sh --offline

# Show the plan, touch nothing
scripts/run_pipeline.sh --offline --dry-run

# Resume a failed run without redoing completed phases
scripts/run_pipeline.sh --resume 20260813-142530 --from generate
```

Each run gets `.atx/app-docs-<YYYYMMDD-HHMMSS>/`, and `.atx/app-docs-latest` points at the newest.
The driver exports `ATX_DOCS_ROOT`, which is how the three workers below agree on one folder.

Phase `verify-split` exits 1 and is recorded `partial` when AWS Transform delivered fewer business
functions than were discovered. That is an expected outcome, not a driver failure, and the pipeline
continues so the coverage matrix can state the boundary honestly.

The nine phases, the gates, resume semantics and the publish modes are documented in full in
[`../atx-pipeline/README.md`](../atx-pipeline/README.md). Two behaviours matter here because they
shape what the suite emits:

**Packaging carries a disclosure gate.** The archive is the thing that leaves the machine, so phase
`package` scans every entry for IAM/STS principal ARNs, `ASIA`/`AKIA` access key ids,
`X-Amz-Security-Token=` and secret-key assignments. A hit deletes the zip and fails the phase. The
AWS account id is deliberately *not* on that list: it appears in 7 of the 31 documents by design and
is disclosed to the caller before publishing.

**Phase output is captured outside the run folder.** Phase `package` zips the run folder, so scratch
files inside it become archive content — and preflight's output contains the caller's account id and
assumed-role ARN. This was an actual leak into a public object, not a hypothetical.

### The three workers, in order

```bash
# 1. gate: can anything be documented, and what is the coverage boundary?
scripts/build_coverage.py --mfre .atx/mfre

# 2. read every shared artifact once into an evidence pack
scripts/extract_evidence.py

# 3. compose, self-check and file
scripts/generate_docs.py                      # all 31, skipping any already complete
scripts/generate_docs.py --levels 5           # one level
scripts/generate_docs.py --only business_rules
scripts/generate_docs.py --force              # regenerate complete documents too
scripts/generate_docs.py --app-name "ACME Claims"   # override the derived application name
```

The application name in every document header is derived from the upstream run — `--app-name` or
`ATX_APP_NAME`, else the `sourceOrigin` archive basename minus any branch suffix, else the workspace
name, else `Unnamed application`. The choice is recorded in `manifest.json` under
`application.nameSource`. It is derived rather than fixed because a literal here would put one
application's name on documents describing another.

All three default to `$ATX_DOCS_ROOT`, falling back to `.atx/app-docs-latest`. Invoked bare, they
update the most recent run rather than creating a new one.

`generate_docs.py` exits 1 if any document failed its self-check. A failed document is reported
and **not filed** — the batch continues with the others.

### `build_coverage.py` — the prerequisite gate

```bash
# Full gate: writes coverage.md + evidence-index.json into $ATX_DOCS_ROOT/00-manifest
scripts/build_coverage.py --mfre .atx/mfre

# Just the verdict, no writes
scripts/build_coverage.py --mfre .atx/mfre --check-only

# Against a relocated or archived run
scripts/build_coverage.py --mfre /path/to/extracted/mfre --out-dir /tmp/out
```

Exit 0 prerequisites met, 1 a hard prerequisite failed, 2 bad usage. It resolves each function's
bundle by the recorded `localPath` first and then by convention under `--mfre`, so an archived or
copied run is still documentable.

---

## Outputs

```
.atx/app-docs-<YYYYMMDD-HHMMSS>/
├── 00-manifest/
│   ├── coverage.md             which functions are documentable, and which are not
│   ├── evidence-index.json     suite-wide artifact paths + sha256 (seeds the hash cache)
│   ├── evidence-pack.json      every shared artifact, read once
│   ├── suite-state.json        the 31-document record; batches MERGE into it
│   ├── document-evidence.json  per-document artifact fingerprints — enables staleness checks
│   ├── ledger.md               31 rows: status, section counts, builder distribution
│   ├── manifest.json           machine-readable run summary
│   ├── review-queue.md         data-dictionary descriptions awaiting SME sign-off
│   ├── generation-log.md       suite state at last generation
│   ├── bundle-selection.md     which extraction attempt each function came from, and what it beat
│   ├── run-log.md              one row per pipeline phase, with elapsed time and exit code
│   ├── run-state.json          phase status, consumed by --resume
│   └── publish.md              share link and its real expiry, when published
├── L0-discovery/ … L8-modernization/

.atx/app-docs-<YYYYMMDD-HHMMSS>.zip     the packaged deliverable
.atx/app-docs-latest -> app-docs-<...>  symlink to the newest run
```

`publish.md` is written *after* the zip is built, so it is deliberately not inside the archive — an
archive cannot contain a truthful record of its own publication. `manifest.json` does carry full
upstream provenance (job, workspace, run id, gates, source origin), so an extracted archive can still
be traced to the run that produced it.

**What the archive is made of.** Just over half is internal machinery, dominated by
`evidence-pack.json`:

| Contents | Compressed | Raw | Share |
|---|---|---|---|
| `00-manifest/` (internal) | 147 KB | 1077 KB | 55% |
| `L0`-`L8` documents | 119 KB | 425 KB | 45% |

`evidence-pack.json` alone is 964 KB raw and is a regenerable intermediate — `extract_evidence.py`
rebuilds it from `.atx/mfre/` in under a second. If the archive is going to external readers, it is
reasonable to exclude it; the human-meaningful manifests (`coverage.md`, `ledger.md`, `run-log.md`,
`bundle-selection.md`, `review-queue.md`, `document-evidence.json`) are a small fraction of the size.

Runs accumulate side by side under `.atx/`, which is gitignored. Two runs over the same evidence
produce byte-identical documents — only `generatedAt`, `docsRoot`, `run-log.md` and `run-state.json`
differ — so diffing two run folders shows evidence drift rather than generator noise.

The zip is the distribution channel. Don't commit a run folder casually: 7 of the 31 documents
carry the AWS account id, and `.atx/` being gitignored is what currently keeps them out of a commit.
Copy to a tracked path deliberately if the documents belong in review.

---

## Coverage: the thing to understand before trusting output

Bob's evidence source scanned every member in the workspace. **This one does not.** AWS Transform
produces requirements per business function, and only for functions that were scoped and
succeeded. On a real run: 6 of 9 scoped functions delivered, 2 more excluded as
infrastructure-only, 3 delivered nothing.

So the suite is built on partial evidence, and that is the normal case rather than the exception.
Three rules follow, enforced by the grounding contract:

- Every document opens with a **Coverage** note naming the functions it represents, the scoped
  functions with no specification, and the excluded ones.
- Every count carries its denominator. "466 functional requirements across 6 of 11 discovered
  business functions" is correct; "466 functional requirements" is not.
- **Absence of evidence for a function is never evidence about that function.** Unrepresented
  functions are named, not characterised.

Functions with no specification are still partly documentable: name, business description,
category, entry points, LOC and data paths all come from the catalog. Only requirement- and
rule-derived content is unavailable for them.

---

## What this evidence source does better, and worse, than Bob

**Better**

| Area | Why |
|---|---|
| Business capabilities, features, requirements, processes | The catalog *is* a validated business decomposition with written descriptions; requirements arrive in EARS form with REQ ids. Bob had to infer capabilities from copybook sharing and job grouping. |
| Business rules | `traceability.yaml` gives every rule a `rule_id`, a disposition and an attributed program. Bob grepped `IF`/`EVALUATE`/`88`. |
| Data dictionary and lineage | Data analysis emits field-level metadata with business descriptions, plus lineage with read/write/update/delete direction, covering DB2 tables. |
| Architecture edges | `interfaces` → `target_bf` gives real function-to-function edges; Bob's call graph was explicitly narrative and unverified. |
| Citations | `REQ-F-042 -> rule R-117 -> CBTRN02C` is a traceable chain, stronger than a bare `member:line`. |
| Dead-code signals | Rule dispositions `unreachable` / `not_applicable` / `delegated` are direct evidence. |

**Worse**

| Area | Why |
|---|---|
| Static scan findings | Bob had Z Code Scan. There is no AWS Transform equivalent. `as_is_assessment` and `security_architecture` carry the most unavailable sections in the suite. |
| Paragraph and variable structure | No `get_paragraphs`, `get_variables`, `get_expanded_source`, `get_control_flow`. Paragraph indexes become parser-derived and are labelled as such. |
| Per-variable data flow | No `get-data-flow`, so field-level lineage stops where the lineage artifact stops. |
| Estate completeness | Bob scanned everything; this covers delivered functions only. |

Unchanged from the Bob port: ISO 5055 scoring, CVE mapping and portfolio roll-up were CAST
capabilities and remain unavailable.

---

## Reading an unavailable section

Two markers appear, and the difference matters when you are deciding whether to chase something:

| Marker | Meaning | Can it be fixed? |
|---|---|---|
| `Not available from AWS Transform analysis` | the evidence does not exist in the run's output | only by a different tool, or not at all |
| `Not extracted by this run` | the evidence **is** in the codebase and the generator did not parse it | yes — extend the generator |

Document status carries the same distinction:

| Status | Meaning |
|---|---|
| `complete` | every heading grounded |
| `partial` | some headings unavailable |
| `unavailable` | nothing grounded, but the plan **did** have evidence — the template asks for what this evidence set cannot answer |
| `blocked` | the plan had no evidence at all |

Keeping these separate is deliberate. An earlier version used the first marker for both, which
blamed AWS Transform for gaps that were the generator's, and made the output look more
fundamentally limited than it is.

## Provenance vocabulary

Every derived artifact carries one of these. The Bob values (`z-workflow-verified`,
`narrative-per-program-not-tool-verified`, `z-understand-verified`) are invalid here and their
appearance in output means content leaked from the wrong skill.

| Value | Meaning |
|---|---|
| `atx-artifact-verified` | straight from an AWS Transform artifact — strongest available |
| `source-read-verified` | read verbatim from a source member |
| `requirements-derived` | inferred from `requirements.md` prose, traceable to a REQ id |
| `parser-derived-not-tool-verified` | derived by parsing source; no structural verifier behind it |
| `unavailable-atx` | no AWS Transform equivalent; heading rendered, content withheld |

---

## Deliberate exclusions

**The AWS Transform chat and its Neptune knowledge graph are not evidence sources.** They would
enrich several plans, but they are non-deterministic and cannot be reproduced from disk, which
breaks the determinism rules the whole contract rests on. Documents must be regenerable from the
same artifacts with the same result.

**This skill never writes outside `docsRoot`.** `.atx/mfre/` belongs to
`mainframe-reverse-engineering`; application source is never modified.

---

## Reference index

| Need | File |
|---|---|
| The 31 documents, levels, plans, output paths | `references/document-catalog.md` |
| Evidence contract, coverage honesty, provenance, determinism, self-check | `references/grounding-contract.md` |
| The nine `atx-*` evidence plans and the artifact inventory | `references/evidence-plans.md` |
| Distributed-stack concept → AWS Transform evidence | `references/atx-substitutions.md` |
| One document's required section set | `references/prompts/<n>-<prompt_type>.md` |

## Companion skills

| Skill | Role |
|---|---|
| `mainframe-reverse-engineering` | **Upstream.** Produces the evidence this skill consumes. Run it first. |
| `z-app-documentation` | Sibling port for IBM Bob + Z Premium Package. Different runtime, different evidence. |
