#!/usr/bin/env python3
"""
verify_extraction.py — Gate G4, deterministic half. For every ledger row
that claims a capability is done (flag = Y), confirm the artifact it claims
actually exists on disk. Reconciles program-inventory.csv against
extraction-status.csv (rows present in one but not the other). Checks that
every dependency provenance label is one of the three allowed values and
never mixed within a single entry.

This script never calls the BobZ MCP server and never mutates a ledger
flag itself — flag correction is the agent's job after reading the report.

Exit codes:
  0  clean — every check passed
  1  at least one defect found
  2  bad usage
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

INVENTORY_HEADER = [
    "program_name", "file_path", "language", "size_bytes",
    "line_count", "status", "in_scope",
]
LEDGER_HEADER = [
    "program_name", "file_path", "language", "dd_generated", "dd_approved",
    "doc_generated", "explain_done", "zcodescan_done", "reviewed_by_sme",
    "batch_id", "notes",
]
ALLOWED_PROVENANCE = {
    "tool-verified",
    "narrative-per-program-not-tool-verified",
    "z-understand-verified",
}


def read_csv(path, header):
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return [{col: row.get(col, "") for col in header} for row in reader]


def dd_artifact(extraction_root, program):
    path = os.path.join(extraction_root, "03-data-structures", "data-dictionary",
                         "by-program", "%s-DD.json" % program)
    if not os.path.isfile(path):
        return False, "%s missing" % path
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return False, "%s unreadable: %s" % (path, exc)
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not entries:
        return False, "%s has no entries" % path
    return True, None


def doc_artifacts(extraction_root, program):
    required = [
        os.path.join(extraction_root, "01-application-architecture", "%s-arch.md" % program),
        os.path.join(extraction_root, "02-business-rules", "by-program", "%s.md" % program),
        os.path.join(extraction_root, "10-error-handling", "exception-paths-by-program", "%s.md" % program),
    ]
    missing = [p for p in required if not os.path.isfile(p)]
    return (len(missing) == 0), missing


def explain_artifact(extraction_root, program):
    candidates = [
        os.path.join(extraction_root, "02-business-rules", "by-program", "%s.md" % program),
        os.path.join(extraction_root, "01-application-architecture", "%s-arch.md" % program),
    ]
    return any(os.path.isfile(p) for p in candidates), candidates


def zcodescan_artifact(extraction_root, program):
    path = os.path.join(extraction_root, "11-code-quality", "zcodescan-findings", "%s.json" % program)
    return os.path.isfile(path), path


def check_dependency_provenance(extraction_root):
    path = os.path.join(extraction_root, "05-dependencies", "internal-dependencies.json")
    defects = []
    if not os.path.isfile(path):
        return defects  # absent is fine if no dependency pass has run yet
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return [{"kind": "dependency-file-unreadable", "detail": str(exc)}]
    entries = payload if isinstance(payload, list) else payload.get("entries", [])
    for idx, entry in enumerate(entries):
        provenance = entry.get("provenance") if isinstance(entry, dict) else None
        if isinstance(provenance, list):
            defects.append({"kind": "mixed-provenance", "index": idx, "entry": entry})
        elif provenance not in ALLOWED_PROVENANCE:
            defects.append({"kind": "invalid-provenance", "index": idx, "provenance": provenance, "entry": entry})
    return defects


def main():
    parser = argparse.ArgumentParser(prog="verify_extraction.py")
    parser.add_argument("--extraction-root", required=True)
    parser.add_argument("--batch-id", default=None,
                         help="limit the check to rows carrying this batch_id")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check-only", action="store_true",
                         help="evaluate and print the verdict; write nothing")
    args = parser.parse_args()

    extraction_root = os.path.abspath(args.extraction_root)
    manifest_dir = os.path.join(extraction_root, "00-manifest")
    inventory_path = os.path.join(manifest_dir, "program-inventory.csv")
    ledger_path = os.path.join(manifest_dir, "extraction-status.csv")

    inventory = read_csv(inventory_path, INVENTORY_HEADER)
    ledger = read_csv(ledger_path, LEDGER_HEADER)
    if inventory is None or ledger is None:
        print("verify_extraction.py: program-inventory.csv or extraction-status.csv missing under %s"
              % manifest_dir, file=sys.stderr)
        sys.exit(2)

    inventory_names = {row["program_name"] for row in inventory}
    ledger_names = {row["program_name"] for row in ledger}

    defects = []

    only_in_inventory = sorted(inventory_names - ledger_names)
    only_in_ledger = sorted(ledger_names - inventory_names)
    if only_in_inventory:
        defects.append({"kind": "in-inventory-not-in-ledger", "programs": only_in_inventory})
    if only_in_ledger:
        defects.append({"kind": "in-ledger-not-in-inventory", "programs": only_in_ledger})

    rows = ledger
    if args.batch_id:
        rows = [r for r in ledger if r.get("batch_id") == args.batch_id]

    checked = {"dd_generated": 0, "doc_generated": 0, "explain_done": 0, "zcodescan_done": 0}
    for row in rows:
        program = row["program_name"]
        if row.get("dd_generated") == "Y":
            checked["dd_generated"] += 1
            ok, detail = dd_artifact(extraction_root, program)
            if not ok:
                defects.append({"kind": "dd_generated=Y-without-artifact", "program": program, "detail": detail})
        if row.get("doc_generated") == "Y":
            checked["doc_generated"] += 1
            ok, missing = doc_artifacts(extraction_root, program)
            if not ok:
                defects.append({"kind": "doc_generated=Y-without-artifact", "program": program, "missing": missing})
        if row.get("explain_done") == "Y":
            checked["explain_done"] += 1
            ok, candidates = explain_artifact(extraction_root, program)
            if not ok:
                defects.append({"kind": "explain_done=Y-without-artifact", "program": program, "checked": candidates})
        if row.get("zcodescan_done") == "Y":
            checked["zcodescan_done"] += 1
            ok, path = zcodescan_artifact(extraction_root, program)
            if not ok:
                defects.append({"kind": "zcodescan_done=Y-without-artifact", "program": program, "expected": path})

    defects.extend(check_dependency_provenance(extraction_root))

    verdict = {
        "verifiedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "extractionRoot": extraction_root.replace(os.sep, "/"),
        "batchId": args.batch_id,
        "rowsChecked": len(rows),
        "flagsChecked": checked,
        "defectCount": len(defects),
        "defects": defects,
        "clean": len(defects) == 0,
    }

    if not args.check_only:
        os.makedirs(manifest_dir, exist_ok=True)
        with open(os.path.join(manifest_dir, "verification.json"), "w", encoding="utf-8") as fh:
            json.dump(verdict, fh, indent=2)
        qa_dir = os.path.join(extraction_root, "17-qa-validation")
        os.makedirs(qa_dir, exist_ok=True)
        with open(os.path.join(qa_dir, "validation-report.md"), "a", encoding="utf-8") as fh:
            fh.write("\n## Verification run — %s\n" % verdict["verifiedAt"])
            fh.write("Batch: %s · Rows checked: %d · Defects: %d\n\n" % (
                args.batch_id or "(all)", len(rows), len(defects)))
            for defect in defects:
                fh.write("- **%s** — %s\n" % (defect.get("kind"), json.dumps(defect)))

    if args.json:
        print(json.dumps(verdict, indent=2))
    else:
        print("verify_extraction.py: %d row(s) checked, %d defect(s)%s" % (
            len(rows), len(defects), " — CLEAN" if not defects else ""))
        for defect in defects:
            detail = {k: v for k, v in defect.items() if k != "kind"}
            print("  - %s: %s" % (defect.get("kind"), detail))

    sys.exit(0 if not defects else 1)


if __name__ == "__main__":
    main()
