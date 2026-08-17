#!/usr/bin/env python3
"""Load every shared artifact once into a compact evidence pack.

Step 5 of the suite skill. Everything the 31 documents share is read here, so no document
re-reads a large artifact. Per-function rule detail is summarised, not dumped: a single
traceability.yaml can carry hundreds of rules and only the documents that detail a function
need its full rule list.
"""
import argparse, csv, json, os, re, glob, collections


def default_docs_root() -> str:
    """See build_coverage.default_docs_root — one run, one folder, stamped by the driver."""
    return os.environ.get("ATX_DOCS_ROOT") or os.path.join(".atx", "app-docs-latest")


_ap = argparse.ArgumentParser(description=__doc__)
_ap.add_argument("--mfre", default=".atx/mfre", help="upstream mainframe-reverse-engineering run")
_ap.add_argument("--docs-root", default=None,
                 help="documentation output root (default: $ATX_DOCS_ROOT)")
_args = _ap.parse_args()
if not _args.docs_root:
    _args.docs_root = default_docs_root()

M = _args.mfre
OUT = os.path.join(_args.docs_root, "00-manifest", "evidence-pack.json")

pack = {"functions": {}, "codeAnalysis": {}, "dataDictionary": {}, "dataLineage": {},
        "interfaces": {}, "source": {}, "run": {}}

st = json.load(open(f"{M}/state.json", encoding="utf-8"))
pack["run"] = {
    "runId": st.get("runId"),
    "job": (st.get("job") or {}).get("name"),
    "workspace": (st.get("workspace") or {}).get("name"),
    "account": (st.get("aws") or {}).get("accountId"),
    "region": (st.get("aws") or {}).get("region"),
    "sourceOrigin": (st.get("source") or {}).get("origin"),
    "fileCounts": (st.get("source") or {}).get("fileCounts"),
    "glossaryProvenance": (st.get("source") or {}).get("glossaryProvenance"),
    "gates": {k: v for k, v in (st.get("gates") or {}).items()
              if not k.endswith(("note", "blocker"))},
    "scope": (st.get("autonomy") or {}).get("scope"),
    "excluded": (st.get("autonomy") or {}).get("excludedInfrastructure"),
    "sharedEntryPoints": (st.get("discovery") or {}).get("sharedEntryPoints"),
}

# ---- catalog ----
for r in csv.DictReader(open(f"{M}/discovery/business_function.csv", newline="", encoding="utf-8")):
    n = (r.get("Name of business function") or "").strip()
    if not n:
        continue
    pack["functions"][n] = {
        "description": (r.get("Business descriptions") or "").strip(),
        "dataPaths": int(r["Number of data paths"]),
        "entryPoints": int(r["Number of entry points"]),
        "loc": int(r["Total LOC"]),
        "missingFiles": int(r["Number of potential missing files"]),
        "entryPointList": [e.strip() for e in r["List of entry points"].split(";") if e.strip()],
        "slug": n.replace(" ", ""),
    }

bfj = json.load(open(f"{M}/discovery/business_function.json", encoding="utf-8"))
for f in bfj.get("business_functions", []):
    n = f.get("name")
    if n in pack["functions"]:
        pack["functions"][n]["category"] = f.get("category")
        pack["interfaces"][n] = [i.get("target_bf") for i in (f.get("interfaces") or [])
                                 if isinstance(i, dict)]

