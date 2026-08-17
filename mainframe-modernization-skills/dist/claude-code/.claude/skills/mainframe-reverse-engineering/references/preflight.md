# Preflight: connectivity and service setup

Two independent questions. Answer both before creating a job.

- **Connectivity** — can we reach and authenticate against the AWS Transform API?
- **Service setup** — does this account have the resources a mainframe *reimagine* job
  requires? A healthy API connection says nothing about connectors, Neptune, or buckets.

The account is expected to be **already set up**: AWS Transform onboarded, the mainframe
reimagine connector created and approved, Neptune running, IAM roles in place, bucket ready.
This stage discovers and confirms that. It never provisions — creating infrastructure is a hard
stop, because it changes the customer's account to make a run possible.

## Part 1 — Connectivity

### 1.1 Environment (deterministic)

```
scripts/preflight.sh --profile <aws-profile> [--bucket <connector-bucket>] [--region <r>]
```

**The profile is the only required input.** Region resolves in this order:

1. `--region` if given
2. `aws configure get region --profile <p>` — the profile's own default
3. `AWS_REGION` / `AWS_DEFAULT_REGION`
4. otherwise: fail with the exact `aws configure set region` command to run

The reported `regionSource` says which applied. Everything downstream — bucket, workspace,
connector, Neptune — is then queried in that one region, so a profile with the wrong default
surfaces immediately instead of halfway through discovery.

Checks: AWS CLI presence and version, profile resolution, `sts get-caller-identity`, credential
expiry headroom, `unzip`, `python3`, `git`, bucket read + CORS when a bucket is given, and
Neptune cluster discovery. Emits JSON with an `ok` boolean.

**Never rely on ambient environment.** A shell with empty `AWS_PROFILE` falls back to the
default profile, which is commonly expired, and the failure surfaces as a confusing
`ExpiredToken` or `HeadObject 400 Bad Request` rather than "wrong profile". The script exports
the resolved profile and region for every call it makes; do the same for any ad-hoc command.

### 1.2 Transform API

`get_status` — no auth required, safe to call first. Interpret:

| Field | Meaning |
|---|---|
| `connection.configured` | false → run `configure`, or fix AWS credentials |
| `connection.authMode` | `sigv4` (AWS credentials), `cookie`, or `sso` |
| `sigv4.accountId` / `.arn` | confirm this is the intended account and principal |
| `sigv4.region` | must match where the workspace and bucket live |
| `sigv4AwsTransformAPI.available` | false → API tools will not work |

Then prove it with a real call: `list_resources resource="workspaces"`. `get_status` reflects
local config; only an API round trip proves reachability and authorization.

If `PROFILE_SELECTION_REQUIRED`: `switch_profile` with the region.

### 1.3 Client-side or account-side? Never guess — cross-check

**Both `get_status` and `list_resources` ride the same MCP client.** When that client is
misconfigured, stale, or holding a cached negative probe, its failure is
*indistinguishable* from an unconfigured account. This has produced a real and expensive
misdiagnosis: a server reporting `sigv4AwsTransformAPI.available: false` and
`NOT_CONFIGURED`, plus an SSO `configure` returning `NO_PROFILES`, on an account that
already had AWS Transform enabled, an IAM-only profile with IAM access on, and an **ACTIVE
reimagine connector**. The user was sent to enable a service that was already running.

So: **you may not conclude anything about account setup from MCP responses alone.** Before
attributing failure to the account, run at least one check that does not go through the MCP
server.

| Cross-check | Command | Reading it |
|---|---|---|
| Transform CLI | `atx custom def list` | returns transformations → the account **has** Transform API access; the MCP client is the problem |
| Signed request | SigV4 `GET https://transform.<region>.api.aws/workspaces` | **403** → authorization genuinely denied. **404 `UnknownOperationException`** → signature accepted, only the path was wrong, so access works |
| Console | AWS Transform → Service management | shows the service profile ARN, access model, and whether IAM access is enabled |

The 403-versus-404 distinction is the sharpest signal available and takes one call. A 404
`UnknownOperationException` is a *success* for this purpose.

When constructing that signed request, do **not** use
`eval "$(aws configure export-credentials --format env)"` in a shell you intend to keep
using — see Environment hygiene below.

### 1.4 Interpreting the failure codes

Order matters. Client-side causes are far more common and far cheaper to fix, so rule them
out first.

| Symptom | Check in this order |
|---|---|
| `NOT_CONFIGURED` with AWS credentials present | 1. reconnect the MCP server (it probes once at startup and caches the result) 2. confirm its env carries `AWS_PROFILE`/`AWS_REGION` 3. only then question the account |
| `sigv4AwsTransformAPI.available: false` | same as above; this is a *probe result*, not an account fact |
| `NO_PROFILES` from `configure authMode="sso"` | means no Transform profile was found for the IdC instance — but confirm with a cross-check, and note the Transform **Start URL for IDE** differs from the IdC portal start URL |

