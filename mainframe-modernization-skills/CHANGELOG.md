# Changelog

Suite-level semver. This is the version users pin. Individual skills also carry
`metadata.version`; see [`docs/VERSIONING.md`](docs/VERSIONING.md) for how the two relate.

`make check-frontmatter` asserts every skill version below appears in this file, so a behaviour change
cannot ship unmentioned.

| Skill | Version |
|---|---|
| `mainframe-reverse-engineering` | 1.1.1 |
| `atx-app-documentation` | 1.0.0 |
| `atx-pipeline` | 1.0.0 |
| `atx-generate-docs` | 1.0.0 |
| `atx-docs-status` | 1.0.0 |

---

## Unreleased

The suite builds for all three runtimes. No release cut yet — see Known gaps.

### Added

- **`src/skills/`** — the five skills as a single runtime-neutral source, with 17 tokens
  (`{{SKILLS_ROOT}}`, `{{RUNTIME_NAME}}`, `{{MCP_PREREQUISITE}}`) and one `@include` fragment marker
  replacing what had been Kiro-specific text.
- **`tools/build.py`** — token substitution, front-matter policy, fragment inclusion and MCP config
  placement. `compatibility` is folded into `description` rather than dropped, because on Claude Code
  and Codex `description` is the only text consulted when loading a skill. Includes a small YAML-subset
  parser, since the build takes no third-party dependencies.
- **`dist/`** — built variants for `kiro` (64 files), `claude-code` (65, plus `.mcp.json`) and `codex`
  (65, plus `.codex/config.toml`).
- **`tools/lint_frontmatter.py`** — validates source and every variant: required keys, name/directory
  agreement, semver, CHANGELOG presence, no literal runtime paths, no dropped key surviving, no
  unresolved token, and that a folded `compatibility` actually reached `description`.
- **`tests/run_golden.sh`** — golden runner with `--record`. Asserts document count, section
  coverage, statuses, delivered-of-discovered, the derived application name and its source,
  determinism across two runs, and that the archive passed the disclosure gate.
- **`tests/fixtures/mfre-synthetic/`** — 19 files, 80 KB, entirely fictional. A deliberately mixed
  estate: two delivered functions, one scoped with no specification, one excluded as infrastructure,
  one never scoped. Includes synthetic COBOL, a copybook and a BMS map, because `extract_evidence`
  reads application source from the workspace and a fixture without it understates coverage.
  Verified able to fail: three mutations each tripped a different assertion.
- Repository skeleton, runtime recipes, `tools/check_bash32.sh`, `tools/scan_secrets.py`,
  `tools/check_links.py`, CI workflow, and the documentation set.

### Changed

- Skill versions: `mainframe-reverse-engineering` 1.1.0 → **1.1.1**. The version had never been bumped
  when its 1.1.1 changelog entry was written; `lint_frontmatter` caught the mismatch on first run.
- Customer-specific identifiers removed from skill prose — an account id, two bucket names, a profile
  name and nine application-name references, all in example commands or illustrations. Real values now
  live only in `docs/EXAMPLES.md`. **No generated document changed**, verified by diff.
- The suite index shipped with the skills now explains that the installed tree is generated and must
  not be edited in place.

### Fixed — carried in from the working suite

These landed before the repository existed and are recorded here because they change behaviour a
consumer can observe. Full detail in [`docs/DEFECTS.md`](docs/DEFECTS.md).

- **Application name is derived, not hardcoded.** Document headers previously carried a literal
  application name, so every document described the wrong subject when the tool was pointed at a
  different codebase. Now derived from upstream provenance with `--app-name` / `ATX_APP_NAME` as an
  override, and the derivation source recorded in `manifest.json`. Adds `--app-name` to the pipeline
  driver.
- **Runtime skill directories excluded from source scans.** `.claude` and `.codex` were not excluded
  when walking for application source, so an installed skill tree could be reported as customer code.
- **Scripts locate themselves.** `generate_docs.py` hardcoded its install path, which broke it on any
  other runtime and forced the working directory to be the workspace root.
- **Packaging carries a disclosure gate.** The archive is scanned for IAM/STS principal ARNs, access
  key ids and session tokens before it can be recorded. Added after a published archive leaked an
  assumed-role ARN including an SSO permission set name and a corporate email address.

### Fixed — in the repository tooling

- **`check-drift` passed while verifying nothing.** `git diff` exits 0 on untracked files, so the gate
  protecting committed generated output reported success without comparing anything. It now requires
  git and a tracked `dist/`, and separately proves the build is deterministic by building twice.
- **`make help` hid `check-bash32`** — the target-name pattern excluded digits, so a security gate was
  undiscoverable.
- **`make test` conflated "no fixture" with "test failed."** Exit 3 now means skipped.
- **`extract_evidence.py` crashed on a catalog CSV missing an optional column.** Five columns were
  hard-indexed, so an absent `List of entry points` produced a `KeyError` traceback from step 5 rather
  than a documentable gap. AWS Transform's catalog output has already varied between runs of this
  project, making that a realistic input. Now read defensively.
- **`scan_secrets --generic` could not distinguish a placeholder from a leak.** Synthetic identifiers
  such as `222222222222` were reported, and the obvious workaround — exempting `tests/fixtures/` —
  would have removed the check from the one place it matters most. It now recognises self-evident
  placeholders (repeated-digit ids, all-zero UUIDs, AWS's documented example account) while still
  catching real-looking values.

### Fixed — carried in from the working suite

These landed before the repository existed and are recorded here because they change behaviour that
a consumer can observe. Full detail in [`docs/DEFECTS.md`](docs/DEFECTS.md).

- **Application name is derived, not hardcoded.** Document headers previously carried a literal
  application name, so every document described the wrong subject when the tool was pointed at a
  different codebase. Now derived from upstream provenance with `--app-name` / `ATX_APP_NAME` as an
  override, and the derivation source is recorded in `manifest.json`.
- **Runtime skill directories excluded from source scans.** `.claude` and `.codex` were not excluded
  when walking for application source, so an installed skill tree could be reported as customer code.
- **Packaging carries a disclosure gate.** The archive is scanned for IAM/STS principal ARNs, access
  key ids and session tokens before it can be recorded. Added after a published archive leaked an
  assumed-role ARN including an SSO permission set name and a corporate email address.

### Known gaps

Blocking a first release:

- **Licence not settled.** Front matter declares `Apache-2.0`; no `LICENSE` file exists.
- **Repository not `git init`-ed**, so `check-drift` cannot verify committed output and `make check`
  fails by design.
- **`.claude-plugin/marketplace.json` carries `REPLACE_WITH_ORG`.**

Not blocking, but incomplete:

- `tools/install.sh` and `tools/release.sh` are not written.
- The richest-wins bundle merge is not covered by the golden test: it runs in phase 3, which
  `--offline` skips. The fixture would need competing raw zips and a non-offline invocation.
- The Claude Code and Codex variants build and lint clean but have not been executed on their own
  runtimes.
