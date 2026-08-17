#!/usr/bin/env python3
"""Split a reimagine spec bundle into one self-contained zip per business function.

A batch reimagine run returns a single spec_gen zip containing spec/<FunctionA>/,
spec/<FunctionB>/, … This produces one independently useful zip per function, each
carrying its own requirements, traceability, program inventory, and a metadata file
describing provenance and quality — so a function's zip can be handed to a team without
the rest of the run.

Usage:
  split_bundle.py --dir <unpacked-bundle> --out-dir <dir> --state <state.json>
                  [--source-root <repo>] [--slug <one-function>] [--no-zip]
                  [--expect "<Function A>,<Function B>"]

Exit codes: 0 all expected functions split and verified | 1 at least one failed or missing
            | 2 bad usage

Scope: the set of functions is NOT taken from whatever happens to be on disk. Doing that
made a batch that silently dropped three of nine functions report "6 of 6 verified". The
expected set comes from --expect, or from --state autonomy.scope, and any function that
produced an empty folder or no folder is reported and fails the exit code.


Output per function:
  <out-dir>/<slug>/spec/<slug>/{requirements.md,traceability.yaml,discovery/…}
  <out-dir>/<slug>/function-metadata.json
  <out-dir>/<slug>/README.md
  <out-dir>/<slug>.zip
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from verify_spec import (  # noqa: E402
    describe_dir, find_bundles, find_function_dirs, resolve_expected, verify_one,
)


def load_state(path: str | None) -> dict:
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def catalog_entry(state: dict, slug: str) -> tuple[str, dict]:
    """Match a slug back to its catalog entry. Returns (display_name, entry)."""
    for f in (state.get("discovery") or {}).get("functions") or []:
        name = f.get("name") or ""
        if f.get("slug") == slug or name.replace(" ", "") == slug:
            return name, f
    return slug, {}


def function_state(state: dict, display_name: str, slug: str) -> dict:
    funcs = state.get("functions") or {}
    if display_name in funcs:
        return funcs[display_name]
    for k, v in funcs.items():
        if v.get("slug") == slug or k.replace(" ", "") == slug:
            return v
    return {}


def glossary_note(state: dict) -> tuple[str, str]:
    """(provenance, human note). Auto-drafted glossaries must be labelled as unverified."""
    src = state.get("source") or {}
    prov = src.get("glossaryProvenance")
    if not prov:
        prov = "user-supplied" if src.get("glossary") else "absent"
    notes = {
        "user-supplied": "A glossary was supplied by the customer and used during extraction.",
        "auto-drafted-unverified": (
            "REFERENCE ONLY — the glossary used during extraction was auto-drafted from "
            "identifiers found in the source. Term expansions are inferred, were not "
            "confirmed by a domain expert, and may be wrong. Treat any terminology in these "
            "requirements that derives from it as unverified."
        ),
        "absent": (
            "No glossary was supplied. Abbreviations in these requirements were interpreted "
            "from context and may not match your business vocabulary."
        ),
    }
    return prov, notes.get(prov, notes["absent"])


def build_metadata(slug: str, display_name: str, cat: dict, fstate: dict,
                   verification: dict, metrics: dict, state: dict) -> dict:
    job = state.get("job") or {}
    ws = state.get("workspace") or {}
    src = state.get("source") or {}
    prov, note = glossary_note(state)
    tr_metrics = metrics or {}

    return {
        "schemaVersion": 1,
        "businessFunction": {
            "name": display_name,
            "slug": slug,
            "category": cat.get("category"),
            "description": cat.get("description"),
        },
        "discovery": {
            "dataPaths": cat.get("dataPaths"),
            "entryPoints": cat.get("entryPoints"),
            "entryPointList": cat.get("entryPointList"),
            "totalLoc": cat.get("loc"),
            "potentialMissingFiles": cat.get("missingFiles"),
        },
        "extraction": {
            "status": fstate.get("status"),
            "attempts": fstate.get("attempts"),
            "readiness": fstate.get("readiness") or {},
            "sourceSpecZip": fstate.get("specZip"),
            "sourceSpecKey": fstate.get("specKey"),
            "startedAt": fstate.get("startedAt"),
            "finishedAt": fstate.get("finishedAt"),
            "durationMin": fstate.get("durationMin"),
        },
        "contents": {
            "requirements": f"spec/{slug}/requirements.md",
            "traceability": f"spec/{slug}/traceability.yaml",
            "programInventory": f"spec/{slug}/discovery/programs.yaml",
            "functionalRequirements": tr_metrics.get("reqF"),
            "nonFunctionalRequirements": tr_metrics.get("reqN"),
            "openQuestions": tr_metrics.get("openQuestions"),
            "workflowSections": tr_metrics.get("sections"),
            "businessRulesTotal": tr_metrics.get("rulesTotal"),
            "businessRulesCaptured": tr_metrics.get("captured"),
            "businessRulesNotApplicable": tr_metrics.get("notApplicable"),
            "programsReferenced": tr_metrics.get("programList") or [],
        },
        "verification": {
            "gate": verification.get("gate"),
            "failures": verification.get("failures") or [],
            "warnings": verification.get("warnings") or [],
            "verifiedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "provenance": {
            "runId": state.get("runId"),
            "workspace": ws.get("name"),
            "job": job.get("name"),
            "region": (state.get("aws") or {}).get("region"),
            "accountId": (state.get("aws") or {}).get("accountId"),
            "sourceMode": src.get("mode"),
            "sourceOrigin": src.get("origin"),
            "sourceCommit": src.get("commit"),
            "sourceZipKey": src.get("zipKey"),
            "sourceZipSha256": src.get("zipSha256"),
            "glossaryProvenance": prov,
            "glossaryNote": note,
        },
        "scope": {
            "phase": "reverse-engineering",
            "note": ("Requirements are technology-agnostic and describe current legacy "
                     "behaviour. Forward engineering decisions are not included."),
        },
    }


def write_readme(path: str, md: dict) -> None:
    bf = md["businessFunction"]
    c = md["contents"]
    v = md["verification"]
    p = md["provenance"]
    d = md["discovery"]
    warn_lines = "\n".join(f"- {w}" for w in v["warnings"]) or "- none"

    unsupported = (md["extraction"].get("readiness") or {}).get("unsupported") or []
    missing = (md["extraction"].get("readiness") or {}).get("missing") or []

    text = f"""# {bf['name']} — modernization requirements

