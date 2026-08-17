---
source: app/jcl/, app/app-*/jcl/, app/proc/, README.md
date: 2025-07-15
provenance: read-from-source + README.md table
---

# CardDemo — JCL Batch Job Documentation

## Job-to-Program Map

| Job Name | Program(s) | Type | Function | Optional Module |
|---|---|---|---|---|
| DUSRSECJ | IEBGENER | Utility | Initial load of user security file | — |
| CLOSEFIL | IEFBR14 | Utility | Close VSAM files in CICS | — |
| ACCTFILE | IDCAMS | VSAM | Refresh account master | — |
| CARDFILE | IDCAMS | VSAM | Refresh card master | — |
| CUSTFILE | IDCAMS | VSAM | Refresh customer master | — |
| XREFFILE | IDCAMS | VSAM | Account/card/customer cross-reference | — |
| TRANFILE | IDCAMS | VSAM | Load transaction master file | — |
| TRANBKP | IDCAMS | VSAM | Refresh/backup transaction master | — |
| DISCGRP | IDCAMS | VSAM | Load disclosure group file | — |
| TRANCATG | IDCAMS | VSAM | Load transaction category types | — |
| TRANTYPE | IDCAMS | VSAM | Load transaction type file | — |
| TCATBALF | IDCAMS | VSAM | Refresh transaction category balance | — |
| DEFGDGB | IDCAMS | VSAM | Setup GDG bases | — |
| DEFGDGD | IDCAMS | VSAM | Setup GDG bases for DB2 | — |
| ESDSRRDS | IDCAMS | VSAM | Create ESDS and RRDS VSAM files | — |
| POSTTRAN | CBTRN02C | Batch | Core transaction posting | — |
| INTCALC | CBACT04C | Batch | Interest calculation | — |
| COMBTRAN | SORT | Utility | Combine daily + system transactions | — |
| CREASTMT | CBSTM03A | Batch | Produce transaction statement | — |
| TRANREPT | CBTRN03C | Batch | Transaction report (from CICS) | — |
| TRANIDX | IDCAMS | VSAM | Define AIX on transaction file | — |
| OPENFIL | IEFBR14 | Utility | Open VSAM files in CICS | — |
| WAITSTEP | COBSWAIT | Batch | Wait step for given time | — |
| PRTCATBL | — | Report | Print category table | — |
| READACCT | CBACT01C | Batch | Read account file | — |
| READCARD | CBACT02C | Batch | Read card file | — |
| READCUST | CBCUS01C | Batch | Read customer file | — |
| READXREF | CBACT03C | Batch | Read XREF file | — |
| CBEXPORT | CBEXPORT | Batch | Export all data to flat file | — |
| CBIMPORT | CBIMPORT | Batch | Import data from flat file | — |
| CBADMCDJ | — | Admin | Admin command job | — |
| DALYREJS | — | Report | Daily rejects report | — |
| REPTFILE | — | Report | Report file job | — |
| TCATBALF | IDCAMS | VSAM | Transaction category balance refresh | — |
| FTPJCL | FTP | Utility | FTP integration | Optional |
| TXT2PDF1 | — | Utility | Text-to-PDF conversion | Optional |
| INTRDRJ1 | — | Utility | Internal reader (submit job) | Optional |
| INTRDRJ2 | — | Utility | Internal reader variant | Optional |
| CREADB21 | DSNTEP4 | DB2 | Create/load DB2 tables | DB2: Transaction Type Mgmt |
| TRANEXTR | DSNTIAUL | DB2 | Extract transaction types from DB2 | DB2: Transaction Type Mgmt |
| MNTTRDB2 | COBTUPDT | Batch | Maintain transaction type table | DB2: Transaction Type Mgmt |
| CBPAUP0J | CBPAUP0C | Batch | Purge expired authorizations | IMS-DB2-MQ |
| LOADPADB | PAUDBLOD | Batch | Load pending authorization DB | IMS-DB2-MQ |
| UNLDPADB | PAUDBUNL | Batch | Unload pending authorization DB | IMS-DB2-MQ |
| UNLDGSAM | DBUNLDGS | Batch | Unload GSAM DB | IMS-DB2-MQ |
| DBPAUTP0 | — | IMS | IMS DB setup | IMS-DB2-MQ |

## Batch Processing Classification

| Category | Jobs |
|---|---|
| Initialization / Setup | DUSRSECJ, CLOSEFIL, DEFGDGB, DEFGDGD, ESDSRRDS |
| VSAM Load/Refresh | ACCTFILE, CARDFILE, CUSTFILE, XREFFILE, TRANFILE, TRANBKP, DISCGRP, TRANCATG, TRANTYPE, TCATBALF |
| Core Business Processing | POSTTRAN, INTCALC, COMBTRAN, CREASTMT |
| Reporting | TRANREPT, PRTCATBL, DALYREJS, REPTFILE, READACCT, READCARD, READCUST, READXREF |
| File Management | TRANIDX, OPENFIL, WAITSTEP, CBEXPORT, CBIMPORT |
| Optional — DB2 | CREADB21, TRANEXTR, MNTTRDB2 |
| Optional — IMS/MQ | CBPAUP0J, LOADPADB, UNLDPADB, UNLDGSAM, DBPAUTP0 |
| Optional — Utilities | FTPJCL, TXT2PDF1, INTRDRJ1, INTRDRJ2 |

## JCL Procs (app/proc/)

| Proc | Purpose |
|---|---|
| TRANREPT.prc | Transaction report procedure |
| REPROC.prc | Re-processing procedure |

## Sample Compile JCLs (samples/jcl/, samples/proc/)

| Sample | Purpose |
|---|---|
| CICCMP.jcl | Compile CICS programs |
| BATCMP.jcl | Compile batch programs |
| BMSCMP.jcl | Compile BMS maps |
| CICDBCMP.jcl | Compile CICS programs with DB2 |
| IMSMQCMP.jcl | Compile IMS/MQ programs |
| BUILDONL.prc | Build online (CICS) programs |
| BUILDBMS.prc | Build BMS maps |
| BUILDBAT.prc | Build batch programs |
| BLDCIDB2.prc | Build CICS + DB2 programs |
