# mainframe-modernization-skills

Five agent skills that take a mainframe codebase through AWS Transform reverse engineering and out
the other side as a 31-document application knowledge base — packaged for **Kiro**, **Claude Code**
and **Codex** from a single source.

Internal repository.

```
COBOL/JCL source
      │
      ▼  mainframe-reverse-engineering      drives AWS Transform via MCP
.atx/mfre/                                  state, spec bundles, analysis artifacts
      │
      ▼  atx-app-documentation              offline, deterministic, evidence-grounded
.atx/app-docs-<run-id>/  +  .zip            31 documents across 9 levels
```

---

## Status

**Skeleton.** The structure, runtime recipes and documentation are in place. `src/skills/` is not yet
populated and `tools/build.py` is not yet implemented — that is step 2, which imports the working
suite and proves the generated Kiro variant is byte-identical to it.

| Component | State |
|---|---|
| `docs/` | complete — work log, defect log, baselines, plan |
| `src/skills/` | **populated** — five skills, runtime-neutral |
| `runtimes/` | three recipes, MCP configs, fragments |
| `tools/build.py` | **working** — all three variants build |
| `dist/` | **generated** — kiro, claude-code, codex |
| `tools/` lints | `check_bash32`, `scan_secrets`, `check_links`, `lint_frontmatter` all working |
| `tests/` | **working** — synthetic fixture + golden test, verified able to fail |
| `tools/install.sh` | specified stub |

**New here?** Start with [`docs/HANDOVER.md`](docs/HANDOVER.md) — setup, status, next steps and the
traps, in one place.

Seven of eight gates pass, including the golden test. `check-drift` is blocked until the repository is
`git init`-ed, which is correct: it refuses to run rather than pass vacuously on an untracked tree.

The built Kiro variant reproduces the reference baseline — 31 documents, 111 grounded / 90 absent / 0
not-extracted — with documents byte-identical to the source tree's own output.

Read [`docs/REPO-PLAN.md`](docs/REPO-PLAN.md) for the design and the open decisions, and
[`docs/WORK-LOG.md`](docs/WORK-LOG.md) for what has been built and verified so far.

---

## The five skills

| Skill | Role | Needs AWS? |
|---|---|---|
| `mainframe-reverse-engineering` | drives AWS Transform: intake, discovery, extraction, requirements | yes — MCP + CLI |
| `atx-app-documentation` | the documentation model: 31 documents, grounding contract, coverage matrix | **no** |
| `atx-pipeline` | end-to-end driver: fetch → documents → published zip | for 5 of 9 phases |
| `atx-generate-docs` | generate documents from a local run | no |
| `atx-docs-status` | coverage, gaps, staleness | no |

The suite installs as a unit. The documentation side is fully offline, which is why it ports to a new
runtime with no environment work at all — see [`docs/MIGRATION.md`](docs/MIGRATION.md).

---

## Repository layout

```
src/skills/              the ONLY hand-edited copy of the skills
runtimes/<runtime>/      per-runtime recipe: install path, frontmatter policy, MCP config
templates/               CLAUDE.md / AGENTS.md pointer snippets
dist/<runtime>/          GENERATED, committed, CI-verified — never hand-edit
tests/fixtures/          synthetic golden-run input
tools/                   build and lint
docs/                    design, work log, defect log, baselines
.claude-plugin/          Claude Code marketplace manifest
```

`dist/<runtime>/` mirrors the true install path, so `cp -R dist/claude-code/. ~/repo/` is correct
without instructions.

---

## Why single-source-plus-build

The variant surface was measured, not assumed. Of 63 files, **60 are byte-identical across all three
runtimes**:

| Asset | Files | Runtime-specific |
|---|---|---|
| scripts (`.py`, `.sh`) | 11 | 0 |
| references (`.md`) | 11 | 0 |
| prompt templates | 31 | 0 |
| `SKILL.md` | 5 | 3 files, 8 path references |

Three hand-maintained trees would mean 189 files drifting over a real difference of eight lines plus
three front-matter keys. So: one source, a thin build, and a CI check that fails if `dist/` was edited
by hand.

The one substantial difference is MCP. `mainframe-reverse-engineering` reaches AWS Transform through
`awslabs.aws-transform-mcp-server`, which Kiro supplies as a Power and the other two runtimes need
configured directly. Even there the tool vocabulary is identical — 55 references port unchanged
because the skills name tools, never invocation paths. See
[`docs/PORTABILITY-RULES.md`](docs/PORTABILITY-RULES.md).

---

## Usage

```bash
make help             # list every target
make build            # src/ + runtimes/ -> dist/
make check            # every CI gate locally
make test             # golden run against the fixture (skips if absent)
make dev              # build the Kiro variant into ../.kiro/skills for dogfooding
```

`make dev` is how the suite is dogfooded in Kiro. Because the build is symmetric, the working
`.kiro/skills` tree is *generated* — edit `src/` and re-run `make dev`, never edit the installed tree.

Install, per runtime:

```bash
# Claude Code — native marketplace
/plugin marketplace add <org>/mainframe-modernization-skills
/plugin install atx-mainframe-suite

# Kiro or Codex — download, inspect, then run
sh tools/install.sh --runtime codex --scope project --dry-run
```

---

## Open decisions

Tracked in [`docs/REPO-PLAN.md`](docs/REPO-PLAN.md#open-decisions). Three need a human:

1. **Licensing.** The skills declare `Apache-2.0` in their front matter, but this is an internal
   repository and no `LICENSE` file has been added — so the repository currently claims a licence it
   does not carry. Either add the file or change the front matter.
2. **`git init`.** Unblocks `check-drift`, which cannot verify committed output without it. Note that
   this directory presently sits inside another git repository; decide whether to move it out first.
3. **Marketplace owner.** `.claude-plugin/marketplace.json` carries `REPLACE_WITH_ORG` placeholders,
   and that string becomes the user-facing install path.

Then two build items: the **synthetic fixture** (unblocks a meaningful `make test`) and
**`tools/install.sh`**.
