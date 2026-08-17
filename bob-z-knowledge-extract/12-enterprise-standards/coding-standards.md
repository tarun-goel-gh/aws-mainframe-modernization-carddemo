# CardDemo — Enterprise Coding Standards

## Status
Generated from source code analysis — 2025-07-15.
NOTE: AGENTS.md has not yet been generated (requires /init workflow in Z Code mode).
This document should be updated after running /init.

---

## 1. Program Header Convention

Every COBOL program begins with a standard header block:

```cobol
      ******************************************************************
      * Program     : <PROGNAME>.CBL
      * Application : CardDemo
      * Type        : BATCH|CICS COBOL Program
      * Function    : <One-line description>
      ******************************************************************
      * Copyright Amazon.com, Inc. or its affiliates.
      * All Rights Reserved.
      * Licensed under the Apache License, Version 2.0
      ******************************************************************
```

## 2. Division and Section Structure

- Standard COBOL division order: IDENTIFICATION → ENVIRONMENT → DATA → PROCEDURE
- WORKING-STORAGE is organized into numbered groups with `*****` comment dividers
- Group-level variable names use prefixes indicating purpose (e.g., `WS-`, `FD-`, `CD-`, `WS-MISC-STORAGE`)
- 88-level condition names used extensively for flags and status codes

## 3. Naming Conventions

| Prefix | Usage |
|---|---|
| `WS-` | Working-Storage variables |
| `FD-` | File Description record fields |
| `CD-` | Communication/CICS data areas |
| `DFHCOMMAREA` | CICS commarea (standard IBM name) |
| `LK-` or `LINKAGE-` | Linkage Section variables |

## 4. CICS Pattern

- All CICS programs use `EXEC CICS ... END-EXEC` blocks
- Response code checking via `WS-RESP-CD` (PIC S9(09) COMP) and `WS-REAS-CD`
- HANDLE CONDITION or RESP/RESP2 parameter checking used for CICS error handling
- Programs use XCTL or LINK for screen navigation

## 5. File Access Patterns

- VSAM KSDS files declared in FILE-CONTROL with ORGANIZATION IS INDEXED
- Both SEQUENTIAL and RANDOM access modes are used
- FILE STATUS fields used for I/O error detection (format: `<name>-STATUS`)
- ALTERNATE RECORD KEY used for AIX (alternate index) access

## 6. Batch Program Patterns

- Batch programs (CB prefix) follow open/read/process/close loop
- Transaction processing programs use sequential read of daily transaction file
- File status checked after every I/O operation

## 7. Optional Module Patterns

| Module | COBOL Programs | Technology |
|---|---|---|
| Core CardDemo | CO* / CB* in app/cbl/ | CICS + VSAM |
| Authorization | COPA*, CBPA*, DBUNL*, PAUD* | IMS DB + DB2 + MQ |
| Transaction Type DB2 | COBT*, COTRT* | DB2 |
| MQ Account Inquiry | COACCT01, CODATE01 | MQ + VSAM |

## 8. Source Member Naming

- CICS online programs: `CO<XX><nn>C.cbl` (CO prefix, function code, sequence number, C suffix)
- Batch programs: `CB<XXX><nn>C.cbl` (CB prefix, function code)
- Utility programs: `CS<XXX>.cbl` (CS prefix)
- HLASM programs: `*.asm` in app/asm/

## 9. AGENTS.md Generation Required

Run `/init` in Z Code mode on this workspace to generate the full `AGENTS.md` governance baseline.
Once generated, copy to `12-enterprise-standards/AGENTS.md`.
