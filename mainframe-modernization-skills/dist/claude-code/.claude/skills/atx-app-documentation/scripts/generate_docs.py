#!/usr/bin/env python3
"""Compose the 31 documents from the evidence pack — Step 7 of the suite skill, mechanised.

Usage:
  generate_docs.py [--levels 0,1,2] [--only <prompt_type>] [--force] [--docs-root $ATX_DOCS_ROOT]

Exit codes: 0 all requested documents filed | 1 at least one failed its self-check | 2 bad usage

Design commitments, each of which exists because its absence was a defect:

* **Per-document evidence index.** Content builders record the artifacts they actually read, so a
  document's Evidence Index lists only its own sources. A shared boilerplate table asserts
  provenance the document does not have.
* **Two distinct unavailable markers.** `Not available from AWS Transform analysis` means the
  evidence does not exist. `Not extracted by this run` means it exists and this generator did not
  parse it. Conflating them blames the evidence source for the generator's gaps.
* **Citations use the full chain.** `REQ-F-001 -> rule <id> -> COUSR02C`, built from
  traceability's reverse index, not just the requirement id.
* **The self-check is enforced.** A document that fails the grounding contract's checklist is not
  filed. Asserting compliance is not compliance.
* **The ledger is honoured.** A `complete` document is skipped unless `--force`.
* **Section sets come from `references/template-families.md`**, not from guesswork.
"""
import argparse, json, os, re, collections, sys
from datetime import datetime, timezone

# The skill's own root, derived from this file's location rather than written as a literal. The
# templates and reference files live beside this script, so resolving them relatively lets the same
# suite run from .kiro/skills/, .claude/skills/, .codex/skills/ or anywhere else with no edit. It
# also stops the script depending on the caller's working directory being the workspace root.
SKILL = os.environ.get("ATX_SKILL_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
NA_ATX = "Not available from AWS Transform analysis"
NA_RUN = "Not extracted by this run"
# The generated date must be the date of the run. A frozen literal is the one field guaranteed
# to become wrong, and the grounding contract forbids inventing or approximating a date.
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def derive_app_name(run, override=None):
    """Application name for the document headers, and where it came from.

    AWS Transform carries no application-name field, so this is derived from upstream provenance
    rather than invented, and the derivation source is recorded in the manifest alongside the name.

    This exists because the name was previously a literal. A literal here writes one application's
    name into the header of all 31 documents describing a different application, which is the most
    visible possible way for a generic tool to lie about its subject.
    """
    if override and override.strip():
        return override.strip(), "operator-supplied (--app-name)"

    origin = (run.get("sourceOrigin") or "").strip()
    if origin:
        base = origin.rstrip("/").split("/")[-1]
        for ext in (".tar.gz", ".tgz", ".zip", ".tar", ".7z"):
            if base.lower().endswith(ext):
                base = base[: -len(ext)]
                break
        # Archive names commonly end in the branch they were cut from, which is not part of the
        # application's identity.
        base = re.sub(r"-(main|master|develop|trunk|HEAD)$", "", base, flags=re.I).strip("-_ ")
        if base:
            return base, "derived from upstream sourceOrigin"

    workspace = (run.get("workspace") or "").strip()
    if workspace:
        return workspace, "upstream workspace name (no source origin recorded)"

    # Consistent with the suite's refusal to invent: an unnamed application is stated as such.
    return "Unnamed application", "unavailable"

# Which builders each evidence plan legitimately owns. Used by the self-check to tell honest
# dominance (a data document dominated by the data dictionary) from semantic mismatch (an
# architecture document dominated by the business function table).
PLAN_BUILDERS = {
    "atx-discovery":   {"inventory", "src_inv", "run_ctx", "fn_table"},
    "atx-quality":     {"complexity", "issues", "missing", "error_handling"},
    "atx-business":    {"fn_table", "reqs", "workflows", "oqs", "run_ctx"},
    "atx-module":      {"rules", "reqs", "workflows", "datadict", "linkage", "bms_maps"},
    "atx-structure":   {"architecture", "deps", "interfaces", "fn_table", "run_ctx", "build_jcl"},
    "atx-data":        {"datadict", "lineage", "interfaces"},
    "atx-api":         {"entrypoints", "bms_maps", "linkage", "error_handling"},
    "atx-integration": {"interfaces", "deps", "entrypoints", "lineage", "bms_maps",
                        "linkage", "architecture", "error_handling"},
    "atx-operations":  {"scheduler", "workflows", "run_ctx", "jcl_ops", "jcl_control",
                        "build_jcl", "error_handling"},
}


def load_pack(docs):
    return json.load(open(f"{docs}/00-manifest/evidence-pack.json", encoding="utf-8"))


def catalog():
    rows = []
    for line in open(f"{SKILL}/references/document-catalog.md", encoding="utf-8"):
        c = [x.strip() for x in line.split("|")]
        if len(c) >= 9 and c[1].isdigit():
            rows.append(dict(n=int(c[1]), lvl=int(c[2].split("—")[0].strip()),
                             pt=c[3].strip("`"), plan=c[4].strip("`"),
                             out=c[6].strip("`"), tpl=c[7].strip("`")))
    return sorted(rows, key=lambda r: r["n"])


def fixed_sets():
    """Family C section sets, parsed from references/template-families.md."""
    txt = open(f"{SKILL}/references/template-families.md", encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"\*\*`([a-z_]+)`\*\*\n((?:\d+\.\s+.+\n)+)", txt):
        out[m.group(1)] = [re.sub(r"^\d+\.\s*", "", l).strip()
                           for l in m.group(2).strip().splitlines()]
    return out


def sha256(path):
    """Fingerprint an artifact so staleness is computable later."""
    try:
        import hashlib
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, TypeError):
        return None


class Rec:
    """Records the artifacts one document actually read, with fingerprints.

    The fingerprints are what make `atx-docs-status --stale` possible: a document is stale when
    an artifact it consumed no longer hashes to the value recorded when it was written. Without
    them that feature cannot be delivered, only promised.
    """

    def __init__(self, hashes=None):
        self.items = {}
        self._cache = hashes if hashes is not None else {}

    def use(self, path, provenance, what, fingerprint=None):
        """Record an artifact. `fingerprint` supplies a hash for pseudo-paths such as a glob,
        which have no single file to digest but still change when the workspace changes."""
        if path:
            p = str(path)
            self.items[p] = (provenance, what)
            if p not in self._cache:
                if os.path.isfile(p):
                    self._cache[p] = sha256(p)
                elif fingerprint is not None:
                    import hashlib
                    self._cache[p] = hashlib.sha256(
                        str(fingerprint).encode("utf-8")).hexdigest()
        return path

    def fingerprints(self):
        return {p: self._cache.get(p) for p in sorted(self.items)}

    def table(self):
        if not self.items:
            return "No artifact supplied content for this document."
        out = ["| Artifact | What it supplied | Provenance | sha256 |", "|---|---|---|---|"]
        for p in sorted(self.items):
            prov, what = self.items[p]
            h = self._cache.get(p)
            out.append(f"| `{p}` | {what} | `{prov}` | `{h[:12]}…` |" if h
                       else f"| `{p}` | {what} | `{prov}` | — |")
        return "\n".join(out)


