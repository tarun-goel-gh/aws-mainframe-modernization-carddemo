# Evidence Plans — AWS Transform artifacts

Direct replacement for the Bob skill's `z-*` plans, which in turn replaced `CAST_TOOL_PLANS` in
`cast-integration/src/cast_integration_service/prompts/grounding.py`.

The service injected a named tool sequence into every prompt so evidence was gathered cheaply,
in order, repeatably. This file does the same job against **artifacts already on disk from a
completed `mainframe-reverse-engineering` run**, plus read-only reads of the workspace source.

No CAST MCP server. No Bob. No live AWS Transform calls — see the exclusion in
`grounding-contract.md` §1.

Run the plan named by the document's row in `document-catalog.md`. Run steps **in order**. Stop
when the document's sections are satisfied.

---

## Artifact inventory (what the plans are built from)

Paths are relative to the workspace root. `<Slug>` is a business function name with spaces
removed.

| Artifact | Holds | Provenance when cited |
|---|---|---|
| `.atx/mfre/state.json` | scope, exclusions with signals, gate results, per-function status and metrics, readiness, glossary provenance | `atx-artifact-verified` |
| `.atx/mfre/discovery/business_function.csv` | per function: name, business description, data paths, entry points, total LOC, potential missing files, entry point list | `atx-artifact-verified` |
| `.atx/mfre/discovery/business_function.json` | per function: `category` (batch/online/mixed), `interfaces` → `target_bf` edges | `atx-artifact-verified` |
| `.atx/mfre/specs/<Slug>/spec/<Slug>/requirements.md` | `REQ-F-*` / `REQ-N-*` in EARS form, numbered workflow sections, `OQ-*` open questions | `requirements-derived` |
| `.atx/mfre/specs/<Slug>/spec/<Slug>/traceability.yaml` | `rules:` rule_id → req_id, disposition, **program**; `requirements:` req_id → rule_ids; `summary` totals and reconciliation | `atx-artifact-verified` |
| `.atx/mfre/specs/<Slug>/spec/<Slug>/discovery/programs.yaml` | program inventory for the function — **frequently empty**, use `traceability.yaml` programs instead | `atx-artifact-verified` |
| `.atx/mfre/specs/<Slug>/function-metadata.json` | metrics, verification verdict and warnings, readiness lists, run provenance, glossary caveat | `atx-artifact-verified` |
| `.atx/mfre/analysis/code-analysis/` | per-file name, type, LOC, comment/empty/effective lines, **cyclomatic complexity**, classification, dependencies, missing-file list | `atx-artifact-verified` |
| `.atx/mfre/analysis/data-analysis/` | **data lineage** (datasets, DB2 tables, program-to-data and JCL-to-data with read/write/update/delete direction) and **field-level data dictionary** with business descriptions | `atx-artifact-verified` |
| `.atx/mfre/report.md`, `manifest.json` | run headline, per-function table, warnings, failures, open-question rollup | `atx-artifact-verified` |
| Workspace source members | exact code, member names, line numbers, literals | `source-read-verified` |

### Parsed from workspace source

Not every gap needs a tool. These are parsed directly from members in the workspace and cited
`source-read-verified` with `member:line`. They exist because the evidence was always present and
nothing was reading it — the documents were reporting "not extracted by this run".

| Parsed | What it yields | Feeds |
|---|---|---|
| JCL steps and DD statements | 49 members, 126 steps, 456 DD, utility frequency | `atx-operations` |
| JCL `COND=` and restart | conditional execution per member; restart contract | `atx-operations` |
| Build / compile / link JCL | members invoking compilers, link-editors, BMS assembly, BIND | `atx-operations`, `atx-structure` |
| BMS mapsets | 21 mapsets, 21 maps, 585 named fields with length, row, column, attributes | `atx-api`, `atx-integration` |
| LINKAGE SECTION | 24 programs, 60 items with level and PIC — the called-program signature | `atx-api`, `atx-module` |
| Error handling constructs | 404 across 36 programs: `ABEND`, `RESP`, `FILE STATUS`, `INVALID KEY`, `AT END`, `EXEC CICS HANDLE` | `atx-api`, `atx-quality`, `atx-integration` |

