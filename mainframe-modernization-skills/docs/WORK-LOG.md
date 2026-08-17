# Work log

What was built, what was verified, and why the design is the way it is.

Organised by theme rather than chronology. Where a claim was verified by running something, the
evidence is given; where it comes from earlier in the working session and was carried forward through
a context summary, it is marked **(summarised)** so the two are not confused.

---

## 1. What exists

Two skills carry all the behaviour. Three are entry points that give an action an invocable name.

| Skill | Version | Purpose |
|---|---|---|
| `mainframe-reverse-engineering` | 1.1.1 | drives AWS Transform end to end via MCP: connectivity, intake, discovery, business-logic extraction, requirements generation |
| `atx-app-documentation` | 1.0.0 | the documentation model — 31 documents over 9 levels, grounding contract, coverage matrix, determinism rules |
| `atx-pipeline` | 1.0.0 | nine-phase driver: fetch → verify → snapshot → documents → zip → publish |
| `atx-generate-docs` | 1.0.0 | generate documents from a local run |
| `atx-docs-status` | 1.0.0 | coverage, gaps, staleness |

63 files: 6 Python scripts, 5 shell scripts, 11 reference documents, 31 prompt templates, 5
`SKILL.md`, plus READMEs.

`atx-app-documentation` is the third port of the same 31-document catalogue. The origin was a CAST
Imaging integration; the second was `z-app-documentation`, sourced from IBM Bob and the Z Premium
Package. This one is sourced from AWS Transform. The prompt catalogue, grounding contract,
determinism rules and evidence-plan mechanism carry across all three; only the evidence source
changes. `z-app-documentation` was deliberately left untouched — it is a different product lineage and
shares no code.

---

## 2. The nine-phase pipeline

`atx-app-documentation/scripts/run_pipeline.sh` drives everything.

```
              ┌──────────── needs AWS ────────────┐
1 preflight → 2 fetch-specs → 3 verify-split → 4 snapshot-analysis
                                                      │
              ┌──── offline, deterministic ───────────┘
              5 coverage → 6 evidence → 7 generate → 8 package
                                                      │
                                      9 publish ◄─────┘  needs AWS
```

Phases 5-8 need no network, which matters more than it sounds: SSO sessions are about an hour and the
documentation half of the suite is unaffected by that. `--offline` is both the fast path and a
complete path.

Design commitments, each of which exists because its absence was a defect:

- **One run, one folder.** The driver stamps `.atx/app-docs-<YYYYMMDD-HHMMSS>` once and exports
  `ATX_DOCS_ROOT`. Each script can compute its own default, so without a single stamp a run would
  straddle two folders.
- **Four statuses, not two.** `ok` / `partial` / `skipped` / `FAILED`. `partial` is a first-class
  outcome, not a soft failure — see §4.
- **Fail-fast.** Phases are dependency-ordered, so a fatal failure stops the run rather than
  proceeding into work that cannot succeed. `--keep-going` overrides.
- **Resumable.** `run-state.json` records per-phase status; `--resume <id> --from <phase>` skips what
  passed.
- **Scratch outside the run folder.** Phase 8 archives the run folder, so anything scratch inside it
  becomes archive content. This is a disclosure boundary, not tidiness (§5).

---

## 3. Verified baseline

Full end-to-end run against a real AWS Transform job, from an empty local state — `specs/`,
`specs-raw/` and `analysis/` all removed first so phases 2-4 had to rebuild from S3.

```
1  preflight          ok        18.8s
2  fetch-specs        ok         2.8s
3  verify-split       partial    2.2s   exit=1, expected
4  snapshot-analysis  ok        34.0s   102 MB
5  coverage           ok         0.2s
6  evidence           ok         0.6s
7  generate           ok         0.4s
8  package            ok         0.4s
9  publish            ok         6.7s
```