Reverse-engineering output from AWS Transform for a single business function. Self-contained:
everything needed to understand and forward-engineer this function is in this bundle.

## Contents

| File | What it holds |
|---|---|
| `{c['requirements']}` | {c['functionalRequirements']} functional and {c['nonFunctionalRequirements']} non-functional requirements in EARS format, across {c['workflowSections']} workflow sections |
| `{c['traceability']}` | maps every business rule to a requirement, and every requirement back to its rules |
| `{c['programInventory']}` | program inventory for this function |
| `function-metadata.json` | provenance, metrics, and verification verdict |

## Function facts

- Category: {bf['category']}
- Data paths: {d['dataPaths']}
- Entry points: {d['entryPoints']}
- Lines of code: {d['totalLoc']}
- Programs referenced: {len(c['programsReferenced'])}
- Business rules: {c['businessRulesCaptured']} captured of {c['businessRulesTotal']} ({c['businessRulesNotApplicable']} not applicable)
- Open questions: {c['openQuestions']}

## Verification

Gate: **{v['gate']}**

Warnings:
{warn_lines}

## Caveats

{p['glossaryNote']}

- Unsupported files skipped during extraction: {', '.join(f'`{x}`' for x in unsupported) if unsupported else 'none'}
- Files referenced but missing from source: {', '.join(f'`{x}`' for x in missing) if missing else 'none'}
- Open questions in `requirements.md` are decisions the legacy code left implicit. They need a
  human answer before implementation.

## Provenance

