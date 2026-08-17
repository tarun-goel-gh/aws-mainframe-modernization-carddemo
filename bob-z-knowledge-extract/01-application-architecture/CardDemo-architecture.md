---
member: CardDemo (application-level)
source_path: app/cbl/, app/asm/, app/app-*/cbl/
perspective: architect
workflow: source-code-analysis + get_paragraphs + execute_sql_query + scan_program
date: 2025-07-15
provenance: tool-verified (local scanner database) + read-from-source
---

# CardDemo — Application Architecture

## 1. Application Overview

CardDemo is a mainframe credit card management application built primarily in COBOL, deployed on z/OS using CICS for online transaction processing and JCL batch for overnight processing. It simulates a realistic credit card system for mainframe modernization testing and demonstration.

- **Primary language**: COBOL (44 programs)
- **Supporting languages**: HLASM (2 programs), JCL (45 jobs/procs)
- **Transaction processor**: CICS
- **Storage**: VSAM KSDS (primary), ESDS, RRDS, GDG
- **Optional modules**: DB2, IMS DB, IBM MQ

---

## 2. Structural Decomposition

### 2a. Online Subsystem (CICS)

All online programs follow a common CICS transaction pattern:
- Entry via `MAIN-PARA` (or `PROGRAM_<PROGNAME>_FIRST_SENTENCES` for batch)
- Screen processing via `SEND-*-SCREEN` / `RECEIVE-*-SCREEN` paragraph pairs
- Navigation via `EXEC CICS XCTL` to `CDEMO-TO-PROGRAM` (dynamic program name in commarea)
- Error handling via `PGMIDERR-ERR-PARA` and `RESP`/`RESP2` checking

#### Transaction Flow (User Path)
```
CC00 → COSGN00C (Signon)
  ↓
CM00 → COMEN01C (Main Menu)
  ├── CAVW → COACTVWC (Account View)
  │    └── CAUP → COACTUPC (Account Update)
  ├── CCLI → COCRDLIC (Credit Card List)
  │    └── CCDL → COCRDSLC (Credit Card View)
  │         └── CCUP → COCRDUPC (Credit Card Update)
  ├── CT00 → COTRN00C (Transaction List)
  │    ├── CT01 → COTRN01C (Transaction View)
  │    └── CT02 → COTRN02C (Transaction Add)
  ├── CR00 → CORPT00C (Transaction Report) → submits CBTRN03C via internal reader
  └── CB00 → COBIL00C (Bill Payment)
```

#### Transaction Flow (Admin Path)
```
CC00 → COSGN00C (Signon)
  ↓
CA00 → COADM01C (Admin Menu)
  ├── CU00 → COUSR00C (User List)
  │    ├── CU01 → COUSR01C (Add User)
  │    ├── CU02 → COUSR02C (Update User)
  │    └── CU03 → COUSR03C (Delete User)
  └── [Optional DB2 transactions: CTTU, CTLI]
```

### 2b. Batch Subsystem (JCL)

#### Core Batch Processing Sequence
```
CLOSEFIL → file initialization
ACCTFILE / CARDFILE / CUSTFILE / XREFFILE → VSAM load (IDCAMS)
TRANFILE → initial transaction load
TRANBKP → transaction backup
POSTTRAN → CBTRN02C → transaction posting (core batch)
INTCALC  → CBACT04C → interest calculation
COMBTRAN → SORT combine daily+system transactions
CREASTMT → CBSTM03A → generate transaction statements
TRANIDX  → IDCAMS AIX definition
OPENFIL  → make VSAM files available to CICS
```

#### Utility Batch Programs
| Program | Function |
|---|---|
| CBACT01C | Sequential read of account file → FB/VB output formats |
| CBACT02C | Sequential read of card file |
| CBACT03C | Sequential read of XREF file |
| CBCUS01C | Sequential read of customer file |
| CBEXPORT | Export all entities to flat file |
| CBIMPORT | Import from flat file to VSAM |
| CBTRN01C | Transaction validation (pre-post) |
| CBTRN03C | Transaction report (submitted from CICS by CORPT00C) |
| COBSWAIT | Batch wait step (calls MVSWAIT HLASM) |

---

## 3. Data Architecture

### 3a. Core VSAM Files

| Logical Name | CICS File | Copybook | Key | Description |
|---|---|---|---|---|
| ACCTFILE | ACCTDAT | CVACT01Y | ACCT-ID (11 digits) | Account master |
| CARDFILE | CARDDAT | CVACT02Y | CARD-NUM (16 chars) | Credit card master |
| CUSTFILE | CUSTDAT | CVCUS01Y | CUST-ID (9 digits) | Customer master |
| CARDXREF | CXACAIX | CVACT03Y | CARD-NUM / ACCT-ID | Card-account cross-reference (with AIX) |
| TRANSACT | TRANSACT | CVTRA05Y | TRAN-ID | Online transaction VSAM |
| DALYTRAN | — | CVTRA06Y | — | Daily transaction sequential file (batch input) |
| DISCGRP | DISCGRP | CVTRA02Y | GROUP-ID | Disclosure groups |
| TCATBALF | TCATBALF | CVTRA01Y | ACCT-ID+TYPE+CAT | Transaction category balances |
| TRANCATG | TRANCATG | CVTRA04Y | — | Transaction categories |
| TRANTYPE | TRANTYPE | CVTRA03Y | — | Transaction types |
| USRSEC | USRSEC | CSUSR01Y | USER-ID | User security file |

### 3b. Key Copybooks

