# CardDemo — Code Quality Summary

**Source**: paragraph count and abend-paragraph analysis from local scanner database (get_paragraphs + SQL)
**Date**: 2025-07-15
**Programs analyzed**: 31 core COBOL programs (44 scanned, 31 with paragraph data in core source)

---

## Complexity Ranking by Paragraph Count

| Rank | Program | Paragraphs | Lines | ABEND paras | Modernization Risk |
|---|---|---|---|---|---|
| 1 | COACTUPC | 101 | 4236 | 2 | 🔴 HIGH |
| 2 | COCRDUPC | 47 | 1560 | 2 | 🔴 HIGH |
| 3 | COCRDLIC | 41 | 1459 | 0 | 🟡 MEDIUM |
| 4 | COACTVWC | 37 | 941 | 1 | 🟡 MEDIUM |
| 5 | COCRDSLC | 36 | 887 | 1 | 🟡 MEDIUM |
| 6 | CBTRN03C | 27 | 649 | 1 | 🟡 MEDIUM |
| 7 | CBTRN02C | 27 | 731 | 1 | 🟡 MEDIUM — Core batch |
| 8 | CBSTM03A | 26 | 924 | 2 | 🟡 MEDIUM |
| 9 | CBACT04C | 23 | 652 | 1 | 🟡 MEDIUM |
| 10 | CBEXPORT | 21 | 582 | 1 | 🟢 LOW |
| 11-31 | (remaining) | 1-18 | 41-783 | 0-1 | 🟢 LOW |

---

## Top-Priority Programs for Explain Code Workflow

The following programs are recommended for `explain-workflow` invocation based on complexity rank (top 20% + core batch):

1. **COACTUPC** — Account update: highest paragraph count (101), largest program (4236 lines). Highest modernization risk.
2. **COCRDUPC** — Credit card update: 47 paragraphs, 1560 lines, complex input validation.
3. **COCRDLIC** — Credit card list: 41 paragraphs, 1459 lines, VSAM browse logic.
4. **CBTRN02C** — Transaction posting: core batch program, 27 paragraphs, VSAM update-heavy.
5. **CBSTM03A** — Statement generator: 26 paragraphs, HTML output, calls CBSTM03B.

---

## ABEND Handling Patterns

| Pattern | Programs | Description |
|---|---|---|
| `9999-ABEND-PROGRAM` | CBACT01C-04C, CBEXPORT, CBIMPORT, CBSTM03A, CBTRN01C-03C | Standard batch abend paragraph |
| `Z-ABEND-PROGRAM` | CBCUS01C | Variant naming (Z- prefix) |
| CICS error paragraph | COADM01C (PGMIDERR-ERR-PARA) | CICS PGMIDERR handling |
| `9910-DISPLAY-IO-STATUS` | CBACT01C-04C, CBTRN01C-02C | Common I/O status display sub-routine |
| `Z-DISPLAY-IO-STATUS` | CBCUS01C | Variant naming |

---

## Key Observations

- COACTUPC is by far the most complex program (4236 lines, 101 paragraphs) and is the highest modernization priority.
- All batch programs use `CEE3ABD` (LE abend service) for abnormal termination — standard z/OS Language Environment pattern.
- CICS programs use XCTL-based navigation with a shared commarea variable `CDEMO-TO-PROGRAM` for dynamic routing.
- CSUTLDTC (date utility) is called by COACTUPC, CORPT00C, and COTRN02C — a shared service candidate.
- MVSWAIT (HLASM) is the only synchronous batch wait mechanism.
- COBDATFT (HLASM) provides date format conversion — called only by CBACT01C.

---

## Z Code Scan Status

Z Code Scan has not yet been run — requires invocation of `zcodescan-check-list-of-local-programs` or per-file `zcodescan-check-current-program` in Z Code mode.
Mark `zcodescan_done=Y` in extraction-status.csv after running.