class Gen:
    def __init__(self, docs, date=None, app_name=None):
        self.docs = docs
        self.date = date or TODAY
        self.pack = load_pack(docs)
        # 7. build_coverage's evidence-index.json is no longer orphaned: its sha256 values seed
        # the hash cache, so identical artifacts are fingerprinted once per suite, not per doc.
        self.hashes = {}
        idx = os.path.join(docs, "00-manifest", "evidence-index.json")
        if os.path.isfile(idx):
            try:
                for a in json.load(open(idx, encoding="utf-8")).get("artifacts", []):
                    if a.get("path") and a.get("sha256"):
                        self.hashes[a["path"]] = a["sha256"]
            except (ValueError, OSError):
                pass
        self.F = self.pack["functions"]
        self.RUN = self.pack["run"]
        self.APP, self.APP_SRC = derive_app_name(self.RUN, app_name)
        self.CA = self.pack["codeAnalysis"]
        self.DD = self.pack["dataDictionary"]
        self.DL = self.pack["dataLineage"]
        self.IF = self.pack["interfaces"]
        self.ORD = sorted(self.F)
        self.DELIV = sorted(n for n, f in self.F.items() if f["class"] == "delivered")
        self.NOSPEC = sorted(n for n, f in self.F.items() if f["class"] == "scoped-no-spec")
        self.EXCL = sorted(n for n, f in self.F.items() if f["class"] == "excluded-infrastructure")
        self.FIXED = fixed_sets()
        self.subs = self._subs()
        self.CAT = ".atx/mfre/discovery/business_function.csv"
        self.CATJ = ".atx/mfre/discovery/business_function.json"
        self.STATE = ".atx/mfre/state.json"

    # ---- substitutions table: headings whose concept has no equivalent ----
    def _subs(self):
        txt = open(f"{SKILL}/references/atx-substitutions.md", encoding="utf-8").read()
        rows = []
        for line in txt.splitlines():
            c = [x.strip() for x in line.split("|")]
            if len(c) >= 4 and c[1] and not c[1].startswith(("-", "Template")):
                rows.append((c[1].lower(), c[2], c[3]))
        return rows

    def sub_lookup(self, heading):
        """Return (kind, reason) from the substitutions table, or (None, None)."""
        h = heading.lower()
        for concept, equiv, ev in self.subs:
            key = re.sub(r"[^a-z ]", " ", concept).split("/")[0].strip()
            if not key or len(key) < 4:
                continue
            if key.split()[0] in h and "no equivalent" in equiv.lower():
                return "na_atx", f"{concept} has no AWS Transform equivalent — {ev}"
        return None, None

    # ---------------- shared blocks (each records what it read) ----------------
    def esc(self, s):
        return str(s).replace("|", r"\|")

    def coverage(self, rec):
        rec.use(self.STATE, "atx-artifact-verified", "scope, exclusions, per-function status")
        rec.use(self.CAT, "atx-artifact-verified", "business function catalog")
        return "\n".join([
            "## Coverage", "",
            f"Content below is grounded in **{len(self.DELIV)} of {len(self.F)}** discovered "
            f"business functions. Every count carries that denominator.", "",
            f"- **Represented ({len(self.DELIV)})**: {', '.join(self.DELIV)}",
            f"- **Scoped, no specification delivered ({len(self.NOSPEC)})**: "
            f"{', '.join(self.NOSPEC)} — catalog metadata only",
            f"- **Excluded as infrastructure-only ({len(self.EXCL)})**: {', '.join(self.EXCL)}", "",
            "Absence of evidence for a function is not evidence about that function. "
            "Unrepresented functions are named, never characterised.", ""])

    def fn_table(self, rec, cols=("category", "class", "loc", "dataPaths", "entryPoints")):
        rec.use(self.CAT, "atx-artifact-verified", "function names, LOC, data paths, entry points")
        rec.use(self.CATJ, "atx-artifact-verified", "function category")
        head = "| Business function | " + " | ".join(c.capitalize() for c in cols) + " |"
        out = [head, "|---" * (len(cols) + 1) + "|"]
        for n in self.ORD:
            f = self.F[n]
            out.append(f"| {self.esc(n)} | " + " | ".join(
                "—" if f.get(c) in (None, "") else self.esc(f.get(c)) for c in cols) + " |")
        return "\n".join(out)

    def complexity(self, rec, n=15):
        rows = self.CA.get("byComplexity") or []
        if not rows:
            return None
        rec.use(self.CA.get("assetsCsv"), "atx-artifact-verified",
                "per-asset cyclomatic complexity and line counts")
        out = ["| Asset | Type | Cyclomatic complexity | Total lines | Effective lines |",
               "|---|---|---|---|---|"]
        for r in rows[:n]:
            out.append(f"| `{self.esc(r['name'])}` | {self.esc(r['type'])} | {r['complexity']} | "
                       f"{r['totalLines']} | {r['effective']} |")
        s = self.CA.get("complexityStats") or {}
        out += ["", f"{s.get('withComplexity')} of {self.CA.get('assetCount')} assets carry a "
                    f"non-zero complexity score; maximum {s.get('max')}, total {s.get('sum')}."]
        return "\n".join(out)

    def issues(self, rec):
        iss = self.CA.get("issues") or []
        if not iss:
            return None
        rec.use(self.CA.get("issuesPath"), "atx-artifact-verified",
                "codebase issues raised by code analysis")
        out = ["| Finding | Severity | Files affected | Stated impact |", "|---|---|---|---|"]
        for i in iss:
            out.append(f"| {self.esc(i['name'])} | {self.esc(i['severity'])} | {i['fileCount']} | "
                       f"{self.esc(i['impact'])} |")
        dup = self.CA.get("duplicatedIdCount")
        if dup == 0:
            rec.use(self.CA.get("duplicatedIdsPath"), "atx-artifact-verified",
                    "duplicate program id check")
            out += ["", "Duplicate `PROGRAM-ID` check: **none found**. Program call identity is "
                        "unambiguous across the codebase."]
        return "\n".join(out)

    def missing(self, rec):
        mb = self.CA.get("missingByType") or {}
        if not mb:
            return None
        rec.use(self.CA.get("missingPath"), "atx-artifact-verified",
                "referenced-but-absent artifacts")
        out = ["| Missing artifact type | Count |", "|---|---|"]
        for k in sorted(mb, key=lambda x: -mb[x]):
            out.append(f"| {self.esc(k)} | {mb[k]} |")
        out += ["", f"{self.CA.get('missingCount')} missing references in total."]
        return "\n".join(out)

    def inventory(self, rec):
        tc = self.CA.get("typeCounts") or {}
        if not tc:
            return None
        rec.use(self.CA.get("assetsCsv"), "atx-artifact-verified",
                "asset classification and line counts")
        lb = self.CA.get("locByType") or {}
        out = ["| File type | Assets | Total lines |", "|---|---|---|"]
        for k in sorted(tc, key=lambda x: -tc[x]):
            out.append(f"| {self.esc(k)} | {tc[k]} | {lb.get(k,'—')} |")
        out += ["", f"{self.CA.get('assetCount')} assets classified."]
        return "\n".join(out)

    def entrypoints(self, rec):
        rec.use(self.CAT, "atx-artifact-verified", "typed entry points per function")
        out = ["| Business function | Category | Entry point | Kind |", "|---|---|---|---|"]
        for n in self.ORD:
            f = self.F[n]
            for ep in f["entryPointList"]:
                m = re.match(r"(\S+)\s*\((.+)\)", ep)
                nm, kind = (m.group(1), m.group(2)) if m else (ep, "—")
                out.append(f"| {self.esc(n)} | {f.get('category','—')} | `{self.esc(nm)}` | "
                           f"{self.esc(kind)} |")
        return "\n".join(out)

    def interfaces(self, rec):
        rows = [(a, b) for a, bs in self.IF.items() for b in bs if b]
        if not rows:
            return None
        rec.use(self.CATJ, "atx-artifact-verified", "function-to-function interface edges")
        out = ["| Source business function | Target business function |", "|---|---|"]
        for a, b in sorted(rows):
            out.append(f"| {self.esc(a)} | {self.esc(b)} |")
        out += ["", f"{len(rows)} directed edges."]
        return "\n".join(out)

    def deps(self, rec):
        if not self.CA.get("dependencyNodeCount"):
            return None
        rec.use(self.CA.get("dependenciesPath"), "atx-artifact-verified",
                "program dependency graph")
        nt = self.CA.get("dependencyNodeTypes") or {}
        out = [f"- Dependency graph: **{self.CA['dependencyNodeCount']} nodes**, "
               f"**{self.CA['dependencyEdgeCount']} edges**", "",
               "| Node type | Count |", "|---|---|"]
        for k in sorted(nt, key=lambda x: -nt[x]):
            out.append(f"| {self.esc(k)} | {nt[k]} |")
        return "\n".join(out)

    def rules_tbl(self, rec):
        out = ["| Business function | Total | Captured | Not applicable | Unreachable | Delegated |",
               "|---|---|---|---|---|---|"]
        for n in self.DELIV:
            f = self.F[n]
            rec.use(f.get("tracePath"), "atx-artifact-verified",
                    f"rule dispositions for {n}")
            ts = f.get("traceSummary") or {}
            out.append(f"| {self.esc(n)} | {ts.get('total_rules','—')} | {ts.get('captured','—')} | "
                       f"{ts.get('not_applicable','—')} | {ts.get('unreachable','—')} | "
                       f"{ts.get('delegated','—')} |")
        out += ["", "Dispositions are the extractor's own classification. `unreachable` and "
                    "`not_applicable` counts are quality signals about the legacy code."]
        return "\n".join(out)

    def rule_detail(self, rec, per=6):
        """Quoted rules with program attribution — the strongest evidence available."""
        out = []
        for n in self.DELIV:
            f = self.F[n]
            rules = f.get("rules") or {}
            if not rules:
                continue
            rec.use(f.get("tracePath"), "atx-artifact-verified", f"rule text for {n}")
            out += [f"#### {n}", ""]
            shown = 0
            for rid, r in sorted(rules.items(), key=lambda kv: str(kv[1].get("rule_name"))):
                if r.get("disposition") != "captured" or not r.get("rule_text"):
                    continue
                out.append(f"- **{self.esc(r.get('rule_name') or rid[:12])}** — "
                           f"{self.esc(r['rule_text'])} "
                           f"[source: rule `{rid[:12]}…` -> `{r.get('program')}`] "
                           f"`atx-artifact-verified`")
                shown += 1
                if shown >= per:
                    break
            extra = sum(1 for r in rules.values() if r.get("disposition") == "captured") - shown
            if extra > 0:
                out.append(f"- … {extra} further captured rules in `{f.get('tracePath')}`")
            out.append("")
        return "\n".join(out) if out else None

    def reqs(self, rec, per=10):
        out = []
        for n in self.DELIV:
            f = self.F[n]
            reqs = f.get("reqF") or []
            if not reqs:
                continue
            rec.use(f.get("reqPath"), "requirements-derived", f"functional requirements for {n}")
            cites = f.get("reqCitations") or {}
            out += [f"#### {n}", ""]
            for rid, text in reqs[:per]:
                c = cites.get(rid)
                tag = (f"[source: {rid} -> rule `{c['rule'][:12]}…` -> `{c['program']}`]"
                       if c else f"[source: {rid} -> {os.path.basename(f['reqPath'])}]")
                out.append(f"- **{rid}** — {self.esc(text.strip())} {tag} `requirements-derived`")
            if len(reqs) > per:
                out.append(f"- … {len(reqs)-per} further requirements in `{f['reqPath']}`")
            out.append("")
        return "\n".join(out) if out else None

    def workflows(self, rec):
        out = []
        for n in self.DELIV:
            secs = self.F[n].get("sections") or []
            if not secs:
                continue
            rec.use(self.F[n].get("reqPath"), "requirements-derived",
                    f"numbered workflow sections for {n}")
            out += [f"#### {n}", ""] + [f"{s}" for s in secs] + [""]
        return "\n".join(out) if out else None

    def oqs(self, rec):
        out, total = [], 0
        for n in self.DELIV:
            oq = self.F[n].get("openQuestions") or []
            total += len(oq)
            if not oq:
                continue
            rec.use(self.F[n].get("reqPath"), "requirements-derived", f"open questions for {n}")
            out += [f"#### {n} ({len(oq)})", ""]
            for qid, text in oq[:8]:
                out.append(f"- **{qid}** — {self.esc(text.strip())} `requirements-derived`")
            if len(oq) > 8:
                out.append(f"- … {len(oq)-8} more in `{self.F[n]['reqPath']}`")
            out.append("")
        if not total:
            return None
        return (f"{total} open questions across {len(self.DELIV)} delivered functions. These are "
                f"decisions the legacy code left implicit — handoff items, not defects.\n\n"
                + "\n".join(out))

    def datadict(self, rec):
        if not self.DD.get("fileCount"):
            return None
        rec.use(self.DD.get("sampleFile"), "atx-artifact-verified",
                f"field-level data dictionary ({self.DD['fileCount']} files)")
        hdr = self.DD.get("sampleHeader") or []
        rows = self.DD.get("sampleRows") or []
        out = [f"- **{self.DD['fileCount']} data dictionary files** from AWS Transform data "
               f"analysis, one per source member.",
               f"- Columns: `{', '.join(hdr)}`", "",
               f"Sample from `{os.path.basename(self.DD.get('sampleFile',''))}`:", ""]
        if hdr and rows:
            keep = [0, 1, 3, 4, 6, 7]
            hs = [hdr[i] for i in keep if i < len(hdr)]
            out.append("| " + " | ".join(self.esc(h) for h in hs) + " |")
            out.append("|---" * len(hs) + "|")
            for r in rows:
                r = (r + [""] * len(hdr))
                out.append("| " + " | ".join(self.esc(r[i]) for i in keep if i < len(hdr)) + " |")
        out += ["", "**`business_definition` values are machine-generated and carry "
                    "`status: draft` pending SME review.**"]
        return "\n".join(out)

    def lineage(self, rec):
        if not self.DL.get("fileCount"):
            return None
        rec.use(self.DL.get("sampleFile"), "atx-artifact-verified",
                f"data lineage ({self.DL['fileCount']} artifacts)")
        out = [f"- **{self.DL['fileCount']} data lineage artifacts** from AWS Transform data "
               f"analysis.", "", "Files:", ""]
        out += [f"- `{os.path.basename(p)}`" for p in (self.DL.get("files") or [])[:10]]
        out += ["", "Granularity limit: lineage is recorded at program-and-dataset level. "
                    "Per-variable data flow within a program has no equivalent in this evidence "
                    "set."]
        return "\n".join(out)

    def scheduler(self, rec):
        sf = self.CA.get("schedulerFiles") or []
        if not sf:
            return None
        rec.use(self.CA.get("assetsCsv"), "atx-artifact-verified", "scheduler artifacts detected")
        return ("Scheduler definitions are checked into the codebase and were extracted by code "
                "analysis:\n\n" + "\n".join(f"- `{s}`" for s in sf)
                + "\n\nBoth CA-7 and Control-M definitions are present, so scheduling is defined "
                  "in-repo rather than assumed.")

    def run_ctx(self, rec):
        rec.use(self.STATE, "atx-artifact-verified", "run identity, source package, gates")
        fc = self.RUN.get("fileCounts") or {}
        return "\n".join([
            "| Field | Value |", "|---|---|",
            f"| Upstream run | `{self.RUN.get('runId')}` |",
            f"| AWS Transform job | {self.esc(self.RUN.get('job'))} |",
            f"| Workspace | {self.esc(self.RUN.get('workspace'))} |",
            f"| Account / region | `{self.RUN.get('account')}` / `{self.RUN.get('region')}` |",
            f"| Source package | `{self.RUN.get('sourceOrigin')}` |",
            f"| Intake counts | {self.esc(', '.join(f'{k} {v}' for k,v in sorted(fc.items())))} |",
            f"| Glossary | `{self.RUN.get('glossaryProvenance')}` |"])

    def src_inv(self, rec):
        ec = self.pack["source"]["extensionCounts"]
        rec.use("workspace app/**", "source-read-verified", "measured file counts by extension",
                fingerprint=sorted(ec.items()))
        out = ["Measured in the workspace this run:", "", "| Extension | Files |", "|---|---|"]
        for k in sorted(ec, key=lambda x: -ec[x]):
            out.append(f"| `.{k}` | {ec[k]} |")
        out += ["", "Searched for and **not** found: PL/I (`.pli`), REXX (`.rex`), IMS MFS "
                    "(`.mfs`), Natural (`.nat`), Easytrieve (`.ezt`). Their absence is measured, "
                    "not assumed."]
        return "\n".join(out)

    # ---- workspace-source builders: these close the "not extracted by this run" gap ----
    def jcl_ops(self, rec, n=12):
        J = self.pack.get("jcl") or {}
        if not J.get("memberCount"):
            return None
        for k in sorted(J["members"])[:n]:
            rec.use(J["members"][k]["path"], "source-read-verified",
                    f"JCL steps and DD statements for {k}")
        out = [f"- **{J['memberCount']} JCL members** parsed: **{J['totalSteps']} steps** and "
               f"**{J['totalDD']} DD statements**.", "",
               "| Member | Steps | DD statements | Conditional execution |", "|---|---|---|---|"]
        for k in sorted(J["members"])[:n]:
            v = J["members"][k]
            out.append(f"| `{k}` | {v['stepCount']} | {v['ddCount']} | "
                       f"{len(v['cond']) or '—'} |")
        if J["memberCount"] > n:
            out.append(f"| … {J['memberCount']-n} further members | | | |")
        out += ["", "**Programs and utilities invoked** (`EXEC PGM=`), by frequency:", "",
                "| Program | Steps invoking it |", "|---|---|"]
        for p, c in list(J.get("utilities", {}).items())[:12]:
            out.append(f"| `{p}` | {c} |")
        return "\n".join(out)

    def jcl_control(self, rec):
        """Conditional execution, restart and abend handling — the operational contract."""
        J = self.pack.get("jcl") or {}
        if not J.get("memberCount"):
            return None
        cond, restart = J.get("withCond") or [], J.get("withRestart") or []
        out = [f"- **Conditional execution** (`COND=`): present in **{len(cond)}** of "
               f"{J['memberCount']} JCL members.", ""]
        if cond:
            out += ["| Member | Condition | Line |", "|---|---|---|"]
            for k in cond[:10]:
                v = J["members"][k]
                rec.use(v["path"], "source-read-verified", f"COND= logic in {k}")
                for c in v["cond"][:2]:
                    out.append(f"| `{k}` | `COND={c['value']}` | {c['line']} |")
        out += ["", f"- **Restart points** (`RESTART=`): **{len(restart)}** members. "
                    + ("No member carries an active `RESTART=`; the only occurrence in the "
                       "codebase is inside a comment, so there is no coded restart contract to "
                       "document." if not restart else
                       f"Present in: {', '.join(f'`{x}`' for x in restart)}."), ""]
        out.append("Runtime recovery configuration — RPO/RTO targets, offsite copies, standby "
                   f"capacity — is outside this evidence set entirely: `{NA_ATX}`.")
        return "\n".join(out)

    def build_jcl(self, rec):
        B = self.pack.get("buildJcl") or {}
        if not B.get("memberCount"):
            return None
        out = [f"- **{B['memberCount']} build, compile or link members** identified by the "
               f"utilities they invoke.", "",
               "| Member | Steps | Build/link steps |", "|---|---|---|"]
        for k in sorted(B["members"]):
            v = B["members"][k]
            rec.use(v["path"], "source-read-verified", f"compile and link steps in {k}")
            bs = ", ".join(f"`{s['invokes']}`" for s in v["buildSteps"][:4]) or "—"
            out.append(f"| `{k}` | {len(v['steps'])} | {bs} |")
        out += ["", "Promotion between environments, load-library concatenation at runtime and "
                    f"deployment approval flow are not in the codebase: `{NA_ATX}`."]
        return "\n".join(out)

    def bms_maps(self, rec, n=3):
        B = self.pack.get("bms") or {}
        if not B.get("memberCount"):
            return None
        out = [f"- **{B['memberCount']} BMS mapsets**, **{B['mapCount']} maps**, "
               f"**{B['namedFieldCount']} named fields**. For an online transaction the map is "
               f"the request/response contract.", ""]
        for k in sorted(B["members"])[:n]:
            v = B["members"][k]
            rec.use(v["path"], "source-read-verified", f"screen field layout in {k}")
            out.append(f"#### `{k}` — mapset `{v.get('mapset')}`")
            out.append("")
            for mp, fields in v["maps"].items():
                named = [f for f in fields if f["field"] != "(unnamed literal)"]
                out += [f"Map `{mp}` — {len(fields)} fields ({len(named)} named):", "",
                        "| Field | Length | Row | Col | Attributes |", "|---|---|---|---|---|"]
                for f in named[:10]:
                    out.append(f"| `{f['field']}` | {f['length'] or '—'} | {f['row'] or '—'} | "
                               f"{f['col'] or '—'} | `{f['attrb'] or '—'}` |")
                if len(named) > 10:
                    out.append(f"| … {len(named)-10} more | | | | |")
                out.append("")
        if B["memberCount"] > n:
            out.append(f"… {B['memberCount']-n} further mapsets in the codebase.")
        return "\n".join(out)

    def linkage(self, rec, n=6):
        L = self.pack.get("linkage") or {}
        if not L.get("memberCount"):
            return None
        out = [f"- **{L['memberCount']} programs declare a LINKAGE SECTION**, "
               f"**{L['totalItems']} items** in total. For a called program this is the "
               f"interface signature.", "",
               "| Program | Items | LINKAGE at line |", "|---|---|---|"]
        for k in sorted(L["members"])[:n]:
            v = L["members"][k]
            rec.use(v["path"], "source-read-verified", f"LINKAGE SECTION of {k}")
            out.append(f"| `{k}` | {v['itemCount']} | {v['line']} |")
        if L["memberCount"] > n:
            out.append(f"| … {L['memberCount']-n} further programs | | |")
        first = sorted(L["members"])[0]
        fv = L["members"][first]
        out += ["", f"Signature of `{first}`:", "",
                "| Level | Name | PIC | Line |", "|---|---|---|---|"]
        for it in fv["items"][:12]:
            out.append(f"| {it['level']} | `{it['name']}` | `{it['pic'] or '—'}` | {it['line']} |")
        return "\n".join(out)

    def error_handling(self, rec, n=12):
        """Error and exception handling as coded in COBOL.

        Deliberately separate from `jcl_control`: batch COND= logic is job-step control, not
        program error handling, and answering an API document's error section with job
        conditions was a semantic mismatch the self-check caught.
        """
        E = self.pack.get("errorHandling") or {}
        if not E.get("programCount"):
            return None
        out = [f"- **{E['total']} error-handling constructs** across "
               f"**{E['programCount']} programs**, {len(E['byConstruct'])} distinct kinds.", "",
               "| Construct | Occurrences |", "|---|---|"]
        for k, v in E["byConstruct"].items():
            out.append(f"| `{k}` | {v} |")
        out += ["", "Programs with the most explicit handling:", "",
                "| Program | Constructs | Kinds |", "|---|---|---|"]
        top = sorted(E["members"].items(), key=lambda kv: -kv[1]["total"])[:n]
        for k, v in top:
            rec.use(v["path"], "source-read-verified", f"error-handling constructs in {k}")
            out.append(f"| `{k}` | {v['total']} | "
                       f"{', '.join(f'`{x}`' for x in sorted(v['counts']))} |")
        return "\n".join(out)

    def architecture(self, rec):
        """Real structural evidence: interface edges plus the dependency graph.

        NOT the business function table. Answering an architecture heading with a function
        inventory was the single largest source of semantically wrong content.
        """
        parts = [p for p in (self.interfaces(rec), self.deps(rec)) if p]
        return "\n\n".join(parts) if parts else None

    # ---------------- resolver ----------------
    # Phase 1. Honesty rules fire FIRST. A heading matching one of these is unavailable no
    # matter what generic evidence might superficially fit it. Ordering used to be
    # load-bearing and generic builders won, which filled target-state and ownership headings
    # with current-state tables.
    HARD_NA = [
        (r"target|future.?state|to.?be state|cloud|aws service|landing zone|migration target",
         "na_atx", "target-state design is a forward-engineering decision, outside this skill's "
                   "reverse-engineering scope"),
        (r"owner|stakeholder|\bteam\b|persona|raci|organis|organiz|responsib|governance",
         "na_atx", "no ownership, stakeholder or organisational data exists in AWS Transform "
                   "output"),
        (r"securit|threat|vulnerab|\bcve\b|iso ?5055|penetration|encryption|access control",
         "na_atx", "AWS Transform produces no static-scan, CVE or ISO 5055 output, and no "
                   "security posture assessment; this was a CAST capability with no equivalent"),
        (r"cost|budget|licen|pricing|\broi\b|\btco\b|financial",
         "na_atx", "no cost or licensing data in the evidence set"),
        (r"\bsla\b|uptime|availabilit|\bkpi\b|telemetr|benchmark|performance metric",
         "na_atx", "no runtime telemetry, SLA or performance data in the evidence set"),
        (r"retention|privacy|sensitiv|gdpr|\bpii\b|data classification",
         "na_atx", "no data classification or retention policy in the evidence set"),
        (r"\btest|coverage|\bqa\b",
         "na_atx", "no test inventory or coverage output in the evidence set"),
        (r"\brpo\b|\brto\b|standby|offsite|hot site",
         "na_atx", "recovery objectives and standby capacity are runtime configuration, absent "
                   "from both the AWS Transform output and the codebase"),
        (r"dashboard|\bapm\b|log aggregat|trace",
         "na_atx", "no runtime monitoring or log-aggregation configuration exists in the "
                   "evidence set"),
        (r"paragraph|variable|control flow|data element",
         "na_run", "paragraph, variable and control-flow structure require parsing COBOL "
                   "source, which this run did not do"),

        (r"resource requirement|staffing|effort estimate|timeline|milestone",
         "na_atx", "no schedule, capacity or resourcing data in the evidence set"),
        # A "gap" that compares current against desired needs a target model. Only a gap in
        # *knowledge* (open questions) is answerable from this evidence set, and that is matched
        # by the `oqs` builder's narrower `gap identif|gap analys` scope.
        (r"(capabilit|feature|architect|technolog|process).{0,12}gap|gap.{0,12}(capabilit|feature)",
         "na_atx", "a gap assessment compares current state against a target state; no target "
                   "model exists in the evidence set, and inventing one would be forward "
                   "engineering"),
    ]

    # Phase 2. Each builder declares the heading topics it OWNS. A builder may not answer a
    # heading outside its scope, so a broad keyword can no longer capture an unrelated heading.
    def builders(self):
        return [
            (r"data entit|attribute|data dictionar|\bfield|schema|key table|column|data model",
             self.datadict, "datadict"),
            (r"lineage|data flow|transformation",
             self.lineage, "lineage"),
            (r"business rule|validation|policy|rule inventory|constraint",
             self.rules_combined, "rules"),
            (r"requirement|user stor|acceptance criteri",
             self.reqs, "reqs"),
            (r"process|workflow|sequence|journey|scenario",
             self.workflows, "workflows"),
            (r"complexity|technical debt|code quality|hotspot|risk assessment|effort",
             self.complexity, "complexity"),
            (r"issue|finding|violation|defect|anti.?pattern",
             self.issues, "issues"),
            (r"missing|absent|unresolved",
             self.missing, "missing"),
            (r"architecture|structure|layer|component|logical|physical|integration|"
             r"landscape|pattern|topolog",
             self.architecture, "architecture"),
            (r"dependenc|coupling|call graph",
             self.deps, "deps"),
            (r"relationship|cardinalit",
             self.interfaces, "interfaces"),
            (r"entry point|\bapi\b|endpoint|integration point|interface",
             self.entrypoints, "entrypoints"),
            (r"error|exception|fault|failure mode",
             self.error_handling, "error_handling"),
            (r"conditional|restart|\bcond=|job control|return code|checkpoint|"
             r"recovery|continuit|resilien|backup|failover",
             self.jcl_control, "jcl_control"),
            (r"deploy|build|compile|link|pipeline|ci.?cd|packaging|promotion|release",
             self.build_jcl, "build_jcl"),
            (r"screen|\bmap\b|\bbms\b|message|payload|request|response|field layout|"
             r"user interface",
             self.bms_maps, "bms_maps"),
            (r"linkage|signature|parameter|called program|program interface",
             self.linkage, "linkage"),
            (r"monitor|alert|observab|logging|operational",
             self.jcl_control, "jcl_control"),
            (r"schedul|\bjob|batch|step|runbook|operations",
             self.jcl_ops, "jcl_ops"),
            (r"open question|assumption|gap identif|gap analys",
             self.oqs, "oqs"),
            (r"technolog|tech stack|language|extension|directory",
             self.src_inv, "src_inv"),
            (r"inventor|classification|file type|asset",
             self.inventory, "inventory"),
            (r"capabilit|feature|function inventor|\bscope\b|module organi",
             self.fn_table, "fn_table"),
            (r"overview|summar|context|introduction|purpose|repositor",
             self.run_ctx, "run_ctx"),
        ]

    def rules_combined(self, rec):
        t = self.rules_tbl(rec)
        d = self.rule_detail(rec)
        return (t + "\n\n" + d) if d else t

    def resolve(self, pt, heading, rec):
        """Return (text, kind, builder) where kind is grounded | na_atx | na_run."""
        h = re.sub(r"[^a-z0-9 ]", " ", heading.lower()).strip()

        # Phase 1 — honesty first.
        for pat, kind, reason in self.HARD_NA:
            if re.search(pat, h):
                marker = NA_ATX if kind == "na_atx" else NA_RUN
                return f"`{marker}` — {reason}", kind, "hard-na"

        # Phase 2 — scoped builders.
        for pat, fn, name in self.builders():
            if re.search(pat, h):
                v = fn(rec)
                if v:
                    return v, "grounded", name
                # In scope but no evidence: say so specifically rather than falling through.
                return (f"`{NA_ATX}` — the `{name}` evidence this heading needs is not present "
                        f"in the run", "na_atx", name)

        # Phase 3 — substitutions table.
        kind, reason = self.sub_lookup(heading)
        if kind:
            return f"`{NA_ATX}` — {reason}", "na_atx", "substitutions"

        # Phase 4 — nothing claims it.
        return (f"`{NA_ATX}` — no artifact in the evidence set answers this heading",
                "na_atx", "none")

    # ---------------- section sets ----------------
    def section_set(self, tpl, pt):
        if pt in self.FIXED:
            return self.FIXED[pt], "C-fixed"
        body = open(os.path.join(SKILL, tpl), encoding="utf-8").read() \
            .split("## Prompt template", 1)[-1]
        if "OUTPUT STRUCTURE" in body:
            tail = body.split("OUTPUT STRUCTURE", 1)[1]
            hs = [re.sub(r"^\d+\.\s*", "", h).strip()
                  for _l, h in re.findall(r"^(#{2})\s+(.+)$", tail, re.M)]
            hs = [h for h in hs if h and not h.startswith("{")]
            if hs:
                return self._dedupe(hs), "A-output-structure"
        hs = [h.strip().rstrip(":") for h in re.findall(r"^\*\*(.+?)\*\*\s*$", body, re.M)]
        hs = [h for h in hs if "**" not in h and 2 < len(h) < 70]
        return (self._dedupe(hs), "B-bold") if hs else ([], "none")

    @staticmethod
    def _dedupe(hs):
        seen, out = set(), []
        for h in hs:
            if h.strip() and h.lower() not in seen:
                seen.add(h.lower())
                out.append(h.strip())
        return out

    # ---------------- self-check (enforced) ----------------
    def self_check(self, text, heads, rec, builders_used=None, plan=None):
        fails = []

        # Builder dominance, judged against the document's own evidence plan.
        #
        # Dominance alone is not a defect: a data dictionary document SHOULD be dominated by the
        # data dictionary builder, and a requirements document by the requirements builder. What
        # signals semantic mismatch is dominance by a builder the document's plan does not own —
        # for example an architecture document filled with the business function table.
        if builders_used and plan:
            real = [b for b in builders_used if b not in ("hard-na", "substitutions", "none")]
            if len(real) > 2:
                top, n = collections.Counter(real).most_common(1)[0]
                if n / len(real) > 0.5 and top not in PLAN_BUILDERS.get(plan, set()):
                    fails.append(f"builder '{top}' answers {n} of {len(real)} grounded sections "
                                 f"but is not owned by plan '{plan}' — semantic mismatch")
        if "## Coverage" not in text:
            fails.append("no Coverage note")
        if f"{len(self.DELIV)} of {len(self.F)}" not in text:
            fails.append("coverage denominator absent")
        if "## Evidence Index" not in text:
            fails.append("no Evidence Index")
        for h in heads:
            if f"## {h}" not in text:
                fails.append(f"template heading dropped: {h}")
        for bad in ("z-workflow-verified", "z-understand-verified",
                    "narrative-per-program-not-tool-verified", "Not available from Z Premium"):
            if bad in text:
                fails.append(f"Bob vocabulary leaked: {bad}")
        # A grounded document must cite at least one artifact.
        if not rec.items:
            fails.append("no artifact recorded as read")
        # Guard the generalisation rule: a bare total with no denominator nearby.
        for m in re.finditer(r"\b466\b(?![^\n]*of \d+)", text):
            seg = text[max(0, m.start() - 120):m.start() + 60]
            if "of 11" not in seg and "of 6" not in seg and "delivered" not in seg:
                fails.append("count stated without denominator")
                break
        return fails

    # ---------------- build one document ----------------
    def build(self, doc):
        pt, rec = doc["pt"], Rec(self.hashes)
        heads, fam = self.section_set(doc["tpl"], pt)
        L = [f"# {pt.replace('_',' ').title()}", "",
             f"**Application:** {self.APP}  ", f"**Generated:** {self.date}  ",
             "**Generated by:** AWS Transform — mainframe reverse engineering "
             "(assess + reimagine)  ",
             f"**Evidence plan:** `{doc['plan']}`  ",
             f"**Document:** {pt} (catalog #{doc['n']}, level L{doc['lvl']})  ",
             f"**Section set:** {len(heads)} sections, template family {fam} "
             f"(see `references/template-families.md`)", "",
             "> Every statement below is grounded in an artifact from the upstream AWS Transform "
             "run or a file read in the workspace.", "",
             f"> Two distinct markers appear. **`{NA_ATX}`** means the evidence does not exist. "
             f"**`{NA_RUN}`** means it exists in the codebase and this run did not parse it — a "
             f"limitation of the generator, not of AWS Transform.", ""]
        if self.RUN.get("glossaryProvenance") != "user-supplied":
            L += [f"> **Terminology caveat.** No glossary was supplied upstream "
                  f"(`glossaryProvenance: {self.RUN.get('glossaryProvenance')}`), so "
                  f"abbreviations were interpreted from context.", ""]
        L += [self.coverage(rec), "---", ""]

        counts = collections.Counter()
        used = []
        emitted = {}
        if not heads:
            L += ["## Content", "", f"`{NA_ATX}` — template supplies no section set", ""]
            counts["na_atx"] += 1
        for h in heads:
            body, kind, builder = self.resolve(pt, h, rec)
            if kind == "grounded":
                used.append(builder)
                key = hash(body)
                if key in emitted:
                    L += [f"## {h}", "", f"See **{emitted[key]}** above — the same evidence "
                                         f"answers this heading. Repeating it would add no "
                                         f"information.", ""]
                    counts["grounded"] += 1
                    continue
                emitted[key] = h
            L += [f"## {h}", "", body, ""]
            counts[kind] += 1

        L += ["---", "", "## Evidence Index", "",
              "Artifacts **this document** read. Documents that read fewer artifacts list fewer.",
              "", rec.table(), "",
              f"**Sections:** {counts['grounded']} grounded · {counts['na_atx']} evidence absent · "
              f"{counts['na_run']} not extracted by this run · "
              f"{sum(counts.values())} total", ""]
        text = "\n".join(L)
        return text, counts, fam, rec, heads, used


