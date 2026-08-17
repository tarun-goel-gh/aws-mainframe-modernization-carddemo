# Handover

Everything needed to pick this up and continue. Read this first, then
[`REPO-PLAN.md`](REPO-PLAN.md) for design reasoning and [`DEFECTS.md`](DEFECTS.md) for why the
mechanisms exist.

Written for someone who has not seen the project. It is long because the alternative is you
rediscovering things the expensive way.

---

## 1. What we are trying to achieve

**The motion.** Mainframe modernization engagements begin with the same problem: nobody knows what the
COBOL estate does. AWS Transform can reverse-engineer it — discover business functions, extract business
rules, generate requirements — but its output is a pile of artifacts, not something a stakeholder can
read.

So there are two halves:

1. **`mainframe-reverse-engineering`** drives AWS Transform end to end and lands verified artifacts on
   disk at `.atx/mfre/`.
2. **`atx-app-documentation`** turns those artifacts into **31 documents across 9 levels** — executive
   summary through business rules, data lineage, migration roadmap — every statement traceable to an
   artifact.

**Why this is hard, and where the value is.** Anyone can have a model write 31 plausible documents. The
difficulty is producing documents a stakeholder can *trust* when the evidence is incomplete — which it
always is. On the reference estate, AWS Transform discovered 11 business functions and delivered usable
specifications for **6**. A naive tool produces 31 documents that read as if they describe the whole
application. This one carries `6 of 11` into every count and marks what it cannot evidence.

That honesty machinery is the product. Guard it.

