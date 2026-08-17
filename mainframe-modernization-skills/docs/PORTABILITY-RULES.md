# Portability rules

Constraints that keep one source buildable into three runtimes. Most were discovered by breaking them.

---

## 1. Name the tool, never the invocation path

The single most valuable rule here, and originally an accident.

`mainframe-reverse-engineering` makes 55 references to AWS Transform MCP tools — `configure`,
`list_resources`, `get_status`, `create_job`, `complete_task`, `send_message`, `create_workspace`.
**All 55 port unchanged**, because the skill says *which* tool it needs and never *how* to reach it.

That matters because the runtimes differ exactly there: Kiro reaches
`awslabs.aws-transform-mcp-server` through a Power wrapper, while Claude Code and Codex expose its
tools directly. Nothing in the instructions should care.

✅ "Call `list_resources` to enumerate workspaces."
❌ "Use `kiro_powers` with `action=use`, `serverName=aws-transform-mcp`, `toolName=list_resources`."

The second form is 5 lines of rewrite per occurrence and a permanent maintenance tax.

---

## 2. Scripts locate themselves

No script may name its own install path. `generate_docs.py` did, which broke it in any runtime other
than Kiro *and* forced the caller's working directory to be the workspace root.

```python
SKILL = os.environ.get("ATX_SKILL_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
```

Reference files live beside the script, so relative resolution works from `.kiro/skills/`,
`.claude/skills/`, `.codex/skills/` or anywhere else.

---

## 3. Exclude every runtime directory from source scans

Agent runtimes install skill trees into dot-directories that contain Markdown, samples and fixtures.
Walking them lets the suite's own contents be reported as the customer's application source.

```python
EXCLUDED_SCAN_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".atx", ".kiro", ".claude", ".codex", ".bobz",
}
```

Add a new runtime here at the same time as adding it to `runtimes/`. Missing `.claude` and `.codex` was
a real defect (D-11), not a hypothetical.

---

## 4. Only three front-matter keys are portable

| Key | Kiro | Claude Code | Codex |
|---|---|---|---|
| `name` | required | required | required |
| `description` | required | required | required |
| `license` | ✅ | ✅ | ✅ |
| `metadata` | ✅ | ✅ | ✅ |
| `compatibility` | ✅ | ✖ | ✖ |
| `metadata.argument-hint` | ✅ | ✖ | ✖ |
| `metadata.delegates-to` | ✅ | ✖ | ✖ |
| `allowed-tools` | ✖ | ✅ | ✖ |

`description` is what both non-Kiro runtimes match against to decide whether to load a skill, so
anything load-bearing in a dropped key must be folded into it. `compatibility` carries the prerequisite
gate — losing it silently lets an agent start a run that cannot succeed.

---

## 5. Runtime-specific paths are tokens, never literals

Use `{{SKILLS_ROOT}}`. The build substitutes `.kiro/skills`, `.claude/skills` or `.codex/skills`.

Zero tokens in prompt templates or scripts — keep it that way. A token in a prompt template becomes a
token in 31 generated documents, and a token in a script is a runtime dependency in code.

### Paths are not the whole surface

An early measurement put the variant surface at 8 path references, arrived at by grepping for
`.kiro/`. That was low, because **the product name appears in prose too**: a troubleshooting step
("restart Kiro"), an activation note, a section heading, and a port table. A path-only scan misses all
four, and each is runtime-specific in exactly the same way.

Current token inventory:

| Token | Occurrences | Substituted with |
|---|---|---|
| `{{SKILLS_ROOT}}` | 11 | `.kiro/skills`, `.claude/skills`, `.codex/skills` |
| `{{RUNTIME_NAME}}` | 4 | `Kiro`, `Claude Code`, `Codex` |
| `{{MCP_PREREQUISITE}}` | 2 | how the host supplies the AWS Transform MCP server |

When adding a runtime, grep for the *product name* as well as its paths.

Keep token values free of markup when they are substituted into front matter. `{{MCP_PREREQUISITE}}`
lands inside the `compatibility` scalar, and adding backticks there changed the shipped text for no
reason — caught only because the Kiro variant then stopped round-tripping.

---

## 6. macOS bash 3.2 is the floor

No associative arrays (`declare -A`), no `${var,,}` / `${var^^}`, no `mapfile` / `readarray`.

`bash -n` parses `${var,,}` without complaint and fails only when the branch executes, so a syntax
check is not sufficient. `make check-bash32` greps for the constructs — with comments stripped, because
the first version flagged the comments explaining this rule (D-18).

---

## 7. Standard library only

No third-party Python packages, no `jq`, no GNU-only flags. `timeout` is absent on macOS. Available and
assumed: `python3`, `bash`, `unzip`, `zip`, `shasum`, `awk`, `sed`, `grep`, and the AWS CLI v2 for the
phases that need it.

---

## 8. Determinism is a contract

Identical inputs produce byte-identical documents; wall-clock values are confined to `generatedAt`,
`docsRoot`, `run-log.md` and `run-state.json`.

This is load-bearing. `document-evidence.json` fingerprints every artifact each document consumed,
which is what makes staleness detection work. Introduce model-generated prose into the documents and
the fingerprints stop meaning anything.

So: **no agent-authored content in generated documents**, and no evidence source that cannot be
fingerprinted — which is why AWS Transform chat and the Neptune knowledge graph are excluded.

---

## 9. Copy the grounding contract verbatim

`references/grounding-contract.md` holds the two absence markers, the provenance vocabulary and the
self-check rules. Summarising it into something shorter is how a suite starts inferring content it
cannot evidence.

---

## 10. No customer specifics outside `docs/EXAMPLES.md`

No account ids, bucket names, profile names, ARNs or customer program names in `src/`, `runtimes/`,
`templates/`, `tools/` or `tests/fixtures/`. Worked examples belong in `docs/EXAMPLES.md`, where they
are clearly examples.

Enforced by `make check-generic`. Scripts must be clean unconditionally — one carried a customer
application name and wrote it into all 31 document headers (D-02).

---

## Adding a runtime

1. `runtimes/<name>/runtime.yaml` — install path, front-matter policy, token values.
2. `runtimes/<name>/fragments/mcp-setup.md` — host-specific MCP setup and recovery.
3. `runtimes/<name>/mcp/` — the config file, if the runtime needs one shipped.
4. Add the runtime's dot-directory to `EXCLUDED_SCAN_DIRS` (rule 3).
5. Add it to `RUNTIMES` in the `Makefile`.
6. `templates/` — a project-instructions snippet, if the runtime has such a file.
7. Verify per `docs/MIGRATION.md`: offline run, then diff documents against another runtime's output.
   They must be byte-identical — the scripts are the behaviour, so any difference is a build defect.
