#!/usr/bin/env python3
"""
build_inventory.py — scan a resolved source scope and write/reconcile
00-manifest/program-inventory.csv and 00-manifest/extraction-status.csv
for the cobol-knowledge-extraction skill (BobZ v3, MCP-direct).

Pure filesystem walk and classification. This script never calls the BobZ
MCP server — only the agent does that, per SKILL.md Step 8. Reconciliation
means: add rows for programs newly in scope, never drop or reorder an
existing row, never touch an existing row's status or ledger flag columns.

Exit codes:
  0  inventory/ledger written or reconciled
  1  no source files found in scope
  2  bad usage
"""
import argparse
import csv
import glob
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

# Extension -> language map, exactly the table in SKILL.md Step 1.
LANGUAGE_EXTENSIONS = {
    ".cbl": "COBOL", ".cob": "COBOL", ".cobol": "COBOL",
    ".cpy": "COBOL copybook", ".copy": "COBOL copybook",
    ".pli": "PL/I", ".pl1": "PL/I",
    ".inc": "PL/I include",
    ".jcl": "JCL", ".prc": "JCL", ".proc": "JCL",
    ".rex": "REXX", ".rexx": "REXX",
    ".asm": "Assembler (HLASM)", ".hlasm": "Assembler (HLASM)", ".mlc": "Assembler (HLASM)",
    ".csd": "CICS resources",
    ".bms": "BMS maps",
}


def load_language_map(config_path):
    mapping = dict(LANGUAGE_EXTENSIONS)
    if config_path:
        try:
            with open(config_path, "r", encoding="utf-8") as fh:
                override = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print("build_inventory.py: cannot read --languages-config %s: %s" % (config_path, exc),
                  file=sys.stderr)
            sys.exit(2)
        if not isinstance(override, dict):
            print("build_inventory.py: --languages-config must be a JSON object of extension -> language",
                  file=sys.stderr)
            sys.exit(2)
        for ext, lang in override.items():
            mapping[ext.lower()] = lang
    return mapping


def classify(path, language_map):
    ext = os.path.splitext(path)[1].lower()
    return language_map.get(ext)


def to_forward_slash(path):
    return path.replace(os.sep, "/")


