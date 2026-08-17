---
source: README.md + program file declarations (SQL query on Files table) + copybook layouts
date: 2025-07-15
provenance: tool-verified (file declarations from local scanner DB) + read-from-source
---

# CardDemo — VSAM and File Structures

## Core VSAM Files

| Logical Name | JCL DD Name | Organization | Access Mode | Key Field | Length | Copybook |
|---|---|---|---|---|---|---|
| Account Master | ACCTFILE | KSDS | Random/Sequential | ACCT-ID (11 digits) | 300 | CVACT01Y |
| Card Master | CARDFILE | KSDS | Random/Sequential | CARD-NUM (16 chars) | 150 | CVACT02Y |
| Customer Master | CUSTFILE | KSDS | Random/Sequential | CUST-ID (9 digits) | 500 | CVCUS01Y |
| Card-Account XREF | CARDXREF | KSDS+AIX | Random (by CARD-NUM or ACCT-ID) | CARD-NUM(16) / AIX: ACCT-ID(11) | 50 | CVACT03Y |
| Online Transaction | TRANSACT | KSDS | Random/Browse | TRAN-ID | 350 | CVTRA05Y |
| Daily Transaction | DALYTRAN | Sequential | Sequential | — | 350 | CVTRA06Y |
| Daily Rejects | DALYREJS | Sequential | Sequential | — | — | — |
| Transaction Category Balance | TCATBALF | KSDS | Random/Sequential | ACCT-ID+TYPE-CD+CAT-CD (17 digits) | 50 | CVTRA01Y |
| Transaction Category | TRANCATG | KSDS | Sequential | — | 60 | CVTRA04Y |
| Transaction Type | TRANTYPE | KSDS | Sequential | — | 60 | CVTRA03Y |
| Disclosure Group | DISCGRP | KSDS | Random | GROUP-ID+TYPE-CD+CAT-CD | 50 | CVTRA02Y |
| User Security | USRSEC | ESDS | Sequential | — | 80 | CSUSR01Y |

## Additional Dataset Types (from JCL)

| Type | Purpose | JCL |
|---|---|---|
| GDG | Base and data definitions | DEFGDGB, DEFGDGD |
| ESDS | VSAM ESDS example | ESDSRRDS.jcl |
| RRDS | VSAM RRDS example | ESDSRRDS.jcl |
| Statement output | HTML/text statement files | CREASTMT |
| Report output | Transaction report | TRANREPT |

## File Access Summary (Batch Programs)

| Program | Reads | Writes | Updates |
|---|---|---|---|
| CBACT01C | ACCTFILE | OUT-FILE, ARRY-FILE, VBRC-FILE | — |
| CBACT02C | CARDFILE | — | — |
| CBACT03C | XREFFILE | — | — |
| CBACT04C | TCATBALF, XREF-FILE, DISCGRP, TRANSACT | TRANSACT | ACCOUNT |
| CBCUS01C | CUSTFILE | — | — |
| CBEXPORT | ACCOUNT, CARD, CUSTOMER, XREF, TRANSACTION | EXPORT-OUTPUT | — |
| CBIMPORT | EXPORT-INPUT | ACCOUNT, CARD, CUSTOMER, XREF, TRANSACTION, ERROR | — |
| CBSTM03A | (reads via CBSTM03B) | HTML-FILE, STMT-FILE | — |
| CBSTM03B | ACCT-FILE, CUST-FILE, TRNX-FILE, XREF-FILE | — | — |
| CBTRN01C | ACCOUNT, CARD, CUSTOMER, DALYTRAN, TRANSACT, XREF | — | — |
| CBTRN02C | DALYTRAN, XREF | DALYREJS, TRANSACT, TCATBAL | ACCOUNT |
| CBTRN03C | TRANSACT, XREF, TRANCATG, TRANTYPE, DATE-PARMS | REPORT-FILE | — |

## Key VSAM Record Layouts

### Account Record (CVACT01Y) — 300 bytes
- ACCT-ID: PIC 9(11)
- ACCT-ENTITY-TYPE: PIC X(1)
- ACCT-CURR-BAL: PIC S9(10)V99 COMP-3
- ACCT-CREDIT-LIMIT: PIC S9(10)V99 COMP-3
- ACCT-CASH-CREDIT-LIMIT: PIC S9(10)V99 COMP-3
- ACCT-INTEREST-RATE: PIC V9(2)
- ACCT-OPEN-DATE: PIC X(10)
- ACCT-EXPIRATION-DATE: PIC X(10)
- ACCT-REISSUE-DATE: PIC X(10)
- ACCT-CURR-CYC-CREDIT: PIC S9(10)V99 COMP-3
- ACCT-CURR-CYC-DEBIT: PIC S9(10)V99 COMP-3
- ACCT-GROUP-ID: PIC X(10)

### Card Record (CVACT02Y) — 150 bytes
- CARD-NUM: PIC X(16)
- CARD-ACCT-ID: PIC 9(11)
- CARD-CVV-CD: PIC 9(3)
- CARD-EMBOSSED-NAME: PIC X(50)
- CARD-EXPIRATION-DATE: PIC X(10)
- CARD-ACTIVE-STATUS: PIC X(1)

### Customer Record (CVCUS01Y) — 500 bytes
- CUST-ID: PIC 9(9)
- CUST-FIRST-NAME: PIC X(25)
- CUST-MIDDLE-NAME: PIC X(25)
- CUST-LAST-NAME: PIC X(25)
- CUST-ADDR-LINE-1 through LINE-3: PIC X(50) each
- CUST-STATE-CD: PIC X(2)
- CUST-ZIP-CD: PIC X(10)
- CUST-PHONE-NUM-1, NUM-2: PIC X(15) each
- CUST-SSN: PIC 9(9)
- CUST-GOVT-ISSUED-ID: PIC X(20)
- CUST-DOB-YYYY-MM-DD: PIC X(10)
- CUST-EFT-ACCOUNT-ID: PIC X(10)
- CUST-PRI-CARD-HOLDER-IND: PIC X(1)
- CUST-FICO-CREDIT-SCORE: PIC 9(3)

### Transaction Record (CVTRA05Y) — 350 bytes (VSAM)
- TRAN-ID: PIC X(16)
- TRAN-TYPE-CD: PIC X(2)
- TRAN-CAT-CD: PIC 9(4)
- TRAN-SOURCE: PIC X(10)
- TRAN-DESC: PIC X(100)
- TRAN-AMT: PIC S9(9)V99 COMP-3
- TRAN-CARD-NUM: PIC X(16)
- TRAN-MERCHANT-ID: PIC 9(9)
- TRAN-MERCHANT-NAME: PIC X(50)
- TRAN-MERCHANT-CITY: PIC X(50)
- TRAN-MERCHANT-ZIP: PIC X(10)
- TRAN-ORIG-TS: PIC X(26)
- TRAN-PROC-TS: PIC X(26)
