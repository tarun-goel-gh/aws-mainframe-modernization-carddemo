# Migrating this suite to Claude Code or Codex

Porting the five mainframe modernization skills out of Kiro.

**Short version: almost all of it moves unchanged.** Kiro, Claude Code and Codex have converged on
the same packaging format — a folder containing `SKILL.md` with YAML front matter — described by the
open [Agent Skills](https://agentskills.io) standard. The port is largely a directory copy plus a
front-matter trim.

> Verified against vendor documentation in August 2026. Both products move quickly; confirm the
> install paths against [Claude Code skills docs](https://code.claude.com/docs/en/agent-sdk/skills)
> and [OpenAI's build-skills guide](https://learn.chatgpt.com/docs/build-skills) before relying on
> this. *Content rephrased for compliance with licensing restrictions.*

---

## What you are moving

```
.kiro/skills/
├── mainframe-reverse-engineering/   SKILL.md + 6 references + 7 scripts
├── atx-app-documentation/           SKILL.md + 5 references + 31 prompts + 4 scripts
├── atx-pipeline/                    SKILL.md  (entry point)
├── atx-generate-docs/               SKILL.md  (entry point)
└── atx-docs-status/                 SKILL.md  (entry point)
```

63 files. The value is concentrated in the scripts and reference documents, and **none of it is
Kiro-specific**:

| Asset | Portability |
|---|---|
| `scripts/*.py` (6) | pure Python 3 stdlib, no third-party packages |
| `scripts/*.sh` (5) | bash 3.2 compatible, POSIX tooling only |
| `references/*.md` (11) | plain Markdown |
| 31 prompt templates | plain Markdown |
| `SKILL.md` (5) | front matter needs a trim; body is portable prose |

There are no Kiro hooks, no steering files, no specs, and no `#[[file:…]]` references in this suite.
`.kiro/` contains only `skills/`, so there is no runtime configuration to translate.

---

## Step 1 — Copy the folder

| Target | Project scope | User scope |
|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Codex | `.codex/skills/` | `~/.codex/skills/` |
| Kiro (origin) | `.kiro/skills/` | `~/.kiro/skills/` |

```bash
# Claude Code, project scope
mkdir -p .claude/skills
cp -R .kiro/skills/mainframe-reverse-engineering \
      .kiro/skills/atx-app-documentation \
      .kiro/skills/atx-pipeline \
      .kiro/skills/atx-generate-docs \
      .kiro/skills/atx-docs-status \
      .claude/skills/

# Codex, project scope
mkdir -p .codex/skills && cp -R .kiro/skills/atx-* .kiro/skills/mainframe-* .codex/skills/
```

Do not copy `README.md` expecting it to be read by the agent — READMEs are for humans. Do not copy
`__pycache__`.

The scripts resolve their own location from `__file__`, so they work from any of these paths with no
edit. `ATX_SKILL_ROOT` overrides it if you ever split scripts from references.

---

## Step 2 — Trim the front matter

Ours currently looks like this:

```yaml
---
name: atx-pipeline
description: Guided end-to-end run from AWS Transform spec artifacts to …
compatibility: Needs .kiro/skills/mainframe-reverse-engineering (scripts) …
license: Apache-2.0
metadata:
  author: tarun.goel
  version: "1.0.0"
  argument-hint: '[--offline] [--resume <run-id>] [--from <phase>] [--dry-run]'
  delegates-to: atx-app-documentation
---
```

| Field | Claude Code | Codex | Action |
|---|---|---|---|
| `name` | required | required | keep |
| `description` | required | required | keep — this is what drives auto-invocation |
| `license` | supported | supported | keep |
| `metadata` | supported | supported | keep |
| `compatibility` | not standard | not standard | **fold into `description` or the body** |
| `metadata.argument-hint` | no equivalent | no equivalent | move into the body as a usage line |
| `metadata.delegates-to` | no equivalent | no equivalent | express as prose: "read X first" |
| `allowed-tools` | supported | — | optional addition, see Step 4 |

Minimum viable port:

```yaml
---
name: atx-pipeline
description: Guided end-to-end run from AWS Transform spec artifacts to the 31-document
  application documentation suite and a shareable zip. Requires a completed
  mainframe-reverse-engineering run. Activate when the user asks to run the whole pipeline,
  fetch specs and generate docs, or publish the documentation.
license: Apache-2.0
---
```

`compatibility` carried real information — the prerequisite gate. Losing it silently would let the
agent start a run that cannot succeed, so fold the substance into `description` (which the agent uses
to decide whether to load the skill) and restate it as a hard gate in the body.

**Update the path references in the bodies.** Each `SKILL.md` names sibling paths:

```bash
cd .claude/skills   # or .codex/skills
grep -rl '\.kiro/skills' . | xargs sed -i '' 's#\.kiro/skills#.claude/skills#g'
```

Nothing under `.atx/` changes. Output paths are runtime-relative and identical across targets.

---

## Step 3 — Replace the invocation layer

Kiro entry-point skills give an action a slash-command name. The three thin ones — `atx-pipeline`,
`atx-generate-docs`, `atx-docs-status` — exist only for that.

**Claude Code** invokes skills by description match and also exposes them as slash commands, so the
three entry points carry over as-is. If you would rather have explicit commands, the same bodies work
as `.claude/commands/*.md`.

**Codex** reads project guidance from `AGENTS.md` and supports skills under `.codex/skills/`. Its
older custom-prompts mechanism is deprecated in favour of skills, so target skills. Note that
community reports indicate `.codex/commands/` is not supported — do not build the invocation layer
around it.

Either way, add a pointer to your project instructions file so the agent knows the suite exists:

```markdown
<!-- CLAUDE.md (Claude Code) or AGENTS.md (Codex) -->
## Mainframe modernization

This repo carries a five-skill suite for AWS Transform reverse engineering and application
documentation. See `.claude/skills/README.md`.

- Reverse engineer a mainframe → `mainframe-reverse-engineering`
- Artifacts exist, want the 31 documents → `atx-pipeline`
- Re-generate from a local run → `atx-generate-docs`
- Coverage and staleness → `atx-docs-status`

Never generate documentation without loading `atx-app-documentation`'s grounding contract. It is
what keeps unavailable sections honest instead of inferred.
```

---

## Step 4 — Tool permissions

Kiro grants tool access by mode. Claude Code lets a skill declare it:

```yaml
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
```

All five skills need file read/write and shell execution. `mainframe-reverse-engineering` and
`atx-pipeline` additionally shell out to the AWS CLI, so `Bash` is mandatory for them;
`atx-docs-status` is read-only and can be restricted to `Read, Glob, Grep`.

Codex governs this through its sandbox and approval settings in `config.toml` rather than per skill.
Phases 2, 4 and 9 need network egress and write access outside the workspace root (`.atx/` is inside,
but the AWS CLI touches `~/.aws`), so a fully sandboxed profile will block them.

---

## Step 5 — What has no equivalent

| Kiro feature | Used by this suite? | Elsewhere |
|---|---|---|
| Hooks (`.kiro/hooks/*.json`) | **no** | Claude Code has hooks in settings; Codex has none |
| Steering (`.kiro/steering/*.md`) | **no** | `CLAUDE.md` / `AGENTS.md` |
| Specs (requirements → design → tasks) | **no** | no equivalent; this is an ops pipeline anyway |
| `#[[file:…]]` reference inclusion | **no** | inline the content or use a relative path |
| MCP servers | **yes — see below** | both support MCP |

Of that list only MCP is load-bearing, and it applies to one of the two behavioural skills.

---

## Step 5a — MCP: the one substantial difference

`atx-app-documentation` needs no MCP, no credentials and no network. `mainframe-reverse-engineering`
is the opposite: its entire control plane is MCP tool calls against
`awslabs.aws-transform-mcp-server`. In Kiro that server arrives via the **`aws-transform` Power**,
which wraps it; Claude Code and Codex need it configured directly.

What actually differs is smaller than it sounds, because the *tool vocabulary is identical* — it is
the same server on every host. Measured across the skill:

| | Count | Ports unchanged? |
|---|---|---|
| Server tool names (`configure`, `list_resources`, `get_status`, `create_job`, `complete_task`, `send_message`, `create_workspace`) | 55 references | **yes** |
| Kiro-host-specific prose ("aws-transform Kiro power", "reconnect from the MCP Server view") | 5 references in 3 files | no |

They port for free because the skill bodies **name the tool, never the invocation path**. Preserve
that when editing: the moment a skill says *how* to reach a tool rather than *which* tool it needs,
it stops being portable. Kiro reaches the server through a Power wrapper while the others expose
tools directly, and nothing in the instructions should care.

### Per-runtime setup

| | Kiro | Claude Code | Codex |
|---|---|---|---|
| Server declared in | the `aws-transform` Power | `.mcp.json` | `config.toml` `[mcp_servers.*]` |
| Tool access | via the Power wrapper | direct | direct |
| Prerequisite | Power installed | `uvx` + the server package | `uvx` + the server package |
| Recovery after a stale probe | reconnect in the MCP Server view | restart the session | restart the session |

Claude Code, project root `.mcp.json`:

```json
{
  "mcpServers": {
    "aws-transform": {
      "command": "uvx",
      "args": ["awslabs.aws-transform-mcp-server@latest"],
      "env": { "AWS_PROFILE": "<profile>", "AWS_REGION": "<region>" }
    }
  }
}
```

Codex, `config.toml`:

```toml
[mcp_servers.aws-transform]
command = "uvx"
args = ["awslabs.aws-transform-mcp-server@latest"]
env = { AWS_PROFILE = "<profile>", AWS_REGION = "<region>" }
```

**Pin `AWS_PROFILE` and `AWS_REGION` in the server's `env` on every runtime.** The server resolves
credentials once at startup and caches the result. Launched from a shell whose SSO token was stale, it
reports failures that look exactly like an unconfigured AWS account — a confusion that has already
sent someone to provision infrastructure they already owned. `references/preflight.md` §1.3 requires a
non-MCP cross-check before any such conclusion, and that rule matters more, not less, on a runtime
where you cannot reconnect the server from a UI.

### What to change in the skill text

`references/preflight.md` carries 15 of the 23 MCP mentions; `code-intake.md`, `discovery.md` and
`state-and-reporting.md` carry none. So the host-specific rewrite is confined to:

1. `SKILL.md` — the `compatibility` line naming the Kiro Power.
2. `references/preflight.md` — the setup block and the "reconnect from the MCP Server view" recovery
   step in the troubleshooting table.
3. `README.md` — the same recovery advice.

Everything else is server-generic.

---

## Step 6 — Verify the port

Run these in the target tool. The first three need no AWS access.

```bash
S=.claude/skills/atx-app-documentation/scripts   # adjust per target

# 1. scripts compile and resolve their own references
python3 -m py_compile $S/*.py && echo ok
bash -n $S/run_pipeline.sh && echo ok

# 2. the driver plans correctly
$S/run_pipeline.sh --offline --dry-run

# 3. full offline run against an existing .atx/mfre  (~3 s)
$S/run_pipeline.sh --offline --run-id PORTCHECK
```

Then assert the output matches the origin:

| Check | Expected |
|---|---|
| documents | 31 |
| sections | 111 grounded / 90 absent / 0 not-extracted (55%) |
| statuses | 4 complete / 25 partial / 2 unavailable |
| coverage | 6 of 11 discovered business functions |
| determinism | two runs byte-identical except `generatedAt`, `docsRoot`, `run-log.md`, `run-state.json` |

```bash
diff -r .atx/app-docs-PORTCHECK .atx/app-docs-<origin-run> -x run-log.md -x run-state.json
```

Anything other than `generatedAt` / `docsRoot` differences means a reference file did not copy, or
`SKILL` is resolving to the wrong root. If the documents are byte-identical, the port is complete —
the scripts are the behaviour.

Confirm the agent side: ask the target tool for documentation status and check it loads
`atx-docs-status` rather than improvising. If it doesn't fire, the `description` is the thing to fix;
that field is what both products match against.

Then verify MCP separately, since none of the above touches it:

```bash
uvx awslabs.aws-transform-mcp-server@latest --help    # package resolves
```

In the target tool, ask for AWS Transform connectivity and check that `mainframe-reverse-engineering`
runs its preflight and reports a real status rather than `NOT_CONFIGURED`. A `NOT_CONFIGURED` here is
far more likely to be an unresolved credential in the server's environment than an account problem —
that is exactly what `references/preflight.md` §1.3 exists to stop you misdiagnosing.

---

## Gotchas

**bash 3.2.** The scripts avoid associative arrays and `${var,,}` because macOS ships bash 3.2. Keep
that floor if the suite may run on a Mac. `bash -n` will *parse* `${var,,}` without complaint and
fail only when the branch executes — a bug of exactly this shape shipped in this suite once.

**Skills are not tracked in git here.** `.kiro/` is currently untracked, so "copy the folder" is the
only transport. Commit the suite in the target repo, and keep `__pycache__` out via `.gitignore`.

**The disclosure gate is not optional.** `run_pipeline.sh` phase 8 refuses to package an archive
containing IAM ARNs, access key ids or session tokens. If you refactor packaging during the port,
carry that check across. It exists because a published zip once leaked an assumed-role ARN including
an SSO permission set name and a corporate email address.

**Determinism is a contract, not a nicety.** Several design choices — no agent-authored prose in
generated documents, no chat or knowledge-graph evidence, wall-clock confined to four fields — exist
to keep two runs byte-identical. A port that introduces model-generated content into the documents
breaks the staleness detection in `document-evidence.json`, because fingerprints stop meaning
anything.

**Coverage honesty travels with the prompts.** The two absence markers, the provenance vocabulary and
the self-check rules live in `references/grounding-contract.md`. Copy it verbatim. Summarising it into
a shorter instruction is how a suite starts inferring content it cannot evidence.

---

## Effort estimate

| Task | Effort |
|---|---|
| Copy 5 folders | minutes |
| Trim front matter, 5 files | ~15 minutes |
| Rewrite sibling paths | one `sed`, minutes |
| Add the `CLAUDE.md` / `AGENTS.md` pointer | ~10 minutes |
| **Configure the MCP server + rewrite 5 host-specific references** | ~30 minutes |
| Verify with an offline run + diff | ~10 minutes |
| Adjust Codex sandbox for AWS phases | varies; may need a policy decision |

The long pole is not the copy. It is the two environment questions: whether the target tool's sandbox
permits the AWS CLI and network egress that phases 1-4 and 9 need, and whether
`awslabs.aws-transform-mcp-server` starts with credentials it can actually resolve.

Note the asymmetry when planning: `atx-app-documentation` and its three entry points are portable with
no environmental work at all, because documentation generation is offline. Only
`mainframe-reverse-engineering` carries the MCP and credential burden. If you need a quick win, port
the documentation side first and verify it end to end with `--offline` before touching MCP.
