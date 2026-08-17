#!/usr/bin/env python3
"""Build the run report from state.json. Generated output cannot drift from reality.

Usage:
  build_report.py --state .atx/mfre/state.json [--out-dir .atx/mfre] [--quiet]

Writes report.md and manifest.json. Enforces gate G5.
Exit codes: 0 pass | 1 G5 failure | 2 bad usage
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

LABEL = {
    "succeeded": "Succeeded",
    "succeeded_degraded": "Succeeded (degraded)",
    "failed": "Failed",
    "failed_verification": "Failed verification",
    "timed_out": "Timed out",
    "awaiting_user": "Awaiting input",
    "readiness_blocked": "Blocked (missing files)",
    "skipped": "Skipped",
    "pending": "Not started",
    "readiness_ok": "In progress",
    "extracting": "In progress",
    "verifying": "In progress",
}
# Both count as delivered output. `succeeded_degraded` ran with files missing from the source,
# so its fidelity is lower — it counts toward the total but is always labelled distinctly.
SUCCESS = {"succeeded", "succeeded_degraded"}
# Statuses that represent a finished decision for this run and can therefore be published.
# timed_out / readiness_blocked / awaiting_user are legitimate outcomes to report — the run
# is allowed to end with them. Blocking the report on those would make it impossible to
# publish results for a partially successful run.
REPORTABLE = SUCCESS | {
    "failed", "failed_verification", "skipped",
    "timed_out", "readiness_blocked", "awaiting_user",
}
# Statuses that mean the run simply is not finished yet.
IN_FLIGHT = {"pending", "readiness_ok", "extracting", "verifying"}


def n(v, dash: str = "—") -> str:
    return dash if v in (None, "") else str(v)


def md_escape(s: str) -> str:
    return str(s).replace("|", r"\|")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--out-dir")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.state):
        print(f"ERROR: state file not found: {args.state}", file=sys.stderr)
        return 2

    with open(args.state, encoding="utf-8") as fh:
        st = json.load(fh)

    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.state))
    os.makedirs(out_dir, exist_ok=True)

    funcs: dict = st.get("functions") or {}
    discovery = st.get("discovery") or {}
    catalog = discovery.get("functions") or []
    autonomy = st.get("autonomy") or {}
    scope = autonomy.get("scope") or list(funcs.keys())

    by_loc = {f.get("name"): f for f in catalog if isinstance(f, dict)}

    rows, gate_errors = [], []
    tot = {"reqF": 0, "reqN": 0, "oq": 0, "captured": 0, "rules": 0}
    counts: dict[str, int] = {}
    all_warnings: list[tuple[str, str]] = []

    for name in scope:
        fs = funcs.get(name) or {}
        status = fs.get("status", "pending")
        counts[status] = counts.get(status, 0) + 1

        if status in IN_FLIGHT:
            gate_errors.append(
                f"'{name}' is still in flight (status '{status}') — the run is not finished")
        elif status not in REPORTABLE:
            gate_errors.append(f"'{name}' has unrecognised status '{status}'")

        m = fs.get("metrics") or {}
        ver = fs.get("verification") or {}
        cat = by_loc.get(name) or {}
        warns = ver.get("warnings") or []
        for w in warns:
            all_warnings.append((name, w))

        if status in SUCCESS:
            for key, mk in (("reqF", "reqF"), ("reqN", "reqN"), ("oq", "openQuestions"),
                            ("captured", "captured"), ("rules", "rulesTotal")):
                tot[key] += int(m.get(mk) or 0)

            local = fs.get("localPath")
            if not local or not os.path.isdir(local):
                gate_errors.append(f"'{name}' is {status} but localPath is missing: {local!r}")
            elif not _has_requirements(local):
                gate_errors.append(f"'{name}' localPath has no requirements.md: {local}")
            if ver.get("gate") != "pass":
                gate_errors.append(f"'{name}' is {status} but verification gate is "
                                   f"{ver.get('gate')!r}")

        if ver.get("gate") == "pass":
            vtxt = "pass" if not warns else f"pass ({len(warns)} warning{'s' if len(warns) > 1 else ''})"
        elif ver.get("gate") == "fail":
            failed = ver.get("failures") or []
            vtxt = "FAIL: " + (", ".join(failed[:2]) if failed else "see verification.json")
        else:
            vtxt = "—"

        reqs = (f"{m.get('reqF')}/{m.get('reqN')}"
                if m.get("reqF") is not None else "—")
        rules = (f"{m.get('captured')}/{m.get('rulesTotal')}"
                 if m.get("rulesTotal") is not None else "—")

        rows.append({
            "name": name,
            "status": LABEL.get(status, status),
            "rawStatus": status,
            "zip": fs.get("specZip"),
            "reqs": reqs,
            "oq": m.get("openQuestions"),
            "rules": rules,
            "na": m.get("notApplicable"),
            "programs": m.get("programs"),
            "loc": cat.get("loc"),
            "paths": cat.get("dataPaths"),
            "verification": vtxt,
            "durationMin": fs.get("durationMin"),
            "localPath": fs.get("localPath"),
            "specKey": fs.get("specKey"),
            "readiness": fs.get("readiness") or {},
            "failure": fs.get("failure"),
            "warnings": warns,
            "metrics": m,
        })

    succeeded = sum(counts.get(s, 0) for s in SUCCESS)
    degraded = counts.get("succeeded_degraded", 0)
    scoped = len(scope)
    discovered = len(catalog) or scoped
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    md = _render(st, rows, tot, succeeded, scoped, discovered, all_warnings,
                 autonomy, generated_at, degraded)

    report_path = os.path.join(out_dir, "report.md")
    manifest_path = os.path.join(out_dir, "manifest.json")

    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(md)

    manifest = {
        "runId": st.get("runId"),
        "generatedAt": generated_at,
        "job": {
            "workspaceName": (st.get("workspace") or {}).get("name"),
            "jobName": (st.get("job") or {}).get("name"),
            "region": (st.get("aws") or {}).get("region"),
            "accountId": (st.get("aws") or {}).get("accountId"),
        },
        "source": st.get("source") or {},
        "summary": {
            "discovered": discovered,
            "scoped": scoped,
            "succeeded": succeeded,
            "degraded": degraded,
            "byStatus": counts,
            "totalReqF": tot["reqF"],
            "totalReqN": tot["reqN"],
            "totalOpenQuestions": tot["oq"],
            "totalRulesCaptured": tot["captured"],
            "totalRules": tot["rules"],
        },
        "functions": [
            {
                "name": r["name"], "status": r["rawStatus"], "specZip": r["zip"],
                "specKey": r["specKey"], "localPath": r["localPath"],
                "metrics": r["metrics"], "warnings": r["warnings"],
                "failure": r["failure"], "readiness": r["readiness"],
                "durationMin": r["durationMin"],
            }
            for r in rows
        ],
        "gateG5": "fail" if gate_errors else "pass",
        "gateG5Errors": gate_errors,
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    if not args.quiet:
        print(md)

    print(f"\nwrote {report_path}", file=sys.stderr)
    print(f"wrote {manifest_path}", file=sys.stderr)

    if gate_errors:
        print("\nGATE G5 FAIL:", file=sys.stderr)
        for e in gate_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    return 0


def _has_requirements(root: str) -> bool:
    for _dp, _dn, fns in os.walk(root):
        if "requirements.md" in fns:
            return True
    return False


def _render(st, rows, tot, succeeded, scoped, discovered, all_warnings,
            autonomy, generated_at, degraded=0) -> str:
    job = st.get("job") or {}
    ws = st.get("workspace") or {}
    aws = st.get("aws") or {}
    src = st.get("source") or {}
    disc = st.get("discovery") or {}
    catalog = disc.get("functions") or []

    L: list[str] = []
    a = L.append

    a("# Mainframe reverse engineering — run report")
    a("")
    a(f"**{succeeded} of {scoped} business functions succeeded"
      + (f", {degraded} of them degraded" if degraded else "")
      + f".** {tot['reqF']} functional and {tot['reqN']} non-functional requirements produced, "
      f"{tot['captured']} of {tot['rules']} business rules captured, "
      f"{tot['oq']} open questions raised.")
    a("")

    if degraded:
        a(f"{degraded} function(s) ran with files missing from the source package. Their "
          "requirements are incomplete for the affected rules — see Failures and blocks.")
        a("")

    problems = [r for r in rows if r["rawStatus"] not in SUCCESS]
    if problems:
        a("Not fully successful: "
          + "; ".join(f"**{r['name']}** ({r['status']})" for r in problems)
          + ". Details below.")
        a("")

    a("## Results")
    a("")
    a("| Business function | Status | Spec zip | Reqs (F/N) | Open Qs | "
      "Rules captured | Programs | LOC | Data paths | Verification |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        na = f" (+{r['na']} n/a)" if r["na"] not in (None, "") else ""
        a("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            md_escape(r["name"]), r["status"],
            f"`{r['zip']}`" if r["zip"] else "—",
            r["reqs"], n(r["oq"]), r["rules"] + na,
            n(r["programs"]), n(r["loc"]), n(r["paths"]), r["verification"]))
    a("")

    a("## Run context")
    a("")
    a(f"- Workspace **{n(ws.get('name'))}**, job **{n(job.get('name'))}**")
    a(f"- Account `{n(aws.get('accountId'))}` in `{n(aws.get('region'))}`")
    mode = src.get("mode")
    origin = src.get("origin")
    commit = src.get("commit")
    src_bits = f"- Source: {n(mode)}"
    if origin:
        src_bits += f" — `{origin}`"
    if commit:
        src_bits += f" @ `{commit[:12]}`"
    a(src_bits)
    if src.get("zipKey"):
        a(f"- Package: `{src['zipKey']}`"
          + (f" (sha256 `{src['zipSha256'][:16]}…`)" if src.get("zipSha256") else ""))
    counts = src.get("fileCounts") or {}
    if counts:
        a("- Files: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    prov = src.get("glossaryProvenance") or (
        "user-supplied" if src.get("glossary") else "absent")
    gloss = {
        "user-supplied": "Glossary: supplied by the customer.",
        "auto-drafted-unverified": (
            "Glossary: **auto-drafted, reference only.** Expansions were inferred from "
            "identifiers in the source, not confirmed by a domain expert. Terminology in the "
            "generated requirements that derives from it is unverified. Each function bundle "
            "repeats this caveat in its `function-metadata.json` and README."),
        "absent": ("Glossary: none supplied — abbreviations were interpreted from context and "
                   "may not match your business vocabulary."),
    }
    a(f"- {gloss.get(prov, gloss['absent'])}")
    mode = autonomy.get("level")
    batch = autonomy.get("batchMode")
    a(f"- Autonomy: {n(mode)}"
      + (f", {'batch' if batch else 'sequential'} extraction" if mode else ""))
    a("")

    # excludedInfrastructure accepts either plain names or {name, signals} objects.
    raw_excluded = autonomy.get("excludedInfrastructure") or []
    excluded = []
    for e in raw_excluded:
        if isinstance(e, dict):
            excluded.append((e.get("name") or "", e.get("signals") or []))
        else:
            excluded.append((str(e), []))
    excluded_names = {name for name, _ in excluded}

    if discovered != scoped or excluded:
        a("## Coverage")
        a("")
        a(f"- Discovered: {discovered} · scoped: {scoped} · succeeded: {succeeded}")
        if excluded:
            a(f"- Excluded as infrastructure-only ({len(excluded)}):")
            for name, signals in excluded:
                detail = f" — {', '.join(signals)}" if signals else ""
                a(f"  - **{name}**{detail}")
            a("  Classified from discovery signals, not a built-in list. They carry no "
              "extractable business rules, so they were not sent through extraction. Any of "
              "them can be added back to scope on request.")
        not_scoped = [f.get("name") for f in catalog
                      if f.get("name") not in (autonomy.get("scope") or [])
                      and f.get("name") not in excluded_names]
        if not_scoped and autonomy.get("scope"):
            a(f"- Discovered but not scoped this run ({len(not_scoped)}): "
              + ", ".join(f"**{x}**" for x in not_scoped))
        a("")

    if all_warnings:
        a("## Warnings")
        a("")
        grouped: dict[str, list[str]] = {}
        for fn, w in all_warnings:
            key = w.split(":", 1)[0].strip()
            grouped.setdefault(key, []).append(fn)
        for key, fns in sorted(grouped.items()):
            noun = "function" if len(fns) == 1 else "functions"
            a(f"- **{key}** — {len(fns)} {noun}: " + ", ".join(fns))
        a("")
        a("Warnings do not invalidate a spec bundle, but they indicate artifacts worth a "
          "human look before forward engineering.")
        a("")

    failures = [r for r in rows
                if r["rawStatus"] in {"failed", "failed_verification", "timed_out",
                                      "readiness_blocked", "awaiting_user"}]
    if failures:
        a("## Failures and blocks")
        a("")
        for r in failures:
            a(f"### {r['name']} — {r['status']}")
            f = r["failure"] or {}
            if f.get("class"):
                a(f"- Class: `{f['class']}`")
            if f.get("reason"):
                a(f"- Reason: {f['reason']}")
            if f.get("attempts"):
                a(f"- Attempts: {f['attempts']}")
            miss = (r["readiness"] or {}).get("missing") or []
            if miss:
                a(f"- Missing files ({len(miss)}): " + ", ".join(f"`{x}`" for x in miss[:10]))
            if r["localPath"] and os.path.isdir(r["localPath"]):
                a(f"- Retained artifacts: `{r['localPath']}`")
            if f.get("nextAction"):
                a(f"- Next action: {f['nextAction']}")
            elif r["rawStatus"] == "timed_out":
                a("- Next action: the run is likely still progressing server-side. Resume this "
                  "function in a new session rather than restarting the job.")
            a("")

    readiness_notes = [r for r in rows if (r["readiness"] or {}).get("unsupported")]
    if readiness_notes:
        a("## Readiness exceptions")
        a("")
        for r in readiness_notes:
            uns = r["readiness"]["unsupported"]
            a(f"- **{r['name']}** — {len(uns)} unsupported file(s) skipped: "
              + ", ".join(f"`{x}`" for x in uns[:10]))
        a("")
        a("Unsupported files are typically infrastructure artifacts such as GDG bases and plain "
          "text, which hold no extractable business logic.")
        a("")

    answered = st.get("answeredTasks") or st.get("acknowledgedTasks") or []
    if answered:
        a("## Checkpoints answered autonomously")
        a("")
        for t in answered:
            line = f"- **{t.get('title')}**"
            if t.get("derivation"):
                line += f" — {t['derivation']}"
            if t.get("at"):
                line += f" ({t['at']})"
            a(line)
        a("")
        a("Each was answered from verified run state or a documented policy, never guessed. "
          "Hard stops — critical-severity tasks, tool approvals, destructive or "
          "scope-expanding requests, and genuine ambiguity — are never answered automatically.")
        a("")

    parked = st.get("awaitingUserTasks") or []
    if parked:
        a("## Checkpoints waiting on you")
        a("")
        for t in parked:
            a(f"- **{t.get('title')}** — {t.get('reason', 'needs a human decision')}")
        a("")

    # Totals aggregate succeeded functions only, so the breakdown must too — otherwise the
    # list does not add up to the stated total.
    oq_rows = [r for r in rows if r["rawStatus"] in SUCCESS and r["oq"]]
    if tot["oq"]:
        a("## Open questions")
        a("")
        a(f"{tot['oq']} open questions across the {len(oq_rows)} verified "
          f"{'function' if len(oq_rows) == 1 else 'functions'}. These are the real handoff "
          "items for forward engineering — each one is a decision the legacy code left "
          "implicit. Per-function detail is in each bundle's `requirements.md` under "
          "**Open Questions**.")
        a("")
        for r in oq_rows:
            a(f"- **{r['name']}** — {r['oq']}")
        unverified = [r for r in rows if r["rawStatus"] not in SUCCESS and r["oq"]]
        if unverified:
            a("")
            a("Not counted above, because the bundle did not pass verification: "
              + ", ".join(f"**{r['name']}** ({r['oq']})" for r in unverified) + ".")
        a("")

    a("## Next step")
    a("")
    a("Reverse engineering is complete for the functions above. Forward engineering (domain "
      "modelling, microservice specifications, code generation) is a separate workflow and has "
      "not been started. The verified spec bundles are the input to it.")
    a("")
    a(f"_Generated {generated_at} from `state.json`._")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
