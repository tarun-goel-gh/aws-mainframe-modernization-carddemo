# HITL task catalog

Human-in-the-loop tasks (Collaborator Requests) are how the agent asks for input. Getting the
submission shape wrong is the most common cause of a stalled job.

## Autonomy rule

Under the default `autonomous` mode, answer any checkpoint whose response is **derivable** —
computable from verified state or a documented policy, with no judgment call. Pause only at the
hard stops. Under `human-touch`, pause at every checkpoint.

Log every autonomous submission to `state.answeredTasks[]` with task id, title, the payload
sent, and the derivation used. The report lists them. "It was automated" is not an acceptable
answer to "why does my spec say that", so the derivation has to be recoverable.

**Hard stops — never auto-answer:**

| Condition | Why |
|---|---|
| `severity: CRITICAL` | non-admins must `SEND_FOR_APPROVAL`; auto-approving as admin discards the review the severity exists to force |
| `category: TOOL_APPROVAL` | an agent asking permission to run a tool |
| Destructive or scope-expanding | workspace/job deletion, provisioning, widening scope |
| Genuinely ambiguous | two valid connectors, unresolvable function name, contradictory catalog |

When a hard stop fires, park the task as `awaiting_user`, keep going with other work, and
surface it in the report. Do not stall the whole run on one checkpoint.

## Finding tasks

```
list_resources resource="tasks" workspaceId=… jobId=…                          # all
list_resources resource="tasks" … taskStatus="AWAITING_HUMAN_INPUT"            # needs input
list_resources resource="tasks" … category="TOOL_APPROVAL"                     # separate flow
```

Three human-actionable states — surface all three, because the person present may be the approver:

| Status | Meaning |
|---|---|
| `AWAITING_HUMAN_INPUT` | first input required |
| `IN_PROGRESS` | engaged, not submitted |
| `AWAITING_APPROVAL` | submitted, awaiting admin/approver |

`blockingType` decides whether progress is actually held: `BLOCKING` stalls the job,
`NON_BLOCKING` does not. Report state regardless; only escalate urgency for `BLOCKING`.

Terminal states — no action: `CLOSED`, `CLOSED_PENDING_NEXT_TASK`, `CANCELLED`, `DELIVERED`.

`INSTRUCTIONS_REQUIRED` on any task call means `load_instructions` was not called for that job.
Call it, then retry the original call **with identical parameters**.

## Reading a task

```
get_resource resource="task" workspaceId=… jobId=… taskId=…
```

Returns two objects that must be read together:

- **`task`** — the submission shape: `_outputSchema`, `_responseTemplate`, `_responseHint`,
  `uxComponentId`, `severity`, `blockingType`.
- **`agentArtifactContent`** — the user-visible context: current values, selectable options,
  component extras that may not appear in the schema.