**Keep job control and program error handling separate.** JCL `COND=` is job-step control; COBOL
`ON SIZE ERROR` / `INVALID KEY` / `RESP` is program error handling. Answering an API document's
error section with batch job conditions is a semantic mismatch, and the self-check now rejects it.

**Unavailable, with no substitute.** State the gap; never approximate.

| Missing | Bob had | Documents affected |
|---|---|---|
| Static scan findings per program | Z Code Scan | `as_is_assessment`, `security_architecture` |
| Paragraph index with line ranges | `get_paragraphs` | `code_structure`, `technical_specs`, `component_design` |
| Working-storage item list with PIC, level, usage | `get_variables` | `technical_specs` — note the **LINKAGE SECTION** is now parsed, but working-storage is not |
| Copybook-expanded source | `get_expanded_source` | any section needing resolved PIC clauses |
| Intra-program control flow | `get_control_flow` | `code_structure`, `component_design` |
| Per-variable data flow | `get-data-flow` | `data_lineage` |
| ISO 5055 scoring, CVE mapping, portfolio roll-up | CAST (already lost in the Bob port) | `as_is_assessment`, `security_architecture` |
| Runtime configuration — RPO/RTO, standby capacity, log aggregation, APM | neither had it | `disaster_recovery`, `monitoring_alerting` |

Paragraph structure and call edges may be **parser-derived** from source instead — grep for
`SECTION.`/paragraph headers and for `CALL`/`EXEC CICS LINK|XCTL|START`. When you do that, label
it `parser-derived-not-tool-verified`. Do not present it as structurally verified.

---

## Plan mapping

| CAST plan (origin) | Bob plan | ATX plan | Net effect versus Bob |
|---|---|---|---|
| `discovery` | `z-discovery` | `atx-discovery` | comparable — file metrics now come from code analysis rather than `wc -l` |
| `architecture` | `z-structure` | `atx-structure` | **stronger** — real function-to-function edges and data paths replace a narrative call graph |
| `module` | `z-module` | `atx-module` | **stronger for rules** (rule→program with disposition), **weaker for paragraphs** |
| `data` | `z-data` | `atx-data` | **much stronger** — explicit lineage with access direction, DB2 tables included |
| `api` | `z-api` | `atx-api` | comparable — typed entry points help, no BMS field extraction tool |
| `integration` | `z-integration` | `atx-integration` | **stronger** — `interfaces` edges are catalog-derived |
| `quality` | `z-quality` | `atx-quality` | **weaker** — complexity survives, scan findings do not |
| `business` | `z-business` | `atx-business` | **much stronger** — the catalog *is* a business decomposition |
| — | `z-operations` | `atx-operations` | comparable — JCL still read from source |
| `comprehensive` | not ported | not ported | each level runs its own plan; the manifest aggregates |

---

## `atx-preflight` — run once per session, before any plan

Not a document plan. Establishes what evidence exists and what the coverage boundary is.

1. Read `.atx/mfre/state.json`. Absent → **stop**; the user must run
   `mainframe-reverse-engineering` first. Do not attempt to document from source alone.
2. Require `gates.G2 == "pass"`. Without a persisted catalog there is no function decomposition
   to document against.
3. Read `autonomy.scope` and `autonomy.excludedInfrastructure`.
4. For each scoped function classify evidence: **delivered** (`status` in `succeeded` /
   `succeeded_degraded` and `localPath` exists with `requirements.md`), **scoped-no-spec** (any
   other status), **excluded** (infrastructure, with its signals).
5. Read `analysis/snapshot-manifest.json`. Missing → code analysis and data analysis are
   unavailable; `atx-data`, `atx-quality` and parts of `atx-discovery` degrade. Record it.
