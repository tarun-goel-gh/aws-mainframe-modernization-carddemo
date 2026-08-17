---
name: atx-docs-status
description: Report the status of the AWS Transform application documentation suite — which of the 31 documents exist, business-function coverage, grounded versus unavailable sections, degraded evidence plans, stale documents, and the SME review queue. Activate when the user asks for documentation status, what documentation is missing, docs coverage, or runs /docs-status.
compatibility: Reads $ATX_DOCS_ROOT or .atx/app-docs-latest/00-manifest/ and .atx/mfre/. Read-only — writes nothing.
license: Apache-2.0
metadata:
  author: tarun.goel
  version: "1.0.0"
  argument-hint: '[--stale] [--gaps]'
  delegates-to: atx-app-documentation
---

# /docs-status

Read-only report. Writes nothing, generates nothing.

## What to do

1. **Locate the suite.** `$ATX_DOCS_ROOT/00-manifest/` if set, else `.atx/app-docs-latest/00-manifest/`.
   When several `.atx/app-docs-*` folders exist, report which run is being read and note that
   others are present. If absent, say documentation has not been
   generated yet and point at `/generate-docs`. Do not build the tree here.

2. **Refresh coverage without writing.** Run the gate in check-only mode so the reported coverage
   is current rather than whatever the last generation recorded:

   ```
   .kiro/skills/atx-app-documentation/scripts/build_coverage.py \
     --mfre .atx/mfre --check-only
   ```

3. **Read the ledger** (`ledger.md`) and the manifest (`manifest.json`).

4. **Report, in this order:**

   - **Coverage headline** — delivered functions of discovered, then documents `n/31`. Coverage
     first: 31 of 31 documents built from 6 of 11 functions is not a complete picture, and the
     document count alone would imply it is.
   - **Per-level table** — level, documents complete / total, unavailable-section count.
   - **Named gaps** — every `pending` and `blocked` document, with the reason for blocked ones.
   - **Degraded plans** — which `atx-*` plans lack evidence and what would restore them, e.g.
     "`analysis/` absent → run `mainframe-reverse-engineering`'s `snapshot_analysis.sh`".
   - **Stale documents** — compare `00-manifest/document-evidence.json`, which records the
     sha256 of every artifact each document actually consumed, against those artifacts on disk.
     A document is stale when any fingerprint no longer matches. An upstream re-run invalidates
     documents silently otherwise.

     ```
     python3 - <<'PY'
     import json, hashlib, os
     root = os.environ.get("ATX_DOCS_ROOT") or ".atx/app-docs-latest"
     d = json.load(open(f"{root}/00-manifest/document-evidence.json"))["documents"]
     def h(p):
         if not os.path.isfile(p): return None
         x = hashlib.sha256()
         for c in iter(lambda: open(p,'rb').read(), b''): break
         return hashlib.sha256(open(p,'rb').read()).hexdigest()
     for doc, arts in sorted(d.items()):
         bad = [p for p, was in arts.items() if os.path.isfile(p) and h(p) != was]
         if bad: print(doc, "STALE via", bad[:3])
     PY
     ```

     Pseudo-paths such as `workspace app/**` carry a fingerprint derived from the measured
     values rather than a file digest, so they participate in the comparison too.
   - **Review queue** — count of generated data-dictionary descriptions awaiting SME sign-off.
     These read as authoritative and were machine-authored, so an unreviewed queue is a risk.

5. `--gaps` reports only unavailable sections and blocked documents. `--stale` reports only the
   staleness comparison.

## Rules

- Freshness: state whether coverage was recomputed this turn or read from the manifest. If read
  from the manifest, say so in past tense and offer to recompute.
- Never estimate a count you did not read. If the ledger disagrees with what is on disk, report
  the disagreement rather than picking one.
- Never write, never generate, never modify `.atx/mfre/`.