| Measure | Value |
|---|---|
| documents | 31 |
| sections | 111 grounded / 90 evidence-absent / 0 not-extracted (55%) |
| document statuses | 4 complete / 25 partial / 2 unavailable |
| business functions | 6 delivered of 11 discovered, 9 scoped |
| determinism | 31 documents byte-identical across runs |

Determinism holds where it matters. Two runs differ only in `generatedAt`, `docsRoot`, `run-log.md`
and `run-state.json` — verified as zero substantive differences in `manifest.json`.

The published archive was fetched with every AWS credential stripped from the environment: HTTP 200,
valid zip, 31 documents. Public access is scoped to one prefix; a sibling prefix in the same bucket
returned 403 anonymously, and so did a bucket listing.

These numbers describe **one job**. They are the regression baseline for that evidence, not a
universal expectation. See [`BASELINES.md`](BASELINES.md).

---

## 4. Coverage honesty

The hardest part of the design, and the reason most of the mechanism exists.

AWS Transform discovered 11 business functions, 9 were scoped, and **6 came back with a usable
specification**. Three returned empty requirements — business rules extracted fine (18 rules across 9
files in one case) but requirements generation emitted only an empty `discovery/programs.yaml`.
Reproduced twice sequentially, which disproved batching as the cause and located the fault AWS-side.

That leaves a genuine dilemma. Refusing to document a partially delivered estate makes the tool
useless; documenting it silently produces 31 documents that read as though they describe the whole
application. Neither is acceptable, so:

- **`partial` is a real status.** Phase 3 exits 1 when delivery is short of discovery, the run
  continues, and this is recorded rather than smoothed over.
- **Every count carries the denominator.** `6 of 11` propagates into the coverage matrix and from
  there into the documents.
- **Two distinct absence markers.** `Not available from AWS Transform analysis` means the evidence
  does not exist. `Not extracted by this run` means it exists and the generator did not parse it.
  Collapsing them would blame the evidence source for tooling gaps. A single marker was considered and
  rejected for exactly that reason.
- **Absence of evidence is not evidence about a function.** Unrepresented functions are named, never
  characterised.
- **Two documents are `unavailable`.** `security_architecture` and `modernization_strategy` have zero
  grounded sections because the evidence genuinely does not exist. Reported as such rather than padded
  with inference.

Provenance vocabulary: `atx-artifact-verified`, `source-read-verified`, `requirements-derived`,
`parser-derived-not-tool-verified`, `unavailable-atx`. Bob's vocabulary is forbidden in this port so
the two lineages cannot be confused.

**(summarised)** Coverage was raised from an initial state through several rounds of parser work:
6 defects fixed, then 1 semantic mismatch, then 8 more, then all 16 remaining `not-extracted`
sections closed by writing the missing parsers. End state is 0 `not-extracted`, which means every
remaining gap is genuine evidence absence rather than a tooling shortfall.

---

## 5. The disclosure incident

The most important thing in this log.

A published archive was **anonymously readable and contained `.phase-preflight.out`**, an internal
scratch file holding the full preflight JSON:

```
arn:aws:sts::<ACCOUNT>:assumed-role/AWSReservedSSO_AdministratorAccess_<id>/<user>@<company>.com
```

That disclosed three things outside the set the user had been told would be public: the SSO permission
set name (revealing AdministratorAccess), its id, and a corporate email address. The account id was
already in the disclosed set; these were not.

**Root cause: phase ordering.** The driver deleted scratch files at the end of the script, but the zip
is built in phase 8, before that cleanup. Exposure window about 30 minutes.

Response, in order:

1. Deleted the object and confirmed anonymous 403 — stopping the exposure before fixing the cause.
2. Moved phase output to a `mktemp` directory outside the run folder, with a trap for cleanup.
   Packaging cannot include what was never in the folder, regardless of ordering.
3. Added redundant guards: `ph_package` clears stale scratch files for `--resume` against older run
   folders, and `zip -x` excludes the pattern.
