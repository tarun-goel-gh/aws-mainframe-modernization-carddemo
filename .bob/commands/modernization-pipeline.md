---
description: Run the modernization-pipeline skill end to end — extraction through packaging — with a gate at each decision point, no AWS involved
argument-hint: '[--offline] [--resume <run-id>] [--from <phase>] [--dry-run] [--no-publish] [scope]'
---
Run the `modernization-pipeline` skill with these arguments: $ARGUMENTS

This is the guided wrapper that drives `cobol-knowledge-extraction` and `z-app-documentation`
(via `generate-docs`) through nine phases — `preflight`, `extract`, `extract-verify`,
`reuse-snapshot`, `coverage`, `evidence`, `generate`, `package`, `publish` — entirely inside the
local IDE workspace. There is no AWS anywhere in this pipeline: no S3, no presigned URLs, no IAM
ARNs, no bucket policies.

Before phase 1 (Gate A), confirm the scope (path, file list, inventory CSV, or glob) and that
`workspaceRoot` is unambiguous, and state that Advanced mode is required. If `--dry-run` appears
anywhere in the arguments, stay in PLAN mode: show the phase plan and stop before touching
anything.

If `--offline` is given, skip the MCP-only phases when a `bob-z-knowledge-extract/` tree already
exists. If `--resume <run-id>` is given, resume that run from its recorded phase instead of
restarting. If `--from <phase>` is given, start at that named phase. If `--no-publish` is given,
run through `package` and stop before the `publish` marker. Any remaining bare argument is the
scope (path, file list, inventory CSV, or glob) forwarded to phase 1's inventory build.

Enforce Gate B after `extract-verify` — name every program not yet `dd_generated=Y AND
dd_approved=Y AND doc_generated=Y`, and which flag is still outstanding; never let a partial
extraction pass silently into `coverage`. Enforce Gate C after `coverage` — show the per-program
coverage matrix and ask whether to generate at all if coverage is low. Enforce Gate D before
`publish` — run the disclosure scan over every file about to enter the package and refuse to
produce the zip on any hit (password, API key, private key, DB connection string, or bearer-token
pattern); treat `publish` as an explicit copy to a user-named local or network path only, never a
public URL, and state plainly what the archive contains before copying it.

Finish by reporting which phase the run reached, the Gate B and Gate C outcomes, the
`cobol-knowledge-extraction` Step 15 report, the `generate-docs` Step 10 report, and the
disclosure-scan result. Never report a bare percentage.
