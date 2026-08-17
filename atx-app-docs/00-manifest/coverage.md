# Coverage

Discovered: **11** · scoped: **9** · delivered: **6**

Requirement- and rule-derived content covers **6 of 11** discovered business functions. Every count in this suite carries that denominator.

| Business function | Category | Class | Reqs (F/N) | Rules | LOC | Data paths | Documentable |
|---|---|---|---|---|---|---|---|
| Account Balance and Transaction Processing | mixed | `delivered` | 286/4 | 286/328 | 8269 | 10 | full |
| Application Build and Deployment | batch | `excluded-infrastructure` | — | — | 256 | 12 | catalog only |
| Credit Card Record Management | online | `delivered` | 22/0 | 14/14 | 4218 | 3 | full |
| Customer and Account Data Export and Import | batch | `delivered` | 22/1 | 37/37 | 1071 | 2 | full |
| Master Data File Initialization | batch | `scoped-no-spec` | — | — | 703 | 9 | catalog only |
| Online Transaction Entry | online | `scoped-no-spec` | — | — | 1592 | 2 | catalog only |
| Payment Authorization Processing and Fraud Review | mixed | `delivered` | 53/3 | 55/57 | 3590 | 8 | full |
| System Administration and Infrastructure Setup | mixed | `excluded-infrastructure` | — | — | 6068 | 20 | catalog only |
| Transaction Reporting and Statement Generation | batch | `scoped-no-spec` | — | — | 2095 | 4 | catalog only |
| Transaction Type Reference Data Maintenance | mixed | `delivered` | 14/0 | 15/15 | 4288 | 9 | full |
| User Security Profile Management | mixed | `delivered` | 69/0 | 59/65 | 2848 | 6 | full |

## Consequences

- **3 scoped function(s) delivered no specification**, so only catalog metadata is documentable for them: Master Data File Initialization, Online Transaction Entry, Transaction Reporting and Statement Generation.
- **2 function(s) excluded as infrastructure-only**:
  - Application Build and Deployment — build/compile toolchain referenced in description (compile, assemble, link-edit, load module); very low LOC density (256 LOC across 5 entry points) — thin wrappers around utilities
  - System Administration and Infrastructure Setup — environment administration (CICS resource definition, DB2 DDL, RACF); operational plumbing (file open/close, FTP, job submission, wait steps); description describes system tasks rather than a business outcome
- Totals across delivered functions only: **466** functional requirements, **466** business rules captured.
- Absence of evidence for a function is not evidence about that function. Unrepresented functions are named, never characterised.

## Degraded evidence

- `verified glossary` missing → affects all — lost: terminology confidence (glossaryProvenance=absent)
