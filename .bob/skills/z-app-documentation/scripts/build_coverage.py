#!/usr/bin/env python3
"""Step 2 — prerequisite gate and per-program coverage matrix for z-app-documentation.

Usage:
  build_coverage.py --workspace-root DIR
                     [--extraction-root DIR] [--docs-root DIR] [--probe-file FILE]
                     [--out-dir DIR] [--json] [--check-only]

Exit codes: 0 prerequisites met | 1 a hard prerequisite failed | 2 bad usage

Reads the MCP capability probe (`.bob/skills/_design/bobz-v3-foundations.md` §2c) and the program
inventory the `cobol-knowledge-extraction` skill's `build_inventory.py` produces (or a prior
doc-only run's own copy of it), and answers one question before any document is written: **for
each program, what evidence already exists, and what still needs an MCP tool call?**

BobZ has no business-function discovery step, so the denominator here is programs, not business
functions: every count in `coverage.md` is `<class count> of <inventory count>` programs, never a
bare percentage.

No third-party dependencies.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

# The three-value provenance vocabulary this suite's evidence pack uses (bobz-v3-foundations.md
# §3). Referenced here only for the coverage report's soft-degrade language, never enforced by
# this script — extract_evidence.py and generate_docs.py are the scripts that actually assign it.
PROVENANCE_VALUES = {
    "tool-verified",
    "narrative-per-program-not-tool-verified",
    "z-understand-verified",
}

# Which Z evidence plans (references/evidence-plans.md) consume which by-program artifact kind.
# Used only to annotate evidence-index.json; it has no bearing on classification.
ARTIFACT_PLANS = {
    "dd":       ["z-data", "z-module"],
    "rules":    ["z-business", "z-module"],
    "arch":     ["z-structure", "z-module"],
    "errh":     ["z-quality", "z-api"],
    "zcs":      ["z-quality"],
    "paras":    ["z-module"],
    "cfg":      ["z-module", "z-structure"],
}


def sha256(path: str) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def md_escape(s) -> str:
    return str(s).replace("|", r"\|")


def truthy(s, default: bool = True) -> bool:
    """Interpret an `in_scope`-style CSV cell. Missing/blank defaults to True — the reconciled
    `program-inventory.csv` schema (bobz-v3-foundations.md §5a) notes that a producer which never
    scopes to a subset still writes `in_scope=true` for every row; an absent column on an older
    row should not silently exclude that program from the run."""
    if s is None:
        return default
    v = str(s).strip().lower()
    if v == "":
        return default
    return v in ("true", "yes", "y", "1")


def read_csv_rows(path: str) -> list[dict]:
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))


def load_json(path: str):
    """Return (obj, error). error is None on success."""
    if not os.path.isfile(path):
        return None, f"not found: {path}"
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), None
    except (ValueError, OSError) as e:
        return None, f"{path}: {e}"


def default_docs_root(workspace_root: str) -> str:
    """See generate-docs/SKILL.md and docs-status/SKILL.md: both pass the same $BOBZ_DOCS_ROOT
    (or the conventional default) to every script in this suite so one run lands in one folder."""
    return os.environ.get("BOBZ_DOCS_ROOT") or os.path.join(workspace_root, "bob-z-app-docs")


def resolve_manifest_dir(extraction_root: str | None, docs_root: str) -> str | None:
    """Locate the directory holding `program-inventory.csv`.

    Precedence: a reused `cobol-knowledge-extraction` run first (SKILL.md Step 0.1: "in
    `bob-z-knowledge-extract/00-manifest/` or under this skill's `docsRoot`"), then this skill's
    own manifest directory for a doc-only run with no upstream extraction at all.
    """
    candidates = []
    if extraction_root:
        candidates.append(os.path.join(extraction_root, "00-manifest"))
    candidates.append(os.path.join(docs_root, "00-manifest"))
    for c in candidates:
        if os.path.isfile(os.path.join(c, "program-inventory.csv")):
            return c
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", default=".", help="the folder the IDE has open")
    ap.add_argument("--extraction-root", default=None,
                     help="upstream cobol-knowledge-extraction run "
                          "(default: <workspace-root>/bob-z-knowledge-extract, if present)")
    ap.add_argument("--docs-root", default=None,
                     help="documentation output root "
                          "(default: $BOBZ_DOCS_ROOT or <workspace-root>/bob-z-app-docs)")
    ap.add_argument("--probe-file", default=None,
                     help="MCP capability probe (default: <docs-root>/00-manifest/"
                          "mcp-capability-probe.json)")
    ap.add_argument("--out-dir", default=None,
                     help="manifest directory (default: <docs-root>/00-manifest)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check-only", action="store_true",
                     help="evaluate prerequisites and print the verdict; write nothing")
    args = ap.parse_args()

    workspace_root = args.workspace_root
    extraction_root = args.extraction_root
    if extraction_root is None:
        cand = os.path.join(workspace_root, "bob-z-knowledge-extract")
        extraction_root = cand if os.path.isdir(cand) else None
    docs_root = args.docs_root or default_docs_root(workspace_root)
    probe_file = args.probe_file or os.path.join(docs_root, "00-manifest",
                                                  "mcp-capability-probe.json")
    out_dir = args.out_dir or os.path.join(docs_root, "00-manifest")

    blockers: list[str] = []
    degraded: list[dict] = []

    # ---- hard prerequisite 1/3: the MCP reachability probe ----
    probe, perr = load_json(probe_file)
    mcp_reachable = False
    advanced_mode = False
    z_understand = False
    if perr:
        blockers.append(f"MCP capability probe unreadable ({perr}) — run the MCP reachability "
                         f"probe (bobz-v3-foundations.md §2) before generating documentation")
        probe = {}
    else:
        mcp_reachable = probe.get("mcpReachable") is True
        if not mcp_reachable:
            blockers.append(f"mcpReachable is {probe.get('mcpReachable')!r} in {probe_file} — "
                             f"the BobZ MCP server did not answer the reachability probe; drop to "
                             f"PLAN mode, there is no fallback path in this version")
        # ---- hard prerequisite 2/3: Advanced mode ----
        advanced_mode = probe.get("advancedMode") is True
        if not advanced_mode:
            blockers.append(f"advancedMode is {probe.get('advancedMode')!r} in {probe_file} — "
                             f"Advanced mode is required for this skill to run at all")
        z_understand = probe.get("zUnderstandConfigured") is True

    # ---- hard prerequisite 3/3: program-inventory.csv, present, >=1 row ----
    manifest_dir = resolve_manifest_dir(extraction_root, docs_root)
    inv_rows: list[dict] = []
    status_rows: dict[str, dict] = {}
    manifest_obj = {}
    if manifest_dir is None:
        searched = [os.path.join(extraction_root, "00-manifest")] if extraction_root else []
        searched.append(os.path.join(docs_root, "00-manifest"))
        blockers.append("no program-inventory.csv found — searched: " + "; ".join(searched))
    else:
        inv_rows = read_csv_rows(os.path.join(manifest_dir, "program-inventory.csv"))
        if not inv_rows:
            blockers.append(f"program-inventory.csv at {manifest_dir} is present but has zero rows")
        status_path = os.path.join(manifest_dir, "extraction-status.csv")
        for r in read_csv_rows(status_path):
            n = (r.get("program_name") or "").strip()
            if n:
                status_rows[n] = r
        if not status_rows:
            degraded.append({
                "missing": os.path.relpath(status_path),
                "plansAffected": ["all"],
                "lost": "no cobol-knowledge-extraction ledger — every in-scope program starts "
                        "cold; there is no reused dd_generated/doc_generated evidence to classify "
                        "'reused-from-extraction' against",
            })
        manifest_json_path = os.path.join(manifest_dir, "extraction-manifest.json")
        manifest_obj, merr = load_json(manifest_json_path)
        if merr:
            degraded.append({"missing": os.path.relpath(manifest_json_path),
                             "plansAffected": ["all"],
                             "lost": "extraction run environment/capability context "
                                     f"(unreadable: {merr})"})
            manifest_obj = {}

    if not extraction_root:
        degraded.append({
            "missing": "bob-z-knowledge-extract/",
            "plansAffected": ["all"],
            "lost": "no reuse — every program's evidence pass starts cold",
        })
    if manifest_dir and not z_understand:
        degraded.append({
            "missing": "zUnderstandConfigured (server not configured)",
            "plansAffected": ["z-integration", "z-structure"],
            "lost": "dependency data stays narrative-per-program-not-tool-verified; every "
                    "get_project_* backed plan degrades",
        })

    # ---- classify every inventoried program ----
    rows = []
    class_counts = {"reused-from-extraction": 0, "needs-evidence-pass": 0, "no-source-in-scope": 0}
    for r in sorted(inv_rows, key=lambda r: (r.get("program_name") or "")):
        name = (r.get("program_name") or "").strip()
        if not name:
            continue
        in_scope = truthy(r.get("in_scope"))
        st = status_rows.get(name) or {}
        dd_y = (st.get("dd_generated") or "").strip().upper() == "Y"
        doc_y = (st.get("doc_generated") or "").strip().upper() == "Y"
        if not in_scope:
            cls = "no-source-in-scope"
        elif dd_y and doc_y:
            cls = "reused-from-extraction"
        else:
            cls = "needs-evidence-pass"
        class_counts[cls] += 1
        rows.append({
            "program_name": name,
            "file_path": r.get("file_path"),
            "language": r.get("language"),
            "line_count": r.get("line_count"),
            "in_scope": in_scope,
            "class": cls,
            "dd_generated": st.get("dd_generated") or "N",
            "dd_approved": st.get("dd_approved") or "N",
            "doc_generated": st.get("doc_generated") or "N",
            "explain_done": st.get("explain_done") or "N",
            "zcodescan_done": st.get("zcodescan_done") or "N",
            "batch_id": st.get("batch_id"),
            "notes": st.get("notes"),
        })

    in_scope_rows = [r for r in rows if r["in_scope"]]
    complete_evidence = sum(1 for r in in_scope_rows if r["class"] == "reused-from-extraction")

    # Deliberately a *degraded* consequence, not a fifth hard blocker: `generate-docs/SKILL.md`,
    # `docs-status/SKILL.md` and this suite's own `SKILL.md` all commit to exactly three exit-1
    # reasons (probe, inventory, Advanced mode). A run where every in-scope program still needs an
    # evidence pass is a normal, reportable state — build_coverage.py's job is to say so loudly,
    # not to block the agent from going and gathering that evidence.
    if in_scope_rows and complete_evidence == 0:
        degraded.append({
            "missing": "reused extraction evidence",
            "plansAffected": ["all"],
            "lost": f"0 of {len(in_scope_rows)} in-scope programs have both dd_generated=Y and "
                    f"doc_generated=Y — every in-scope program needs a fresh MCP evidence pass "
                    f"before generate_docs.py can ground anything beyond inventory-level facts",
        })

    verdict = "blocked" if blockers else "ok"
    summary = {
        "verdict": verdict,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workspaceRoot": workspace_root,
        "extractionRoot": extraction_root,
        "docsRoot": docs_root,
        "probeFile": probe_file,
        "mcp": {
            "reachable": mcp_reachable,
            "advancedMode": advanced_mode,
            "zUnderstandConfigured": z_understand,
            "serverVersion": (probe or {}).get("mcpServerVersion"),
        },
        "counts": {
            "inventory": len(rows),
            "inScope": len(in_scope_rows),
            **class_counts,
            "completeEvidencePairs": complete_evidence,
        },
        "blockers": blockers,
        "degraded": degraded,
        "programs": rows,
    }

    if args.check_only or args.json:
        print(json.dumps(summary, indent=2))
    if args.check_only:
        return 1 if blockers else 0

    if blockers:
        for b in blockers:
            print(f"BLOCKED: {b}", file=sys.stderr)
        print("\nFix the upstream run before generating documentation.", file=sys.stderr)
        return 1

    # ---- write coverage.md + evidence-index.json ----
    os.makedirs(out_dir, exist_ok=True)
    c = summary["counts"]
    lines = [
        "# Coverage",
        "",
        f"Inventory: **{c['inventory']}** programs · in scope: **{c['inScope']}** · "
        f"reused from extraction: **{c['reused-from-extraction']}** · "
        f"needs an evidence pass: **{c['needs-evidence-pass']}** · "
        f"out of scope: **{c['no-source-in-scope']}**",
        "",
        f"BobZ has no business-function discovery step; the denominator here is programs. Every "
        f"count in this suite carries `of {c['inventory']}`.",
        "",
        "| Program | Language | Class | dd | doc | explain | zcodescan | Lines |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {md_escape(r['program_name'])} | {r['language'] or '—'} | `{r['class']}` | "
            f"{r['dd_generated']} | {r['doc_generated']} | {r['explain_done']} | "
            f"{r['zcodescan_done']} | {r['line_count'] or '—'} |")

    lines += ["", "## Consequences", ""]
    needs = [r["program_name"] for r in rows if r["class"] == "needs-evidence-pass"]
    excl = [r["program_name"] for r in rows if r["class"] == "no-source-in-scope"]
    if needs:
        lines.append(f"- **{len(needs)} program(s) need a fresh MCP evidence pass** before "
                     f"`generate_docs.py` can ground anything about them beyond inventory facts: "
                     f"{', '.join(needs)}.")
    if excl:
        lines.append(f"- **{len(excl)} program(s) are out of scope** for this run "
                     f"(`in_scope=false` in `program-inventory.csv`): {', '.join(excl)}.")
    lines.append(f"- **{c['reused-from-extraction']} of {c['inventory']}** programs are fully "
                 f"reusable from a prior `cobol-knowledge-extraction` run "
                 f"(`dd_generated=Y` and `doc_generated=Y`).")
    lines.append("- Absence of evidence for a program is not evidence about that program. "
                 "Unrepresented programs are named, never characterised.")

    if degraded:
        lines += ["", "## Degraded evidence", ""]
        for d in degraded:
            lines.append(f"- `{d['missing']}` missing → affects "
                         f"{', '.join(d['plansAffected'])} — lost: {d['lost']}")

    with open(os.path.join(out_dir, "coverage.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    # Evidence index — the design doc's flat, atx-mirrored `artifacts` list (build_coverage.py's
    # own contract, bobz-v3-foundations.md §4d) *plus* a `documents` convenience dict keyed by
    # program (docs-status/SKILL.md's staleness snippet reads `idx.get("documents", idx)` and
    # expects `{key: {path: sha256}}`). Both shapes are derived from one artifact list so neither
    # can drift from the other.
    artifacts: list[dict] = []
    documents: dict[str, dict] = {}

    def record(path: str, plans: list[str], program: str | None = None):
        if not path or not os.path.isfile(path):
            return
        h = sha256(path)
        entry = {"path": path, "sha256": h, "plans": plans}
        if program:
            entry["program"] = program
        artifacts.append(entry)
        bucket = documents.setdefault(program or "_manifest", {})
        bucket[path] = h

    record(probe_file, ["all"])
    if manifest_dir:
        record(os.path.join(manifest_dir, "program-inventory.csv"), ["all"])
        record(os.path.join(manifest_dir, "extraction-status.csv"), ["all"])
        record(os.path.join(manifest_dir, "extraction-manifest.json"), ["all"])

    if extraction_root:
        for r in rows:
            if r["class"] != "reused-from-extraction":
                continue
            p = r["program_name"]
            record(os.path.join(extraction_root, "03-data-structures", "data-dictionary",
                                 "by-program", f"{p}-DD.json"), ARTIFACT_PLANS["dd"], p)
            record(os.path.join(extraction_root, "02-business-rules", "by-program", f"{p}.md"),
                   ARTIFACT_PLANS["rules"], p)
            record(os.path.join(extraction_root, "01-application-architecture", f"{p}-arch.md"),
                   ARTIFACT_PLANS["arch"], p)
            record(os.path.join(extraction_root, "10-error-handling",
                                 "exception-paths-by-program", f"{p}.md"),
                   ARTIFACT_PLANS["errh"], p)
            record(os.path.join(extraction_root, "11-code-quality", "zcodescan-findings",
                                 f"{p}.json"), ARTIFACT_PLANS["zcs"], p)
        record(os.path.join(extraction_root, "03-data-structures", "data-dictionary",
                             "DD-master.json"), ["z-data"])
        record(os.path.join(extraction_root, "05-dependencies", "internal-dependencies.json"),
               ["z-structure", "z-integration"])

    idx = {
        "generatedAt": summary["generatedAt"],
        "workspaceRoot": workspace_root,
        "extractionRoot": extraction_root,
        "docsRoot": docs_root,
        "artifacts": artifacts,
        "documents": documents,
    }
    with open(os.path.join(out_dir, "evidence-index.json"), "w", encoding="utf-8") as fh:
        json.dump(idx, fh, indent=2)

    print(f"coverage: {c['reused-from-extraction']} reused, {c['needs-evidence-pass']} need an "
          f"evidence pass, {c['no-source-in-scope']} out of scope, of {c['inventory']} programs "
          f"({c['inScope']} in scope)")
    print(f"wrote {out_dir}/coverage.md")
    print(f"wrote {out_dir}/evidence-index.json  ({len(artifacts)} artifacts indexed)")
    if degraded:
        print(f"degraded evidence: {len(degraded)} item(s) — see coverage.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
