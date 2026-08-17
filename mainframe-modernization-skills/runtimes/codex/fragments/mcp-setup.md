### AWS Transform MCP server

Declared in `config.toml`. Install the prerequisite first — unlike Kiro, no Power supplies it:

```bash
uvx awslabs.aws-transform-mcp-server@latest --help    # confirms the package resolves
```

**Merge** this into your existing `~/.codex/config.toml` or the project's `.codex/config.toml`. Do not
replace the file; it holds unrelated settings.

```toml
[mcp_servers.aws-transform]
command = "uvx"
args = ["awslabs.aws-transform-mcp-server@latest"]

[mcp_servers.aws-transform.env]
AWS_PROFILE = "<profile>"
AWS_REGION = "<region>"
```

**Pin `AWS_PROFILE` and `AWS_REGION`.** The server resolves credentials once at startup and caches the
result. Started from a shell whose SSO token was stale, it reports failures indistinguishable from an
unconfigured AWS account — a confusion that has already sent someone to provision infrastructure they
already owned.

Recovery after a stale probe is to restart the session; there is no per-server reconnect.

Note that some configuration keys are ignored in a project-local `.codex/config.toml` and must be set
at user level instead. If the server does not appear, try the user-level file before assuming the
server definition is wrong.

### Sandbox

Codex governs capability through sandbox and approval settings rather than per-skill grants. Phases
1-4 and 9 shell out to the AWS CLI, which needs network egress and reads `~/.aws` — outside the
workspace root — so a fully sandboxed profile will block them.

Phases 5-8, the documentation half, need neither and run under any profile. If the sandbox is
restrictive, `--offline` remains a complete path to the 31 documents.

A `NOT_CONFIGURED` status is far more likely to be an unresolved credential than an account problem.
Before concluding anything about account setup, run the non-MCP cross-check required by
`references/preflight.md` §1.3.
