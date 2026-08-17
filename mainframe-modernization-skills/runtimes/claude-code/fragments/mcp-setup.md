### AWS Transform MCP server

Declared in `.mcp.json` at the project root. Install the prerequisite first — unlike Kiro, no Power
supplies it:

```bash
uvx awslabs.aws-transform-mcp-server@latest --help    # confirms the package resolves
```

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

**Pin `AWS_PROFILE` and `AWS_REGION`.** The server resolves credentials once at startup and caches the
result. Started from a shell whose SSO token was stale, it reports failures indistinguishable from an
unconfigured AWS account — a confusion that has already sent someone to provision infrastructure they
already owned.

Recovery after a stale probe is to restart the session; there is no per-server reconnect. That makes
pinning more important here than on a host that offers one.

A `NOT_CONFIGURED` status is far more likely to be an unresolved credential in this server's
environment than an account problem. Before concluding anything about account setup, run the non-MCP
cross-check required by `references/preflight.md` §1.3.