6. Note `source.glossaryProvenance`. If `auto-drafted-unverified` or `absent`, every document
   carries the terminology caveat.
7. Write the coverage matrix to `00-manifest/coverage.md` and the evidence index to
   `00-manifest/evidence-index.json`.

**Stop condition:** coverage matrix written, degradations recorded.

---

## `atx-discovery`

Scope, size and technology inventory.

1. `business_function.csv` → the function table: names, descriptions, data paths, entry points,
   LOC, missing files. This is the application's shape.
2. `analysis/code-analysis/` → per-file type, LOC, effective lines, classification. Aggregate to
   counts per language. These are the only size metrics you may state; if the snapshot is
   absent, fall back to `glob` counts and say so.
3. `state.source.fileCounts` → the intake inventory as submitted, and `unknownShare`.
4. `business_function.json` → `category` distribution (batch / online / mixed).
5. `glob` for languages the catalog does not mention, so "not found" is a measured claim rather
   than an omission. Record every language **found and not found**.
6. `state.json` gate notes and `report.md` warnings → known quality caveats at intake.

**Stop condition:** inventory table and technology profile filled.
**Never:** state a count you did not read from an artifact or measure with a tool this run.

---

## `atx-structure`

Architecture, layering and modernization framing.

1. `atx-discovery` results (reuse — do not re-read).
2. `business_function.json` `interfaces` → **function-to-function edges** with `target_bf`.
   This is the top-level architecture, catalog-derived, `atx-artifact-verified`.
3. `analysis/code-analysis/` dependencies → program-to-program edges.
4. `analysis/business-function-discovery/` graphs (`producer_consumer_graph.json`,
   `result_graph.json`, `dp_name_map.json`) → data-path-derived structure.
5. `traceability.yaml` per delivered function → the program set actually attributed to each
   function. Union of these is the documented program inventory.
6. Layer assignment from entry-point type in the catalog: `cics_transaction` → online,
   `cics_link` → called service, `jcl` → batch. State this as the criterion used.
7. `grep` for `CALL '`, `EXEC CICS LINK|XCTL|START`, `COPY ` only for edges steps 2–4 do not
   cover; label those `parser-derived-not-tool-verified`.

**Never:** present the union of function-level edges as a complete program call graph. It is
complete with respect to *delivered* functions only.

---

## `atx-module`

Program-, rule- and requirement-level depth.

1. `traceability.yaml` for the function → `rules:` gives every business rule with its
   `rule_id`, `disposition` (`captured` / `not_applicable` / `unreachable` / `delegated`) and
   attributed `program`. This is the rule catalog, and it is the strongest evidence this skill
   has. Quote rule text verbatim.
2. `requirements.md` → the `REQ-F-*` / `REQ-N-*` statements and the numbered workflow sections.
   Cite by REQ id.
3. `requirements:` reverse index → for each requirement, the rules behind it. Use this for
   provenance, not the forward index; a requirement can be absent from `rules:` yet fully
   mapped here.
4. `function-metadata.json` → `programsReferenced`, metrics, verification warnings.
5. For paragraph-level structure: `grep` the attributed programs for paragraph and `SECTION.`
   headers to build an index with `member:line`. Label `parser-derived-not-tool-verified`.
6. `grep` for `IF `, `EVALUATE `, `WHEN `, `88 ` in attributed programs → conditions the rule
   catalog does not already carry; quote verbatim with `member:line`.
7. `OQ-*` open questions → the decisions the legacy code left implicit. Carry them into the
   document rather than resolving them.

**Stop condition:** every documented rule has a `rule_id` or a `member:line`, and every
requirement cited by REQ id.
**Never:** state a rule count for a function whose spec was not delivered.

---

## `atx-data`

Data dictionary, record layouts and lineage. The strongest plan in this port.

1. `analysis/data-analysis/` **data dictionary** → field-level metadata with business
   descriptions for COBOL structures and DB2 tables. File as `status: draft` and queue for SME
   review; the descriptions are generated, not authored.