The MCP server resolves credentials **once**, at startup, and caches the result. If the SSO
token was stale at that moment, every later call reports a failure that has nothing to do with
the account. How the server is declared and recovered depends on the host:

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

Only after a non-MCP cross-check also fails may you report the account as unconfigured. If
`configure` is genuinely needed: with AWS credentials present, no `configure` call is
required. Otherwise offer SSO (`configure authMode="sso"` with `startUrl` + `idcRegion`) or
cookie mode. Frame sign-in around the action the user asked for, not as a lecture.

### 1.5 Environment hygiene

`scripts/preflight.sh` checks this, but it applies to every ad-hoc command too.

If `AWS_CREDENTIAL_EXPIRATION` is exported and its timestamp has passed, **every** AWS call
fails with:

```
Credentials were refreshed, but the refreshed credentials are still expired
```

even when the SSO login is valid, the clock is correct, and freshly minted keys are
injected. botocore treats env credentials carrying an expiry as refreshable, finds the
expiry in the past, and refuses. The usual cause is self-inflicted:
`eval "$(aws configure export-credentials --format env)"` in a long-lived shell exports the
expiry alongside the keys, and the shell keeps it after the credentials die.

Diagnose it before suspecting expiry or clock skew — those look identical from the error
text. To confirm the clock is innocent, compare it against an authoritative source:

```
curl -sI https://s3.<region>.amazonaws.com | grep -i '^date:'
```

Do not use that `eval` in a persistent shell. Either scope it to a subshell, or strip the
inherited set per command:

```
env -u AWS_CREDENTIAL_EXPIRATION -u AWS_ACCESS_KEY_ID \
    -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
    AWS_PROFILE=<p> AWS_REGION=<r> aws <command>
```

## Part 2 — Service setup

### 2.1 Region support

Mainframe capabilities are not in every region. If the resolved region is unsupported, nothing
downstream works. Confirm against the current supported-region list rather than assuming, and
keep every subsequent call in that region. If the profile's default region is unsupported but
the account has Transform resources elsewhere, say so and ask which to use — silently switching
regions would put artifacts somewhere the user is not looking.

### 2.2 Orchestrator agent

```
list_resources resource="agents" agentType="ORCHESTRATOR_AGENT"
```

Find the mainframe orchestrator. **Never hardcode the name** — it changes between releases.
Record the resolved identifier in state. `create_job` accepts either `jobType` (for example
`MAINFRAME_V2`) or `orchestratorAgent`; if one is rejected, retry with the other.

### 2.3 Workspace

```
list_resources resource="workspaces"
```

Reuse an existing mainframe workspace when one fits, otherwise `create_workspace`. Reusing
keeps prior jobs and artifacts discoverable in one place.

### 2.4 Connector — the step most likely to block

```
list_resources resource="connectors" workspaceId="<id>"
get_resource resource="connector" workspaceId="<id>" connectorId="<id>"
```

Lifecycle: `PENDING → ACTIVE → COMPLETED`, with `REJECTED` and `FAILED` as terminal
failures. **Do not start dependent work until the connector is `ACTIVE`.**

Assess-and-reimagine needs the **mainframe reimagine connector**, which is more than an S3
bucket. It also requires an **Amazon Neptune** cluster holding the knowledge graph of extracted
artifacts — that graph is what answers questions in the Transform chat interface. A connector
built for a custom-plan job (plain S3, optionally an S3 vector bucket) will not serve a
reimagine job.

The connector's configuration references all of: S3 bucket ARN, Neptune cluster ARN, Neptune
cluster resource ID, application subnet IDs, application security group ID, and the Neptune S3
bulk loader role ARN.

