# batch-1 Run Summary — 2025-07-15

- **Mode**: EXECUTE — auto-approved
- **Application**: CardDemo
- **Batch ID**: batch-1
- **Date**: 2025-07-15
- **Programs in batch**: 46

## Pass Results

| Program | DD | Doc | Explain | Z Scan |
|---|---|---|---|---|
| 31 core COBOL (app/cbl) | ❌ pending | ⚠ partial | ❌ pending | ❌ pending |
| 13 optional COBOL (app-*/cbl) | ❌ pending | ❌ pending | ❌ pending | ❌ pending |
| 2 HLASM (app/asm) | ❌ pending | ❌ pending | ❌ pending | ❌ pending |

## Coverage: 0/46 complete (0%)
(Complete = dd_generated=Y AND dd_approved=Y AND doc_generated=Y)

## What was accomplished this batch
- Local scanner database created (44 files scanned)
- Paragraph index: 610 paragraphs across 31 programs
- Dependency graph: program calls, file access, copybook includes (all tool-verified)
- Application architecture document
- CICS transaction / BMS map cross-walk
- VSAM file structures
- JCL job-to-program map
- Complexity metrics and quality ranking

## DD Review Queue
0 entries — Generate data dictionary not yet run.

## What's next (batch-2)
1. Run Generate data dictionary workflow for all 44 COBOL programs
2. Run Generate documentation (architect + developer + business) for all 44 programs
3. Run Explain code for top 5 by complexity
4. Run Z Code Scan for all 46 programs