# ---- per-function class + spec detail ----
fstate = st.get("functions") or {}
for n, fn in pack["functions"].items():
    s = fstate.get(n) or {}
    slug = fn["slug"]
    fn["status"] = s.get("status")
    fn["metrics"] = s.get("metrics") or {}
    fn["verification"] = s.get("verification") or {}
    excl = {e.get("name") for e in (pack["run"]["excluded"] or []) if isinstance(e, dict)}
    scope = set(pack["run"]["scope"] or [])
    spec = None
    for cand in (s.get("localPath"), os.path.join(M, "specs", slug)):
        if cand and os.path.isfile(os.path.join(cand, "spec", slug, "requirements.md")):
            spec = cand
            break
    if n in excl:
        fn["class"] = "excluded-infrastructure"
        fn["exclusionSignals"] = next((e.get("signals") for e in pack["run"]["excluded"]
                                       if e.get("name") == n), [])
    elif n not in scope:
        fn["class"] = "not-scoped"
    elif spec:
        fn["class"] = "delivered"
    else:
        fn["class"] = "scoped-no-spec"
    fn["specDir"] = spec

    if not spec:
        continue
    req_path = os.path.join(spec, "spec", slug, "requirements.md")
    txt = open(req_path, encoding="utf-8", errors="replace").read()
    fn["reqPath"] = req_path
    fn["sections"] = re.findall(r"^##\s+(\d+\.\s+.+)$", txt, re.M)
    fn["reqF"] = re.findall(r"^(REQ-F-\d+):\s*(.+)$", txt, re.M)[:400]
    fn["reqN"] = re.findall(r"^(REQ-N-\d+):\s*(.+)$", txt, re.M)
    fn["openQuestions"] = re.findall(r"^(OQ-\d+):\s*(.+)$", txt, re.M)

    tr_path = os.path.join(spec, "spec", slug, "traceability.yaml")
    if os.path.isfile(tr_path):
        ttxt = open(tr_path, encoding="utf-8", errors="replace").read()
        fn["tracePath"] = tr_path
        fn["programs"] = sorted(set(re.findall(r"^\s*program:\s*(\S+)\s*$", ttxt, re.M)))
        fn["dispositions"] = dict(collections.Counter(
            re.findall(r"^\s*disposition:\s*(\S+)\s*$", ttxt, re.M)))
        summ = {}
        for k in ("total_rules", "captured", "not_applicable", "unreachable", "delegated"):
            m = re.search(rf"^\s*{k}:\s*(\d+)\s*$", ttxt, re.M)
            if m:
                summ[k] = int(m.group(1))
        fn["traceSummary"] = summ

        # Full rule records, so a document can quote a rule and name its program.
        rules = {}
        for blk in re.split(r"\n(?=- rule_id:)", ttxt.split("rules:", 1)[-1]):
            rid = re.search(r"rule_id:\s*(\S+)", blk)
            if not rid:
                continue
            def g(k):
                m = re.search(rf"^\s*{k}:\s*(.+)$", blk, re.M)
                return m.group(1).strip().strip("'\"") if m else None
            rules[rid.group(1)] = {
                "program": g("program"), "disposition": g("disposition"),
                "rule_name": g("rule_name"), "reason": g("reason"),
                "rule_text": re.sub(r"\s+", " ", (g("rule_text") or ""))[:400],
            }
        fn["rules"] = rules

        # Reverse index: req_id -> rule_ids, which is authoritative for provenance.
        chain = {}
        rev = ttxt.split("\nrequirements:", 1)
        if len(rev) > 1:
            for blk in re.split(r"\n(?=- req_id:)", rev[1]):
                rq = re.search(r"req_id:\s*(REQ-[FN]-\d+)", blk)
                if not rq:
                    continue
                ids = re.findall(r"^\s*-\s*([0-9a-f_]{8,})\s*$", blk, re.M)
                chain[rq.group(1)] = ids
        fn["reqChain"] = chain

        # Precompute a citable chain string per requirement: REQ -> rule -> program
        cites = {}
        for rq, ids in chain.items():
            for rid in ids:
                r = rules.get(rid)
                if r and r.get("program"):
                    cites[rq] = {"rule": rid, "program": r["program"],
                                 "ruleName": r.get("rule_name")}
                    break
        fn["reqCitations"] = cites

# ---- code analysis ----
# The authoritative per-asset metrics live in assets_*.csv, which is the only artifact
# carrying Cyclomatic Complexity. The generic-analysis JSONs duplicate line counts without it.
CA = f"{M}/analysis/code-analysis"
ACR = f"{CA}/analyze_code_results"


def one(pattern):
    hits = sorted(glob.glob(pattern))
    return hits[0] if hits else None