**Verifying (this skill's job).** Confirm the connector exists, is `ACTIVE`, and looks like a
reimagine connector rather than a plain S3 one. `scripts/preflight.sh` reports Neptune clusters
in the region with identifier, status, and engine version; a cluster that is not `available`, or
older than engine 1.4.5.1, is a finding worth surfacing. If the caller lacks
`neptune:DescribeDBClusters` the probe warns rather than fails — Transform itself remains the
authority on connector state.

**Diagnosing a missing setup (report, do not build).** AWS publishes a CloudFormation template
(`neptune-kg-setup.yaml`) that provisions this against the same bucket the connector will use;
its Outputs tab carries the values the connector needs. A hand-built environment needs: Neptune
Serverless 1.4.5.1+ with IAM auth and storage encryption; a VPC with DNS support and ≥2 subnets
across AZs (size /20); interface endpoints for the Transform Agents API, Bedrock Runtime, RDS,
EC2, and CloudWatch; an S3 gateway endpoint on the subnet route tables; security groups allowing
outbound TCP 8182 to Neptune and 443 to the endpoints, with Neptune allowing inbound 8182; and
an IAM role trusted by `rds.amazonaws.com` with `s3:GetObject`, `s3:ListBucket`, and
`s3:GetBucketLocation`, associated with the cluster for bulk loading.

Hand that list to whoever owns the account. Do not run the template yourself.

Custom-plan (non-reimagine) jobs can use the simpler **S3 connector**, optionally with an S3
vector bucket for search. If the user only needs discovery-style capabilities, that is a
cheaper setup — but the per-function requirements generation in this skill's Stage 5 is a
reimagine capability.

To activate a connector:
- Open the verification link returned by `create_connector` (lets an admin create the role
  during approval), **or**
- `accept_connector` with an existing role ARN. Needs AWS credentials in the environment.

Connector approval is an **admin action**. If the user is not an admin, hand them the link and
wait — do not spin.

### 2.5 Bucket usability

- Read access from the current principal (covered by `scripts/preflight.sh --bucket`).
- **CORS policy** allowing `GET` from the `https://*.transform.<region>.on.aws` origins.
  Without it, inline artifact viewing and file comparison break in the console. This does not
  affect this skill's S3 downloads, so treat a missing CORS policy as a warning, not a G0 blocker.
- Reserve a **separate folder** for SMF records if activity metrics are ever added. SMF must
  not share a folder with source code.

### 2.6 Quotas

Check the account's Transform quotas against the codebase size before a large run. Relevant
if the estate is millions of lines. Do not quote prices or completion times — direct pricing
questions to the AWS Transform and EC2 pricing pages.

## Gate G0

All must hold:

- [ ] `AWS_CREDENTIAL_EXPIRATION` not set to a past timestamp (env not poisoned)
- [ ] Auth valid, correct account, credential headroom compared against the expected run length
- [ ] Region resolved (record `regionSource`) and supported for mainframe
- [ ] A live API call succeeded this session
- [ ] Region consistent across bucket, workspace, and calls
- [ ] Mainframe orchestrator agent discovered and recorded
- [ ] Workspace available
- [ ] Reimagine connector identified and `ACTIVE`
- [ ] Connector bucket readable
- [ ] Neptune cluster present and `available`, or the probe explicitly warned about permissions

Fail → name the single blocking item, give its remediation, stop. Creating a job on a broken
setup produces a job that fails at "Specify resource location" and wastes a cycle.

**One extra condition before any G0 failure may be attributed to the account:** a non-MCP
cross-check from §1.3 must also have failed. Reporting "AWS Transform is not set up" on MCP
evidence alone is a gate violation, not a judgement call. The cheap failure is reconnecting
a server that did not need it; the expensive failure is sending someone to provision
infrastructure they already own — and, because the access-model choice at enablement is
irreversible, potentially to create a second profile they cannot undo.

A `PENDING` connector is not good enough to start. It needs admin approval, and the job will
fail at the first dependent step. Report it and stop.

## Remediation quick reference

| Symptom | Cause | Fix |
|---|---|---|
| `Credentials were refreshed, but the refreshed credentials are still expired` | stale `AWS_CREDENTIAL_EXPIRATION` in the environment — **not** an expired login and **not** clock skew | `env -u AWS_CREDENTIAL_EXPIRATION -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN …`; stop using `eval "$(aws configure export-credentials --format env)"` in a persistent shell |
| Same error, but env is clean | genuinely expired SSO session, or real clock skew | `aws sso login --profile <p>`; compare the clock against an `s3.<region>.amazonaws.com` `Date` header before blaming skew |
| `ExpiredToken` in shell, MCP fine | shell missing `AWS_PROFILE` | pass `--profile` explicitly; re-auth SSO if truly expired |
| `HeadObject` 400 Bad Request | expired creds or region mismatch | same as above; confirm bucket region |
| `NOT_CONFIGURED` / `sigv4AwsTransformAPI.available: false` | **usually the MCP client**, which probes once at startup and caches | reconnect `aws-transform-mcp` from the MCP Server view; pin `AWS_PROFILE`/`AWS_REGION` in its `env`; cross-check per §1.3 before blaming the account |
| `NO_PROFILES` from SSO `configure` | no Transform profile for that IdC instance — or the wrong start URL | cross-check per §1.3; the Transform **Start URL for IDE** is not the IdC portal start URL |
| Signed request returns 404 `UnknownOperationException` | wrong API path, signature accepted | this means access **works**; correct the path, do not re-auth |
| `PROFILE_SELECTION_REQUIRED` | multi-region profiles | `switch_profile` |
| `INSTRUCTIONS_REQUIRED` | `load_instructions` not called for the job | call it, then retry the original call unchanged |
| Connector stuck `PENDING` | admin has not approved | share verification link; wait |
| Connector `FAILED` | IAM role/trust wrong | trust policy must allow `transform.amazonaws.com` |
| Job fails immediately | connector not `ACTIVE` | fix connector, recreate job |
| Job type not found | hardcoded/stale name | rediscover agents; swap `jobType` ↔ `orchestratorAgent` |
| MCP tools missing | server not started / bad `mcp.json` | restart Claude Code; absolute paths in `mcp.json` |
