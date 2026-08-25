#!/usr/bin/env python3
"""
build_report.py — recompute extraction-manifest.json's `coverage` block from
extraction-status.csv (never from memory, never from a prior manifest value)
and render the Step 15 close-out report deterministically.

This script never calls the BobZ MCP server. It reads program-inventory.csv,
extraction-status.csv, and extraction-manifest.json, writes the recomputed
coverage block back into the manifest, writes a run-history summary, appends
one line to extraction-log.md, and renders the report to stdout (or
--out-file) — the same "never a bare percentage" requirement as SKILL.md
Step 15: the report always includes the named list of incomplete programs.

Exit codes:
  0  report written and manifest coverage recomputed
  1  ledger or manifest missing or unreadable
  2  bad usage
"""
import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timezone

LEDGER_HEADER = [
    "program_name", "file_path", "language", "dd_generated", "dd_approved",
    "doc_generated", "explain_done", "zcodescan_done", "reviewed_by_sme",
    "batch_id", "notes",
]


def read_ledger(path):
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return [{col: row.get(col, "") for col in LEDGER_HEADER} for row in reader]


def read_inventory_count(path):
    if not os.path.isfile(path):
        return 0
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return sum(1 for _ in csv.DictReader(fh))


def count_dd_review_queue(path):
    total, approved = 0, 0
    if not os.path.isfile(path):
        return total, approved
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
                total += 1
                approved += 1
            elif stripped.startswith("- [ ]"):
                total += 1
    return total, approved


def compute_coverage(ledger, inventory_count):
    # Exact counting rules from SKILL.md Step 15 / F4, updated: doc_generated
    # no longer produces a "P" (partial) value in v2.0.0 — the Autonomous
    # Fallback Path that produced it is retired. A legacy "P" row can still
    # appear if this ledger was started under v1.3.0; it is surfaced
    # separately below and never counted toward docDone or completeness.
    dd_done = sum(1 for r in ledger if r["dd_generated"] == "Y")
    dd_approved = sum(1 for r in ledger if r["dd_approved"] == "Y")
    doc_done = sum(1 for r in ledger if r["doc_generated"] == "Y")
    doc_partial_legacy = sum(1 for r in ledger if r["doc_generated"] == "P")
    explain_done = sum(1 for r in ledger if r["explain_done"] == "Y")
    zcodescan_done = sum(1 for r in ledger if r["zcodescan_done"] == "Y")
    complete = sum(
        1 for r in ledger
        if r["dd_generated"] == "Y" and r["dd_approved"] == "Y" and r["doc_generated"] == "Y"
    )
    return {
        "inventoryCount": inventory_count,
        "ddDone": dd_done,
        "ddApproved": dd_approved,
        "docDone": doc_done,
        "docPartialLegacy": doc_partial_legacy,
        "explainDone": explain_done,
        "zcodescanDone": zcodescan_done,
        "completeProgramCount": complete,
    }


def incomplete_programs(ledger):
    out = []
    for row in ledger:
        if row["dd_generated"] == "Y" and row["dd_approved"] == "Y" and row["doc_generated"] == "Y":
            continue
        pending = []
        for flag in ("dd_generated", "dd_approved", "doc_generated"):
            if row[flag] != "Y":
                pending.append("%s=%s" % (flag, row[flag] or "N"))
        out.append((row["program_name"], pending))
    return out


