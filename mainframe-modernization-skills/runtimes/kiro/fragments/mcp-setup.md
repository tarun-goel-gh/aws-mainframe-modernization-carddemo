### AWS Transform MCP server

Supplied by the **`aws-transform` Kiro Power**, which wraps
`awslabs.aws-transform-mcp-server`. There is no configuration file to write.

The server is launched by the Power with no `env` block, so it inherits whatever environment the IDE
had at startup and resolves credentials **once**. If the SSO token was stale at that moment, every
later call reports a failure that has nothing to do with the AWS account.

Reconnecting the server from the **MCP Server view** in the Kiro feature panel re-runs its probe.
Pinning its environment removes the failure mode entirely:

```json
"aws-transform-mcp": {
  "command": "uvx",
  "args": ["awslabs.aws-transform-mcp-server@latest"],
  "env": { "AWS_PROFILE": "<profile>", "AWS_REGION": "<region>" }
}
```

Because the Power wraps the server, its tools are not exposed directly — reach them through the Power
rather than as top-level tools. This is a host detail and nothing in the skill instructions depends on
it: they name the tool they need, never the route to it.