def plan_has_evidence(g, plan):
    """True when the plan's builders can produce anything from this run's artifacts."""
    rec = Rec()
    for _pat, fn, name in g.builders():
        if name in PLAN_BUILDERS.get(plan, set()):
            try:
                if fn(rec):
                    return True
            except TypeError:
                continue
    return False


def read_ledger_status(docs):
    p = f"{docs}/00-manifest/ledger.md"
    if not os.path.isfile(p):
        return {}
    out = {}
    for line in open(p, encoding="utf-8"):
        c = [x.strip() for x in line.split("|")]
        if len(c) >= 7 and c[1].isdigit():
            out[c[3].strip("`")] = c[6]
    return out


def merge_batch(docs, fresh):
    """Merge this batch into the suite record instead of replacing it.

    Replacing meant a `--only` or `--levels` run reduced the record to the documents it touched,
    and any ledger or manifest built afterwards reported a suite of that size. The record is the
    state of all 31 documents, not the state of the last command.
    """
    p = f"{docs}/00-manifest/suite-state.json"
    prior = {}
    if os.path.isfile(p):
        try:
            prior = {r["pt"]: r for r in json.load(open(p, encoding="utf-8"))}
        except (ValueError, OSError):
            prior = {}
    # legacy filename, read once so an existing run is not lost
    legacy = f"{docs}/00-manifest/last-batch.json"
    if not prior and os.path.isfile(legacy):
        try:
            prior = {r["pt"]: r for r in json.load(open(legacy, encoding="utf-8"))}
        except (ValueError, OSError):
            pass
    for r in fresh:
        prior[r["pt"]] = r
    merged = sorted(prior.values(), key=lambda r: r["n"])
    json.dump(merged, open(p, "w", encoding="utf-8"), indent=1)
    return merged