- Run: {p['runId']}
- Workspace: {p['workspace']} · job: {p['job']}
- Region: {p['region']} · account: {p['accountId']}
- Source: {p['sourceMode']} `{p['sourceOrigin']}`{f" @ {p['sourceCommit'][:12]}" if p.get('sourceCommit') else ""}
- Source package sha256: {p['sourceZipSha256'] or 'n/a'}
- Verified: {v['verifiedAt']}
"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="unpacked multi-function bundle")
    ap.add_argument("--out-dir", required=True, help="where per-function bundles are written")
    ap.add_argument("--state", help="state.json, for provenance and catalog facts")
    ap.add_argument("--source-root", help="repo root, to resolve referenced programs")
    ap.add_argument("--slug", help="split only this function")
    ap.add_argument("--expect", help="comma-separated function names the bundle must contain; "
                                     "defaults to autonomy.scope from --state")
    ap.add_argument("--no-zip", action="store_true", help="leave folders unzipped")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(args.dir):
        print(f"ERROR: not a directory: {args.dir}", file=sys.stderr)
        return 2

    bundles = find_bundles(args.dir)
    all_dirs = find_function_dirs(args.dir)
    delivered = {slug for _d, slug in bundles}
    empty_dirs = {s: p for s, p in all_dirs.items() if s not in delivered}

    if args.slug:
        bundles = [b for b in bundles if b[1] == args.slug]
        empty_dirs = {s: p for s, p in empty_dirs.items() if s == args.slug}

    # Expected scope: explicit list, else state.autonomy.scope. Never "whatever is on disk".
    if args.slug:
        expected, expected_src = set(), "none"
    else:
        expected, expected_src = resolve_expected(args.expect, args.state if not args.expect else None)
    absent = sorted(expected - set(all_dirs)) if expected else []

    if not bundles and not empty_dirs and not absent:
        print(f"ERROR: no function bundles found under {args.dir}", file=sys.stderr)
        return 1

    state = load_state(args.state)
    os.makedirs(args.out_dir, exist_ok=True)
    results = []

    for spec_dir, slug in bundles:
        display_name, cat = catalog_entry(state, slug)
        fstate = function_state(state, display_name, slug)

        rep, metrics = verify_one(spec_dir, slug, args.source_root)
        verification = {
            "gate": rep.gate,
            "failures": [c["check"] for c in rep.failures],
            "warnings": [f"{c['check']}: {c['detail']}" for c in rep.warnings],
        }

        target = os.path.join(args.out_dir, slug)
        spec_target = os.path.join(target, "spec", slug)
        if os.path.isdir(target):
            shutil.rmtree(target)
        os.makedirs(os.path.dirname(spec_target), exist_ok=True)
        shutil.copytree(spec_dir, spec_target)

        md = build_metadata(slug, display_name, cat, fstate, verification, metrics, state)
        with open(os.path.join(target, "function-metadata.json"), "w", encoding="utf-8") as fh:
            json.dump(md, fh, indent=2)
        write_readme(os.path.join(target, "README.md"), md)

        zip_path = None
        if not args.no_zip:
            zip_path = f"{target}.zip"
            if os.path.exists(zip_path):
                os.remove(zip_path)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for dp, _dn, fns in os.walk(target):
                    for fn in fns:
                        full = os.path.join(dp, fn)
                        zf.write(full, os.path.relpath(full, target))

        results.append({
            "slug": slug,
            "name": display_name,
            "dir": target,
            "zip": zip_path,
            "gate": rep.gate,
            "metrics": metrics,
            "warnings": verification["warnings"],
            "failures": verification["failures"],
        })

        status = "pass" if rep.gate == "pass" else "FAIL"
        nw = len(verification["warnings"])
        print(f"[{status}] {display_name} -> {os.path.basename(zip_path or target)}"
              f"  ({metrics.get('reqF', 0)} functional reqs, {nw} warning(s))", file=sys.stderr)

    # Functions with a slot but no specification, and functions with no slot at all. Both
    # are reported here rather than left to be noticed downstream.
    for slug in sorted(empty_dirs):
        results.append({
            "slug": slug, "name": catalog_entry(state, slug)[0],
            "dir": None, "zip": None, "gate": "fail", "metrics": {},
            "warnings": [],
            "failures": ["empty_function_folder"],
            "detail": (f"spec/{slug}/ exists but has no requirements.md — contains: "
                       f"{describe_dir(empty_dirs[slug])}"),
        })
        print(f"[FAIL] {slug} -> nothing to split (empty function folder)", file=sys.stderr)

    for slug in absent:
        results.append({
            "slug": slug, "name": catalog_entry(state, slug)[0],
            "dir": None, "zip": None, "gate": "fail", "metrics": {},
            "warnings": [],
            "failures": ["function_missing_from_bundle"],
            "detail": f"expected function '{slug}' has no spec/ folder in this bundle",
        })
        print(f"[FAIL] {slug} -> absent from bundle entirely", file=sys.stderr)

    results.sort(key=lambda r: r["slug"])
    overall = "fail" if any(r["gate"] == "fail" for r in results) else "pass"
    n_pass = sum(1 for r in results if r["gate"] == "pass")
    payload = {
        "gate": overall,
        "scope": {
            "expectedSource": expected_src,
            "expected": sorted(expected),
            "delivered": sorted(delivered),
            "emptyFolders": sorted(empty_dirs),
            "missingEntirely": absent,
            "enforced": bool(expected),
        },
        "functionCount": len(results),
        "passed": n_pass,
        "failed": sum(1 for r in results if r["gate"] == "fail"),
        "outDir": args.out_dir,
        "functions": results,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        denom = len(expected) if expected else len(results)
        label = "expected" if expected else "found"
        print(f"\n{n_pass} of {denom} {label} function bundle(s) verified; "
              f"written to {args.out_dir}")
        if empty_dirs:
            print(f"EMPTY function folders ({len(empty_dirs)}): {', '.join(sorted(empty_dirs))}")
        if absent:
            print(f"MISSING from bundle ({len(absent)}): {', '.join(absent)}")
        if not expected:
            print("Scope NOT enforced — pass --state or --expect so a function that produced "
                  "nothing cannot go unnoticed.")

    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
