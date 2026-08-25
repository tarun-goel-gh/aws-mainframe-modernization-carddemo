#!/usr/bin/env python3
"""Step 4 — aggregate mcp-cache/ and any reused extraction tree into evidence-pack.json.

Usage:
  extract_evidence.py --workspace-root DIR [--extraction-root DIR] --docs-root DIR [--force]

Exit codes: 0 evidence-pack.json written | 1 no program-inventory.csv and no cached evidence of
any kind to aggregate | 2 bad usage

This is aggregation, not parsing, for anything that already went through a BobZ MCP tool this
run: DD entries, docgen JSON, Z Code Scan findings arrive as structured JSON in
`00-manifest/mcp-cache/{PROGRAM}/{tool}.json` (written by the agent, never by this script — no
script in this suite ever calls the MCP server) or as already-filed artifacts under a reused
`bob-z-knowledge-extract/` tree, whose existing provenance labels are carried forward unchanged.
The one legitimate text-mining left is JCL, BMS maps and LINKAGE SECTION source, which never go
through an MCP tool.

A program with no evidence for a given field simply has that field absent from its entry — this
script records the absence explicitly (`evidenceGaps`) rather than silently omitting the program.

No third-party dependencies.
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import re
import sys
import collections
from datetime import datetime, timezone

SCHEMA_VERSION = "1.0"
SKILL_ROOT = os.environ.get("BOBZ_SKILL_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))

PROVENANCE_VALUES = {
    "tool-verified",
    "narrative-per-program-not-tool-verified",
    "z-understand-verified",
}

# Collapse the four-value grounding-contract vocabulary a reused artifact may still carry (from a
# pre-MCP run, or from cobol-knowledge-extraction's own filed provenance labels) into the
# evidence-pack's narrower three-value vocabulary (bobz-v3-foundations.md §3, §0).
LEGACY_PROVENANCE_MAP = {
    "z-workflow-verified": "tool-verified",
    "source-read-verified": "tool-verified",
    "narrative-per-program-not-tool-verified": "narrative-per-program-not-tool-verified",
    "z-understand-verified": "z-understand-verified",
    "tool-verified": "tool-verified",
}

# Mcp-cache filenames, per bobz-v3-foundations.md §4e step 2 / SKILL.md Step 3.
CACHE_FILES = {
    "docgen-architect": "docgen-architect.json",
    "docgen-developer": "docgen-developer.json",
    "docgen-business": "docgen-business.json",
    "explain": "explain.json",
    "zcodescan": "zcodescan.json",
    "control-flow": "control-flow.json",
    "paragraphs": "paragraphs.json",
    "variables": "variables.json",
    "data-dictionary": "data-dictionary.json",
}

EVIDENCE_CATEGORIES = ("dataDictionary", "businessRules", "architectureNotes", "errorHandling",
                        "dependencies", "zCodeScan")


def sha256(path: str) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def read_text(path: str) -> str | None:
    if path and os.path.isfile(path):
        try:
            return open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            return None
    return None


def read_json(path: str):
    if path and os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (ValueError, OSError):
            return None
    return None


def normalise_provenance(raw) -> str:
    v = str(raw or "").strip()
    return LEGACY_PROVENANCE_MAP.get(v, "narrative-per-program-not-tool-verified")


def split_front_matter(text: str):
    """`---\\nkey: value\\n---\\nbody` front matter, exactly the shape
    cobol-knowledge-extraction files by-program markdown with. Returns (dict, body)."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, text[m.end():]