4. Added a **disclosure gate**: phase 8 scans every archive entry for IAM/STS principal ARNs,
   `ASIA`/`AKIA` access key ids, `X-Amz-Security-Token=` and secret-key assignments. A hit deletes the
   zip and fails the phase. Tested against the known-bad archive; it catches exactly the file that
   leaked.
5. Re-published and verified the live object: zero hits for scratch files, ARNs, keys, tokens or the
   email.

The account id is deliberately **not** in the gate's pattern list. It appears in 7 of the 31 documents
by design and the user is told so before publishing. A gate that fires on expected content gets
disabled.

Two related decisions:

- **`--public` is refused when the upload bucket is also the artifact bucket.** That bucket holds the
  raw source analysis, spec bundles and data dictionary; a policy there is one edit from exposing all
  of it. Refusal, not a warning.
- **Public policies are prefix-scoped and merged, never replacing.** `put-bucket-policy` replaces the
  whole document, so the existing policy is read first and the statement replaced by `Sid`. Verified
  it preserves unrelated statements and is idempotent.

---

## 6. Publishing

Default is a presigned URL: no policy change, one object, self-expiring.

A presigned URL **cannot outlive the credentials that signed it**. With a one-hour SSO session,
`--expires-in 604800` still dies in an hour, so the publish phase compares the two and reports the
real lifetime. Observed live: credentials expiring in 3,404 s against a requested 604,800 s.

`--public` writes a prefix-scoped statement into a dedicated bucket. Verified anonymously against the
live object: the documentation prefix returned 200, a sibling prefix 403, and bucket listing 403.

---

## 7. Bundle selection

AWS Transform writes **one zip per generation attempt**, each holding only the functions that attempt
produced, so the delivered estate is the *union* across zips. Two measurements killed the obvious
heuristics:

- The largest zip in the job contains exactly **one** function.
- One function returned **294** requirements on the first attempt and **14** on a later one.

So neither size nor recency identifies the best copy, and a newest-wins rule measurably destroyed
data — an 81,708-byte requirements file replaced by 8,576 bytes.

Phase 3 now stages every zip, splits each into its own output, and selects per function by requirement
count with bytes as tie-break. The existing `specs/` entry competes too, which makes a re-run
**monotonic**: the estate can improve or hold, never degrade. Every decision is recorded in
`00-manifest/bundle-selection.md`.

Verified from scratch, with no prior tree to lean on, the merge picked the 294-requirement copy. It
also found a function bundle the single-zip approach missed entirely — from the *earliest* zip, which
a largest-wins rule could never have selected.

---

## 8. Determinism, and why it is a contract

Identical inputs produce byte-identical documents. Wall-clock values are confined to `generatedAt`,
`docsRoot`, `run-log.md` and `run-state.json`.

This is load-bearing, not tidiness. `document-evidence.json` fingerprints every artifact each document
consumed, which is what makes staleness detection possible: a document is stale when a fingerprint no
longer matches disk. Introduce model-generated prose into the documents and the fingerprints stop
meaning anything.

Consequences accepted deliberately:

- **Documents are generated, not composed by an agent.** Freehand composition cannot guarantee
  byte-identical output.
- **AWS Transform chat and the Neptune knowledge graph are excluded as evidence.** Both are
  non-deterministic. Richer evidence plans that used them were considered and rejected.
- **The self-check blocks filing.** Eight rules; a document that fails is reported and not written.
  Asserting compliance is not compliance.

---

## 9. Documentation written

| Document | Purpose |
|---|---|
| `.kiro/skills/README.md` | suite index and data flow |
| `atx-pipeline/README.md` | the detailed nine-phase workflow reference |
| `atx-app-documentation/README.md` | the documentation model |
| `mainframe-reverse-engineering/README.md` | the reverse-engineering skill, gates G0-G5 |
| `atx-generate-docs/README.md`, `atx-docs-status/README.md` | thin entry points |
| `MIGRATION.md` | porting to Claude Code and Codex |

