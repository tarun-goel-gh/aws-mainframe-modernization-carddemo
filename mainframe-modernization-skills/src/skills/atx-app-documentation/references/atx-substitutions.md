# ATX Substitutions

The 31 document templates were written for distributed applications (Java/Python/Node, REST,
relational ORMs, containers). They are ported **verbatim** so the section set stays identical to
the origin service's output. This table tells you what each distributed-stack concept means when
the evidence base is an AWS Transform reverse-engineering run.

**Rules:**

1. If the template names a concept in the left column, gather the middle column instead.
2. If the middle column says *no equivalent*, render the heading and write
   `Not available from AWS Transform analysis`. Record it in the manifest's `notApplicable` list.
3. Never re-frame mainframe evidence as REST/microservice concepts to make a section look
   filled. A CICS transaction is not an HTTP endpoint — document it as a CICS transaction under
   the template's heading.
4. Prefer an AWS Transform artifact over a source read wherever both could answer. The artifact
   is `atx-artifact-verified`; a grep is `source-read-verified` or
   `parser-derived-not-tool-verified`.

**Difference from the Bob port.** Bob's substitutions leaned on Z Premium workflows and editor
tools. Here the middle column leans on catalog fields, `traceability.yaml`, code analysis and
data analysis. Several rows get *stronger* evidence as a result; the quality rows get weaker,
because there is no scan equivalent. Both directions are marked.

---

## Build, packaging and dependencies

| Template concept | ATX equivalent | Evidence |
|---|---|---|
| `pom.xml`, `build.gradle`, `package.json`, `requirements.txt` | Compile/link JCL and PROC members, BIND cards | `read_file`, `atx-operations` step 6 |
| Dependency versions / lockfile | Library concatenation order in JCL `STEPLIB`/`SYSLIB` | `read_file` |
| Package / module organisation | Business function grouping from the catalog, then member naming and JCL job grouping | `atx-discovery` step 1, `atx-structure` step 6 |
| Third-party libraries | Called vendor subprograms and utility programs (IDCAMS, SORT, IEBGENER, IKJEFT1B, SDSF) | code-analysis dependencies, `grep` on `EXEC PGM=` |
| Internal dependency graph | **code-analysis dependencies JSON** — program-to-program edges | `atx-structure` step 3 *(stronger than Bob)* |
| Build tool version | Compiler options in compile JCL (`ARCH`, `OPT`, `SQL`, `CICS` suboptions) | `read_file` |
| Docker / Kubernetes / cloud config | *No equivalent* — LPAR, CICS region and PROCLIB definitions are usually outside the repo | Mark unavailable unless checked in |
| CI/CD pipeline | Build JCL and any checked-in pipeline definitions only | `read_file` |
| `git log` / last modified | Filesystem `stat`, or intake `inventory.csv` | `atx-discovery` |

## Interfaces

| Template concept | ATX equivalent | Evidence |
|---|---|---|
| REST endpoint / HTTP method + path | **Typed entry point from the catalog** — `cics_transaction`, `cics_link` or `jcl` — plus its program binding | `atx-api` step 1 *(stronger than Bob: already typed)* |
| Request / response schema | BMS map fields (online) or LINKAGE SECTION copybook layout (called program) | `.bms` read, copybook read |
| API status codes | CICS `RESP`/`RESP2` values, `RETURN-CODE`, ABEND codes | `grep` |
| Endpoint behaviour / contract | `REQ-F-*` statements of the owning business function | `atx-api` step 7, cite by REQ id *(stronger than Bob)* |
| Authentication / authorization | RACF/ESM calls, `EXEC CICS VERIFY PASSWORD`, transaction security in `.csd`, signon programs | `grep`, `.csd` read |
| Rate limiting / throttling / quotas | *No equivalent* — closest is CICS MAXTASKS / transaction class, usually not in the repo | Mark unavailable unless checked in |
| API versioning / deprecation policy | Program suffix conventions, copybook version members — only if demonstrably present | `atx-discovery` |
| Message queue / event bus | MQ `MQOPEN`/`MQPUT`/`MQGET` calls and queue names | `grep` |
| Webhooks / callbacks | `EXEC CICS START` (async transaction start), triggered MQ transactions | `grep` |
| Service-to-service calls | **Business function `interfaces` → `target_bf` edges** | `atx-integration` step 2 *(stronger than Bob)* |

## Data

| Template concept | ATX equivalent | Evidence |
|---|---|---|
| Database schema / tables / columns | **Data-analysis data dictionary** — field-level metadata for COBOL structures and DB2 tables, with business descriptions | `atx-data` step 1 *(much stronger than Bob)* |
| ORM entities / models | Copybook record layouts | Copybook read |
| Data access patterns | **Data lineage with read / write / update / delete direction**, program-to-data and JCL-to-data | `atx-data` step 2 *(much stronger than Bob)* |
| Indexes, constraints, triggers, DDL | Only what `.ddl` / `.dcl` members in the repo carry; live catalog objects are out of scope | `read_file`; otherwise mark out of scope |
| Migrations | Conversion/load JCL and utility steps (IDCAMS REPRO, DSNUTILB), if checked in | `read_file` |
| Data validation rules | **`traceability.yaml` rules** with program attribution, then `88` condition names and `IF`/`EVALUATE` edits | `atx-module` steps 1, 6 *(stronger than Bob)* |
| Row counts / DB size | *No equivalent* — no live catalog access | Mark unavailable |
| Data lineage | Program- and dataset-level lineage from data analysis; **field-level only where the artifact carries it** | `atx-data` step 6 — state the granularity limit |
| Field-level data flow within a program | *No equivalent* — Bob had `get-data-flow`; there is no per-variable tool here | Mark unavailable |

