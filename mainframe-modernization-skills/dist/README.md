# dist/ — generated output

**Do not hand-edit anything here.** Edit `src/skills/` or `runtimes/<runtime>/` and run `make build`.

`make check-drift` rebuilds every variant and fails if the result differs from what is committed, so a
manual edit here will break CI rather than survive.

## Why generated files are committed

Normally a smell. Justified here because:

- users can `cp -R dist/<runtime>/. ~/repo/` without running a build
- variants are browsable in the web UI, which matters for an internal audience
- the Claude Code marketplace sources a plugin directly from `dist/claude-code`

The cost is diff noise on every source change. The mitigation is that the invariant is *enforced*, not
trusted: `check-drift` makes hand edits impossible to land.

## Layout

Each directory mirrors the runtime's true install path:

```
dist/kiro/.kiro/skills/…
dist/claude-code/.claude/skills/…   + .mcp.json
dist/codex/.codex/skills/…          + .codex/config.toml.fragment
```

That is why the nesting looks redundant. It makes a plain copy into a repository root a correct install
with no accompanying instructions.

## Current contents

All three variants are built and verified.

| Runtime | Files | Extras beyond the skills tree |
|---|---|---|
| `kiro` | 64 | none — the `aws-transform` Power supplies the MCP server |
| `claude-code` | 65 | `.mcp.json` |
| `codex` | 65 | `.codex/config.toml` |

Verified: two builds of the same source are byte-identical, and running the pipeline **from**
`dist/kiro` reproduces the reference baseline (31 documents, 111 grounded / 90 absent / 0
not-extracted) with documents byte-identical to the source tree's own output.