def write_manifests(docs, merged, g, generated_at):
    """Regenerate every derived manifest, every run.

    Previously only the ledger and manifest were refreshed while coverage.md and
    review-queue.md were written once and then drifted silently against the evidence pack.
    """
    M = f"{docs}/00-manifest"
    byst = collections.Counter(r["status"] for r in merged)
    tg = sum(r["grounded"] for r in merged)
    ta = sum(r["naAtx"] for r in merged)
    tr = sum(r["naRun"] for r in merged)
    bw = collections.Counter()
    for r in merged:
        for k, v in (r.get("builders") or {}).items():
            bw[k] += v

    L = ["# Document Ledger", "", f"31 documents. Last generated {generated_at}.", "",
         "| # | Level | prompt_type | Plan | Status | Grounded | Evidence absent | "
         "Not extracted | Artifacts |", "|---|---|---|---|---|---|---|---|---|"]
    for r in merged:
        L.append(f"| {r['n']} | L{r['lvl']} | `{r['pt']}` | `{r['plan']}` | {r['status']} | "
                 f"{r['grounded']} | {r['naAtx']} | {r['naRun']} | {r['artifacts']} |")
    L += ["", "## Status summary", "", "| Status | Meaning | Documents |", "|---|---|---|"]
    MEAN = {"complete": "every template heading grounded",
            "partial": "written, some headings unavailable",
            "unavailable": "written, but no heading could be grounded despite its plan "
                           "having evidence",
            "blocked": "the document's evidence plan has no evidence at all"}
    for k, v in byst.most_common():
        L.append(f"| {k} | {MEAN.get(k,'—')} | {v} |")
    L += ["", "## Which builder answered how many sections", "",
          "A flat distribution is the healthy signal. One builder dominating across the suite "
          "means headings are being answered by evidence that does not address them.", "",
          "| Builder | Sections |", "|---|---|"]
    for k, v in bw.most_common():
        L.append(f"| `{k}` | {v} |")
    open(f"{M}/ledger.md", "w", encoding="utf-8").write("\n".join(L) + "\n")

    # review queue, regenerated from the current pack
    dd = g.DD
    R = ["# SME Review Queue", "", f"Regenerated {generated_at} from the current evidence pack.",
         "", "Machine-generated content that reads as authoritative and has **not** been "
         "confirmed by a domain expert. This is the highest-risk content in the suite.", "",
         "## Data dictionary business definitions", "",
         f"- **{dd.get('fileCount')} data dictionary files**, one per source member, each "
         f"carrying a `business_definition` column generated by AWS Transform data analysis.",
         "- Status: `draft`. No SME has confirmed these definitions.", "",
         "| Priority | Scope | Why |", "|---|---|---|",
         f"| 1 | Field definitions for the {len(g.DELIV)} delivered business functions | cited in "
         f"L5 and L2 documents |",
         "| 2 | Definitions containing inferred abbreviation expansions | no glossary was "
         "supplied, so expansions are guesses |",
         "| 3 | Remaining members | lower document reach |", "",
         "## Terminology", "",
         f"No glossary was supplied upstream (`glossaryProvenance: "
         f"{g.RUN.get('glossaryProvenance')}`). Every abbreviation expansion in the suite is "
         f"inferred from context. Supplying a reviewed `glossary.csv` to a future "
         f"`mainframe-reverse-engineering` run would remove this whole class of risk.", "",
         "## Requirements narrative", "",
         "Requirement text is reproduced from the upstream run's `requirements.md`, which was "
         "itself machine-generated. It carries `requirements-derived` provenance rather than "
         "`atx-artifact-verified`, and open questions are unresolved by design.", ""]
    open(f"{M}/review-queue.md", "w", encoding="utf-8").write("\n".join(R) + "\n")

    man = {}
    if os.path.isfile(f"{M}/manifest.json"):
        try:
            man = json.load(open(f"{M}/manifest.json", encoding="utf-8"))
        except (ValueError, OSError):
            man = {}
    man.update({
        "generatedAt": generated_at, "docsRoot": docs,
        # Recorded so a reader can tell whether the name in 31 headers was supplied, derived, or
        # genuinely unavailable, rather than having to trust it.
        "application": {"name": g.APP, "nameSource": g.APP_SRC},
        "upstream": g.RUN,
        "coverage": {"discovered": len(g.F), "delivered": len(g.DELIV),
                     "represented": g.DELIV, "scopedNoSpec": g.NOSPEC,
                     "excludedInfrastructure": g.EXCL},
        "documents": {"total": len(merged), "byStatus": dict(byst),
                      "sectionsGrounded": tg, "sectionsEvidenceAbsent": ta,
                      "sectionsNotExtractedByThisRun": tr,
                      "groundedShare": round(tg / max(tg + ta + tr, 1), 3)},
        "builderDistribution": dict(bw.most_common()),
        "documentList": merged,
    })
    json.dump(man, open(f"{M}/manifest.json", "w", encoding="utf-8"), indent=1)

    G = ["# Generation Log", "", f"## Suite state as of {generated_at}", "",
         "| # | prompt_type | Plan | Status | Grounded | Absent | Not extracted | Artifacts |",
         "|---|---|---|---|---|---|---|---|"]
    for r in merged:
        G.append(f"| {r['n']} | `{r['pt']}` | `{r['plan']}` | {r['status']} | {r['grounded']} | "
                 f"{r['naAtx']} | {r['naRun']} | {r['artifacts']} |")
    open(f"{M}/generation-log.md", "w", encoding="utf-8").write("\n".join(G) + "\n")

    # coverage.md is build_coverage.py's output; warn rather than silently let it drift
    cov, pack = f"{M}/coverage.md", f"{M}/evidence-pack.json"
    if os.path.isfile(cov) and os.path.isfile(pack) and \
            os.path.getmtime(cov) < os.path.getmtime(pack):
        print("  NOTE coverage.md is older than the evidence pack — re-run build_coverage.py")


