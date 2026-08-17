---
member: CARDDEMO.CSD (and variants)
source_path: app/csd/, app/app-*/csd/
workflow: read-from-checked-in-source
date: 2025-07-15
provenance: read-from-checked-in-source
---

# CardDemo — CICS Transactions and BMS Maps

## Core Application (CARDDEMO.CSD)

| Transaction ID | BMS Mapset | BMS Map | COBOL Program | Function | User Type |
|---|---|---|---|---|---|
| CC00 | COSGN00 | COSGN00A | COSGN00C | Signon screen | Both |
| CM00 | COMEN01 | COMEN01A | COMEN01C | Main menu | User |
| CAVW | COACTVW | COACTVWA | COACTVWC | Account view | User |
| CAUP | COACTUP | COACTUPA | COACTUPC | Account update | User |
| CCLI | COCRDLI | COCRDLIA | COCRDLIC | Credit card list | User |
| CCDL | COCRDSL | COCRDSLB | COCRDSLC | Credit card view/detail | User |
| CCUP | COCRDUP | COCRDUPA | COCRDUPC | Credit card update | User |
| CT00 | COTRN00 | COTRN00A | COTRN00C | Transaction list | User |
| CT01 | COTRN01 | COTRN01A | COTRN01C | Transaction view | User |
| CT02 | COTRN02 | COTRN02A | COTRN02C | Transaction add | User |
| CR00 | CORPT00 | CORPT00A | CORPT00C | Transaction report | User |
| CB00 | COBIL00 | COBIL00A | COBIL00C | Bill payment | User |
| CA00 | COADM01 | COADM01A | COADM01C | Admin menu | Admin |
| CU00 | COUSR00 | COUSR00A | COUSR00C | User list | Admin |
| CU01 | COUSR01 | COUSR01A | COUSR01C | Add user | Admin |
| CU02 | COUSR02 | COUSR02A | COUSR02C | Update user | Admin |
| CU03 | COUSR03 | COUSR03A | COUSR03C | Delete user | Admin |

## Optional Module: Authorization (CRDDEMO2.csd — IMS/DB2/MQ)

| Transaction ID | BMS Mapset | BMS Map | COBOL Program | Function |
|---|---|---|---|---|
| CPVS | COPAU00 | COPAU00A | COPAUS0C | Pending authorization summary |
| CPVD | COPAU01 | COPAU01A | COPAUS1C | Pending authorization details |
| CP00 | — | — | COPAUA0C | Process authorization requests (MQ trigger) |

## Optional Module: Transaction Type DB2 (CRDDEMOD.csd)

| Transaction ID | BMS Mapset | BMS Map | COBOL Program | Function |
|---|---|---|---|---|
| CTTU | COTRTUP | COTRTUPA | COTRTUPC | Transaction type add/edit |
| CTLI | COTRTLI | COTRTLIA | COTRTLIC | Transaction type list/update/delete |

## Optional Module: MQ Account Inquiry (CRDDEMOM.csd)

| Transaction ID | BMS Mapset | BMS Map | COBOL Program | Function |
|---|---|---|---|---|
| CDRD | — | — | CODATE01 | System date inquiry via MQ |
| CDRA | — | — | COACCT01 | Account details inquiry via MQ |

## BMS Map Files

| BMS File | Copybook | Associated Transaction |
|---|---|---|
| app/bms/COSGN00.bms | app/cpy-bms/COSGN00.CPY | CC00 |
| app/bms/COMEN01.bms | app/cpy-bms/COMEN01.CPY | CM00 |
| app/bms/COACTVW.bms | app/cpy-bms/COACTVW.CPY | CAVW |
| app/bms/COACTUP.bms | app/cpy-bms/COACTUP.CPY | CAUP |
| app/bms/COCRDLI.bms | app/cpy-bms/COCRDLI.CPY | CCLI |
| app/bms/COCRDSL.bms | app/cpy-bms/COCRDSL.CPY | CCDL |
| app/bms/COCRDUP.bms | app/cpy-bms/COCRDUP.CPY | CCUP |
| app/bms/COTRN00.bms | app/cpy-bms/COTRN00.CPY | CT00 |
| app/bms/COTRN01.bms | app/cpy-bms/COTRN01.CPY | CT01 |
| app/bms/COTRN02.bms | app/cpy-bms/COTRN02.CPY | CT02 |
| app/bms/CORPT00.bms | app/cpy-bms/CORPT00.CPY | CR00 |
| app/bms/COBIL00.bms | app/cpy-bms/COBIL00.CPY | CB00 |
| app/bms/COADM01.bms | app/cpy-bms/COADM01.CPY | CA00 |
| app/bms/COUSR00.bms | app/cpy-bms/COUSR00.CPY | CU00 |
| app/bms/COUSR01.bms | app/cpy-bms/COUSR01.CPY | CU01 |
| app/bms/COUSR02.bms | app/cpy-bms/COUSR02.CPY | CU02 |
| app/bms/COUSR03.bms | app/cpy-bms/COUSR03.CPY | CU03 |
| app/app-transaction-type-db2/bms/COTRTUP.bms | app/app-transaction-type-db2/cpy-bms/COTRTUP.cpy | CTTU |
| app/app-transaction-type-db2/bms/COTRTLI.bms | app/app-transaction-type-db2/cpy-bms/COTRTLI.cpy | CTLI |
| app/app-authorization-ims-db2-mq/bms/COPAU00.bms | app/app-authorization-ims-db2-mq/cpy-bms/COPAU00.cpy | CPVS |
| app/app-authorization-ims-db2-mq/bms/COPAU01.bms | app/app-authorization-ims-db2-mq/cpy-bms/COPAU01.cpy | CPVD |

## CICS File Definitions (from CSD)

Key VSAM files managed by CICS:
- ACCTDAT — Account master (KSDS)
- CARDDAT — Card master (KSDS)  
- CUSTDAT — Customer master (KSDS)
- CXACAIX — Card-account cross-reference (KSDS with AIX)
- TRANSACT — Online transaction file (KSDS)
- USRSEC — User security file (ESDS)
- DISCGRP — Disclosure group file (KSDS)
- TCATBALF — Transaction category balance file (KSDS)
- TRANCATG — Transaction category file (KSDS)
- TRANTYPE — Transaction type file (KSDS)