## Runtime and operations

| Template concept | ATX equivalent | Evidence |
|---|---|---|
| Environment variables / config files | JCL SYMBOLS and PARM values, control-card datasets, PROC parameters | `read_file` |
| Deployment procedure | Compile/link/BIND JCL sequence, promotion JCL if checked in | `atx-operations` step 6 |
| Service / process | CICS transaction (online) or JCL job step (batch), from the catalog's entry-point type | `atx-operations` steps 1, 3 |
| Job-to-dataset flow | **JCL-to-data lineage with direction** | `atx-operations` step 2 *(stronger than Bob)* |
| Logging | `DISPLAY` statements, SYSOUT DD, CICS journal writes, audit dataset writes | `grep` |
| Monitoring / alerting | Return-code checks, `COND=` gates, ABEND handling, checked-in automation rules | `atx-operations` steps 4–5 |
| Disaster recovery / failover | Restart logic (`RESTART=`, checkpoint records), backup/recovery JCL, GDG generations | `atx-operations` steps 4, 6 |
| SLA / uptime metrics | *No equivalent* — no runtime telemetry | Mark unavailable |
| Scaling / performance tuning | Compiler options, `OCCURS` sizing, sort work allocation, access-method choice | `read_file`, `atx-quality` |

## Quality and testing

| Template concept | ATX equivalent | Evidence |
|---|---|---|
| Unit / integration tests | Test JCL jobs, test data members, driver programs | `atx-discovery` step 5 |
| Coverage metrics | *No equivalent* unless a coverage tool's output is checked in | Mark unavailable |
| Static analysis findings | *No equivalent* — **Bob had Z Code Scan; AWS Transform has no scan output** | Mark unavailable *(weaker than Bob)* |
| Cyclomatic complexity | **code-analysis per-file cyclomatic complexity** | `atx-quality` step 1 *(stronger than Bob: a number, not a signal)* |
| Code quality signals | Missing-file counts, duplicate program IDs, identically named files, unclassified files, verification warnings | `atx-quality` step 2 — these are real findings from the run |
| Unreachable / dead code | **`traceability.yaml` dispositions** — `unreachable`, `not_applicable`, `delegated` per rule | `atx-quality` step 3 *(stronger than Bob)* |
| CVE / dependency vulnerabilities | *No equivalent* — CAST supplied this; neither Bob nor AWS Transform does | Mark unavailable |
| ISO 5055 characteristics | *No equivalent* — CAST supplied this | Mark unavailable |
| Code smells / tech debt | Complexity ranking plus the run's own quality signals | `atx-quality` |
| Paragraph / section structure | Parser-derived from source headers only | `atx-module` step 5, label `parser-derived-not-tool-verified` *(weaker than Bob)* |

## Business and organisation

| Template concept | ATX equivalent | Evidence |
|---|---|---|
| Business capability | **A business function from the catalog**, with its written description | `atx-business` step 1 *(much stronger than Bob)* |
| Business feature | Business function plus its typed entry points and BMS screen titles | `atx-business` steps 1, 6 |
| Business requirement | **`REQ-F-*` in EARS form** from the function's `requirements.md` | `atx-business` step 3 *(much stronger than Bob)* |
| Non-functional requirement | `REQ-N-*` statements | `requirements.md` |
| Business process / workflow | **Numbered workflow sections** in `requirements.md`, in order | `atx-business` step 4 *(stronger than Bob)* |
| Business rule | **`traceability.yaml` rule with `rule_id`, disposition and attributed program** | `atx-module` step 1 *(much stronger than Bob)* |
| Open business decision | **`OQ-*` open questions** | `atx-business` step 7 — carry forward, do not answer |
| Delivery channel | Catalog `category`: batch / online / mixed | `business_function.json` |
| Team ownership / CODEOWNERS | Author comments in member headers, change-log comment blocks — only if present | `grep` |
| Stakeholders / business owners / org units | *No equivalent* — not in the evidence set | Mark unavailable; never invent a stakeholder |
| KPIs / business metrics | *No equivalent* | Mark unavailable |
| User personas | CICS transaction groupings and screen flows | `atx-api`, `atx-business` — label `Assumption — not tool-verified` |

---

## Coverage qualifier — applies to every row above

Every substitution is bounded by the delivered function set. A row sourced from
`requirements.md` or `traceability.yaml` yields evidence **only for functions whose spec was
delivered**. For a scoped function with no specification, the catalog rows still apply (name,
description, category, entry points, LOC, data paths) but every requirement- and rule-derived row
reads `Not available from AWS Transform analysis — no specification delivered for this function`.

This is why `atx-preflight` builds the coverage matrix before any document is written: it
determines, per function, which half of this table is usable.
