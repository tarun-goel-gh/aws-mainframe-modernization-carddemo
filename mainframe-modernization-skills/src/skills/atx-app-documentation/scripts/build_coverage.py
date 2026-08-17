#!/usr/bin/env python3
"""Step 2 — prerequisite gate and coverage matrix for atx-app-documentation.

Usage:
  build_coverage.py --mfre .atx/mfre [--out-dir $ATX_DOCS_ROOT/00-manifest] [--json] [--check-only]

Exit codes: 0 prerequisites met | 1 a hard prerequisite failed | 2 bad usage

Reads a completed `mainframe-reverse-engineering` run and answers one question before any
document is written: **for each business function, what can honestly be documented?**

AWS Transform produces requirements per business function, and only for functions that were
scoped and that succeeded. A run can therefore cover a fraction of the estate. Classifying that
up front is what stops the suite generalising from delivered functions to "the application".

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

SUCCESS = {"succeeded", "succeeded_degraded"}

# Soft inputs: absent => the named plans degrade rather than the run stopping.
SOFT = [
    ("analysis/code-analysis", ["atx-discovery", "atx-quality", "atx-structure"],
     "per-file metrics, cyclomatic complexity, dependency graph"),
    ("analysis/data-analysis", ["atx-data"],
     "data dictionary and lineage with access direction"),
    ("analysis/business-function-discovery", ["atx-structure", "atx-integration"],
     "data-path graphs"),
]


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


def resolve_spec_dir(mfre: str, local: str | None, slug: str) -> tuple[str | None, bool]:
    """Locate a function's bundle, tolerating a relocated run.

    `state.localPath` is recorded relative to the workspace the run executed in. A run that was
    archived, copied, or is being read through a different --mfre root would otherwise look like
    it delivered nothing, which is a false negative on the hard prerequisite. Try the recorded
    path first, then the conventional location under this mfre root.
    """
    candidates = []
    if local:
        candidates.append(local)
        candidates.append(os.path.join(mfre, os.path.basename(local.rstrip("/"))))
    candidates.append(os.path.join(mfre, "specs", slug))
    for c in candidates:
        if os.path.isfile(os.path.join(c, "spec", slug, "requirements.md")):
            return c, True
    return (local or None), False


def default_docs_root() -> str:
    """Documentation root for this invocation.

    One pipeline run must land entirely in one folder, so `run_pipeline.sh` stamps the folder
    name once and exports ATX_DOCS_ROOT; every step then agrees even though each computes its
    own default. A bare invocation follows the `latest` symlink, which keeps ad-hoc reruns
    pointed at the most recent run rather than resurrecting a stale repo-root path.
    """
    return os.environ.get("ATX_DOCS_ROOT") or os.path.join(".atx", "app-docs-latest")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mfre", default=".atx/mfre", help="upstream run directory")
    ap.add_argument("--out-dir", default=None,
                    help="manifest directory (default: $ATX_DOCS_ROOT/00-manifest)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check-only", action="store_true",
                    help="evaluate prerequisites and print the verdict; write nothing")
    args = ap.parse_args()
    if not args.out_dir:
        args.out_dir = os.path.join(default_docs_root(), "00-manifest")

    M = args.mfre
    blockers: list[str] = []
    degraded: list[dict] = []

    state_path = os.path.join(M, "state.json")
    if not os.path.isfile(state_path):
        print(f"BLOCKED: no upstream run at {state_path}\n"
              f"  Run the mainframe-reverse-engineering skill first; this skill documents an "
              f"existing run and cannot analyse the codebase itself.", file=sys.stderr)
        return 1
    try:
        st = json.load(open(state_path, encoding="utf-8"))
    except Exception as e:
        print(f"BLOCKED: {state_path} is not valid JSON: {e}", file=sys.stderr)
        return 1

    gates = st.get("gates") or {}
    autonomy = st.get("autonomy") or {}
    scope = autonomy.get("scope") or []
    excluded = {e.get("name"): e.get("signals") or []
                for e in (autonomy.get("excludedInfrastructure") or [])
                if isinstance(e, dict)}
    funcs = st.get("functions") or {}
    catalog = ((st.get("discovery") or {}).get("functions")) or []

    if str(gates.get("G2", "")).split("_")[0] != "pass":
        blockers.append(f"gate G2 is {gates.get('G2')!r}, not pass — no persisted business "
                        f"function catalog to document against")
    if not scope:
        blockers.append("autonomy.scope is empty — nothing was selected for extraction")

    csv_path = os.path.join(M, "discovery", "business_function.csv")
    if not os.path.isfile(csv_path) and not catalog:
        blockers.append(f"no catalog: neither {csv_path} nor state.discovery.functions")

    # Catalog facts, preferring the CSV artifact, falling back to state.
    cat: dict[str, dict] = {}
    if os.path.isfile(csv_path):
        with open(csv_path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                name = (r.get("Name of business function") or "").strip()
                if not name:
                    continue
                cat[name] = {
                    "description": (r.get("Business descriptions") or "").strip(),
                    "dataPaths": r.get("Number of data paths"),
                    "entryPoints": r.get("Number of entry points"),
                    "loc": r.get("Total LOC"),
                    "missingFiles": r.get("Number of potential missing files"),
                }
    for f in catalog:
        n = f.get("name")
        if not n:
            continue
        cat.setdefault(n, {}).update({
            "description": f.get("description") or cat.get(n, {}).get("description", ""),
            "category": f.get("category"),
            "dataPaths": f.get("dataPaths"),
            "entryPoints": f.get("entryPoints"),
            "loc": f.get("loc"),
            "missingFiles": f.get("missingFiles"),
            "slug": f.get("slug"),
        })

    # Classify every discovered function.
    rows = []
    delivered = 0
    for name in sorted(cat):
        c = cat[name]
        fs = funcs.get(name) or {}
        slug = c.get("slug") or fs.get("slug") or name.replace(" ", "")
        status = fs.get("status")
        local, has_reqs = resolve_spec_dir(M, fs.get("localPath"), slug)

        if name in excluded:
            cls, doc = "excluded-infrastructure", "catalog only"
        elif name not in scope:
            cls, doc = "not-scoped", "catalog only"
        elif status in SUCCESS and has_reqs:
            cls, doc = "delivered", "full"
            delivered += 1
        else:
            cls, doc = "scoped-no-spec", "catalog only"

        m = fs.get("metrics") or {}
        rows.append({
            "name": name, "slug": slug, "category": c.get("category"),
            "class": cls, "documentable": doc, "status": status,
            "reqF": m.get("reqF"), "reqN": m.get("reqN"),
            "captured": m.get("captured"), "rulesTotal": m.get("rulesTotal"),
            "loc": c.get("loc"), "dataPaths": c.get("dataPaths"),
            "missingFiles": c.get("missingFiles"),
            "exclusionSignals": excluded.get(name) or [],
            "specPath": local,
        })

    if delivered == 0:
        blockers.append("no function delivered a specification — there is nothing to document "
                        "beyond catalog metadata")

    # Soft inputs.
    for rel, plans, what in SOFT:
        p = os.path.join(M, rel)
        present = os.path.isdir(p) or os.path.isfile(p)
        if not present:
            degraded.append({"missing": rel, "plansAffected": plans, "lost": what})

    # business_function.json carries two things. `category` is usually mirrored into
    # state.discovery.functions, but `interfaces` (function-to-function edges) exists only in
    # the JSON artifact. Report only what is actually lost, so the warning stays actionable.
    bfj = os.path.join(M, "discovery", "business_function.json")
    if not os.path.isfile(bfj):
        lost = ["function-to-function interface edges"]
        plans = ["atx-structure", "atx-integration"]
        if not any(r.get("category") for r in rows):
            lost.append("function category (batch/online/mixed)")
            plans.append("atx-business")
        degraded.append({"missing": "discovery/business_function.json",
                         "plansAffected": plans, "lost": ", ".join(lost)})

    glossary = (st.get("source") or {}).get("glossaryProvenance") or "absent"
    if glossary != "user-supplied":
        degraded.append({"missing": "verified glossary",
                         "plansAffected": ["all"],
                         "lost": f"terminology confidence (glossaryProvenance={glossary})"})

    verdict = "blocked" if blockers else "ok"
    summary = {
        "verdict": verdict,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "upstream": {
            "runId": st.get("runId"), "stage": st.get("stage"),
            "job": (st.get("job") or {}).get("name"),
            "workspace": (st.get("workspace") or {}).get("name"),
            "gates": {k: v for k, v in gates.items() if not k.endswith(("note", "blocker"))},
            "statePath": state_path, "stateSha256": sha256(state_path),
        },
        "counts": {
            "discovered": len(rows), "scoped": len(scope), "delivered": delivered,
            "scopedNoSpec": sum(1 for r in rows if r["class"] == "scoped-no-spec"),
            "excludedInfrastructure": sum(1 for r in rows if r["class"] == "excluded-infrastructure"),
            "totalReqF": sum(r["reqF"] or 0 for r in rows if r["class"] == "delivered"),
            "totalRulesCaptured": sum(r["captured"] or 0 for r in rows if r["class"] == "delivered"),
        },
        "blockers": blockers,
        "degraded": degraded,
        "functions": rows,
    }

    if args.check_only or args.json:
        print(json.dumps(summary, indent=2))
        if not args.check_only:
            pass
    if args.check_only:
        return 1 if blockers else 0

    if blockers:
        for b in blockers:
            print(f"BLOCKED: {b}", file=sys.stderr)
        print("\nFix the upstream run before generating documentation.", file=sys.stderr)
        return 1

    # ---- write coverage.md + evidence-index.json ----
    os.makedirs(args.out_dir, exist_ok=True)
    c = summary["counts"]
    lines = [
        "# Coverage",
        "",
        f"Discovered: **{c['discovered']}** · scoped: **{c['scoped']}** · "
        f"delivered: **{c['delivered']}**",
        "",
        f"Requirement- and rule-derived content covers **{c['delivered']} of "
        f"{c['discovered']}** discovered business functions. Every count in this suite carries "
        f"that denominator.",
        "",
        "| Business function | Category | Class | Reqs (F/N) | Rules | LOC | Data paths | Documentable |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        reqs = f"{r['reqF']}/{r['reqN']}" if r["reqF"] is not None else "—"
        rules = (f"{r['captured']}/{r['rulesTotal']}"
                 if r["rulesTotal"] is not None else "—")
        lines.append(
            f"| {md_escape(r['name'])} | {r['category'] or '—'} | `{r['class']}` | {reqs} | "
            f"{rules} | {r['loc'] or '—'} | {r['dataPaths'] or '—'} | {r['documentable']} |")

    lines += ["", "## Consequences", ""]
    nospec = [r["name"] for r in rows if r["class"] == "scoped-no-spec"]
    excl = [r for r in rows if r["class"] == "excluded-infrastructure"]
    if nospec:
        lines.append(f"- **{len(nospec)} scoped function(s) delivered no specification**, so only "
                     f"catalog metadata is documentable for them: {', '.join(nospec)}.")
    if excl:
        lines.append(f"- **{len(excl)} function(s) excluded as infrastructure-only**:")
        for r in excl:
            sig = "; ".join(r["exclusionSignals"]) or "no signals recorded"
            lines.append(f"  - {r['name']} — {sig}")
    lines.append(f"- Totals across delivered functions only: **{c['totalReqF']}** functional "
                 f"requirements, **{c['totalRulesCaptured']}** business rules captured.")
    lines.append("- Absence of evidence for a function is not evidence about that function. "
                 "Unrepresented functions are named, never characterised.")

    if degraded:
        lines += ["", "## Degraded evidence", ""]
        for d in degraded:
            lines.append(f"- `{d['missing']}` missing → affects "
                         f"{', '.join(d['plansAffected'])} — lost: {d['lost']}")

    with open(os.path.join(args.out_dir, "coverage.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    # Evidence index: what exists, its fingerprint, and which plans consume it.
    idx = {"generatedAt": summary["generatedAt"], "mfreRoot": M, "artifacts": []}
    candidates = [
        ("state.json", ["all"]),
        ("discovery/business_function.csv", ["atx-discovery", "atx-business", "atx-operations"]),
        ("discovery/business_function.json", ["atx-structure", "atx-integration", "atx-business"]),
        ("report.md", ["atx-quality", "atx-discovery"]),
        ("manifest.json", ["atx-discovery"]),
        ("analysis/snapshot-manifest.json", ["atx-discovery", "atx-data", "atx-quality"]),
    ]
    for rel, plans in candidates:
        p = os.path.join(M, rel)
        if os.path.isfile(p):
            idx["artifacts"].append({"path": p, "sha256": sha256(p), "plans": plans})
    for r in rows:
        if r["class"] != "delivered" or not r["specPath"]:
            continue
        for fname, plans in (("requirements.md", ["atx-business", "atx-module", "atx-api"]),
                             ("traceability.yaml", ["atx-module", "atx-quality"])):
            p = os.path.join(r["specPath"], "spec", r["slug"], fname)
            if os.path.isfile(p):
                idx["artifacts"].append({"path": p, "sha256": sha256(p),
                                         "function": r["name"], "plans": plans})
    with open(os.path.join(args.out_dir, "evidence-index.json"), "w", encoding="utf-8") as fh:
        json.dump(idx, fh, indent=2)

    print(f"coverage: {c['delivered']} delivered of {c['discovered']} discovered "
          f"({c['scoped']} scoped)")
    print(f"wrote {args.out_dir}/coverage.md")
    print(f"wrote {args.out_dir}/evidence-index.json  ({len(idx['artifacts'])} artifacts indexed)")
    if degraded:
        print(f"degraded evidence: {len(degraded)} item(s) — see coverage.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
