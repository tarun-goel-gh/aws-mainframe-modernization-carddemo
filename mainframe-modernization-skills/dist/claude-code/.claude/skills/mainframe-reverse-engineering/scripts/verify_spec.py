#!/usr/bin/env python3
"""Gate G4: verify an AWS Transform spec bundle, including what is missing from it.

Usage:
  verify_spec.py --dir <bundle-dir> [--source-root <repo-root>] [--json] [--write]
                 [--expect "<Function A>,<Function B>" | --state <state.json>]
                 [--slug <one-function>]

<bundle-dir> is where the spec zip was unpacked. Expected inside:
  spec/<FunctionSlug>/requirements.md
  spec/<FunctionSlug>/traceability.yaml
  spec/<FunctionSlug>/discovery/programs.yaml   (optional)

Exit codes: 0 pass (warnings allowed) | 1 fail | 2 bad usage

## Scope enforcement — why this is not optional

Discovering functions by scanning for `requirements.md` makes a function that produced
*no* specification invisible to the gate. Observed on a real 9-function batch: three
functions emitted only an empty `discovery/programs.yaml`, and an earlier version of this
script reported `functionCount: 6, passed: 6, gate: pass` — a clean pass over two thirds
of the requested scope, while the job's own worklog claimed "9/9 passed".

So the gate reconciles three sets, and any shortfall is a **failure**, not a warning:

  expected   what was asked for (--expect, or --state autonomy.scope)
  delivered  spec/<Slug>/ with a substantive requirements.md
  empty      spec/<Slug>/ present but carrying no requirements.md

An empty function folder fails unconditionally, with or without an expected list — a
folder the generator created but never filled is a defect on its own evidence. Passing an
expected list additionally catches functions that produced no folder at all.

No third-party dependencies. PyYAML is used when importable, otherwise a targeted
line parser reads the handful of fields the gate needs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

FAIL, WARN, INFO, OK = "fail", "warn", "info", "ok"

REQ_DEF_RE = re.compile(r"^(REQ-[FN]-\d+):", re.M)      # definitions in requirements.md
REQ_ANY_RE = re.compile(r"REQ-[FN]-\d+")                 # any mention
OQ_DEF_RE = re.compile(r"^(OQ-\d+):", re.M)
SECTION_RE = re.compile(r"^##\s+\d+\.\s+(.+)$", re.M)
TERMINAL_PUNCT = (".", "?", "!", "`", ")", "]", ":", "—")

SOURCE_EXTS = (
    ".cbl", ".cob", ".cobol", ".cpy", ".jcl", ".prc", ".proc", ".inc", ".ctl",
    ".bms", ".csd", ".dcl", ".sql", ".ddl", ".psb", ".dbd", ".ims", ".mfs",
    ".pl1", ".pl1_copy", ".asm", ".mac", ".nat", ".rex", ".rexx", ".ezt",
)

# Directories never treated as application source. Agent runtimes install their skill trees into
# dot-directories that can hold samples, fixtures and documentation; walking them lets a skill's own
# contents be reported as the customer's source. `.kiro` was excluded from the start, and the other
# runtime directories are the same class of thing — omitting them was a portability bug rather than a
# deliberate choice, so they are listed together here where the next walk will find them.
EXCLUDED_SCAN_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".atx",                      # this skill's own output
    ".kiro", ".claude", ".codex",  # agent runtimes that host these skills
    ".bobz",                     # Bob IDE, the other documentation lineage
}


class Report:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append({"check": name, "status": status, "detail": detail})

    @property
    def failures(self) -> list[dict]:
        return [c for c in self.checks if c["status"] == FAIL]

    @property
    def warnings(self) -> list[dict]:
        return [c for c in self.checks if c["status"] == WARN]

    @property
    def gate(self) -> str:
        return "fail" if self.failures else "pass"


def find_bundles(root: str) -> list[tuple[str, str]]:
    """Every (spec_function_dir, slug) under root.

    A batch reimagine run returns one zip containing spec/<FunctionA>/,
    spec/<FunctionB>/, … so verification must enumerate all of them, not just the first.
    """
    found: list[tuple[str, str]] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        if "requirements.md" in filenames and os.path.basename(os.path.dirname(dirpath)) == "spec":
            found.append((dirpath, os.path.basename(dirpath)))
    if not found:
        # Fallback for bundles that omit the spec/ wrapper.
        for dirpath, _dirnames, filenames in os.walk(root):
            if "requirements.md" in filenames:
                found.append((dirpath, os.path.basename(dirpath)))
    return sorted(found, key=lambda t: t[1])


def slugify(name: str) -> str:
    """Business function name -> bundle folder name. Spaces removed, nothing else."""
    return name.replace(" ", "")


def find_function_dirs(root: str) -> dict[str, str]:
    """Every spec/<Slug>/ directory, whether or not it holds a requirements.md.

    This is the counterpart to find_bundles(). find_bundles() answers "what was
    delivered"; this answers "what did the generator create a slot for". The difference
    between them is the set of empty function folders, which is the defect this catches.
    """
    found: dict[str, str] = {}
    for dirpath, dirnames, _filenames in os.walk(root):
        if os.path.basename(dirpath) == "spec":
            for d in sorted(dirnames):
                found.setdefault(d, os.path.join(dirpath, d))
    return found


def describe_dir(path: str) -> str:
    """Short inventory of a function folder, for explaining why it is considered empty."""
    entries: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(path):
        rel = os.path.relpath(dirpath, path)
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(p)
            except OSError:
                size = -1
            entries.append(f"{fn if rel == '.' else os.path.join(rel, fn)} ({size}B)")
    return ", ".join(entries) if entries else "no files at all"


def resolve_expected(expect: str | None, state_path: str | None) -> tuple[set[str], str]:
    """Expected function slugs, from an explicit list or from state.autonomy.scope."""
    if expect:
        names = [n.strip() for n in expect.split(",") if n.strip()]
        return {slugify(n) for n in names}, "flag"
    if state_path:
        if not os.path.isfile(state_path):
            raise SystemExit(f"ERROR: state file not found: {state_path}")
        with open(state_path, encoding="utf-8") as fh:
            st = json.load(fh)
        scope = ((st.get("autonomy") or {}).get("scope")) or []
        if not scope:
            raise SystemExit("ERROR: --state supplied but autonomy.scope is empty; "
                             "nothing to reconcile against")
        return {slugify(n) for n in scope}, "state"
    return set(), "none"


def load_traceability(path: str) -> dict:
    """Parse the fields the gate needs. Prefer PyYAML; fall back to a line parser.

    Real bundles carry two indices, and both matter:
      rules:        forward  rule_id -> req_id / req_ids, plus disposition and program
      requirements: reverse  req_id  -> rule_ids
    The reverse index is authoritative for "does this requirement have provenance",
    because a requirement can be absent from the forward index yet fully mapped in the
    reverse one. Reading only `rules:` produces false negatives.
    """
    text = open(path, encoding="utf-8", errors="replace").read()
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        summary = data.get("summary") or {}
        recon = summary.get("reconciliation") or {}
        rules = data.get("rules") or []

        programs: set[str] = set()
        dispositions: dict[str, int] = {}
        fwd: set[str] = set()
        for r in rules:
            if not isinstance(r, dict):
                continue
            if r.get("program"):
                programs.add(str(r["program"]))
            d = str(r.get("disposition", "unknown"))
            dispositions[d] = dispositions.get(d, 0) + 1
            if r.get("req_id"):
                fwd.add(str(r["req_id"]))
            for rid in r.get("req_ids") or []:
                fwd.add(str(rid))

        rev: set[str] = set()
        rev_empty: list[str] = []
        reverse = data.get("requirements") or []
        for e in reverse:
            if not isinstance(e, dict) or not e.get("req_id"):
                continue
            rid = str(e["req_id"])
            rev.add(rid)
            if not (e.get("rule_ids") or []):
                rev_empty.append(rid)

        return {
            "function": data.get("function"),
            "summary": summary,
            "reconciliation": recon,
            "ruleCount": len(rules),
            "reverseCount": len(reverse),
            "programs": sorted(programs),
            "dispositions": dispositions,
            "reqForward": fwd,
            "reqReverse": rev,
            "reqRefs": fwd | rev,
            "reverseEmpty": rev_empty,
            "parser": "pyyaml",
        }
    except Exception:
        pass

    def scalar(key: str) -> int | None:
        m = re.search(rf"^\s*{re.escape(key)}:\s*(\d+)\s*$", text, re.M)
        return int(m.group(1)) if m else None

    summary_keys = ("total_rules", "captured", "not_applicable", "unreachable",
                    "delegated", "not_accounted_for")
    summary = {k: scalar(k) for k in summary_keys if scalar(k) is not None}
    recon = {k: scalar(k) for k in ("expected", "written", "shortfall") if scalar(k) is not None}

    programs = set(re.findall(r"^\s*program:\s*(\S+)\s*$", text, re.M))
    dispositions: dict[str, int] = {}
    for d in re.findall(r"^\s*disposition:\s*(\S+)\s*$", text, re.M):
        dispositions[d] = dispositions.get(d, 0) + 1

    # Structural mentions only. A whole-text grep would also catch REQ ids quoted in
    # prose `reason:` fields and overstate coverage.
    refs = set(re.findall(r"^\s*-?\s*req_id:\s*(REQ-[FN]-\d+)\s*$", text, re.M))
    refs |= set(re.findall(r"^\s*-\s*(REQ-[FN]-\d+)\s*$", text, re.M))
    fn = re.search(r"^function:\s*(\S+)\s*$", text, re.M)

    return {
        "function": fn.group(1) if fn else None,
        "summary": summary,
        "reconciliation": recon,
        "ruleCount": len(re.findall(r"^\s*-\s*rule_id:", text, re.M)),
        "reverseCount": len(re.findall(r"^-\s*req_id:", text, re.M)),
        "programs": sorted(programs),
        "dispositions": dispositions,
        "reqForward": refs,
        "reqReverse": refs,
        "reqRefs": refs,
        "reverseEmpty": [],
        "parser": "fallback",
    }


def index_source(root: str) -> set[str]:
    """Basenames-without-extension of source files under root, uppercased."""
    stems: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_SCAN_DIRS]
        for fn in filenames:
            stem, ext = os.path.splitext(fn)
            if ext.lower() in SOURCE_EXTS:
                stems.add(stem.upper())
    return stems


def verify_one(spec_dir: str, slug: str, source_root: str | None) -> tuple[Report, dict]:
    """Run every gate check against a single function bundle."""
    rep = Report()
    metrics: dict = {"slug": slug}

    req_path = os.path.join(spec_dir, "requirements.md")
    trace_path = os.path.join(spec_dir, "traceability.yaml")
    programs_yaml = os.path.join(spec_dir, "discovery", "programs.yaml")

    rep.add("bundle_shape", OK, f"spec/{slug}")

    # ---- requirements.md ----
    req_text = open(req_path, encoding="utf-8", errors="replace").read()
    if len(req_text.strip()) < 200:
        rep.add("requirements_substance", FAIL,
                f"requirements.md is only {len(req_text.strip())} chars")
    req_ids = REQ_DEF_RE.findall(req_text)
    req_f = [r for r in req_ids if r.startswith("REQ-F-")]
    req_n = [r for r in req_ids if r.startswith("REQ-N-")]
    oq_ids = OQ_DEF_RE.findall(req_text)
    sections = SECTION_RE.findall(req_text)

    metrics.update({
        "reqF": len(req_f), "reqN": len(req_n),
        "openQuestions": len(oq_ids), "sections": len(sections),
    })

    if not req_f:
        rep.add("requirements_substance", FAIL, "no REQ-F-* requirements defined")
    elif not sections:
        rep.add("requirements_substance", WARN,
                f"{len(req_f)} functional requirements but no numbered '## N.' sections")
    else:
        rep.add("requirements_substance", OK,
                f"{len(sections)} sections, {len(req_f)} functional, {len(req_n)} non-functional")

    dupes = sorted({r for r in req_ids if req_ids.count(r) > 1})
    rep.add("requirements_unique_ids", FAIL if dupes else OK,
            f"duplicate ids: {', '.join(dupes)}" if dupes else "no duplicate REQ ids")

    # Truncation: the last defined requirement or open question should read as a finished
    # sentence. Observed real-world defect: a final open question cut mid-sentence and
    # ending in an ellipsis, which a naive "ends with a period" test lets through.
    tail = [ln.strip() for ln in req_text.strip().splitlines() if ln.strip()]
    last_content = next(
        (ln for ln in reversed(tail)
         if not ln.startswith(("#", "---", "|", "*", ">")) and len(ln) > 40),
        "",
    )
    trunc_reason = ""
    if last_content:
        stripped = last_content.rstrip()
        # A quoted mainframe message legitimately ends '...' inside quotes; a sentence
        # that simply stops does not.
        ends_quoted = stripped.endswith(("'", '"', "’", "”", "`"))
        if (stripped.endswith("...") or stripped.endswith("…")) and not ends_quoted:
            trunc_reason = "ends in an ellipsis mid-sentence"
        elif not stripped.endswith(TERMINAL_PUNCT):
            trunc_reason = "no terminal punctuation"

    if trunc_reason:
        rep.add("requirements_truncation", WARN,
                f"final line may be truncated ({trunc_reason}): …{last_content[-70:]}")
    else:
        rep.add("requirements_truncation", OK, "no truncation detected")

    # ---- traceability.yaml ----
    if not os.path.isfile(trace_path):
        rep.add("traceability_present", FAIL, "traceability.yaml missing")
        return rep, metrics

    tr = load_traceability(trace_path)
    rep.add("traceability_present", OK,
            f"parsed via {tr['parser']}, {tr['ruleCount']} rules + "
            f"{tr['reverseCount']} requirement index entries")

    s = tr["summary"]
    recon = tr["reconciliation"]
    metrics.update({
        "rulesTotal": s.get("total_rules"),
        "captured": s.get("captured"),
        "notApplicable": s.get("not_applicable"),
        "programs": len(tr["programs"]),
        "programList": tr["programs"],
    })

    total = s.get("total_rules")
    if total is None:
        rep.add("traceability_summary", WARN, "no summary.total_rules found")
    else:
        parts = {k: s.get(k, 0) or 0 for k in
                 ("captured", "not_applicable", "unreachable", "delegated")}
        got = sum(parts.values())
        if got == total:
            rep.add("disposition_math", OK,
                    f"{parts['captured']} captured + {parts['not_applicable']} n/a "
                    f"+ {parts['unreachable']} unreachable + {parts['delegated']} delegated = {total}")
        else:
            rep.add("disposition_math", FAIL,
                    f"dispositions sum to {got} but total_rules is {total}")

        nafo = s.get("not_accounted_for")
        if nafo in (None, 0):
            rep.add("rules_accounted", OK, "no unaccounted rules")
        else:
            rep.add("rules_accounted", FAIL, f"not_accounted_for = {nafo}")

    if recon:
        exp, wri = recon.get("expected"), recon.get("written")
        short = recon.get("shortfall")
        if exp is not None and wri is not None and exp != wri:
            rep.add("reconciliation", FAIL, f"expected {exp} but wrote {wri}")
        elif short not in (None, 0):
            rep.add("reconciliation", FAIL, f"shortfall = {short}")
        else:
            rep.add("reconciliation", OK, f"expected == written == {exp}, shortfall 0")
    else:
        rep.add("reconciliation", WARN, "no reconciliation block in summary")

    # ---- REQ symmetry ----
    # Asymmetric severity, deliberately:
    #   traced but undefined  -> FAIL. A dangling reference means a broken artifact.
    #   defined but untraced  -> WARN. The requirement exists but lacks source provenance;
    #                            worth a human look, not grounds for rejecting the bundle.
    defined = set(req_ids)
    referenced = {r for r in tr["reqRefs"] if REQ_ANY_RE.fullmatch(r)}
    only_yaml = sorted(referenced - defined)
    only_md = sorted(defined - referenced)

    if only_yaml:
        rep.add("req_dangling", FAIL,
                f"{len(only_yaml)} REQ id(s) traced but not defined in requirements.md: "
                f"{', '.join(only_yaml[:8])}")
    else:
        rep.add("req_dangling", OK, "no dangling REQ references")

    if only_md:
        rep.add("req_provenance", WARN,
                f"{len(only_md)} requirement(s) defined with no rule mapped: "
                f"{', '.join(only_md[:8])}")
    else:
        rep.add("req_provenance", OK,
                f"all {len(defined)} requirements trace back to at least one rule")

    if tr["reverseEmpty"]:
        rep.add("req_empty_mapping", WARN,
                f"{len(tr['reverseEmpty'])} requirement index entr(ies) carry an empty "
                f"rule list: {', '.join(tr['reverseEmpty'][:8])}")

    metrics["reqTracedForward"] = len(tr["reqForward"])
    metrics["reqTracedReverse"] = len(tr["reqReverse"])

    # ---- programs.yaml ----
    if os.path.isfile(programs_yaml):
        ptext = open(programs_yaml, encoding="utf-8", errors="replace").read()
        listed = re.findall(r"^\s*-\s+(\S+)", ptext, re.M)
        if re.search(r"^\s*programs:\s*\[\s*\]\s*$", ptext, re.M) or not listed:
            rep.add("program_inventory", WARN,
                    "discovery/programs.yaml lists no programs even though traceability "
                    f"references {len(tr['programs'])}")
        else:
            rep.add("program_inventory", OK, f"{len(listed)} programs listed")
    else:
        rep.add("program_inventory", WARN, "discovery/programs.yaml absent")

    # ---- program resolution ----
    if source_root and os.path.isdir(source_root):
        stems = index_source(source_root)
        missing = [p for p in tr["programs"] if p.upper() not in stems]
        if missing:
            rep.add("program_resolution", WARN,
                    f"{len(missing)}/{len(tr['programs'])} referenced programs not found "
                    f"under source root: {', '.join(missing[:8])}")
        else:
            rep.add("program_resolution", OK,
                    f"all {len(tr['programs'])} referenced programs resolve to source files")
    else:
        rep.add("program_resolution", INFO, "skipped (no --source-root)")

    rep.add("open_questions", INFO,
            f"{len(oq_ids)} open question(s) for the forward-engineering team")

    return rep, metrics


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--dir", required=True, help="unpacked spec bundle directory")
    ap.add_argument("--source-root", help="repo root, to resolve referenced programs")
    ap.add_argument("--slug", help="verify only this function slug")
    ap.add_argument("--expect", help="comma-separated business function names or slugs that "
                                     "the bundle must contain")
    ap.add_argument("--state", help="read the expected function list from this state.json "
                                    "(autonomy.scope)")
    ap.add_argument("--json", action="store_true", help="emit JSON on stdout")
    ap.add_argument("--write", action="store_true",
                    help="write verification.json beside each bundle and at --dir root")
    args = ap.parse_args()

    if not os.path.isdir(args.dir):
        print(f"ERROR: not a directory: {args.dir}", file=sys.stderr)
        return 2
    if args.expect and args.state:
        print("ERROR: pass --expect or --state, not both", file=sys.stderr)
        return 2

    expected, expected_src = resolve_expected(args.expect, args.state)

    bundles = find_bundles(args.dir)
    all_dirs = find_function_dirs(args.dir)
    delivered = {slug for _d, slug in bundles}
    # Present on disk but with nothing in it. A defect regardless of expected scope.
    empty_dirs = {s: p for s, p in all_dirs.items() if s not in delivered}

    if args.slug:
        bundles = [b for b in bundles if b[1] == args.slug]
        empty_dirs = {s: p for s, p in empty_dirs.items() if s == args.slug}
        expected, expected_src = set(), "none"   # single-function mode: nothing to reconcile

    # Expected but no folder at all.
    absent = sorted(expected - set(all_dirs)) if expected else []

    if not bundles and not empty_dirs and not absent:
        payload = {
            "gate": "fail", "functionCount": 0, "functions": [],
            "error": (f"no bundle for slug '{args.slug}'" if args.slug
                      else "no requirements.md found anywhere under the bundle"),
        }
        print(json.dumps(payload, indent=2) if args.json else f"[FAIL] {payload['error']}")
        return 1

    results = []
    for spec_dir, slug in bundles:
        rep, metrics = verify_one(spec_dir, slug, args.source_root)
        entry = {
            "slug": slug,
            "specDir": spec_dir,
            "gate": rep.gate,
            "metrics": metrics,
            "checks": rep.checks,
            "failures": [c["check"] for c in rep.failures],
            "warnings": [f"{c['check']}: {c['detail']}" for c in rep.warnings],
        }
        results.append(entry)
        if args.write:
            with open(os.path.join(spec_dir, "verification.json"), "w", encoding="utf-8") as fh:
                json.dump(entry, fh, indent=2)

    # ---- function folders the generator created but never filled ----
    for slug in sorted(empty_dirs):
        path = empty_dirs[slug]
        detail = (f"spec/{slug}/ exists but has no requirements.md — contains: "
                  f"{describe_dir(path)}")
        results.append({
            "slug": slug,
            "specDir": path,
            "gate": "fail",
            "metrics": {"slug": slug},
            "checks": [{"check": "empty_function_folder", "status": FAIL, "detail": detail}],
            "failures": ["empty_function_folder"],
            "warnings": [],
        })

    # ---- functions that were expected and produced nothing at all ----
    for slug in absent:
        results.append({
            "slug": slug,
            "specDir": None,
            "gate": "fail",
            "metrics": {"slug": slug},
            "checks": [{"check": "function_missing_from_bundle", "status": FAIL,
                        "detail": f"expected function '{slug}' has no spec/ folder in this bundle "
                                  f"(expected list came from {expected_src})"}],
            "failures": ["function_missing_from_bundle"],
            "warnings": [],
        })

    results.sort(key=lambda r: r["slug"])

    overall = "fail" if any(r["gate"] == "fail" for r in results) else "pass"
    scope = {
        "expectedSource": expected_src,
        "expected": sorted(expected),
        "delivered": sorted(delivered),
        "emptyFolders": sorted(empty_dirs),
        "missingEntirely": absent,
        "enforced": bool(expected),
    }
    payload = {
        "gate": overall,
        "scope": scope,
        "functionCount": len(results),
        "delivered": len([r for r in results if r["gate"] == "pass"]),
        "passed": sum(1 for r in results if r["gate"] == "pass"),
        "failed": sum(1 for r in results if r["gate"] == "fail"),
        "functions": results,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        icon = {OK: "ok  ", WARN: "warn", FAIL: "FAIL", INFO: "info"}
        for r in results:
            if len(results) > 1:
                print(f"\n=== {r['slug']} ===")
            for c in r["checks"]:
                print(f"[{icon[c['status']]}] {c['check']}"
                      + (f" — {c['detail']}" if c["detail"] else ""))
            nf, nw = len(r["failures"]), len([c for c in r["checks"] if c["status"] == WARN])
            print(f"G4 {r['slug']}: {r['gate'].upper()}  ({nf} failure(s), {nw} warning(s))")
        if len(results) > 1:
            print(f"\nG4 overall: {overall.upper()} — "
                  f"{payload['passed']} passed, {payload['failed']} failed "
                  f"of {len(results)} function(s)")

        if scope["emptyFolders"]:
            print(f"\nEMPTY function folders ({len(scope['emptyFolders'])}): "
                  f"{', '.join(scope['emptyFolders'])}")
            print("  The generator created these slots and produced no specification for them.")
        if scope["missingEntirely"]:
            print(f"\nMISSING from bundle ({len(scope['missingEntirely'])}): "
                  f"{', '.join(scope['missingEntirely'])}")
        if scope["enforced"]:
            print(f"\nScope: {len(scope['delivered'])} delivered of "
                  f"{len(scope['expected'])} expected (source: {expected_src})")
        elif not args.slug:
            print("\nScope NOT enforced — pass --state or --expect so functions that produced "
                  "nothing cannot pass unnoticed.")

    if args.write:
        out = os.path.join(args.dir, "verification.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"wrote {out}", file=sys.stderr)

    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