2. `analysis/data-analysis/` **data lineage** → datasets, DB2 tables, program-to-data and
   JCL-to-data relationships **with read/write/update/delete direction**. This is
   `atx-artifact-verified` and needs no narrative reconstruction.
3. `read_file` on each copybook → record layouts. Derive offsets and lengths only by computation
   from PIC clauses, and show the computation basis. Note that copybooks are **unexpanded**
   here; nested `COPY` members must be resolved by reading them too.
4. `grep` for `EXEC SQL` → statement inventory per program; `DECLARE ... CURSOR`, `SELECT`,
   `INSERT`, `UPDATE`, `DELETE` and the tables each touches. Cross-check against step 2.
5. `grep` for `SELECT ... ASSIGN TO`, `FD `, `RECORD KEY` → VSAM/QSAM definitions and DDNAMEs;
   cross-reference DDNAMEs against JCL from `atx-operations`.
6. Field-level lineage: chain `read → transform → write` using step 2 direction data. Where step
   2 stops at program granularity and the document needs field granularity, say so — there is no
   per-variable data-flow tool in this evidence set.

**Out of scope — state plainly, never infer:** DDL, constraints, triggers, indexes and catalog
statistics beyond what the data dictionary carries. `.ddl` and `.dcl` members in the workspace
may be read directly and cited as `source-read-verified`.

---

## `atx-api`

Interfaces and entry points.

1. `business_function.csv` `List of entry points` → entry points already typed as
   `cics_transaction`, `cics_link` or `jcl`. This is the interface inventory, catalog-derived.
2. `read_file` on `.csd` resource definitions → transaction ID to program bindings.
3. `read_file` on `.bms` maps → screen fields, lengths, attributes: the online request/response
   contract.
4. `grep` for `PROCEDURE DIVISION USING` and read the LINKAGE SECTION of `cics_link` targets →
   called-program interface signature, the Z equivalent of a request/response schema.
5. `grep` for `EXEC CICS RECEIVE MAP|SEND MAP|LINK|XCTL|START|RETURN TRANSID` → online control
   transfer.
6. `grep` for `MQOPEN|MQPUT|MQGET|MQCLOSE` → asynchronous interfaces.
7. `requirements.md` of the owning function → the behaviour behind each interface, cited by REQ.

**Mapping note:** where the template asks for HTTP method, path, status code, rate limiting or
versioning, use `references/atx-substitutions.md`. If a concept has no equivalent, render the
heading with `Not available from AWS Transform analysis` — never invent a REST framing.

---

## `atx-integration`

Inbound and outbound coupling.

1. `atx-api` results (reuse).
2. `business_function.json` `interfaces` → function-to-function coupling with direction. Primary
   evidence, `atx-artifact-verified`.
3. `analysis/business-function-discovery/` `dp_connections` and `producer_consumer_graph.json` →
   data-path-level producer/consumer relationships.
4. `analysis/data-analysis/` lineage → shared datasets and tables between functions: the
   strongest integration signal, because a shared dataset with write-then-read direction is a
   real handoff.
5. `grep` for `CALL '` (literal) versus `CALL identifier` (dynamic) → called subprograms.
   Dynamic calls are reported as **unresolved edges**, never guessed.
6. JCL `DD` statements, `SYSOUT`, FTP/NDM steps → dataset handoffs and external transfer.
7. Copybook sharing across attributed programs → shared-contract coupling.
8. **Shared entry points** from `state.discovery.sharedEntryPoints` → functions that overlap.
   Overlap is a genuine architectural finding, not a catalog defect.

Every edge carries provenance.

---

## `atx-quality`

Quality, risk and security. **The weakest plan in this port — be explicit about it.**

1. `analysis/code-analysis/` → **cyclomatic complexity** per file, with LOC and effective
   lines. Rank the delivered program set by complexity. `atx-artifact-verified`.
2. `state.json` and `report.md` → missing-file counts per function, duplicate program IDs,
   identically named files, unclassified/UNKNOWN files, and every verification warning. These
   are the run's own quality signals and they are real findings.