def infer_legacy_provenance(front_matter: dict) -> str:
    """A reused by-program markdown file rarely carries an explicit `provenance:` field (the
    v1.3.0 front-matter shape only has member/source_path/perspective/workflow/date/origin) —
    infer it from `workflow`/`origin`, carrying an explicit `provenance:` field forward verbatim
    if a v2.0.0 filer already wrote one. Ambiguous input defaults to the weaker, narrative label:
    understating trust is safe, overstating it is not."""
    if front_matter.get("provenance"):
        return normalise_provenance(front_matter["provenance"])
    workflow = (front_matter.get("workflow") or "").lower()
    origin = (front_matter.get("origin") or "").lower()
    if "fallback" in workflow or "ai" in origin:
        return "narrative-per-program-not-tool-verified"
    direct_tool_markers = ("generate_documentation", "generate documentation", "docgen-workflow",
                           "explain_code", "explain code", "explain-workflow", "z_code_scan",
                           "get_variables", "generate_data_dictionary")
    if any(t in workflow for t in direct_tool_markers):
        return "tool-verified"
    return "narrative-per-program-not-tool-verified"


def default_docs_root(workspace_root: str) -> str:
    return os.environ.get("BOBZ_DOCS_ROOT") or os.path.join(workspace_root, "bob-z-app-docs")


def resolve_manifest_dir(extraction_root, docs_root):
    candidates = []
    if extraction_root:
        candidates.append(os.path.join(extraction_root, "00-manifest"))
    candidates.append(os.path.join(docs_root, "00-manifest"))
    for c in candidates:
        if os.path.isfile(os.path.join(c, "program-inventory.csv")):
            return c
    return None


def read_csv_rows(path):
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))


def skill_version() -> str:
    p = os.path.join(SKILL_ROOT, "SKILL.md")
    txt = read_text(p) or ""
    m = re.search(r'^\s*version:\s*"?([\w.\-]+)"?', txt, re.M)
    return m.group(1) if m else "unknown"


# ---------------------------------------------------------------------------
# JCL / BMS / LINKAGE / error-handling — the one legitimate text-mining step left: these artifact
# types never go through an MCP tool (bobz-v3-foundations.md §3, §4e step 4).
# ---------------------------------------------------------------------------

def _glob(root, *patterns):
    out = []
    for pat in patterns:
        out += glob.glob(os.path.join(root, "**", pat), recursive=True)
        out += glob.glob(os.path.join(root, pat))
    return sorted(set(p for p in out if os.path.isfile(p)))


def parse_jcl(root):
    members = {}
    for p in _glob(root, "*.jcl", "*.prc", "*.proc"):
        try:
            lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        steps, dds, conds, restarts, aborts = [], [], [], [], []
        for i, ln in enumerate(lines, 1):
            if ln.startswith("//*") or not ln.startswith("//"):
                continue
            m = re.match(r"//(\S+)\s+EXEC\s+(?:PGM=|PROC=)?([A-Z0-9#$@.]+)", ln)
            if m and "EXEC" in ln:
                steps.append({"step": m.group(1), "invokes": m.group(2), "line": i})
            m = re.match(r"//(\S+)\s+DD\s+(.+)", ln)
            if m:
                dsn = re.search(r"DSN=([^,\s]+)", m.group(2))
                disp = re.search(r"DISP=\(?([^,)\s]+)", m.group(2))
                dds.append({"ddname": m.group(1), "dsn": dsn.group(1) if dsn else None,
                            "disp": disp.group(1) if disp else None, "line": i})
            for pat, bucket in ((r"COND=\(?([^\s]+)", conds), (r"RESTART=(\S+)", restarts),
                                (r"(ABEND|TYPRUN=\S+)", aborts)):
                mm = re.search(pat, ln)
                if mm:
                    bucket.append({"value": mm.group(1).rstrip(","), "line": i})
        if steps or dds:
            members[os.path.basename(p)] = {
                "path": os.path.relpath(p), "steps": steps, "dds": dds, "cond": conds,
                "restart": restarts, "abend": aborts, "stepCount": len(steps), "ddCount": len(dds),
            }
    return {
        "memberCount": len(members), "members": members,
        "totalSteps": sum(v["stepCount"] for v in members.values()),
        "totalDD": sum(v["ddCount"] for v in members.values()),
        "withCond": sorted(k for k, v in members.items() if v["cond"]),
        "withRestart": sorted(k for k, v in members.items() if v["restart"]),
        "utilities": dict(collections.Counter(
            s["invokes"] for v in members.values() for s in v["steps"]).most_common(20)),
    }