`_responseHint` is authoritative for the component. If it uses merge language ("provide only
the fields you want to change"), send **only** fields the user actually changed. Including
unchanged fields violates the merge contract and can overwrite values silently.

Empty `agentArtifactContent` (`{}`) usually means the agent is still generating. Check
worklogs, wait 30–60s, retry. Do not submit against an empty artifact.

## Submitting

1. Show the user the artifact content **and** the fields needed.
2. Wait for the decision.
3. Show the exact payload about to be submitted.
4. `complete_task` with `action`: `APPROVE` (default), `REJECT`, `SEND_FOR_APPROVAL`, `SAVE_DRAFT`.

Payload shapes by component family:

| Family | `content` |
|---|---|
| TextInput | `{"data": "text"}` |
| AutoForm | flat JSON matching `_outputSchema` |
| File upload | `upload_artifact` first, then pass `artifactId` (or use `filePath`) |
| Display-only | omit `content` — server submits `{}` |

Severity: `STANDARD` → APPROVE/REJECT submits immediately. `CRITICAL` → non-admins must use
`SEND_FOR_APPROVAL`.

`TOOL_APPROVAL` tasks use the tool-approval flow, **not** `complete_task` — the backend rejects
`complete_task` for them. If the dedicated approval tools are unavailable in the running MCP
server version, surface the pending approval to the user and let them act in the web app rather
than forcing a wrong call.

## Observed task sequence — mainframe assess-and-reimagine

Order and components observed on a real job. Treat as a strong prior, not a contract;
always read `uxComponentId` and `_responseHint` from the live task.

| # | Title | `uxComponentId` | Class | Notes |
|---|---|---|---|---|
| 1 | Add collaborators | `InviteCollaboratorsContent` | decision | `NON_BLOCKING`; empty artifact. Answering with no invitees is valid — but it is still the user's call |
| 2 | Connect to AWS account | `CreateOrSelectConnectors` | decision | needs `connectorId` **and** `connectorType`; look up type via `get_resource resource="connector"` |
| 3 | Specify resource location | `SpecifyAssetsLocation` | decision | artifact field is `value`, output field is `assetLocation`; must be a `.zip` |
| 4 | View code analysis results | `MainframeAnalysisResults` | review | display-only; triage quality signals before acknowledging |
| 5 | View data analysis results | `MainframeDataLineageResultComponent` | review | display-only |
| 6 | Review data path discovery | `MainframeBreResultComponent` | review | display-only |
| 7 | Review business functions discovery | `MainframeAssessmentBusinessProcessDiscoveryComponent` | **decision** | where business functions are selected for reimagine |
| 8 | Configure settings (BRE) | `MainframeBreInputComponent` | decision | see the BRE trap below |
| 9 | Business rule extraction results | `MainframeBreResultComponent` | review | display-only |
| 10 | Review generated modernization requirements | `AutoForm` | review | description carries the `spec_gen` S3 link |

Classification rule of thumb: if the task changes what the job will *do*, it is a decision. If
it only shows what the job *did*, it is a review.

## Derivation rules (autonomous mode)

Each of these has exactly one defensible answer given verified state, so answering it is a
lookup rather than a decision.

| Task | Derivation | Guard |
|---|---|---|
| Add collaborators | submit with no invitees | `NON_BLOCKING`; the user can invite later in the web app |
| Connect to AWS account | the single `ACTIVE` reimagine connector found at G0; send `connectorId` + `connectorType` from `get_resource resource="connector"` | more than one candidate → hard stop |
| Specify resource location | `assetLocation` = the `zipKey` this run uploaded and recorded at G1 | no recorded key → hard stop |
| Review code analysis results | read, extract quality signals into state, acknowledge | — |
| Review data analysis results | read, record lineage/dictionary counts, acknowledge | — |
| Review data path discovery | read, record counts, acknowledge | — |
| Review business functions discovery | select `state.autonomy.scope`, computed at G2 from the catalog | empty scope → hard stop |
| Configure settings (BRE) | `userSelectedFiles` = every file attributed to the selected function(s); set the detailed-specification flag | empty file list → hard stop |
| Business rule extraction results | read, record issue list, acknowledge | — |
| Review generated requirements | read, capture the `spec_gen` S3 link, acknowledge | link absent → poll again before answering |

Two rules that apply to all of them:

- **Read before answering.** Extract the artifact's signals into state first. Acknowledging a
  results review without reading it defeats the checkpoint and lets bad analysis reach the
  requirements stage unnoticed.
- **Respect merge semantics.** Send only fields you are actually setting. `_responseHint` is
  authoritative per component.

### BRE configuration trap

For `MainframeBreInputComponent` you must **always populate `userSelectedFiles`**, regardless of
`reportScope`:

- `applicationLevel` — one application-wide business rules summary
- `fileLevel` — per-file reports

The web app auto-selects all files for `applicationLevel`; **the API does not**. Omitting the
list produces an empty or failed extraction. Optionally enable the detailed functional
specification flag for control flow and comprehensive rules.

Also note: the number of generated business rule files can exceed the selection, because
selected files pull in dependents.

### Business function selection

Component `MainframeAssessmentBusinessProcessDiscoveryComponent` is unlisted in the response
hints, so it falls under merge semantics: send only the fields you are changing. Read
`agentArtifactContent` to see the exact selection structure and the available function names
before constructing a payload — do not assume a shape.

Selection cardinality follows the extraction shape:

- **Sequential** — one function per submission. Cleanest attribution.
- **Batch** — the whole batch in one submission, for large estates. The run then returns a
  single combined spec zip that must be split per function (see `references/extraction.md`).

Match names exactly as they appear in the artifact. Do not normalise, re-case, or guess at a
name — if a scoped function cannot be matched to an option, that is a hard stop, not a
best-effort pick.

### Re-selection resets displayed results

Selecting a second set restarts the reimagine step for the new selection, and the console then
shows results only for the newest set. Earlier outputs survive in S3 and the artifacts tab but
stop being surfaced. Always snapshot before re-selecting.

## Troubleshooting

| Problem | Fix |
|---|---|
| `VALIDATION_ERROR` on submit | re-read `_outputSchema`; do not wrap in `{"data":…}` or `{"properties":…}` unless required |
| Empty `agentArtifactContent` | agent still generating — wait and retry |
| File upload fails | verify the path; set `fileType` explicitly |
| Task reappears after submit | check `severity` — `CRITICAL` may need `SEND_FOR_APPROVAL` |
| Job active but no progress | pending `BLOCKING` task; also check `TOOL_APPROVAL` category |
| `HTTP 400 ValidationException: A message is already being processed for this conversation` | one in-flight message per job conversation — see below |

### One message at a time per conversation

`send_message` is not concurrent-safe per job. A second call while the first is still being
processed fails with `HTTP 400 ValidationException: A message is already being processed for
this conversation`, and the rejected message is simply lost — no queueing.

This bites hardest when a message is slow because a sub-agent is erroring: the previous send
looks finished from the caller's side but is still open server-side.

- Serialise sends. Never fire a follow-up before the previous one has produced a
  `FINAL_RESPONSE`.
- Use `skipPolling: true` for a long trigger, then read replies with
  `list_resources resource="messages"` — this avoids holding the 60-second poll open and makes
  the in-flight window explicit.
- On this error, back off 60–150 seconds and resend. It is transient and self-clearing.
- Confirm delivery by matching `parentMessageId` to your `sentMessageId` and looking for
  `messageType: FINAL_RESPONSE`; `THINKING` entries mean the turn is still open.