assets = one(f"{ACR}/assets_*.csv")
rows = []
if assets:
    for r in csv.DictReader(open(assets, newline="", encoding="utf-8", errors="replace")):
        def num(k):
            try:
                return int(r.get(k) or 0)
            except ValueError:
                return None
        rows.append({
            "name": r.get("Name"), "path": r.get("Path"), "type": r.get("File type"),
            "complexity": num("Cyclomatic Complexity"), "totalLines": num("Total lines"),
            "effective": num("Effective Lines"), "comments": num("Comment Lines"),
        })
pack["codeAnalysis"]["assetsCsv"] = os.path.relpath(assets) if assets else None
pack["codeAnalysis"]["assetCount"] = len(rows)
pack["codeAnalysis"]["perFile"] = rows
cx = [r for r in rows if isinstance(r.get("complexity"), int) and r["complexity"] > 0]
pack["codeAnalysis"]["byComplexity"] = sorted(cx, key=lambda x: -x["complexity"])[:30]
pack["codeAnalysis"]["complexityStats"] = {
    "withComplexity": len(cx),
    "max": max((r["complexity"] for r in cx), default=None),
    "sum": sum(r["complexity"] for r in cx) or None,
}
pack["codeAnalysis"]["typeCounts"] = dict(collections.Counter(
    str(r["type"]) for r in rows if r.get("type")))
pack["codeAnalysis"]["locByType"] = dict(collections.Counter())
agg = collections.defaultdict(int)
for r in rows:
    if r.get("type") and isinstance(r.get("totalLines"), int):
        agg[str(r["type"])] += r["totalLines"]
pack["codeAnalysis"]["locByType"] = dict(agg)

# quality signals
issues = one(f"{CA}/codebase_issues_*.json")
if issues:
    pack["codeAnalysis"]["issuesPath"] = os.path.relpath(issues)
    pack["codeAnalysis"]["issues"] = []
    for i in json.load(open(issues, encoding="utf-8")):
        it = i.get("item") or {}
        pack["codeAnalysis"]["issues"].append({
            "name": it.get("name"), "severity": it.get("severity"),
            "description": it.get("description"), "impact": it.get("impact"),
            "action": it.get("action"),
            "fileCount": len(i.get("files") or []),
            "files": (i.get("files") or [])[:12],
        })

missing = one(f"{ACR}/missing_*.csv")
if missing:
    mr = list(csv.DictReader(open(missing, newline="", encoding="utf-8", errors="replace")))
    pack["codeAnalysis"]["missingPath"] = os.path.relpath(missing)
    pack["codeAnalysis"]["missingCount"] = len(mr)
    pack["codeAnalysis"]["missing"] = mr[:40]
    pack["codeAnalysis"]["missingByType"] = dict(collections.Counter(
        r.get("Type") for r in mr if r.get("Type")))

dup = one(f"{ACR}/duplicatedIds_*.json")
if dup:
    dj = json.load(open(dup, encoding="utf-8"))
    pack["codeAnalysis"]["duplicatedIdsPath"] = os.path.relpath(dup)
    pack["codeAnalysis"]["duplicatedIds"] = dj
    pack["codeAnalysis"]["duplicatedIdCount"] = len(dj) if hasattr(dj, "__len__") else None

deps = one(f"{ACR}/dependencies_*.json")
if deps:
    dj = json.load(open(deps, encoding="utf-8"))
    pack["codeAnalysis"]["dependenciesPath"] = os.path.relpath(deps)
    pack["codeAnalysis"]["dependencyNodeCount"] = len(dj)
    edge = 0
    bytype = collections.Counter()
    idx = {}
    for n in dj:
        if not isinstance(n, dict):
            continue
        ds = n.get("dependencies") or []
        edge += len(ds)
        bytype[str(n.get("type"))] += 1
        idx[n.get("name")] = {"type": n.get("type"), "path": n.get("path"),
                              "deps": [d.get("name") if isinstance(d, dict) else d for d in ds]}
    pack["codeAnalysis"]["dependencyEdgeCount"] = edge
    pack["codeAnalysis"]["dependencyNodeTypes"] = dict(bytype)
    pack["codeAnalysis"]["dependencyIndex"] = idx

sched = sorted(glob.glob(f"{ACR}/scheduler/**/*.json", recursive=True))
pack["codeAnalysis"]["schedulerFiles"] = [os.path.basename(p) for p in sched]

