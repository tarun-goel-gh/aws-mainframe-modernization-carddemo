# Z Substitutions

The 31 document templates were written for distributed applications (Java/Python/Node, REST,
relational ORMs, containers). They are ported **verbatim** so the section set stays identical
to the service output. This table tells you what each distributed-stack concept means on Z.

**Rules:**

1. If the template names a concept in the left column, gather the middle column instead.
2. If the middle column says *no equivalent*, render the heading and write
   `Not available from Z Premium analysis`. Record it in the manifest's `notApplicable` list.
3. Never re-frame mainframe evidence as REST/microservice concepts to make a section look
   filled. A CICS transaction is not an HTTP endpoint — document it as a CICS transaction
   under the template's heading.

---

## Build, packaging and dependencies

| Template concept | Z equivalent | Evidence |
|---|---|---|
| `pom.xml`, `build.gradle`, `package.json`, `requirements.txt` | Compile/link JCL, PROC members, `zapp.yaml` / `.zapp` property groups, BIND cards | `read_file`, `z-discovery` step 2 |
| Dependency versions / lockfile | Library concatenation order in `zapp.yaml` `libraries.locations` and JCL `STEPLIB`/`SYSLIB` | `read_file` |
| Package / module organisation | Source library (PDS) grouping, member naming convention, JCL job grouping | `z-discovery` step 1, `z-structure` step 6 |
| Third-party libraries | Called vendor subprograms, CICS/IMS/DB2 system stubs, utility programs (IDCAMS, SORT, IEBGENER) | `grep` on `CALL '`, JCL `EXEC PGM=` |
| Build tool version | Compiler options in compile JCL / `zapp.yaml` (`ARCH`, `OPT`, `SQL`, `CICS` suboptions) | `read_file` |
| Docker / Kubernetes / cloud config | *No equivalent* — LPAR, CICS region and PROCLIB definitions are usually outside the repo | Mark unavailable unless checked in |
| CI/CD pipeline | Build JCL and any checked-in pipeline definitions only | `read_file` |
| `git log` / last modified | ISPF statistics if present, otherwise filesystem `stat` | `execute_command` (read-only) |

## Interfaces

| Template concept | Z equivalent | Evidence |
|---|---|---|
| REST endpoint / HTTP method + path | CICS transaction ID → program binding; program entry point via `PROCEDURE DIVISION USING` | `z-api` steps 1–4 |
| Request / response schema | BMS map fields (online) or LINKAGE SECTION copybook layout (called program) | `.bms` read, copybook read |
| API status codes | CICS `RESP`/`RESP2` values, `RETURN-CODE`, ABEND codes | `grep` |
| Authentication / authorization | RACF/ESM calls, `EXEC CICS VERIFY PASSWORD`, transaction security in `.csd`, signon programs | `grep`, `.csd` read |
| Rate limiting / throttling / quotas | *No equivalent* — closest is CICS MAXTASKS / transaction class, usually not in the repo | Mark unavailable unless checked in |
| API versioning / deprecation policy | Program suffix conventions (e.g. `PROGA`, `PROGA2`), copybook version members — only if a convention is demonstrably present | `z-discovery` step 1 |
| Message queue / event bus | MQ `MQOPEN`/`MQPUT`/`MQGET` calls and queue names | `grep` |
| Webhooks / callbacks | `EXEC CICS START` (async transaction start), triggered MQ transactions | `grep` |

## Data

| Template concept | Z equivalent | Evidence |
|---|---|---|
| Database schema / tables / columns | DB2 tables referenced in `EXEC SQL`, DCLGEN copybooks; VSAM/QSAM datasets via `FD` and `SELECT ... ASSIGN TO` | `z-data` steps 4–5 |
| ORM entities / models | Copybook record layouts | Copybook read |
| Indexes, constraints, triggers, DDL | *No equivalent in scope* — requires DBA tooling outside Bob | Always mark out of scope |
| Migrations | Conversion/load JCL and utility steps (IDCAMS REPRO, DSNUTILB), if checked in | `read_file` |
| Data validation rules | `88` condition names, `IF`/`EVALUATE` edits, PIC clause constraints | `z-module` step 7 |
| Row counts / DB size | *No equivalent* — no live catalog access | Mark unavailable |
| Data lineage | Field-level `read → transform → write` chain across programs and datasets | `z-data` step 6 |

## Runtime and operations

| Template concept | Z equivalent | Evidence |
|---|---|---|
| Environment variables / config files | JCL SYMBOLS and PARM values, control-card datasets, PROC parameters | `read_file` |
| Deployment procedure | Compile/link/BIND JCL sequence, promotion JCL if checked in | `z-operations` step 5 |
| Service / process | CICS transaction (online) or JCL job step (batch) | `z-operations` step 2 |
| Logging | `DISPLAY` statements, SYSOUT DD, CICS journal writes, audit dataset writes | `grep` |
| Monitoring / alerting | Return-code checks, `COND=` gates, ABEND handling, checked-in automation rules | `z-operations` steps 3–4 |
| Disaster recovery / failover | Restart logic (`RESTART=`, checkpoint records), backup/recovery JCL, GDG generations | `z-operations` steps 3, 5 |
| SLA / uptime metrics | *No equivalent* — no runtime telemetry | Mark unavailable |
| Scaling / performance tuning | Compiler options, `OCCURS` sizing, sort work allocation, access-method choice | `read_file`, `z-quality` |

## Quality and testing

| Template concept | Z equivalent | Evidence |
|---|---|---|
| Unit / integration tests | Test JCL jobs, test data members, driver programs | `z-discovery` step 1 |
| Coverage metrics | *No equivalent* unless a coverage tool's output is checked in | Mark unavailable |
| Static analysis findings | Z Code Scan results | `z-quality` step 1 |
| Cyclomatic complexity | Z Code Scan complexity signals | `z-quality` step 2 |
| CVE / dependency vulnerabilities | *No equivalent* — CAST supplied this; Z Code Scan does not | Mark unavailable |
| ISO 5055 characteristics | *No equivalent* — CAST supplied this | Mark unavailable |
| Code smells / tech debt | Z Code Scan findings plus coding-standard deviations from `AGENTS.md` | `z-quality` |

## Organisation and people

| Template concept | Z equivalent | Evidence |
|---|---|---|
| Team ownership / CODEOWNERS | Author comments in member headers, change-log comment blocks — only if present | `grep` |
| Stakeholders | Inferred from job naming, department codes in comments, business terms in the data dictionary | `z-business` — label as `Assumption — not tool-verified` |
| User personas | CICS transaction groupings and screen flows | `z-api`, `z-business` |
