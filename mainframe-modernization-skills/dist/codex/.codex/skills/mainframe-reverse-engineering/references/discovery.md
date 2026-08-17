# Discovery: business function catalog

Four capabilities in dependency order. Code analysis is the foundation for everything else, so
never try to skip it.

```
Analyze code → Analyze data → Discover data paths → Discover business functions
```

A **data path** is the route data takes from a business trigger to its final write. A
**business function** is a body of work starting at a business trigger and ending at a
measurable business outcome, built from a set of data paths. Because the same code blocks that
define a function are the ones used to generate its specification, there is no translation
layer between assessment and extraction — which is exactly why getting the catalog right
matters more than getting it fast.

## Driving the phase

After `create_job`, the agent plans and executes. Your job is to service HITL tasks and hold
the quality bar. Poll with `get_job_status`; use `list_resources resource="plan"` to see step
status (`SUCCEEDED` per step is the signal to look for).

If the agent stalls with no pending task, check `list_resources resource="tasks"` for all
three human-actionable states before assuming a hang — see `references/hitl-tasks.md`.

## Per-capability quality signals

### Analyze code

Produces per-file name, type, LOC, path, comment/empty/effective lines, and **cyclomatic
complexity**. Four signals must be triaged, not skimmed:

| Signal | Why it matters | Action |
|---|---|---|
| **Missing files** | referenced but absent; every dependent rule is degraded | list them; ask whether to supply and re-run analysis |
| **Duplicated program IDs** | COBOL `PROGRAM-ID` is the call identity; duplicates corrupt dependency mapping | report file pairs; recommend fixing IDs and re-running |
| **Identically named files** | ambiguous references | report; usually benign but confirm |
| **Codebase issues** | missing references, unsupported links | report before continuing |
| **UNKNOWN / TXT files** | unclassified source is invisible to extraction | offer reclassification (only these two classes are eligible, only after the initial loop) |

Missing files are the single most common cause of thin requirements. Treat a non-empty missing
list as a decision point for the user, not a footnote.

The code-analysis result bundle is downloadable from the job's artifacts (`results` folder):
classification file, assets list, dependencies JSON, and missing-file list. Snapshot it — it is
the evidence for anything you claim about coverage.

**Snapshot the analysis artifacts as a step, not as an afterthought:**

```
scripts/snapshot_analysis.sh --profile <p> --region <r> \
  --bucket <connector-bucket> --job-id <jobId> --dest .atx/mfre/analysis
```

This captures code analysis, data analysis (lineage + data dictionary), business function
discovery and the business-documentation outputs, unpacks any zips, and writes
`snapshot-manifest.json` recording which prefixes existed. Record the result in
`state.discovery.analysisSnapshot`.

Two reasons this is required rather than optional. It is the evidence for every coverage claim
in the report, and it is the **primary evidence source for the `atx-app-documentation` skill**,
which generates the 31-document suite from these artifacts. A run without it produces a catalog
and specs but leaves the documentation pipeline with nothing to ground against.

### Analyze data

Two outputs:
- **Data lineage** — datasets, DB2 tables, program-to-data, JCL-to-data relationships, with
  read/write/update/delete direction.
- **Data dictionary** — field-level metadata for COBOL structures and DB2 tables, with business
  descriptions.

Lineage table counts can legitimately differ from dictionary counts. Do not report that as a
defect.

### Discover data paths

Traces control flow, data flow, and I/O across programs. Spans batch jobs and CICS
transactions rather than following a single entry point, which is what allows coherent
cross-channel functions to emerge.

### Discover business functions

Groups data paths into functions by shared business purpose. Delivers two artifacts:
- **Business function summary** — the list with natural-language descriptions
- **Business function details** — interactive graph of relationships across the source

## Capturing the catalog

Snapshot `business_function_outputs.zip` from under
`transform-output/<jobId>/business-function-discovery/` using `scripts/fetch_artifact.sh`.

The authoritative machine-readable catalog is `reports/business_function.csv`:

```
Name of business function, Business descriptions, Number of data paths,
Number of entry points, Total LOC, Number of potential missing files, List of entry points
```

`debug/business_process-artifacts/business_function.json` adds a `category` field
(`batch` / `online` / `mixed`) and per-function `interfaces`. Merge both into
`state.discovery.functions`. Prefer these files over parsing chat prose — the chat summary is a
rendering, the CSV is the data.

Write each function's `slug` (name with spaces removed) at this point; it is the folder name
used later in spec bundles.

## Presenting the catalog

Show a table: function, category, data paths, entry points, LOC, missing files. Sort by LOC
descending — it puts the expensive work at the top where the user will actually weigh it.

Then, before extraction, distinguish **business** functions from **infrastructure** groupings.
Discovery includes everything reachable, so build/deploy JCL and sysadmin utilities routinely
appear as "functions". They carry no business rules to extract, and they tend to dominate the
missing-file counts, which makes the catalog look alarming for no reason.

### Infrastructure detection — derived, never hardcoded

Classify from the run's own catalog. **Never match against a list of known application or
function names** — the skill must work on any COBOL estate, and a hardcoded name is a bug.

Signals, applied to the function's description and entry-point list:

| Signal | Example evidence |
|---|---|
| Build / compile toolchain | entry points invoking compilers, link-editors, BMS assembly; description mentions compile, link-edit, load module |
| Environment administration | CICS resource definition, DB2 DDL creation, security/RACF command execution |
| Operational plumbing | file open/close, FTP or managed file transfer, job submission, scheduling, wait steps |
| No business outcome | description describes system tasks rather than a business trigger reaching a measurable business result |
| Very low LOC across many entry points | thin wrappers around utilities rather than logic |

Two or more signals, and no clear business outcome → propose as infrastructure-only. Under
`autonomous`, exclude by default and list every exclusion with the signals that triggered it, so
the decision is auditable and reversible. Under `human-touch`, ask.

Borderline cases stay **in** scope. A wrongly included function costs compute; a wrongly
excluded one silently loses business logic, which is far worse.

### Overlap

Flag functions that **share entry points**. The catalog is not guaranteed disjoint, and
overlapping functions produce overlapping requirements the user should expect rather than
discover later.

## Gate G2

- [ ] Catalog persisted to state from the CSV/JSON artifacts, not from prose
- [ ] Analysis artifacts snapshotted to `.atx/mfre/analysis/` and recorded in state
- [ ] Every function has ≥1 data path and ≥1 entry point
- [ ] Code-analysis signals triaged: missing files, duplicate IDs, identical names, unclassified files
- [ ] Infrastructure-only functions flagged, each with the signals that classified it
- [ ] Shared entry points across functions flagged
- [ ] Scope written to `state.autonomy.scope`; exclusions to `state.autonomy.excludedInfrastructure`
- [ ] Extraction shape chosen and recorded (`batchMode` true/false, batch size)

Only after G2 does extraction start. Each function costs real compute, so scope is the last
cheap decision in this pipeline. Under `autonomous`, present the catalog and the computed scope
as a statement of what is about to run rather than a question — but present it, so a wrong
exclusion is visible before the compute is spent, not after.