def parse_bms(root):
    members = {}
    for p in _glob(root, "*.bms"):
        try:
            lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        mapset, maps, cur = None, collections.OrderedDict(), None
        i = 0
        while i < len(lines):
            ln = lines[i]
            if ln.startswith("*"):
                i += 1
                continue
            m = re.match(r"(\S+)\s+DFHMSD", ln)
            if m:
                mapset = m.group(1)
            m = re.match(r"(\S+)\s+DFHMDI", ln)
            if m:
                cur = m.group(1)
                maps[cur] = []
            m = re.match(r"(\S*)\s*DFHMDF", ln)
            if m and cur:
                blk, j = ln, i
                while blk.rstrip().endswith("-") and j + 1 < len(lines):
                    j += 1
                    blk += " " + lines[j].strip()
                length = re.search(r"LENGTH=(\d+)", blk)
                pos = re.search(r"POS=\((\d+),(\d+)\)", blk)
                attrb = re.search(r"ATTRB=\(([^)]*)\)", blk)
                init = re.search(r"INITIAL='([^']*)'", blk)
                maps[cur].append({
                    "field": m.group(1) or "(unnamed literal)",
                    "length": int(length.group(1)) if length else None,
                    "row": int(pos.group(1)) if pos else None,
                    "col": int(pos.group(2)) if pos else None,
                    "attrb": attrb.group(1) if attrb else None,
                    "initial": init.group(1) if init else None,
                    "line": i + 1,
                })
                i = j
            i += 1
        if maps:
            members[os.path.basename(p)] = {"path": os.path.relpath(p), "mapset": mapset,
                                            "maps": {k: v for k, v in maps.items()}}
    return {
        "memberCount": len(members), "members": members,
        "mapCount": sum(len(v["maps"]) for v in members.values()),
        "fieldCount": sum(len(f) for v in members.values() for f in v["maps"].values()),
        "namedFieldCount": sum(1 for v in members.values() for f in v["maps"].values()
                               for x in f if x["field"] != "(unnamed literal)"),
    }


def parse_linkage(root):
    members = {}
    for p in _glob(root, "*.cbl", "*.cob", "*.cobol"):
        try:
            lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        start = None
        for i, ln in enumerate(lines):
            if re.search(r"\bLINKAGE\s+SECTION\b", ln):
                start = i
                break
        if start is None:
            continue
        items = []
        for i in range(start + 1, min(start + 200, len(lines))):
            ln = lines[i]
            if re.search(r"\bPROCEDURE\s+DIVISION\b", ln):
                break
            m = re.match(r"\s*(\d\d)\s+([A-Z0-9\-]+)(?:\s+PIC\s+(\S+))?", ln)
            if m:
                items.append({"level": m.group(1), "name": m.group(2),
                              "pic": m.group(3).rstrip(".") if m.group(3) else None,
                              "line": i + 1})
        if items:
            members[os.path.splitext(os.path.basename(p))[0].upper()] = {
                "path": os.path.relpath(p), "items": items[:40], "itemCount": len(items),
                "line": start + 1,
            }
    return {"memberCount": len(members), "members": members,
            "totalItems": sum(v["itemCount"] for v in members.values())}


EH_PATTERNS = {
    "ON SIZE ERROR": r"\bON\s+SIZE\s+ERROR\b",
    "INVALID KEY": r"\bINVALID\s+KEY\b",
    "AT END": r"\bAT\s+END\b",
    "EXEC CICS HANDLE": r"EXEC\s+CICS\s+HANDLE",
    "RESP check": r"\bRESP\s*\(",
    "ABEND": r"\bABEND\b",
    "FILE STATUS": r"\bFILE\s+STATUS\b",
    "NOT INVALID KEY": r"\bNOT\s+INVALID\s+KEY\b",
}


