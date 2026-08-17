#!/usr/bin/env bash
# Install a runtime variant of the suite into a target repository or user directory.
#
# STATUS: SPECIFIED STUB. Step 5 implements this.
#
# Claude Code users do not need this — the native plugin marketplace handles install and updates:
#   /plugin marketplace add <org>/mainframe-modernization-skills
#   /plugin install atx-mainframe-suite
# This exists for Kiro and Codex, which have no equivalent channel.
#
# Usage:
#   install.sh --runtime kiro|claude-code|codex [options]
#
#   --scope project|user   default project
#   --target DIR           default current directory (project scope)
#   --version X.Y.Z        install a pinned release rather than the working tree
#   --dry-run              print what would be written, touch nothing
#   --force                overwrite a modified existing install
#
# Exit: 0 installed | 1 refused or failed | 2 bad usage
#
# REQUIREMENTS, each for a reason:
#
#   * --dry-run must be honest. It prints every path that would be written, including the MCP config
#     and the project-instructions append, and writes nothing at all.
#
#   * Refuse to clobber. If a target skill file differs from what this version would install, stop and
#     name the file. Someone editing an installed skill has a reason, and silently discarding it
#     destroys work with no record. --force overrides.
#
#   * Never overwrite project-instructions files. CLAUDE.md and AGENTS.md belong to the user. Append
#     the snippet, and skip if an equivalent block is already present.
#
#   * Never overwrite an existing MCP config. Both .mcp.json and config.toml hold unrelated settings.
#     Merge the server stanza, or print it and ask the user to merge it.
#
#   * Verify a checksum for --version installs, against the release SHA256SUMS.
#
#   * Check the MCP prerequisite for claude-code and codex: `uvx` on PATH and
#     awslabs.aws-transform-mcp-server resolvable. Kiro gets this from the aws-transform Power, the
#     others do not, and a missing prerequisite fails at the first Transform call rather than at
#     install time — which is the expensive place to discover it.
#
#   * Print the post-install steps that cannot be automated: replacing the AWS_PROFILE and AWS_REGION
#     placeholders in the MCP config, and where to read next.
#
#   * No `curl | sh`. This script is downloaded, readable, and then run.
#
# NOT this script's job: creating AWS resources, configuring credentials, or running the pipeline.

set -uo pipefail

cat >&2 <<'EOF'
install.sh: NOT IMPLEMENTED — see docs/REPO-PLAN.md, step 5.

Until then, install by copying the built variant into the target repository root:

    cp -R dist/kiro/.         /path/to/repo/     # or dist/claude-code, dist/codex

dist/<runtime>/ mirrors the real install path, so that copy is a correct install. For the two runtimes
that need it, also merge the MCP server config from runtimes/<runtime>/mcp/ and append the snippet from
templates/ to the project instructions file.
EOF
exit 1
