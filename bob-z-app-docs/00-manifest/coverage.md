# Coverage

Inventory: **46** programs · in scope: **46** · reused from extraction: **0** · needs an evidence pass: **46** · out of scope: **0**

BobZ has no business-function discovery step; the denominator here is programs. Every count in this suite carries `of 46`.

| Program | Language | Class | dd | doc | explain | zcodescan | Lines |
|---|---|---|---|---|---|---|---|
| CBACT01C | COBOL | `needs-evidence-pass` | N | P | N | N | 430 |
| CBACT02C | COBOL | `needs-evidence-pass` | N | P | N | N | 178 |
| CBACT03C | COBOL | `needs-evidence-pass` | N | P | N | N | 178 |
| CBACT04C | COBOL | `needs-evidence-pass` | N | P | N | N | 652 |
| CBCUS01C | COBOL | `needs-evidence-pass` | N | P | N | N | 178 |
| CBEXPORT | COBOL | `needs-evidence-pass` | N | P | N | N | 582 |
| CBIMPORT | COBOL | `needs-evidence-pass` | N | P | N | N | 487 |
| CBPAUP0C | COBOL | `needs-evidence-pass` | N | N | N | N | 386 |
| CBSTM03A | COBOL | `needs-evidence-pass` | N | P | N | N | 924 |
| CBSTM03B | COBOL | `needs-evidence-pass` | N | P | N | N | 230 |
| CBTRN01C | COBOL | `needs-evidence-pass` | N | P | N | N | 494 |
| CBTRN02C | COBOL | `needs-evidence-pass` | N | P | N | N | 731 |
| CBTRN03C | COBOL | `needs-evidence-pass` | N | P | N | N | 649 |
| COACCT01 | COBOL | `needs-evidence-pass` | N | N | N | N | 620 |
| COACTUPC | COBOL | `needs-evidence-pass` | N | P | N | N | 4236 |
| COACTVWC | COBOL | `needs-evidence-pass` | N | P | N | N | 941 |
| COADM01C | COBOL | `needs-evidence-pass` | N | P | N | N | 288 |
| COBDATFT | HLASM | `needs-evidence-pass` | N | N | N | N | 84 |
| COBIL00C | COBOL | `needs-evidence-pass` | N | P | N | N | 572 |
| COBSWAIT | COBOL | `needs-evidence-pass` | N | P | N | N | 41 |
| COBTUPDT | COBOL | `needs-evidence-pass` | N | N | N | N | 237 |
| COCRDLIC | COBOL | `needs-evidence-pass` | N | P | N | N | 1459 |
| COCRDSLC | COBOL | `needs-evidence-pass` | N | P | N | N | 887 |
| COCRDUPC | COBOL | `needs-evidence-pass` | N | P | N | N | 1560 |
| CODATE01 | COBOL | `needs-evidence-pass` | N | N | N | N | 524 |
| COMEN01C | COBOL | `needs-evidence-pass` | N | P | N | N | 308 |
| COPAUA0C | COBOL | `needs-evidence-pass` | N | N | N | N | 1026 |
| COPAUS0C | COBOL | `needs-evidence-pass` | N | N | N | N | 1032 |
| COPAUS1C | COBOL | `needs-evidence-pass` | N | N | N | N | 604 |
| COPAUS2C | COBOL | `needs-evidence-pass` | N | N | N | N | 244 |
| CORPT00C | COBOL | `needs-evidence-pass` | N | P | N | N | 649 |
| COSGN00C | COBOL | `needs-evidence-pass` | N | P | N | N | 260 |
| COTRN00C | COBOL | `needs-evidence-pass` | N | P | N | N | 699 |
| COTRN01C | COBOL | `needs-evidence-pass` | N | P | N | N | 330 |
| COTRN02C | COBOL | `needs-evidence-pass` | N | P | N | N | 783 |
| COTRTLIC | COBOL | `needs-evidence-pass` | N | N | N | N | 2098 |
| COTRTUPC | COBOL | `needs-evidence-pass` | N | N | N | N | 1702 |
| COUSR00C | COBOL | `needs-evidence-pass` | N | P | N | N | 695 |
| COUSR01C | COBOL | `needs-evidence-pass` | N | P | N | N | 299 |
| COUSR02C | COBOL | `needs-evidence-pass` | N | P | N | N | 414 |
| COUSR03C | COBOL | `needs-evidence-pass` | N | P | N | N | 359 |
| CSUTLDTC | COBOL | `needs-evidence-pass` | N | P | N | N | 157 |
| DBUNLDGS | COBOL | `needs-evidence-pass` | N | N | N | N | 366 |
| MVSWAIT | HLASM | `needs-evidence-pass` | N | N | N | N | 30 |
| PAUDBLOD | COBOL | `needs-evidence-pass` | N | N | N | N | 369 |
| PAUDBUNL | COBOL | `needs-evidence-pass` | N | N | N | N | 317 |

## Consequences

- **46 program(s) need a fresh MCP evidence pass** before `generate_docs.py` can ground anything about them beyond inventory facts: CBACT01C, CBACT02C, CBACT03C, CBACT04C, CBCUS01C, CBEXPORT, CBIMPORT, CBPAUP0C, CBSTM03A, CBSTM03B, CBTRN01C, CBTRN02C, CBTRN03C, COACCT01, COACTUPC, COACTVWC, COADM01C, COBDATFT, COBIL00C, COBSWAIT, COBTUPDT, COCRDLIC, COCRDSLC, COCRDUPC, CODATE01, COMEN01C, COPAUA0C, COPAUS0C, COPAUS1C, COPAUS2C, CORPT00C, COSGN00C, COTRN00C, COTRN01C, COTRN02C, COTRTLIC, COTRTUPC, COUSR00C, COUSR01C, COUSR02C, COUSR03C, CSUTLDTC, DBUNLDGS, MVSWAIT, PAUDBLOD, PAUDBUNL.
- **0 of 46** programs are fully reusable from a prior `cobol-knowledge-extraction` run (`dd_generated=Y` and `doc_generated=Y`).
- Absence of evidence for a program is not evidence about that program. Unrepresented programs are named, never characterised.

## Degraded evidence

- `zUnderstandConfigured (server not configured)` missing → affects z-integration, z-structure — lost: dependency data stays narrative-per-program-not-tool-verified; every get_project_* backed plan degrades
- `reused extraction evidence` missing → affects all — lost: 0 of 46 in-scope programs have both dd_generated=Y and doc_generated=Y — every in-scope program needs a fresh MCP evidence pass before generate_docs.py can ground anything beyond inventory-level facts