def parse_error_handling_constructs(root):
    members, totals = {}, collections.Counter()
    for p in _glob(root, "*.cbl", "*.cob", "*.cobol"):
        try:
            lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        hits, first = collections.Counter(), {}
        for i, ln in enumerate(lines, 1):
            u = ln.upper()
            for name, pat in EH_PATTERNS.items():
                if re.search(pat, u):
                    hits[name] += 1
                    first.setdefault(name, i)
        if hits:
            prog = os.path.splitext(os.path.basename(p))[0].upper()
            members[prog] = {"path": os.path.relpath(p), "counts": dict(hits), "firstLine": first,
                             "total": sum(hits.values())}
            totals.update(hits)
    return {"programCount": len(members), "members": members,
            "byConstruct": dict(totals.most_common()), "total": sum(totals.values())}


def build_jcl_job_map(jcl: dict) -> list[dict]:
    out = []
    for job, v in sorted(jcl["members"].items()):
        for s in v["steps"]:
            out.append({"job": job, "step": s["step"], "invokes": s["invokes"],
                        "provenance": "tool-verified",
                        "source": "regex parse of JCL member (this run) — deterministic, no MCP "
                                  "tool covers JCL"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", default=".")
    ap.add_argument("--extraction-root", default=None)
    ap.add_argument("--docs-root", required=True)
    ap.add_argument("--force", action="store_true",
                    help="re-aggregate even if evidence-pack.json is newer than every input")
    args = ap.parse_args()

    workspace_root = args.workspace_root
    extraction_root = args.extraction_root
    if extraction_root is None:
        cand = os.path.join(workspace_root, "bob-z-knowledge-extract")
        extraction_root = cand if os.path.isdir(cand) else None
    docs_root = args.docs_root
    manifest_out_dir = os.path.join(docs_root, "00-manifest")
    cache_root = os.path.join(manifest_out_dir, "mcp-cache")
    out_path = os.path.join(manifest_out_dir, "evidence-pack.json")

    manifest_dir = resolve_manifest_dir(extraction_root, docs_root)
    inv_rows = read_csv_rows(os.path.join(manifest_dir, "program-inventory.csv")) if manifest_dir else []
    status_rows = {}
    if manifest_dir:
        for r in read_csv_rows(os.path.join(manifest_dir, "extraction-status.csv")):
            n = (r.get("program_name") or "").strip()
            if n:
                status_rows[n] = r

    program_names = set(r.get("program_name", "").strip() for r in inv_rows if r.get("program_name"))

    have_cache = os.path.isdir(cache_root)
    have_extraction_artifacts = bool(extraction_root and any(
        os.path.isdir(os.path.join(extraction_root, d)) for d in
        ("02-business-rules", "01-application-architecture", "10-error-handling",
         "03-data-structures", "11-code-quality", "05-dependencies", "08-jcl-batch")))

    if not program_names:
        # Fall back to whatever program names any cache actually names.
        if have_cache:
            program_names |= set(d for d in os.listdir(cache_root)
                                  if os.path.isdir(os.path.join(cache_root, d)))
        if extraction_root:
            for sub, suffix in (("02-business-rules/by-program", ".md"),
                                 ("01-application-architecture", "-arch.md"),
                                 ("03-data-structures/data-dictionary/by-program", "-DD.json")):
                d = os.path.join(extraction_root, sub)
                if os.path.isdir(d):
                    for fn in os.listdir(d):
                        if fn.endswith(suffix):
                            program_names.add(fn[: -len(suffix)])
        program_names |= set(status_rows)

    if not program_names and not have_cache and not have_extraction_artifacts:
        print("BLOCKED: no program-inventory.csv and no cached evidence of any kind to "
              "aggregate — run cobol-knowledge-extraction's build_inventory.py, or gather at "
              "least one MCP tool result into mcp-cache/, before running this script.",
              file=sys.stderr)
        return 1

    # ---- staleness short-circuit ----
    inputs = []
    if manifest_dir:
        inputs += [os.path.join(manifest_dir, "program-inventory.csv"),
                   os.path.join(manifest_dir, "extraction-status.csv"),
                   os.path.join(manifest_dir, "extraction-manifest.json")]
    probe_path = os.path.join(manifest_out_dir, "mcp-capability-probe.json")
    inputs.append(probe_path)
    if have_cache:
        for dirpath, _dirs, files in os.walk(cache_root):
            inputs += [os.path.join(dirpath, f) for f in files]
    if extraction_root:
        for dirpath, _dirs, files in os.walk(extraction_root):
            inputs += [os.path.join(dirpath, f) for f in files]
    newest_input = 0.0
    for p in inputs:
        try:
            newest_input = max(newest_input, os.path.getmtime(p))
        except OSError:
            continue
    if not args.force and os.path.isfile(out_path) and newest_input and \
            os.path.getmtime(out_path) >= newest_input:
        print(f"{out_path} is already newer than every input — nothing to re-aggregate "
              f"(use --force to override)")
        return 0

    inv_by_name = {r["program_name"].strip(): r for r in inv_rows if r.get("program_name")}

    probe = read_json(probe_path) or {}
    pack = {
        "schemaVersion": SCHEMA_VERSION,
        "skillVersion": skill_version(),
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workspaceRoot": workspace_root,
        "docsRoot": docs_root,
        "extractionRoot": extraction_root,
        "mcp": {
            "reachable": probe.get("mcpReachable") is True,
            "serverVersion": probe.get("mcpServerVersion"),
            "zUnderstandConfigured": probe.get("zUnderstandConfigured") is True,
            "probeFile": os.path.relpath(probe_path) if os.path.isfile(probe_path) else None,
        },
        "programs": {},
        "application": {},
    }

    gaps: dict[str, list[str]] = {}

    for name in sorted(program_names):
        inv = inv_by_name.get(name, {})
        st = status_rows.get(name, {})
        entry: dict = {}
        if inv.get("file_path"):
            entry["filePath"] = inv["file_path"]
            abspath = os.path.join(workspace_root, inv["file_path"])
            if os.path.isfile(abspath):
                entry["sizeBytes"] = os.path.getsize(abspath)
        if inv.get("language"):
            entry["language"] = inv["language"]

        pcache = os.path.join(cache_root, name)

        # dataDictionary
        dd_cache = read_json(os.path.join(pcache, CACHE_FILES["data-dictionary"]))
        if dd_cache is not None:
            ent = dd_cache.get("entries") if isinstance(dd_cache, dict) else dd_cache
            entry["dataDictionary"] = {
                "provenance": "tool-verified",
                "source": "get_variables + generate_data_dictionary",
                "entries": ent if isinstance(ent, list) else [],
            }
        else:
            ddp = os.path.join(extraction_root or "", "03-data-structures", "data-dictionary",
                               "by-program", f"{name}-DD.json") if extraction_root else None
            ddj = read_json(ddp) if ddp else None
            if ddj is not None:
                ent = ddj.get("entries") if isinstance(ddj, dict) else ddj
                entry["dataDictionary"] = {
                    "provenance": normalise_provenance(
                        (ddj.get("provenance") if isinstance(ddj, dict) else None)
                        or "tool-verified"),
                    "source": "cobol-knowledge-extraction by-program data dictionary (reused)",
                    "entries": ent if isinstance(ent, list) else [],
                }

        # businessRules / architectureNotes / errorHandling (narrative, from docgen)
        narrative_map = (
            ("businessRules", "docgen-business", "generate_documentation(perspective=business)",
             "02-business-rules/by-program/{n}.md"),
            ("architectureNotes", "docgen-architect", "generate_documentation(perspective=architect)",
             "01-application-architecture/{n}-arch.md"),
            ("errorHandling", "docgen-developer", "generate_documentation(perspective=developer)",
             "10-error-handling/exception-paths-by-program/{n}.md"),
        )
        for field, cache_key, tool_source, rel_tpl in narrative_map:
            cached = read_json(os.path.join(pcache, CACHE_FILES[cache_key]))
            if cached is not None:
                text = cached.get("text") if isinstance(cached, dict) else str(cached)
                entry[field] = {"provenance": "tool-verified", "source": tool_source,
                                "text": text or ""}
                continue
            if extraction_root:
                rel = rel_tpl.format(n=name)
                p = os.path.join(extraction_root, rel)
                raw = read_text(p)
                if raw is not None:
                    fm, body = split_front_matter(raw)
                    entry[field] = {
                        "provenance": infer_legacy_provenance(fm),
                        "source": f"cobol-knowledge-extraction {rel} (reused)",
                        "text": body.strip(),
                    }

        # explain
        explain_cache = read_json(os.path.join(pcache, CACHE_FILES["explain"]))
        if explain_cache is not None:
            paras = explain_cache.get("paragraphs") if isinstance(explain_cache, dict) else None
            entry["explain"] = {"provenance": "tool-verified", "source": "explain_code",
                                "paragraphs": paras or {}}

        # codeFlow
        code_flow = {}
        paras_cache = read_json(os.path.join(pcache, CACHE_FILES["paragraphs"]))
        if paras_cache is not None:
            items = paras_cache.get("items") if isinstance(paras_cache, dict) else paras_cache
            code_flow["paragraphs"] = {"provenance": "tool-verified", "source": "get_paragraphs",
                                       "items": items if isinstance(items, list) else []}
        cfg_cache = read_json(os.path.join(pcache, CACHE_FILES["control-flow"]))
        if cfg_cache is not None:
            graph = cfg_cache.get("graph") if isinstance(cfg_cache, dict) else cfg_cache
            code_flow["controlFlow"] = {"provenance": "tool-verified", "source": "get_control_flow",
                                        "graph": graph if isinstance(graph, dict) else {}}
        if code_flow:
            entry["codeFlow"] = code_flow

        # dependencies — internal-dependencies.json entries owned by this program
        deps = []
        if extraction_root:
            dep_all = read_json(os.path.join(extraction_root, "05-dependencies",
                                             "internal-dependencies.json"))
            if isinstance(dep_all, list):
                for d in dep_all:
                    if not isinstance(d, dict):
                        continue
                    owner = d.get("program") or d.get("source") or d.get("from") or d.get("caller")
                    if owner != name:
                        continue
                    target = d.get("target") or d.get("to") or d.get("callee") or d.get("dependency")
                    kind = d.get("kind") or d.get("type") or "CALL"
                    deps.append({
                        "target": target,
                        "kind": kind,
                        "provenance": normalise_provenance(d.get("provenance")),
                        "source": d.get("source_label") or "05-dependencies/internal-dependencies.json "
                                                            "(reused)",
                    })
        if deps:
            entry["dependencies"] = deps

        # zCodeScan
        zcs_cache = read_json(os.path.join(pcache, CACHE_FILES["zcodescan"]))
        if zcs_cache is not None:
            findings = zcs_cache.get("findings") if isinstance(zcs_cache, dict) else zcs_cache
            complexity = zcs_cache.get("complexity") if isinstance(zcs_cache, dict) else None
            entry["zCodeScan"] = {"provenance": "tool-verified", "source": "z_code_scan",
                                  "findings": findings if isinstance(findings, list) else [],
                                  "complexity": complexity}
        elif extraction_root:
            p = os.path.join(extraction_root, "11-code-quality", "zcodescan-findings",
                             f"{name}.json")
            zj = read_json(p)
            if zj is not None:
                findings = zj.get("findings") if isinstance(zj, dict) else zj
                complexity = zj.get("complexity") if isinstance(zj, dict) else None
                entry["zCodeScan"] = {"provenance": "tool-verified",
                                      "source": "z_code_scan (reused via cobol-knowledge-extraction)",
                                      "findings": findings if isinstance(findings, list) else [],
                                      "complexity": complexity}

        pack["programs"][name] = entry

        missing = [c for c in EVIDENCE_CATEGORIES if c not in entry]
        if missing:
            gaps[name] = missing

    pack["evidenceGaps"] = gaps

    # ---- application aggregates ----
    app = pack["application"]

    # JCL job-to-program map: prefer the extraction skill's own already-filed map (carrying its
    # provenance forward unchanged), else build it fresh from a deterministic regex pass.
    jcl_map = None
    if extraction_root:
        p = os.path.join(extraction_root, "08-jcl-batch", "job-to-program-map.json")
        jcl_map = read_json(p)
    if isinstance(jcl_map, list):
        app["jclJobToProgramMap"] = [
            {**e, "provenance": normalise_provenance(e.get("provenance"))}
            for e in jcl_map if isinstance(e, dict)
        ]
        app["jclJobToProgramMapSource"] = "reused from cobol-knowledge-extraction"
    else:
        jcl = parse_jcl(workspace_root)
        app["jclJobToProgramMap"] = build_jcl_job_map(jcl)
        app["jcl"] = jcl

    app["bms"] = parse_bms(workspace_root)
    app["linkage"] = parse_linkage(workspace_root)
    app["errorHandlingConstructs"] = parse_error_handling_constructs(workspace_root)

    complexity_ranking = []
    for name, entry in pack["programs"].items():
        zcs = entry.get("zCodeScan")
        if zcs and zcs.get("complexity") is not None:
            complexity_ranking.append({"programName": name, "complexity": zcs["complexity"],
                                       "source": "z_code_scan"})
    complexity_ranking.sort(key=lambda r: (-r["complexity"], r["programName"]))
    app["complexityRanking"] = complexity_ranking

    scanned = [n for n, e in pack["programs"].items() if e.get("zCodeScan")]
    all_findings = [f for n in scanned for f in (pack["programs"][n]["zCodeScan"].get("findings") or [])]
    by_sev = collections.Counter()
    for f in all_findings:
        if isinstance(f, dict):
            sev = str(f.get("severity") or "unknown").lower()
            by_sev[sev] += 1
    app["zCodeScanSummary"] = {
        "provenance": "tool-verified" if scanned else "narrative-per-program-not-tool-verified",
        "programsScanned": len(scanned),
        "findingsTotal": len(all_findings),
        "bySeverity": dict(by_sev),
    }

    dd_master_path = None
    dd_entry_count = 0
    if extraction_root:
        p = os.path.join(extraction_root, "03-data-structures", "data-dictionary", "DD-master.json")
        j = read_json(p)
        if j is not None:
            dd_master_path = os.path.relpath(p)
            dd_entry_count = len(j.get("entries", [])) if isinstance(j, dict) else (
                len(j) if isinstance(j, list) else 0)
    if dd_master_path is None:
        p = os.path.join(workspace_root, "bobz", "DD.json")
        j = read_json(p)
        if j is not None:
            dd_master_path = os.path.relpath(p)
            dd_entry_count = len(j.get("entries", [])) if isinstance(j, dict) else (
                len(j) if isinstance(j, list) else 0)
    synced_marker = os.path.join(cache_root, "_project", "sync-data-dictionary.json")
    app["dataDictionaryMaster"] = {
        "provenance": "tool-verified" if dd_master_path else "narrative-per-program-not-tool-verified",
        "path": dd_master_path,
        "entryCount": dd_entry_count,
        "syncedViaZUnderstand": os.path.isfile(synced_marker),
    }

    os.makedirs(manifest_out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(pack, fh, indent=1)

    n_gaps = sum(len(v) for v in gaps.values())
    print(f"evidence pack -> {out_path}")
    print(f"  programs {len(pack['programs'])}, evidence gaps recorded for "
          f"{len(gaps)} program(s), {n_gaps} field(s) total")
    print(f"  jcl job map entries: {len(app['jclJobToProgramMap'])}")
    print(f"  bms mapsets: {app['bms']['memberCount']}, linkage programs: "
          f"{app['linkage']['memberCount']}")
    print(f"  z code scan: {app['zCodeScanSummary']['programsScanned']} programs scanned, "
          f"{app['zCodeScanSummary']['findingsTotal']} findings")
    print(f"  data dictionary master: {app['dataDictionaryMaster']['entryCount']} entries "
          f"({app['dataDictionaryMaster']['path'] or 'not found'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