3. `traceability.yaml` `summary` → rules `not_applicable` / `unreachable` / `delegated` per
   function. A high unreachable count is a quality signal about the legacy code.
4. `function-metadata.json` verification warnings → truncated requirements, empty program
   inventories, untraced requirements.
5. `grep` for security-relevant patterns actually present: `EXEC CICS VERIFY PASSWORD`, RACF
   calls, hard-coded literals in `VALUE` clauses, `ACCEPT` from console, unencrypted dataset
   writes.
6. `grep` for error handling: `ON SIZE ERROR`, `INVALID KEY`, `AT END`, `EXEC CICS HANDLE`,
   `ABEND`, `RESP` checks → error-handling coverage.

**Not available — state, do not approximate:** static scan findings per program (Bob had Z Code
Scan; there is no equivalent here), ISO 5055 characteristic scoring, CVE mapping, portfolio-level
roll-up. `as_is_assessment` and `security_architecture` will carry more
`Not available from AWS Transform analysis` markers than any other documents in the suite. That
is the honest outcome and the manifest counts it.

---

## `atx-business`

Business capability, feature and requirement content. **The strongest plan in this port.**

1. `business_function.csv` → the business decomposition itself: function name plus a written
   business description, already validated through the discovery gate. These **are** the
   capabilities and features; do not re-derive them from copybook sharing.
2. `business_function.json` `category` → whether a capability is delivered online, in batch, or
   both. Directly answers "how is this used".
3. `requirements.md` per delivered function → `REQ-F-*` in EARS form. These are the business
   requirements; cite by REQ id rather than paraphrasing.
4. `requirements.md` numbered workflow sections → business process steps, in order.
5. `traceability.yaml` `rules:` → policy and eligibility rules with program attribution. Use for
   `business_rules`.
6. Entry points typed `cics_transaction` plus `.bms` screen titles → user-facing feature names.
7. `OQ-*` open questions → unresolved business decisions, which belong in `business_requirements`
   and `gap_analysis` rather than being answered.

Grouping criterion is fixed and needs no invention: the business function **is** the grouping.
State that. Anything not evidenced by a catalog field or a REQ id must be labelled
`Assumption — not tool-verified` per the grounding contract, or omitted.

**Never:** invent a stakeholder, KPI, business owner or org unit. None of that is in the
evidence set. `stakeholder_analysis` is largely `Not available from AWS Transform analysis`, and
saying so is correct.

---

## `atx-operations`

Batch operations, scheduling and recovery.

1. `business_function.csv` filtered to `category: batch` and `jcl` entry points → the job
   inventory that matters, already grouped by business purpose.
2. `analysis/data-analysis/` JCL-to-data relationships → which job touches which dataset, with
   direction. Primary evidence for job data flow.
3. `read_file` on each JCL member → steps, `EXEC PGM=`, `DD` statements, dispositions. Build the
   job-to-program map, `source-read-verified`.
4. `grep` for `COND=`, `IF `, `RESTART=`, `TYPRUN=` → conditional execution and restart points.
5. `grep` for `ABEND`, `RETURN-CODE`, `SET RETURN-CODE`, `EXEC CICS ABEND` → failure modes and
   return-code contracts.
6. `read_file` on PROC members and PROCLIB references → build/compile and runtime configuration.
   This answers the template's build-and-deployment sections.
7. Scheduler metadata **only if checked into the repository** (`.ca7`, `.controlm`, control
   cards, scheduler comments). Never assume a scheduler product.
8. Functions excluded as infrastructure-only often *are* the operations story. Read their catalog
   descriptions and entry points even though no spec was generated for them — and label that
   content `atx-artifact-verified` from the catalog, with no requirements to cite.

**Out of scope:** live scheduler state, SMF data, runtime monitoring feeds, production console
logs. `monitoring_alerting` and `disaster_recovery` are therefore thin; state that rather than
inferring a monitoring posture.
