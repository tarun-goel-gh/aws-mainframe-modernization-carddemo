# Versioning and release

## Two version numbers

**Suite version** — the git tag, `v1.2.0`. This is what users pin and what release artifacts carry.

**Skill version** — `metadata.version` inside each `SKILL.md`. Tracks that skill's own behaviour and
moves independently. Currently `mainframe-reverse-engineering` is at 1.1.1 while the rest are at 1.0.0.

The suite version is not the maximum of the skill versions. It advances when *anything shipped*
changes, including build tooling or a runtime recipe.

`make check-frontmatter` asserts every skill version appears in `CHANGELOG.md` for the release being
cut, so a behaviour change cannot ship unmentioned.

---

## What each bump means

Semver applied to *consumers of the suite*, which includes the skills, the scripts, and the on-disk
contracts between them.

### Major

- The `.atx/mfre/` layout changes, breaking `atx-app-documentation`'s ability to read an existing run.
- `state.json` shape changes.
- The run-folder contract changes — manifest filenames, `run-state.json` keys consumed by `--resume`.
- A script's flags change incompatibly.
- The install path for a runtime changes.

These break someone who has an existing run on disk or a wrapper script. That is the test.

### Minor

- A new skill, script or flag.
- A new runtime.
- New parsers that raise coverage — more grounded sections from the same evidence.
- A new document, or new sections in an existing one.

### Patch

- Defect fixes that do not change document content.
- Documentation.
- CI and tooling.

---

## The awkward case: fixes that change document content

A parser fix that raises coverage changes the generated documents. The determinism contract means
consumers may be diffing runs, so a document that changes without upstream evidence changing looks
like a bug.

Rule: **any change to generated document content is at least a minor bump, and the CHANGELOG entry
must state the expected baseline movement.**

```markdown
### Changed
- `technical_specs`: working-storage parser added. Grounded sections 111 → 118.
  A re-run against unchanged evidence will differ from 1.2.0 output in 7 sections.
```

Without that, the next person to run a determinism diff has no way to tell an improvement from a
regression.

The application-name fix (D-02) is the clearest example: it altered a header line in all 31 documents
while changing no evidence at all.

---

## Release process

```bash
make check                          # every gate, including drift against committed dist/
make test                           # golden run
# update CHANGELOG.md: move Unreleased -> vX.Y.Z, dated, and the skill-version table
git tag -a vX.Y.Z -m "vX.Y.Z"
git push --follow-tags
tools/release.sh vX.Y.Z             # NOT YET WRITTEN — per-runtime tarballs + SHA256SUMS
```

`make check` includes `check-drift`, which requires the repository to be git-initialised and `dist/` to
be tracked. It refuses rather than passing when it cannot verify, so a release cannot be cut from an
unverified tree.

`tools/release.sh` does not exist yet. Until it does, build the tarballs by hand from `dist/`, one per
runtime, each expanding to that runtime's real install path.

Artifacts, one per runtime:

```
atx-skills-X.Y.Z-kiro.tar.gz
atx-skills-X.Y.Z-claude-code.tar.gz
atx-skills-X.Y.Z-codex.tar.gz
SHA256SUMS
```

Each expands to the runtime's real install path, so extracting at a repo root is correct with no
further instruction.

---

## Claude Code marketplace

`.claude-plugin/marketplace.json` carries its own `version` for the plugin entry. Keep it equal to the
suite version — a marketplace that reports a version users cannot correlate with a tag is worse than no
version.

Because the marketplace source is this git repository, **a tag alone does not publish**. The manifest
has to be updated in the same commit, or clients will report they are already current while pointing at
older content.

For an internal repository, users need working git credentials for the marketplace source. Worth
verifying with one person before announcing it.

---

## Pinning

```bash
# Marketplace — tracks the default branch
/plugin marketplace add <org>/mainframe-modernization-skills

# Installer, pinned
sh install.sh --runtime codex --version 1.2.0

# Tarball, pinned and verified
curl -LO .../releases/download/v1.2.0/atx-skills-1.2.0-codex.tar.gz
shasum -c SHA256SUMS
```

Recommend pinning for anything that runs unattended. The suite writes to S3 and can publish
anonymously readable archives; an unpinned auto-update changing that behaviour is not a surprise worth
having.

---

## Deprecation

Flags and scripts get one minor release with a warning before removal, and the warning names the
replacement. On-disk contracts — `.atx/mfre/` layout, run-folder manifests — get a major bump with a
migration note in the CHANGELOG, because a consumer cannot rewrite existing runs on disk.