**Why this repository exists.** The suite was built inside one workspace's `.kiro/skills/`. It now has
to be installable on **Kiro, Claude Code and Codex**, versioned, and shareable across the team. Since
all three converged on the open [Agent Skills](https://agentskills.io) standard, that is a packaging
problem, not a rewrite.

---

## 2. Repository tour

```
mainframe-modernization-skills/
├── src/skills/          THE ONLY HAND-EDITED COPY of the five skills
├── runtimes/<rt>/       per-runtime recipe: install path, frontmatter policy, MCP config, fragments
├── dist/<rt>/           GENERATED + committed. Never hand-edit.
├── templates/           CLAUDE.md / AGENTS.md pointer snippets
├── tests/               golden runner + synthetic fixture + recorded baseline
├── tools/               build and lint
├── docs/                this file and nine others
├── .claude-plugin/      Claude Code marketplace manifest
└── Makefile             every entry point
```

313 files: 64 source, 195 generated, 22 under `tests/`, 10 documents.

The generated tree is three times the source tree. That ratio is the whole argument for the build — see
§9.

### The five skills

| Skill | Version | Role | Needs AWS |
|---|---|---|---|
| `mainframe-reverse-engineering` | 1.1.1 | drives AWS Transform via MCP | yes |
| `atx-app-documentation` | 1.0.0 | the document model, grounding contract, coverage matrix | **no** |
| `atx-pipeline` | 1.0.0 | 9-phase end-to-end driver | 5 of 9 phases |
| `atx-generate-docs` | 1.0.0 | generate from a local run | no |
| `atx-docs-status` | 1.0.0 | coverage, gaps, staleness | no |

The last three are thin entry points that give an action an invocable name. All behaviour is in the
first two.

### Documents in `docs/`

| File | Read it when |
|---|---|
| `HANDOVER.md` | now |
| `REPO-PLAN.md` | you want the design and the open decisions |
| `DEFECTS.md` | **before removing anything that looks redundant** |
| `WORK-LOG.md` | you want the full history and rationale |
| `BASELINES.md` | the golden test failed |
| `PORTABILITY-RULES.md` | you are editing `src/` or adding a runtime |
| `MIGRATION.md` | you are installing on Claude Code or Codex |
| `VERSIONING.md` | you are cutting a release |
| `EXAMPLES.md` | you want a real run's numbers |
| `WORKFLOW.md` | pointer to the pipeline reference, which ships with the skill |

---

## 3. Setup from zero

### Prerequisites

`python3` (3.9+; developed on 3.14), `bash`, `unzip`, `zip`, `shasum`, `git`. **No third-party Python
packages** — that is deliberate and should stay true. AWS CLI v2 only for the AWS phases.

Nothing to install:

```bash
cd mainframe-modernization-skills
make help
make build          # src/ + runtimes/ -> dist/
make check          # every gate
make test           # golden run against the synthetic fixture
```

`make check` will fail on one gate until `git init` — see §5.

### Working on the suite in Kiro

The build is symmetric: the Kiro variant is generated like the others, so **the working
`.kiro/skills/` tree is build output**.

```bash
make dev            # builds and installs into ../.kiro/skills
```

Edit `src/`, run `make dev`, exercise it in Kiro. Never edit `.kiro/skills/` directly — the change is
lost on the next build and reaches nobody.

### The live workspace

This repository sits inside a CardDemo checkout used as the reference estate. That parent workspace
holds artifacts you will want:

```
.atx/mfre/                        104 MB — a completed AWS Transform run
.atx/app-docs-20260814-194447/    1.5 MB — 31 generated documents
.atx/app-docs-<id>.zip            the packaged deliverable
```

`.atx/` is gitignored in the parent, so these are **local only**. If you need them and they are gone,
they can be rebuilt from S3 — see §7.

---

## 4. What is done

### Working and verified

**The pipeline.** Nine phases, fully exercised against a real AWS Transform job from an empty local
state, including publish to S3:

```
1 preflight  2 fetch-specs  3 verify-split  4 snapshot-analysis
5 coverage   6 evidence     7 generate      8 package  9 publish
```

Reference output: **31 documents, 111 grounded / 90 evidence-absent / 0 not-extracted (55%),
4 complete / 25 partial / 2 unavailable, 6 of 11 business functions.** Two runs produce byte-identical
documents.

**The build.** All three variants generate from one source. A rebuild is byte-identical. Running the
pipeline *from* `dist/kiro` reproduces the reference baseline with documents byte-identical to the source
tree's own output — which is the assertion that matters, since the build is verified functionally rather
than by comparing against a tree we deliberately modified.

**The golden test.** 19-file, 80 KB synthetic fixture with a recorded baseline, and — importantly —
**verified able to fail**. Three mutations each trip a different assertion. Details in
[`BASELINES.md`](BASELINES.md#proven-to-fail).

**The gates.** Seven pass; each maps to a defect that actually happened.

| Gate | Catches |
|---|---|
| `check-scripts` | compile and parse |
| `check-bash32` | bash 4 constructs (macOS ships 3.2) |
| `check-frontmatter` | invalid or leaked front matter, version/CHANGELOG drift |
| `check-generic` | customer identifiers outside `docs/EXAMPLES.md` |
| `check-secrets` | credentials and principal identity anywhere |
| `check-links` | broken relative links |
| `test` | golden run + determinism |
| `check-drift` | **blocked** — needs `git init` |

### Publishing works

Presigned by default; `--public` writes a **prefix-scoped** policy, merged into any existing one. Verified
anonymously with all credentials stripped: documentation prefix 200, a sibling prefix in the same bucket
403, bucket listing 403.

`--public` is **refused** when the upload bucket is also the artifact bucket. Do not work around that;
§8 explains why.

---

## 5. What is pending

### Blocked on a human decision — take these to the owner

**1. Licence.** `SKILL.md` front matter declares `Apache-2.0`; there is no `LICENSE` file. The
repository currently claims a licence it does not carry. Add the file or change the front matter.
Blocks any release.

**2. `git init`.** `check-drift` verifies that committed `dist/` matches a fresh build. `git diff` exits
0 on untracked files, so without git the gate would pass while checking nothing — it therefore refuses,
and `make check` fails by design. Note this directory currently sits **inside** the CardDemo git
repository; decide whether to move it out first.

**3. Marketplace owner.** `.claude-plugin/marketplace.json` carries `REPLACE_WITH_ORG`. That string
becomes the user-facing install path (`/plugin marketplace add <org>/<repo>`).

### Build work, in priority order

**4. Install a non-Kiro variant and run it.** Both build and lint clean; **neither has ever been
executed on its own runtime.** This is the highest-risk unknown. Start with the documentation half,
which is fully offline and needs no MCP:

```bash
cp -R dist/claude-code/. /path/to/some/repo/
cd /path/to/some/repo
.claude/skills/atx-app-documentation/scripts/run_pipeline.sh --offline --dry-run
```

Then the reverse-engineering half, which needs the MCP server configured — see
[`MIGRATION.md`](MIGRATION.md#step-5a--mcp-the-one-substantial-difference).

**5. `tools/install.sh`.** A specified stub; the docstring lists every requirement and why. Claude Code
does not need it (the marketplace covers install and updates), but Kiro and Codex have no equivalent.

**6. `tools/release.sh`.** Referenced by [`VERSIONING.md`](VERSIONING.md) and not written. Per-runtime
tarballs plus `SHA256SUMS`.

**7. Bundle merge is untested.** The richest-wins selection is the single most valuable correctness
mechanism in the pipeline (§8) and the golden test does **not** cover it, because it runs in phase 3 and
`--offline` skips that phase. Needs competing raw zips in the fixture and a non-offline invocation.

**8. Coverage long tail.** Working-storage and paragraph-index parsers would lift `technical_specs` and
`code_structure`. Each new parser must move `grounded` up and keep `not-extracted` at 0.

### Upstream, not ours

**9. Three business functions return empty requirements from AWS Transform.** Business rules extract
correctly — 18 rules across 9 files in one case — but requirements generation emits only an empty
`discovery/programs.yaml`. Reproduced twice sequentially, which ruled out batching. The empty bundles
were kept as support evidence. This is why the reference estate is 6 of 11 rather than 9 of 11.

---

## 6. How to test

### Fast loop, no AWS

```bash
make check          # all gates, seconds
make test           # golden run, ~10s
```

### Against the real estate

From the **parent workspace**, not this repo:

```bash
cd ..
.kiro/skills/atx-app-documentation/scripts/run_pipeline.sh --offline --force --run-id TRY
```

Expect 31 documents and 111/90/0. Anything else means a regression — diff the run folder against
`.atx/app-docs-20260814-194447/`.

### Determinism

The contract is that identical evidence produces byte-identical documents. Wall-clock values are confined
to `generatedAt`, `docsRoot`, `run-log.md` and `run-state.json`.

```bash
diff -r runA runB -x run-log.md -x run-state.json
```

The zip is **not** byte-reproducible — zip embeds mtimes. Its sha256 is recorded in `run-log.md` for
traceability, not determinism.

### When the golden test fails

Read the side-by-side diff it prints. Then decide which you have:

- **A regression** — fix it.
- **An intended change** — `tests/run_golden.sh --record`, *and* state the movement in `CHANGELOG.md`.
  [`VERSIONING.md`](VERSIONING.md) requires this: a document-content change without an evidence change
  is otherwise indistinguishable from a regression.

### Full AWS run

Needs credentials and an upload bucket. See [`EXAMPLES.md`](EXAMPLES.md) for a real invocation with
real output. Roughly 70 seconds, dominated by the ~100 MB analysis download in phase 4.

---

## 7. Environment

Values specific to the current setup, not to the tool. Confirm them with the owner; they are not
product configuration.

| Thing | Value |
|---|---|
| AWS profile | `ace-prod-us` |
| Region | `us-east-1` |
| Artifact bucket (read) | `ace-modernization-demo` |
| Docs bucket (published, public prefix) | `ace-modernization-output-us`, prefix `generated-zip/` |
| Transform job id | `2da94a4d-92a4-49eb-9fdb-b9d68d18cb5e` |
| Reference estate | AWS CardDemo sample |

Rebuilding `.atx/mfre/` from scratch:

```bash
cd ..   # the parent workspace
.kiro/skills/atx-app-documentation/scripts/run_pipeline.sh \
  --profile ace-prod-us --region us-east-1 \
  --bucket ace-modernization-demo \
  --job-id 2da94a4d-92a4-49eb-9fdb-b9d68d18cb5e \
  --no-upload
```

SSO sessions last about an hour: `aws sso login --profile ace-prod-us`.

---

## 8. Things that will bite you

Each of these cost real time to find. [`DEFECTS.md`](DEFECTS.md) has the full list with evidence.

**`dist/` is generated.** Editing it is silently undone by the next build. `check-drift` catches it once
git is initialised.

**macOS ships bash 3.2.** No `declare -A`, no `${var,,}`, no `mapfile`. And `bash -n` *parses*
`${var,,}` happily — it fails only when the branch executes. A validation loop once used it, the bad
substitution aborted the compound command, `usage` never ran, and **a missing required argument stopped
stopping the script.** `make check-bash32` exists for this.

**zsh does not word-split unquoted variables.** `E="env -u ..."; $E aws ...` fails with `command not
found`. Use a function.

**Always pass `--profile` explicitly.** An empty `AWS_PROFILE` silently falls back to the default
profile, usually expired. A stale `AWS_CREDENTIAL_EXPIRATION` produces `Credentials were refreshed, but
the refreshed credentials are still expired` — neither an expired login nor clock skew. The pipeline
driver now unsets those variables for itself; anything you write by hand must too.

**Newest is not best.** AWS Transform writes one zip per generation attempt, and a later attempt can be
dramatically worse — one function returned **294** requirements on the first attempt and **14** on a
later one. The largest zip in the reference job contains exactly **one** function. Phase 3 therefore
selects by requirement count and treats the existing tree as a candidate, making a re-run monotonic.
Every decision lands in `bundle-selection.md`. **Do not simplify this to newest-wins or largest-wins.**

**Never let scratch files into the archive.** A published zip once contained
`.phase-preflight.out`, leaking an assumed-role ARN including an SSO permission set name and a corporate
email address, because packaging ran before cleanup. Phase output now goes to a `mktemp` directory
outside the run folder, and phase 8 runs a **disclosure gate** over every archive entry. If you refactor
packaging, carry that gate across.

**A gate that cannot check must fail.** `check-drift` once passed while comparing nothing. If you find a
check that is green in a situation where it could not possibly have verified anything, that is a bug.

**Determinism is load-bearing, not tidiness.** `document-evidence.json` fingerprints every artifact each
document consumed, which is what makes staleness detection possible. Introduce model-generated prose into
the documents and the fingerprints stop meaning anything. **No agent-authored content in generated
documents.**

**Two absence markers, deliberately.** `Not available from AWS Transform analysis` means the evidence
does not exist. `Not extracted by this run` means it exists and the generator did not parse it. Merging
them blames AWS for our gaps. `not-extracted` is currently **0** — keep it there.

---

## 9. Decisions already made

Do not relitigate these without reading the reasoning; each has evidence behind it.

| Decision | Why |
|---|---|
| One source + generated variants, not three copies | 60 of 63 files are identical across runtimes |
| Symmetric build (Kiro generated too) | stops Kiro becoming the privileged variant that drifts |
| `dist/` committed to git | direct download and browsing; safe only because `check-drift` enforces it |
| Skills name tools, never invocation paths | 55 MCP tool references port across runtimes for free |
| Scripts self-locate from `__file__` | works from any install path, any working directory |
| Sequential extraction, not batch | measured depth loss: 286 requirements → 14 |
| Transform chat and Neptune KG excluded as evidence | non-deterministic, breaks the determinism contract |
| Presigned URLs by default, `--public` opt-in | one object, self-expiring, no policy change |
| `--public` refused into the artifact bucket | that bucket holds the raw source analysis |
| `z-app-documentation` left alone | separate Bob/Z lineage, shares no code |

---

## 10. Suggested first week

**Day 1.** `make check`, `make test`, then `make dev` and drive `/atx-pipeline` in Kiro against the live
`.atx/mfre`. Read `DEFECTS.md` end to end — it is the fastest way to understand why the code looks the
way it does.

**Day 2.** Resolve the three human decisions in §5, or escalate them. `git init` unblocks the last gate
and makes `make check` fully green, which you want before changing anything.

**Day 3-4.** Item 4: install `dist/claude-code` or `dist/codex` somewhere real and run `--offline`. This
is the largest remaining unknown and the whole point of the packaging work. Expect the surprises to be
environmental — sandbox permissions, MCP server credential resolution — not in the skills.

**Day 5.** Item 7: extend the fixture with competing bundles so the richest-wins merge is covered. It is
the most valuable untested mechanism.

Then items 5 and 6 (installer, release script) whenever distribution becomes urgent.

---

## 11. One-page summary

- **Goal:** turn an AWS Transform mainframe analysis into 31 trustworthy documents, packaged for three
  agent runtimes.
- **Works:** the full pipeline against a real estate; all three variants build; a golden test that is
  proven able to fail; seven of eight gates.
- **Blocked on you:** licence, `git init`, marketplace org.
- **Biggest unknown:** neither non-Kiro variant has ever been run.
- **Do not break:** determinism, the two absence markers, richest-wins bundle selection, the disclosure
  gate.
- **Read next:** [`DEFECTS.md`](DEFECTS.md) — it explains the code better than the code does.