# ---- data dictionary + lineage ----
dd = glob.glob(f"{M}/analysis/data-analysis/**/data_dictionary_output/**/*.csv", recursive=True)
pack["dataDictionary"]["fileCount"] = len(dd)
pack["dataDictionary"]["files"] = [os.path.basename(p) for p in sorted(dd)]
if dd:
    sample = sorted(dd)[0]
    with open(sample, newline="", encoding="utf-8", errors="replace") as fh:
        rd = list(csv.reader(fh))
    pack["dataDictionary"]["sampleFile"] = os.path.relpath(sample)
    pack["dataDictionary"]["sampleHeader"] = rd[0] if rd else []
    pack["dataDictionary"]["sampleRows"] = rd[1:6]

dl = glob.glob(f"{M}/analysis/data-analysis/**/data_lineage_output/**/*", recursive=True)
dlf = [p for p in dl if os.path.isfile(p)]
pack["dataLineage"]["fileCount"] = len(dlf)
pack["dataLineage"]["files"] = [os.path.relpath(p) for p in sorted(dlf)][:40]
if dlf:
    s = sorted(dlf)[0]
    pack["dataLineage"]["sampleFile"] = os.path.relpath(s)
    try:
        head = open(s, encoding="utf-8", errors="replace").read(1200)
        pack["dataLineage"]["sampleHead"] = head
    except OSError:
        pass

# ---- workspace source parsing ----
# These four parsers exist to close the "Not extracted by this run" gap. The evidence was always
# present in the codebase; nothing was reading it. Each records member:line so a document can
# cite `source-read-verified` rather than a marker.

JCL_DIRS = ["app/**/*.jcl", "app/**/*.prc", "samples/**/*.jcl", "*.jcl"]


def _jcl_files():
    out = []
    for pat in JCL_DIRS:
        out += glob.glob(pat, recursive=True)
    return sorted(set(p for p in out if os.path.isfile(p)))


jcl = {}
for p in _jcl_files():
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
        jcl[os.path.basename(p)] = {"path": p, "steps": steps, "dds": dds,
                                    "cond": conds, "restart": restarts, "abend": aborts,
                                    "stepCount": len(steps), "ddCount": len(dds)}
pack["jcl"] = {
    "memberCount": len(jcl),
    "members": jcl,
    "totalSteps": sum(v["stepCount"] for v in jcl.values()),
    "totalDD": sum(v["ddCount"] for v in jcl.values()),
    "withCond": sorted(k for k, v in jcl.items() if v["cond"]),
    "withRestart": sorted(k for k, v in jcl.items() if v["restart"]),
    "utilities": dict(collections.Counter(
        s["invokes"] for v in jcl.values() for s in v["steps"]).most_common(20)),
}

# build / compile / link members, identified by the utilities they invoke
BUILD_PGMS = {"IGYCRCTL", "IEWL", "IEWBLINK", "DFHMAPS", "DFHECP1$", "DSNHPC", "ASMA90",
              "IKJEFT01", "IKJEFT1B", "DFHEAP1$"}
build = {}
for k, v in jcl.items():
    hits = [s for s in v["steps"] if s["invokes"] in BUILD_PGMS]
    if hits or re.search(r"CMP|COMPIL|LINK|BIND", k, re.I):
        build[k] = {"path": v["path"], "steps": v["steps"], "buildSteps": hits}
pack["buildJcl"] = {"memberCount": len(build), "members": build}

# BMS maps: mapset -> map -> fields with length, position and attributes
bms = {}
for p in sorted(glob.glob("app/**/*.bms", recursive=True) + glob.glob("*.bms")):
    try:
        txt = open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    lines = txt.splitlines()
    mapset = None
    maps = collections.OrderedDict()
    cur = None
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
            blk = ln
            j = i
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
        bms[os.path.basename(p)] = {"path": p, "mapset": mapset,
                                    "maps": {k: v for k, v in maps.items()}}
pack["bms"] = {
    "memberCount": len(bms), "members": bms,
    "mapCount": sum(len(v["maps"]) for v in bms.values()),
    "fieldCount": sum(len(f) for v in bms.values() for f in v["maps"].values()),
    "namedFieldCount": sum(1 for v in bms.values() for f in v["maps"].values()
                           for x in f if x["field"] != "(unnamed literal)"),
}

