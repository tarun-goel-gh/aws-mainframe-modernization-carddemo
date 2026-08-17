# Repository plan

The design, the reasoning, and what is still undecided.

---

## Decided

| Question | Decision |
|---|---|
| Visibility | internal |
| Name | `mainframe-modernization-skills` |
| Granularity | the suite always installs all five skills |
| Source model | **symmetric** — `src/` is canonical, all three variants generated, including Kiro |
| Fixture | synthetic, not derived from a customer codebase |
| Bob lineage | excluded; `z-app-documentation` is a separate product |

---

## Why single-source-plus-generated

The variant surface was measured before choosing:

| Asset | Files | Runtime-specific |
|---|---|---|
| scripts (`.py`, `.sh`) | 11 | 0 |
| references (`.md`) | 11 | 0 |
| prompt templates | 31 | 0 |
| `SKILL.md` | 5 | 3 files, 8 path references |

**60 of 63 files are byte-identical across runtimes.** Three hand-maintained trees would be 189 files
drifting over a real difference of eight path references and three front-matter keys.

Three options were considered:

1. **Three full copies.** Simple to download, guarantees drift. Rejected.
2. **Single source, build on demand.** No drift, but nothing browsable and no direct download.
3. **Single source, generated variants committed, CI-verified.** Chosen.

Option 3's cost is that generated files are in git, which is normally a smell. It is acceptable here
only because `make check-drift` rebuilds and fails on any difference — the invariant is enforced, not
hoped for.

`dist/<runtime>/` mirrors the true install path so `cp -R dist/claude-code/. ~/repo/` is correct with
no instructions.

### Why symmetric

Generating the Kiro variant too, rather than treating `src/` as the Kiro copy, costs a `make dev` step
in the inner loop. It buys the guarantee that Kiro cannot quietly become the privileged variant whose
paths and front matter drift from the others. Since Kiro is where development happens, that risk is
real.

---

## The build

Three transforms, in order:

1. **Token substitution.** `{{SKILLS_ROOT}}` → the runtime's skills path.
2. **Front-matter policy.** Drop `compatibility`, `metadata.argument-hint`, `metadata.delegates-to`
   for non-Kiro runtimes; fold the substance of `compatibility` into `description`; add `allowed-tools`
   for Claude Code.
3. **Fragment inclusion.** `<!-- @include: mcp-setup -->` resolves from
   `runtimes/<runtime>/fragments/`.

Then copy the runtime's MCP config into `dist/<runtime>/`.

The build must be deterministic: same `src/`, same `dist/`, byte for byte. `check-drift` depends on it.

---

## MCP, the one substantial difference

`atx-app-documentation` needs no MCP, no credentials and no network — it ports with zero environment
work. `mainframe-reverse-engineering` is the opposite: its control plane is MCP tool calls against
`awslabs.aws-transform-mcp-server`.

| | Kiro | Claude Code | Codex |
|---|---|---|---|
| Server declared in | the `aws-transform` Power | `.mcp.json` | `config.toml` `[mcp_servers.*]` |
| Tool access | via the Power wrapper | direct | direct |
| Prerequisite | Power installed | `uvx` + the server package | `uvx` + the server package |
| Recovery | reconnect in the MCP Server view | restart the session | restart the session |

Only 5 references are host-specific, in `SKILL.md`, `references/preflight.md` and `README.md`. The other
55 port unchanged — see [`PORTABILITY-RULES.md`](PORTABILITY-RULES.md) rule 1.

Practical consequence for sequencing: **port the documentation side first**, verify it end to end with
`--offline`, then take on MCP. The two halves have very different environmental risk.

---

## Distribution

| Runtime | Channel |
|---|---|
| Claude Code | native plugin marketplace — this repo is the marketplace |
| Kiro | `tools/install.sh` + release tarball |
| Codex | `tools/install.sh` + release tarball |

Claude Code's marketplace gives discovery, version tracking and updates for free. The others have no
equivalent, hence the installer.

Installer requirements: `--dry-run`, `--scope project|user`, `--runtime`, `--version`, refuse to
overwrite a modified install without `--force`, verify a checksum, and **check the MCP prerequisite**
since that is no longer handled by a Power. No `curl … | sh`.

---

## CI