| Copybook | Purpose | Users |
|---|---|---|
| CVACT01Y | Account record layout | CBACT01C, CBACT04C, CBEXPORT, CBIMPORT, CBSTM03A, CBTRN01C, CBTRN02C |
| CVACT02Y | Card record layout | CBACT02C, CBEXPORT, CBIMPORT, CBTRN01C |
| CVACT03Y | XREF record layout | CBACT03C, CBACT04C, CBEXPORT, CBIMPORT, CBSTM03A, CBTRN01C, CBTRN02C, CBTRN03C |
| CVTRA05Y | Transaction record (VSAM) | CBACT04C, CBEXPORT, CBIMPORT, CBTRN01C, CBTRN02C, CBTRN03C |
| CVTRA06Y | Daily transaction record | CBTRN01C, CBTRN02C |
| CVCUS01Y | Customer record | CBCUS01C, CBEXPORT, CBIMPORT, CBTRN01C |
| CVEXPORT | Export record layout | CBEXPORT, CBIMPORT |
| COCOM01Y | CICS commarea common area | All CICS programs |
| COTTL01Y | Screen title definitions | CICS programs |
| CSDAT01Y | Date-related fields | CICS programs using date |
| CSUSR01Y | User security record | COSGN00C, COUSR* |

---

## 4. Program Dependency Graph

```
                      ┌──────────────────────────────────────────────────┐
                      │              CICS Online Subsystem               │
                      │                                                  │
  COSGN00C ──XCTL──▶ COMEN01C ──XCTL──▶ [User Functions]               │
     │                   │               COACTVWC / COACTUPC             │
     └──XCTL──▶ COADM01C │               COCRDLIC / COCRDSLC / COCRDUPC  │
                         │               COTRN00C / COTRN01C / COTRN02C  │
                         │               CORPT00C / COBIL00C             │
                         └──XCTL──▶ [Admin Functions]                    │
                                    COUSR00C / COUSR01C                  │
                                    COUSR02C / COUSR03C                  │
                      └──────────────────────────────────────────────────┘
                              │ CALL
                              ▼
                         CSUTLDTC (Date utility) ──CALL──▶ CEEDAYS
                              │
                    ┌─────────┘─────────────────────────────────────────┐
                    │              Batch Subsystem                       │
                    │                                                    │
  POSTTRAN ──runs──▶ CBTRN02C                                           │
  INTCALC  ──runs──▶ CBACT04C                                           │
  CREASTMT ──runs──▶ CBSTM03A ──CALL──▶ CBSTM03B                       │
  TRANREPT ──runs──▶ CBTRN03C                                           │
  WAITSTEP ──runs──▶ COBSWAIT ──CALL──▶ MVSWAIT (HLASM)                │
  CBACT01C ──CALL──▶ COBDATFT (HLASM)                                   │
    └────────── All batch programs ──CALL──▶ CEE3ABD (LE abend)        │
                    └────────────────────────────────────────────────────┘
```

---

## 5. Optional Module Architecture

### Module: Credit Card Authorization (IMS + DB2 + MQ)

```
MQ Trigger ──▶ COPAUA0C (Authorization Processor)
                  ├── Reads MQ request queue (MQGET)
                  ├── Inserts/Updates IMS DB (CBLTDLI)
                  └── Responds via MQ
CICS CPVS ──▶ COPAUS0C (Pending Auth Summary)
                  └── Read IMS + VSAM
CICS CPVD ──▶ COPAUS1C (Pending Auth Details)
                  └── Update IMS + Insert DB2
CICS CPAU2 ──▶ COPAUS2C (Auth Detail sub-screen)
CBPAUP0J  ──▶ CBPAUP0C (Batch purge expired auths)
              PAUDBUNL / PAUDBLOD (IMS DB load/unload)
              DBUNLDGS (GSAM unload)
```

### Module: Transaction Type Management (DB2)

```
CICS CTTU ──▶ COTRTUPC (Transaction type add/edit)  ──SQL──▶ DB2 TRNTYPE table
CICS CTLI ──▶ COTRTLIC (Transaction type list/update/delete) ──SQL cursor──▶ DB2
Batch     ──▶ COBTUPDT (Maintain transaction type table)
              TRANEXTR JCL extracts DB2 data to flat files
```

### Module: MQ Account Inquiry

```
CICS CDRD ──▶ CODATE01 (System date inquiry via MQ)
CICS CDRA ──▶ COACCT01 (Account details inquiry via MQ)
```

---

## 6. Technology Summary

| Component | Technology | Count |
|---|---|---|
| Online programs | COBOL + CICS | 21 core + 8 optional |
| Batch programs | COBOL | 15 core + 3 optional |
| Utility/sub programs | COBOL | 3 |
| System programs | HLASM | 2 |
| JCL jobs | JCL | 37 core + 8 optional |
| BMS map sets | BMS | 17 core + 4 optional |
| Copybooks | COBOL COPY | 30 core + 13 optional |
| BMS-derived copybooks | COBOL COPY | 17 core + 4 optional |
| CSD resource definitions | CICS CSD | 4 (1 per module variant) |

---

## Evidence Index

| Section | Source |
|---|---|
| Transaction flows | README.md application inventory table |
| Paragraph structure | get_paragraphs tool (local scanner DB) |
| Program calls | SQL query on StatementReference (ResourceType=5) |
| File access | SQL query on StatementReference (ResourceType=9) |
| Copybook dependencies | SQL query on StatementReference (ResourceType=13) |
| Optional modules | README.md + app/app-*/README.md |
| Technology counts | Directory scan (glob) |