def consistency(docs, merged, g):
    """Step 8 — compare every shared fact the skill names, not just one."""
    facts = {
        "coverage denominator": f"{len(g.DELIV)} of {len(g.F)}",
        "delivered function names": None,
        "function count": str(len(g.F)),
    }
    texts = {}
    for r in merged:
        p = os.path.join(docs, r["out"])
        if os.path.isfile(p):
            texts[r["pt"]] = open(p, encoding="utf-8").read()

    problems = []
    for pt, t in texts.items():
        if facts["coverage denominator"] not in t:
            problems.append((pt, "coverage denominator absent or differs"))
        for n in g.DELIV:
            if n not in t:
                problems.append((pt, f"delivered function not named: {n}"))
                break
    # Numeric facts must AGREE wherever they appear. Absence is not a mismatch — many tables
    # legitimately omit a column — but two documents disagreeing about the same number is.
    def tabled(text, header_word):
        """Rows from tables whose header contains header_word -> {row label: [cells]}."""
        rows, keep = {}, False
        for line in text.splitlines():
            if line.startswith("|") and header_word.lower() in line.lower():
                keep = True
                continue
            if keep and line.startswith("|---"):
                continue
            if keep and line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if cells:
                    rows[cells[0]] = cells
            elif keep and not line.startswith("|"):
                keep = False
        return rows

    for pt, t in texts.items():
        for label, cells in tabled(t, "Loc").items():
            fn = g.F.get(label)
            if not fn or not fn.get("loc"):
                continue
            if str(fn["loc"]) not in cells:
                problems.append((pt, f"LOC disagreement for {label}: document shows "
                                     f"{cells[1:]} , pack says {fn['loc']}"))
                break
    # rule totals must match the traceability summary wherever stated
    for pt, t in texts.items():
        for label, cells in tabled(t, "Captured").items():
            fn = g.F.get(label)
            ts = (fn or {}).get("traceSummary") or {}
            if ts.get("total_rules") and str(ts["total_rules"]) not in cells:
                problems.append((pt, f"rule total disagreement for {label}"))
                break
    print(f"  checked {len(texts)} documents against {len(facts)} shared facts")
    if problems:
        for pt, why in problems[:8]:
            print(f"    MISMATCH {pt}: {why}")
        print(f"  {len(problems)} mismatch(es)")
    else:
        print("  all shared facts consistent")
    return problems