def render_markdown(batch_id, run_date, coverage, batch_rows, incomplete, dd_queue_total, dd_queue_approved):
    lines = []
    lines.append("# Extraction batch report — %s" % batch_id)
    lines.append("")
    lines.append("Date: %s" % run_date)
    lines.append("")
    total = coverage["inventoryCount"] or 1
    pct = round(100.0 * coverage["completeProgramCount"] / total, 1)
    lines.append("## Coverage")
    lines.append("")
    lines.append("`%d/%d complete (%.1f%%)`" % (
        coverage["completeProgramCount"], coverage["inventoryCount"], pct))
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|---|---|")
    lines.append("| Inventory total | %d |" % coverage["inventoryCount"])
    lines.append("| ddDone | %d |" % coverage["ddDone"])
    lines.append("| ddApproved | %d |" % coverage["ddApproved"])
    lines.append("| docDone | %d |" % coverage["docDone"])
    if coverage["docPartialLegacy"]:
        lines.append("| docPartialLegacy (retired flag, carried from a pre-v2.0.0 run) | %d |"
                      % coverage["docPartialLegacy"])
    lines.append("| explainDone | %d |" % coverage["explainDone"])
    lines.append("| zcodescanDone | %d |" % coverage["zcodescanDone"])
    lines.append("| completeProgramCount | %d |" % coverage["completeProgramCount"])
    lines.append("")
    lines.append("## Programs processed in batch `%s`" % batch_id)
    lines.append("")
    if batch_rows:
        lines.append("| Program | dd_generated | dd_approved | doc_generated | explain_done | zcodescan_done |")
        lines.append("|---|---|---|---|---|---|")
        for row in batch_rows:
            lines.append("| %s | %s | %s | %s | %s | %s |" % (
                row["program_name"], row["dd_generated"] or "N", row["dd_approved"] or "N",
                row["doc_generated"] or "N", row["explain_done"] or "N", row["zcodescan_done"] or "N"))
    else:
        lines.append("_No ledger rows carry batch_id=%s._" % batch_id)
    lines.append("")
    lines.append("## Data dictionary review queue")
    lines.append("")
    lines.append("%d entries queued, %d approved, %d awaiting SME sign-off." % (
        dd_queue_total, dd_queue_approved, dd_queue_total - dd_queue_approved))
    lines.append("")
    lines.append("## Programs not yet complete (%d)" % len(incomplete))
    lines.append("")
    if incomplete:
        for program, pending in incomplete:
            lines.append("- **%s** — %s" % (program, ", ".join(pending)))
    else:
        lines.append("_None — every inventory program is complete._")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(prog="build_report.py")
    parser.add_argument("--extraction-root", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--date", default=None,
                         help="YYYY-MM-DD, from conversation context — pass explicitly; "
                              "the script's own fallback is the system clock, not context")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out-file", default=None,
                         help="write the rendered report here instead of stdout")
    args = parser.parse_args()

    extraction_root = os.path.abspath(args.extraction_root)
    manifest_dir = os.path.join(extraction_root, "00-manifest")
    ledger_path = os.path.join(manifest_dir, "extraction-status.csv")
    inventory_path = os.path.join(manifest_dir, "program-inventory.csv")
    manifest_path = os.path.join(manifest_dir, "extraction-manifest.json")

    ledger = read_ledger(ledger_path)
    if ledger is None:
        print("build_report.py: extraction-status.csv missing under %s" % manifest_dir, file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(manifest_path):
        print("build_report.py: extraction-manifest.json missing under %s" % manifest_dir, file=sys.stderr)
        sys.exit(1)
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except json.JSONDecodeError as exc:
        print("build_report.py: extraction-manifest.json unreadable: %s" % exc, file=sys.stderr)
        sys.exit(1)

    run_date = args.date
    if not run_date:
        run_date = date.today().isoformat()
        print("build_report.py: WARNING — no --date given; using system date %s. "
              "The skill must pass the conversation's context date explicitly." % run_date, file=sys.stderr)

    inventory_count = read_inventory_count(inventory_path)
    coverage = compute_coverage(ledger, inventory_count)
    manifest["coverage"] = coverage
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    batch_rows = [r for r in ledger if r.get("batch_id") == args.batch_id]
    incomplete = incomplete_programs(ledger)
    dd_queue_path = os.path.join(extraction_root, "17-qa-validation", "dd-review-queue.md")
    dd_total, dd_approved = count_dd_review_queue(dd_queue_path)

    report_md = render_markdown(args.batch_id, run_date, coverage, batch_rows, incomplete, dd_total, dd_approved)

    run_history_dir = os.path.join(manifest_dir, "run-history")
    os.makedirs(run_history_dir, exist_ok=True)
    summary_path = os.path.join(run_history_dir, "%s-%s-summary.md" % (run_date, args.batch_id))
    with open(summary_path, "w", encoding="utf-8") as fh:
        fh.write(report_md)

    log_path = os.path.join(manifest_dir, "extraction-log.md")
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write("\n[%s] build_report.py: batch %s closed — %d/%d complete (%s)\n" % (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), args.batch_id,
            coverage["completeProgramCount"], coverage["inventoryCount"],
            summary_path.replace(os.sep, "/")))

    if args.out_file:
        with open(args.out_file, "w", encoding="utf-8") as fh:
            fh.write(report_md)
    elif not args.json:
        print(report_md)

    if args.json:
        print(json.dumps({
            "coverage": coverage,
            "batchId": args.batch_id,
            "date": run_date,
            "summaryPath": summary_path.replace(os.sep, "/"),
            "outFile": args.out_file,
            "incompleteCount": len(incomplete),
        }, indent=2))

    sys.exit(0)


if __name__ == "__main__":
    main()