def program_name_of(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    return stem.upper()


def count_lines(abs_path):
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def walk_folder(root):
    found = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            found.append(os.path.join(dirpath, name))
    return found


def resolve_scope(scope, workspace_root):
    """Return (input_mode, list_of_absolute_file_paths, explicit_rows_or_None).

    explicit_rows_or_None is only populated for the inventory-csv branch, where
    the CSV itself is the authoritative program list (rows are used as-is —
    SKILL.md Step 1, precedence #1).
    """
    if not scope:
        if not os.path.isdir(workspace_root):
            print("build_inventory.py: --workspace-root %s does not exist" % workspace_root, file=sys.stderr)
            sys.exit(2)
        return "workspace", walk_folder(workspace_root), None

    candidate = scope if os.path.isabs(scope) else os.path.join(workspace_root, scope)

    if scope.lower().endswith(".csv"):
        csv_path = scope if os.path.isfile(scope) else candidate
        if not os.path.isfile(csv_path):
            print("build_inventory.py: inventory CSV not found: %s" % scope, file=sys.stderr)
            sys.exit(2)
        with open(csv_path, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None or "program_name" not in reader.fieldnames:
                print("build_inventory.py: %s has no program_name column" % csv_path, file=sys.stderr)
                sys.exit(2)
            rows = list(reader)
        return "inventory-csv", [], rows

    if scope.startswith("@"):
        list_path = scope[1:]
        list_path = list_path if os.path.isfile(list_path) else os.path.join(workspace_root, list_path)
        if not os.path.isfile(list_path):
            print("build_inventory.py: file list not found: %s" % scope[1:], file=sys.stderr)
            sys.exit(2)
        files = []
        with open(list_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                files.append(line if os.path.isabs(line) else os.path.join(workspace_root, line))
        return "file-list", files, None

    if any(ch in scope for ch in "*?["):
        pattern = scope if os.path.isabs(scope) else os.path.join(workspace_root, scope)
        matches = sorted(
            set(glob.glob(pattern, recursive=True))
            | set(glob.glob(os.path.join(workspace_root, "**", scope), recursive=True))
        )
        return "glob", [m for m in matches if os.path.isfile(m)], None

    if os.path.isdir(candidate):
        return "folder", walk_folder(candidate), None

    if os.path.isfile(candidate):
        return "file-list", [candidate], None

    print("build_inventory.py: scope not found: %s" % scope, file=sys.stderr)
    sys.exit(2)


def find_by_stem(workspace_root, program_name):
    target = program_name.lower()
    for dirpath, _dirnames, filenames in os.walk(workspace_root):
        for name in filenames:
            if os.path.splitext(name)[0].lower() == target:
                return os.path.join(dirpath, name)
    return None


def read_existing_csv(path, header):
    rows = []
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows.append({col: row.get(col, "") for col in header})
    return rows


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in header})


def main():
    parser = argparse.ArgumentParser(
        prog="build_inventory.py",
        description="Scan a resolved source scope and write/reconcile program-inventory.csv "
                     "and extraction-status.csv for cobol-knowledge-extraction. Never calls MCP.",
    )
    parser.add_argument("--scope", default=None,
                         help="PATH|@FILELIST|INVENTORY.CSV|GLOB — default: workspace root")
    parser.add_argument("--workspace-root", default=os.getcwd())
    parser.add_argument("--extraction-root", default=None,
                         help="default: <workspace-root>/bob-z-knowledge-extract")
    parser.add_argument("--out-dir", default=None,
                         help="default: <extraction-root>/00-manifest")
    parser.add_argument("--languages-config", default=None,
                         help="default: built-in extension map, SKILL.md Step 1")
    parser.add_argument("--dry-run", action="store_true", help="print counts, write nothing")
    parser.add_argument("--json", action="store_true", help="emit summary JSON to stdout")
    args = parser.parse_args()

    workspace_root = os.path.abspath(args.workspace_root)
    extraction_root = (os.path.abspath(args.extraction_root) if args.extraction_root
                        else os.path.join(workspace_root, "bob-z-knowledge-extract"))
    out_dir = os.path.abspath(args.out_dir) if args.out_dir else os.path.join(extraction_root, "00-manifest")

    language_map = load_language_map(args.languages_config)
    input_mode, files, explicit_rows = resolve_scope(args.scope, workspace_root)

    discovered = {}  # program_name -> row dict

    if input_mode == "inventory-csv":
        for row in explicit_rows:
            program_name = row.get("program_name", "").strip().upper()
            if not program_name:
                continue
            file_path = (row.get("file_path") or "").strip()
            abs_path = None
            if file_path:
                abs_path = file_path if os.path.isabs(file_path) else os.path.join(workspace_root, file_path)
            if not abs_path or not os.path.isfile(abs_path):
                found = find_by_stem(workspace_root, program_name)
                if found:
                    abs_path = found
            language = (row.get("language") or "").strip()
            size_bytes = (row.get("size_bytes") or "").strip()
            line_count = (row.get("line_count") or "").strip()
            if abs_path and os.path.isfile(abs_path):
                file_path = to_forward_slash(os.path.relpath(abs_path, workspace_root))
                language = language or classify(abs_path, language_map) or "unknown"
                size_bytes = size_bytes or str(os.path.getsize(abs_path))
                line_count = line_count or str(count_lines(abs_path))
            else:
                print("build_inventory.py: WARNING — no source file found on disk for %s "
                      "(row kept with file_path as given in the CSV)" % program_name, file=sys.stderr)
                language = language or "unknown"
                size_bytes = size_bytes or "0"
                line_count = line_count or "0"
            discovered[program_name] = {
                "program_name": program_name, "file_path": file_path,
                "language": language, "size_bytes": size_bytes,
                "line_count": line_count, "status": "pending", "in_scope": "true",
            }
    else:
        for abs_path in files:
            if not os.path.isfile(abs_path):
                continue
            language = classify(abs_path, language_map)
            if language is None:
                continue
            program_name = program_name_of(abs_path)
            file_path = to_forward_slash(os.path.relpath(abs_path, workspace_root))
            if program_name in discovered and discovered[program_name]["file_path"] != file_path:
                print("build_inventory.py: WARNING — duplicate program_name %s at %s and %s; "
                      "keeping the first occurrence"
                      % (program_name, discovered[program_name]["file_path"], file_path), file=sys.stderr)
                continue
            discovered[program_name] = {
                "program_name": program_name, "file_path": file_path,
                "language": language, "size_bytes": str(os.path.getsize(abs_path)),
                "line_count": str(count_lines(abs_path)), "status": "pending",
                "in_scope": "true",
            }

    if not discovered:
        print("build_inventory.py: no source files found in scope", file=sys.stderr)
        sys.exit(1)

    inventory_path = os.path.join(out_dir, "program-inventory.csv")
    ledger_path = os.path.join(out_dir, "extraction-status.csv")

    existing_inventory = read_existing_csv(inventory_path, INVENTORY_HEADER)
    existing_by_name = {r["program_name"] for r in existing_inventory}

    new_count = 0
    final_inventory = list(existing_inventory)
    for name in sorted(discovered):
        if name in existing_by_name:
            continue  # never overwrite an existing row/status
        final_inventory.append(discovered[name])
        new_count += 1

    existing_ledger = read_existing_csv(ledger_path, LEDGER_HEADER)
    existing_ledger_names = {r["program_name"] for r in existing_ledger}
    final_ledger = list(existing_ledger)
    for name in sorted(discovered):
        if name in existing_ledger_names:
            continue  # never touch an existing row's flags
        row = discovered[name]
        final_ledger.append({
            "program_name": name, "file_path": row["file_path"], "language": row["language"],
            "dd_generated": "N", "dd_approved": "N", "doc_generated": "N",
            "explain_done": "N", "zcodescan_done": "N", "reviewed_by_sme": "N",
            "batch_id": "", "notes": "",
        })

    summary = {
        "inputMode": input_mode,
        "workspaceRoot": to_forward_slash(workspace_root),
        "extractionRoot": to_forward_slash(extraction_root),
        "inventoryPath": to_forward_slash(inventory_path),
        "ledgerPath": to_forward_slash(ledger_path),
        "discoveredThisRun": len(discovered),
        "newInventoryRows": new_count,
        "existingInventoryRows": len(existing_inventory),
        "totalInventoryRows": len(final_inventory),
        "languagesPresent": sorted({row["language"] for row in discovered.values()}),
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    if args.dry_run:
        summary["dryRun"] = True
    else:
        write_csv(inventory_path, INVENTORY_HEADER, final_inventory)
        write_csv(ledger_path, LEDGER_HEADER, final_ledger)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("build_inventory.py: %s mode, %d discovered, %d new row(s), %d total row(s)%s" % (
            input_mode, len(discovered), new_count, len(final_inventory),
            " (dry-run — nothing written)" if args.dry_run else ""))

    sys.exit(0)


if __name__ == "__main__":
    main()