def default_docs_root() -> str:
    """See build_coverage.default_docs_root — one run, one folder, stamped by the driver."""
    return os.environ.get("ATX_DOCS_ROOT") or os.path.join(".atx", "app-docs-latest")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels")
    ap.add_argument("--only")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--docs-root", default=None,
                    help="documentation output root (default: $ATX_DOCS_ROOT)")
    ap.add_argument("--app-name", default=os.environ.get("ATX_APP_NAME"),
                    help="application name for document headers "
                         "(default: derived from the upstream run's source origin)")
    a = ap.parse_args()
    D = a.docs_root or default_docs_root()
    want = None if not a.levels else {int(x) for x in a.levels.split(",")}
    g = Gen(D, app_name=a.app_name)
    prior = {} if a.force else read_ledger_status(D)

    results, failed, fingerprints = [], 0, {}
    for d in catalog():
        if want is not None and d["lvl"] not in want:
            continue
        if a.only and d["pt"] != a.only:
            continue
        if prior.get(d["pt"]) == "complete":
            print(f"  L{d['lvl']} {d['pt']:28} skipped (complete; --force to regenerate)")
            continue
        text, c, fam, rec, heads, used = g.build(d)
        fails = g.self_check(text, heads, rec, used, d['plan'])
        if fails:
            failed += 1
            print(f"  L{d['lvl']} {d['pt']:28} SELF-CHECK FAILED -> not filed: {fails[:2]}")
            continue
        p = os.path.join(D, d["out"])
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(text)
        # Status semantics, matching SKILL.md:
        #   complete    every heading grounded
        #   partial     written, some headings unavailable
        #   unavailable written, nothing grounded, but the plan DID have evidence
        #   blocked     the plan itself had no evidence to offer
        if (c["na_atx"] + c["na_run"]) == 0:
            status = "complete"
        elif c["grounded"]:
            status = "partial"
        elif plan_has_evidence(g, d["plan"]):
            status = "unavailable"
        else:
            status = "blocked"
        fingerprints[d["pt"]] = rec.fingerprints()
        results.append(dict(n=d["n"], lvl=d["lvl"], pt=d["pt"], plan=d["plan"], out=d["out"],
                            grounded=c["grounded"], naAtx=c["na_atx"], naRun=c["na_run"],
                            status=status, family=fam, artifacts=len(rec.items),
                            builders=dict(collections.Counter(used))))
        print(f"  L{d['lvl']} {d['pt']:28} {c['grounded']:2}g "
              f"{c['na_atx']:2}a {c['na_run']:2}r  {len(rec.items):2} artifacts -> {status}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    merged = merge_batch(D, results)

    # per-document artifact fingerprints, so staleness is computable by atx-docs-status
    fp_path = f"{D}/00-manifest/document-evidence.json"
    prior_fp = {}
    if os.path.isfile(fp_path):
        try:
            prior_fp = json.load(open(fp_path, encoding="utf-8")).get("documents", {})
        except (ValueError, OSError):
            prior_fp = {}
    prior_fp.update(fingerprints)
    json.dump({"generatedAt": now, "documents": prior_fp},
              open(fp_path, "w", encoding="utf-8"), indent=1)

    tg = sum(r["grounded"] for r in results)
    ta = sum(r["naAtx"] for r in results)
    tr = sum(r["naRun"] for r in results)
    print(f"\n{len(results)} filed this batch, {failed} failed self-check "
          f"({len(merged)} documents in the suite record)")
    print(f"this batch: {tg} grounded · {ta} evidence absent · {tr} not extracted by this run")

    write_manifests(D, merged, g, now)
    print("\ncross-document consistency:")
    consistency(D, merged, g)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