# LINKAGE SECTION: the called-program interface signature
link = {}
for p in sorted(glob.glob("app/**/*.cbl", recursive=True)):
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
            using = re.search(r"USING\s+([A-Z0-9\-, ]+)", ln)
            break
        m = re.match(r"\s*(\d\d)\s+([A-Z0-9\-]+)(?:\s+PIC\s+(\S+))?", ln)
        if m:
            items.append({"level": m.group(1), "name": m.group(2),
                          "pic": m.group(3).rstrip(".") if m.group(3) else None,
                          "line": i + 1})
    if items:
        link[os.path.basename(p)] = {"path": p, "items": items[:40],
                                     "itemCount": len(items),
                                     "line": start + 1}
pack["linkage"] = {"memberCount": len(link), "members": link,
                   "totalItems": sum(v["itemCount"] for v in link.values())}

# Error and exception handling as actually coded. Batch JCL COND= logic is job control and a
# different thing entirely; conflating the two put job-step conditions under API error handling.
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
eh, eh_tot = {}, collections.Counter()
for p in sorted(glob.glob("app/**/*.cbl", recursive=True)):
    try:
        lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        continue
    hits = collections.Counter()
    first = {}
    for i, ln in enumerate(lines, 1):
        u = ln.upper()
        for name, pat in EH_PATTERNS.items():
            if re.search(pat, u):
                hits[name] += 1
                first.setdefault(name, i)
    if hits:
        eh[os.path.basename(p)] = {"path": p, "counts": dict(hits), "firstLine": first,
                                   "total": sum(hits.values())}
        eh_tot.update(hits)
pack["errorHandling"] = {
    "programCount": len(eh), "members": eh,
    "byConstruct": dict(eh_tot.most_common()),
    "total": sum(eh_tot.values()),
}

# ---- source inventory (measured, not assumed) ----
EXT = ["cbl", "cob", "cpy", "jcl", "bms", "csd", "ddl", "dcl", "psb", "dbd", "mfs",
       "asm", "mac", "ca7", "prc", "proc", "sql", "pli", "rex", "txt"]
counts = {}
for e in EXT:
    n = len([p for p in glob.glob(f"app/**/*.{e}", recursive=True)
             + glob.glob(f"*.{e}")])
    if n:
        counts[e] = n
pack["source"]["extensionCounts"] = counts
# Named generically rather than listing one host's directory: this suite runs on several agent
# runtimes, each installing into its own dot-directory.
pack["source"]["note"] = ("Counted under app/ and the workspace root this run. Excludes .atx/ "
                          "and agent runtime directories.")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(pack, open(OUT, "w", encoding="utf-8"), indent=1)

d = sum(1 for f in pack["functions"].values() if f["class"] == "delivered")
print(f"evidence pack -> {OUT}")
print(f"  functions {len(pack['functions'])} ({d} delivered)")
print(f"  code-analysis per-file rows {len(pack['codeAnalysis']['perFile'])}, "
      f"with complexity {len(cx)}")
print(f"  data dictionary CSVs {pack['dataDictionary']['fileCount']}, "
      f"lineage files {pack['dataLineage']['fileCount']}")
print(f"  source extensions {counts}")
print(f"  jcl: {pack['jcl']['memberCount']} members, {pack['jcl']['totalSteps']} steps, "
      f"{pack['jcl']['totalDD']} DD, cond in {len(pack['jcl']['withCond'])}, "
      f"restart in {len(pack['jcl']['withRestart'])}")
print(f"  build jcl: {pack['buildJcl']['memberCount']} members")
print(f"  bms: {pack['bms']['memberCount']} members, {pack['bms']['mapCount']} maps, "
      f"{pack['bms']['namedFieldCount']} named fields")
print(f"  linkage: {pack['linkage']['memberCount']} programs, "
      f"{pack['linkage']['totalItems']} items")
print(f"  error handling: {pack['errorHandling']['programCount']} programs, "
      f"{pack['errorHandling']['total']} constructs, "
      f"{len(pack['errorHandling']['byConstruct'])} kinds")