| Gate | Catches |
|---|---|
| `check-drift` | hand-edited `dist/` |
| `check-bash32` | bash 4 constructs; comments stripped first |
| `check-scripts` | compile and parse |
| `check-frontmatter` | Kiro-only keys leaking; missing CHANGELOG entries |
| `check-generic` | customer identifiers outside `docs/EXAMPLES.md` |
| `check-secrets` | credentials and principal identity anywhere |
| `check-links` | broken relative links |
| `test` | golden run + determinism |

Every gate maps to a defect that actually occurred. See [`DEFECTS.md`](DEFECTS.md#defect-to-guard-map).

---

## Open decisions

### 1. Licence — blocks first release

The skills declare `Apache-2.0` in front matter, but no `LICENSE` file exists and the repository is
internal. Either add the licence file or change the front matter; the current state claims a licence the
repository does not carry.

### 2. `git init` — blocks `check-drift`

`git diff` exits 0 on untracked files, so the drift gate cannot verify committed output in an
un-initialised repository. It refuses rather than passing vacuously, which means `make check` fails
until this is done. The determinism half of that gate runs regardless and currently passes.

Note this directory presently sits inside another git repository; decide whether to move it out before
initialising.

### 3. Where worked examples live

Customer-specific examples are still in skill prose. Moving them to `docs/EXAMPLES.md` lets
`check-generic` gate `src/` strictly. The tension: examples are more useful *in* the reference documents
where the reader is.

Suggested split — keep generic illustrations inline, move anything naming a real job, bucket, account or
program to `EXAMPLES.md`.

### 4. Marketplace access for an internal repo

Marketplace sources are git, so users need credentials for a private repo. Unverified. Test with one
person before announcing.

### 5. Does `dist/` belong in git at all

Committed here for direct download and browsability, guarded by `check-drift`. If the noise in diffs
becomes annoying, the alternative is release-artifact-only distribution and a `dist/`-free repo — at the
cost of losing `cp -R` install and GitHub browsing.

---

## Sequence

1. ~~Fix genericity and portability defects in the working suite~~ — **done**: application name derived,
   runtime directories excluded from source scans, MCP documentation corrected.
2. ~~Populate `src/`, implement `build.py`, prove the Kiro variant reproduces the working tree~~ —
   **done**. All three variants build; a rebuild is byte-identical; the built Kiro variant reproduces
   the reference baseline with documents byte-identical to the source tree's output. See below.
3. ~~Synthetic fixture and golden test~~ — **done**. 19 files, 80 KB, entirely fictional, with a
   recorded baseline and three mutations proving each assertion family actually trips. See
   [`BASELINES.md`](BASELINES.md#fixture-baseline).
4. Install a Claude Code or Codex variant in a real project and run `--offline`. ← next
5. Installer, marketplace manifest, CI workflow.

### What step 2 established

The acceptance gate was "`dist/kiro` reproduces the working tree byte-for-byte". The outcome was more
useful than a pass/fail:

- **All five `SKILL.md` files round-trip exactly.** Front-matter handling is lossless.
- **Four files differ, all deliberate edits** made during genericisation — the suite index's provenance
  section, a generic note in `extract_evidence.py`, a restructured prerequisites row, and the MCP block
  replaced by a fragment include. No unintended difference.
- **The functional test is stronger than byte-identity anyway.** Running the pipeline *from*
  `dist/kiro` produced 31 documents at 111/90/0 with documents byte-identical to the source tree's
  output. Since the byte comparison is against a tree deliberately modified, this is the assertion that
  actually matters.
- **A rebuild is byte-identical**, so `check-drift` is trustworthy.

The variant surface turned out larger than the earlier measurement. Grepping for `.kiro/` paths found
11 occurrences, but the product *name* appears in prose too — a troubleshooting step, an activation
note, a section heading, a port table. A path-only scan missed those. Final token count: 11
`{{SKILLS_ROOT}}`, 4 `{{RUNTIME_NAME}}`, 2 `{{MCP_PREREQUISITE}}`.

Two defects surfaced while building:

- `mainframe-reverse-engineering` declared `metadata.version: 1.1.0` while its own README documented a
  `1.1.1` entry. `lint_frontmatter` caught it on first run, which is precisely the check's purpose.
- The genericity scan found 27 customer-specific identifiers in skill prose, including an account id
  and two bucket names in copy-pasteable example commands. All scrubbed to placeholders; the real
  values live in `docs/EXAMPLES.md`. Verified the scrub did not alter a single generated document.