Every number quoted in these was checked against the real run rather than trusted from memory, which
caught three stale counts and one stale line-count claim. Link, code-fence and table integrity
verified: 8 documents, 0 problems.

---

## 10. Portability work

Both Claude Code and Codex have converged on the open [Agent Skills](https://agentskills.io) standard
— a folder with `SKILL.md`, front matter requiring `name` and `description` at minimum. So the port is
a directory copy plus a front-matter trim, not a rewrite.

Measured variant surface: **60 of 63 files are byte-identical** across runtimes. The delta is three
`SKILL.md` bodies (8 path references) and three Kiro-only front-matter keys.

Two portability fixes made:

- `generate_docs.py` hardcoded its own install path, which also forced the working directory to be the
  workspace root. Now self-locating from `__file__`, with `ATX_SKILL_ROOT` as an override. Verified it
  resolves its templates from a different working directory and produces byte-identical output.
- Source walks excluded `.kiro` but not `.claude` or `.codex`, so an installed skill tree would be
  scanned as application source. Proved with a decoy COBOL file.

The one substantial difference is MCP, and it applies to one skill. See
[`PORTABILITY-RULES.md`](PORTABILITY-RULES.md).

---

## 11. Operating environment notes

Hard-won and worth keeping:

- **Always pass `--profile` explicitly, and strip stale credential variables.** A shell with an empty
  `AWS_PROFILE` silently falls back to the default profile, which is usually expired. A stale
  `AWS_CREDENTIAL_EXPIRATION` produces `Credentials were refreshed, but the refreshed credentials are
  still expired` — which is neither an expired login nor clock skew.
- **zsh does not word-split unquoted variables.** `E="env -u ..."; $E aws ...` fails with
  `command not found`. Use a function.
- **macOS ships bash 3.2.** No associative arrays, no `${var,,}`. And `bash -n` parses `${var,,}`
  without complaint, so this class of bug only surfaces when the branch executes.
- **`aws s3api put-object --body /dev/null` is rejected** — the CLI requires a real file path.
- **`timeout` is not present on macOS.**

---

## 12. Rejected alternatives

| Considered | Rejected because |
|---|---|
| Three hand-maintained skill trees | 189 files drifting over an 8-line real difference |
| Single absence marker | blames the evidence source for generator gaps |
| Batch extraction as the default | measured depth loss: 286 requirements → 14 |
| First-match-wins keyword routing in the resolver | dropped one document's coverage from 29% to 5% |
| Bare >50% builder-dominance self-check | false-positived legitimate documents |
| Collapsing `unavailable` and `blocked` | different causes, different remedies |
| AWS Transform chat / Neptune KG as evidence | non-deterministic, breaks the determinism contract |
| Editing `z-app-documentation` in place | different product lineage; forked instead |
| Public S3 as the default share mechanism | presigned exposes one object and self-expires |

---

## 13. Packaging the suite as a repository

The suite began life in a single workspace's `.kiro/skills/`. Turning it into something installable on
three runtimes required measuring the variant surface rather than guessing at it.

**60 of 63 files are byte-identical across runtimes.** Scripts, references and all 31 prompt templates
need no runtime-specific change at all. That ruled out three maintained copies — 189 files drifting over
a real difference of a few tokens — and settled the design: one source, a thin build, generated variants
committed, and a CI gate that fails if a variant was hand-edited.

### What the build does

Three transforms, then a file copy:

1. **Token substitution.** 17 tokens: 11 `{{SKILLS_ROOT}}`, 4 `{{RUNTIME_NAME}}`,
   2 `{{MCP_PREREQUISITE}}`.
2. **Front-matter policy.** Drop `compatibility`, `metadata.argument-hint` and
   `metadata.delegates-to` for non-Kiro runtimes; add per-skill `allowed-tools` for Claude Code.
   `compatibility` is **folded into `description`**, not discarded — it carries the prerequisite gate,
   and on both non-Kiro runtimes `description` is the only text consulted when deciding whether to load
   a skill.
3. **Fragment inclusion.** `<!-- @include: mcp-setup -->` resolves per runtime, which is how one
   `preflight.md` serves a Power-supplied MCP server, a `.mcp.json` and a `config.toml`.
4. **MCP config copy**, for the two runtimes that need one shipped.

Front-matter editing is line-based on purpose. Round-tripping through a parser would reflow
`description`, and that text is a matching surface — reflowing it changes activation behaviour.

### Verification

The acceptance gate was "the Kiro variant reproduces the working tree byte-for-byte". The result was
more informative than a pass:

- **All five `SKILL.md` files round-trip exactly.**
- **Four files differ, every one a deliberate genericisation edit** — no unintended difference.
- **A rebuild is byte-identical**, so the drift gate is trustworthy.
- **The functional test is the stronger one.** Running the pipeline *from* the built variant produced
  31 documents at 111/90/0, byte-identical to the source tree's own output. Since the byte comparison
  is against a tree that was intentionally modified, this is the assertion that carries weight.

### Two measurement errors worth recording

**The variant surface was larger than first measured.** An early count said 8 path references, obtained
by grepping `.kiro/`. But the *product name* also appears in prose — a troubleshooting step, an
activation note, a section heading, a port table. A path-only scan misses those, and each is
runtime-specific in the same way.

**"No MCP" was wrong.** An audit concluded the suite shelled out to the AWS CLI exclusively. True for
`atx-app-documentation`; false for `mainframe-reverse-engineering`, whose entire control plane is MCP
tool calls. A migration performed against that conclusion would have produced a non-functional
reverse-engineering skill. Corrected, and the surface measured: 55 tool references port unchanged,
5 host-specific ones do not.

The reason those 55 port for free is worth stating as a rule: **the skills name the tool, never the
invocation path.** Kiro reaches the server through a Power wrapper and the others expose tools
directly, and no instruction cares. That was an accident; it is now a review rule.

### Genericisation

A tool intended for any mainframe estate carried one application's specifics:

- `generate_docs.py` wrote a **hardcoded application name into all 31 document headers**. Now derived
  from upstream provenance with the derivation source recorded in the manifest.
- Source walks excluded `.kiro` but not `.claude` or `.codex`, so an installed skill tree would be
  scanned as customer source.
- 27 customer-specific identifiers sat in skill prose, including an account id and two bucket names in
  copy-pasteable example commands. Scrubbed to placeholders; the real values live in
  [`EXAMPLES.md`](EXAMPLES.md), which is the one file the genericity gate exempts.

The scrub altered **zero** generated documents, which is the evidence that it was cosmetic to output
and not a behaviour change.

---

## 14. Open items

**Needs a decision, not code**

- **Licence.** The skills declare `Apache-2.0` in front matter but no `LICENSE` file exists, so the
  repository claims a licence it does not carry.
- **`git init`.** `check-drift` cannot verify committed output without it, and refuses rather than
  passing vacuously. The repository directory currently sits inside another git repository.
- **Marketplace owner.** `.claude-plugin/marketplace.json` carries `REPLACE_WITH_ORG`, and that string
  becomes the user-facing install path.

**Build work**

- **`tools/install.sh`.** Specified stub. Claude Code does not need it — the plugin marketplace covers
  install and updates — but Kiro and Codex have no equivalent channel.
- **Bundle merge is untested.** The richest-wins selection runs in phase 3, which `--offline` skips, so
  the golden test does not cover it. Needs competing raw zips in the fixture and a non-offline
  invocation.
- **Install and run a non-Kiro variant.** Both are built and lint clean, but neither has been executed
  on its own runtime.

**Product gaps, upstream or long-tail**

- Three business functions still return empty requirements from AWS Transform. Empty bundles were
  retained as support evidence.
- Working-storage and paragraph-index parsers would lift `technical_specs` and `code_structure`
  coverage further.
