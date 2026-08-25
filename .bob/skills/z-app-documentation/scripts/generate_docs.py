#!/usr/bin/env python3
"""Step 5 — compose, self-check and file the 31 documents from evidence-pack.json.

Usage:
  generate_docs.py [--levels 0,1,2] [--only PROMPT_TYPE] [--force]
                    [--docs-root DIR] [--app-name NAME]

Exit codes: 0 every requested document filed | 1 at least one document failed its self-check
(and was NOT filed) | 2 bad usage

Design commitments (bobz-v3-foundations.md §4f, SKILL.md "Non-negotiable rules"):

* **One marker.** `references/grounding-contract.md` defines exactly one unavailable marker,
  `Not available from Z Premium analysis` — unlike the AWS-evidence port this mirrors, there is
  no second "not extracted by this run" marker, because BobZ's MCP surface answers
  paragraph/control-flow/variable-level questions directly per program.
* **Two vocabularies, never blended.** `evidence-pack.json` carries the narrower three-value
  vocabulary (`tool-verified`, `narrative-per-program-not-tool-verified`, `z-understand-verified`)
  because MCP tool output and a deterministic local read are no longer meaningfully different
  trust levels *in the pack*. Rendered documents still use the grounding contract's four-value
  vocabulary (`z-workflow-verified`, `source-read-verified`, `narrative-per-program-not-tool-
  verified`, `z-understand-verified`) — SKILL.md rule 4 is explicit that the two must never blend
  in either direction. `doc_provenance_label()` is the one place that resolves pack -> document.
* **The self-check is enforced.** A document that fails is not filed — reported, batch continues.
* **The ledger never shrinks.** A `--levels`/`--only` run only ever touches the rows it generated.
* **Section sets come from `references/template-families.md`**, not from guesswork.
* **Feature-scoped documents** (`business_features`, `feature_catalog`, `business_rules` — any
  document whose own prompt file states `Scope: Feature-scoped`) emit one file per feature under
  a directory named after the catalog document, one ledger row per feature.
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

SKILL = os.environ.get("BOBZ_SKILL_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))

NA = "Not available from Z Premium analysis"
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

EVIDENCE_CATEGORIES = ("dataDictionary", "businessRules", "architectureNotes", "errorHandling",
                       "dependencies", "zCodeScan")

DOC_PROVENANCE_VALUES = {
    "z-workflow-verified", "source-read-verified",
    "narrative-per-program-not-tool-verified", "z-understand-verified",
}

LEDGER_COLUMNS = ["doc_key", "level", "scope", "feature_name", "z_plan", "output_path",
                  "evidence_gathered", "generated", "self_check_passed", "reviewed",
                  "batch_id", "run_date", "notes"]


def esc(s) -> str:
    return str(s).replace("|", r"\|")


def sha256_file(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, TypeError):
        return None


def read_text(path):
    if path and os.path.isfile(path):
        try:
            return open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            return None
    return None


def default_docs_root():
    return os.environ.get("BOBZ_DOCS_ROOT") or os.path.join(".", "bob-z-app-docs")


def doc_provenance_label(pack_provenance, source_text=None):
    """Resolve evidence-pack.json's three-value provenance into the grounding contract's
    four-value document vocabulary. This is the ONLY place that crossing happens (SKILL.md rule
    4: 'do not blend the two vocabularies in either direction')."""
    pv = pack_provenance or ""
    if pv == "z-understand-verified":
        return "z-understand-verified"
    if pv == "narrative-per-program-not-tool-verified":
        return "narrative-per-program-not-tool-verified"
    s = (source_text or "").lower()
    read_markers = ("regex", "read_file", "jcl member", "bms", "linkage section", "grep",
                    "source read", "workspace source", "deterministic")
    if any(m in s for m in read_markers):
        return "source-read-verified"
    # pv == "tool-verified" or unrecognised: an MCP tool call is the default assumption for
    # anything not flagged as a plain source read.
    return "z-workflow-verified"


def derive_app_name(pack, override=None):
    if override and override.strip():
        return override.strip(), "operator-supplied (--app-name)"
    ws = pack.get("workspaceRoot") or "."
    zapp = os.path.join(ws, "zapp.yaml")
    txt = read_text(zapp)
    if txt:
        m = re.search(r'^\s*name:\s*["\']?([^\n"\']+)', txt, re.M)
        if m and m.group(1).strip():
            return m.group(1).strip(), "derived from zapp.yaml"
    base = os.path.basename(os.path.normpath(ws))
    if base and base not in (".", "", os.sep):
        return base, "workspace folder name (no zapp.yaml found)"
    return "Unnamed application", "unavailable"


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "feature"


def derive_features(pack: dict) -> list[dict]:
    """Deterministic, evidence-backed feature grouping. BobZ has no business-function discovery
    step (bobz-v3-foundations.md §4d), so the closest tool-adjacent grouping available is JCL job
    membership (a job's steps name the programs it drives) and BMS mapset. Both are explicitly
    `narrative-per-program-not-tool-verified` groupings — a job or mapset is real, but "this is a
    business feature" is an inference, per evidence-plans.md's `z-business` plan note: label such
    items `Assumption — not tool-verified` or omit. Here we label, never omit."""
    app = pack.get("application") or {}
    job_map = app.get("jclJobToProgramMap") or []
    by_job = collections.OrderedDict()
    for e in job_map:
        job = e.get("job")
        if not job:
            continue
        by_job.setdefault(job, set()).add(e.get("invokes"))

    features = []
    covered = set()
    for job in sorted(by_job):
        progs = sorted(p for p in by_job[job] if p)
        covered |= set(progs)
        features.append({
            "name": job, "slug": slugify(job), "programs": progs,
            "groupingCriterion": "JCL job grouping (job-to-program map)",
            "provenance": "narrative-per-program-not-tool-verified",
        })

    bms = app.get("bms") or {}
    mapsets = sorted({v.get("mapset") for v in (bms.get("members") or {}).values()
                      if v.get("mapset")})
    for ms in mapsets:
        if any(f["name"] == ms for f in features):
            continue
        features.append({
            "name": ms, "slug": slugify(ms), "programs": [],
            "groupingCriterion": "BMS mapset grouping — no CICS transaction-to-program binding "
                                 "in this evidence pack, so no program list is claimed",
            "provenance": "narrative-per-program-not-tool-verified",
        })

    all_programs = sorted(pack.get("programs") or {})
    remainder = [p for p in all_programs if p not in covered]
    if remainder or not features:
        features.append({
            "name": "Ungrouped Programs", "slug": "ungrouped-programs",
            "programs": remainder or all_programs,
            "groupingCriterion": "catch-all — no JCL job or BMS mapset in this evidence pack "
                                 "grouped these programs into a feature",
            "provenance": "narrative-per-program-not-tool-verified",
        })
    features.sort(key=lambda f: f["name"])
    return features


def catalog() -> list[dict]:
    rows = []
    for line in open(f"{SKILL}/references/document-catalog.md", encoding="utf-8"):
        c = [x.strip() for x in line.split("|")]
        if len(c) >= 9 and c[1].isdigit():
            rows.append(dict(n=int(c[1]), lvl=int(c[2].split("—")[0].strip()),
                             pt=c[3].strip("`"), z_plan=c[4].strip("`"),
                             cast_plan=c[5].strip("`"), out=c[6].strip("`"), tpl=c[7].strip("`")))
    return sorted(rows, key=lambda r: r["n"])


def fixed_sets() -> dict:
    """Family C section sets, parsed from references/template-families.md — exactly the parser
    contract bobz-v3-foundations.md §6b specifies: a bold ``prompt_type`` line immediately
    followed by a numbered list, no blank line in between."""
    p = f"{SKILL}/references/template-families.md"
    txt = read_text(p)
    if not txt:
        return {}
    out = {}
    for m in re.finditer(r"\*\*`([a-z_]+)`\*\*\n((?:\d+\.\s+.+\n)+)", txt):
        out[m.group(1)] = [re.sub(r"^\d+\.\s*", "", ln).strip()
                           for ln in m.group(2).strip().splitlines()]
    return out


def sub_rows() -> list[tuple]:
    txt = read_text(f"{SKILL}/references/z-substitutions.md") or ""
    rows = []
    for line in txt.splitlines():
        c = [x.strip() for x in line.split("|")]
        if len(c) >= 5 and c[1] and not c[1].startswith(("-", "Template")):
            rows.append((c[1], c[2], c[3]))
    return rows


def sub_lookup(subs, heading: str):
    h = heading.lower()
    for concept, z_equiv, evidence in subs:
        key = re.sub(r"[^a-z ]", " ", concept.lower()).split("/")[0].strip()
        if not key or len(key) < 4:
            continue
        if key.split()[0] in h and "no equivalent" in z_equiv.lower():
            return f"{concept} has no Z Premium equivalent — {evidence}"
    return None


def prompt_scope_info(tpl_rel: str):
    """(feature_scoped, prompt_text) from a document's own reference file."""
    txt = read_text(os.path.join(SKILL, tpl_rel)) or ""
    m = re.search(r"^\|\s*Scope\s*\|(.+)\|\s*$", txt, re.M)
    feature_scoped = bool(m and "feature-scoped" in m.group(1).lower())
    return feature_scoped, txt


def section_set(tpl_rel: str, pt: str, fixed: dict):
    if pt in fixed:
        return fixed[pt], "C-fixed"
    txt = read_text(os.path.join(SKILL, tpl_rel)) or ""
    body = txt.split("## Prompt template", 1)[-1]
    if "OUTPUT STRUCTURE" in body:
        tail = body.split("OUTPUT STRUCTURE", 1)[1]
        hs = [re.sub(r"^\d+\.\s*", "", h).strip()
              for _l, h in re.findall(r"^(#{2})\s+(.+)$", tail, re.M)]
        hs = [h for h in hs if h and not h.startswith("{")]
        if hs:
            return _dedupe(hs), "A-output-structure"
    hs = [h.strip().rstrip(":") for h in re.findall(r"^\*\*(.+?)\*\*\s*$", body, re.M)]
    hs = [h for h in hs if "**" not in h and 2 < len(h) < 70]
    return (_dedupe(hs), "B-bold") if hs else ([], "none")


def _dedupe(hs):
    seen, out = set(), []
    for h in hs:
        if h.strip() and h.lower() not in seen:
            seen.add(h.lower())
            out.append(h.strip())
    return out


class Rec:
    """Records the artifacts one document actually read, with fingerprints and a *document-level*
    (four-value) provenance label already resolved — see `doc_provenance_label`."""

    def __init__(self, hashes=None):
        self.items = {}
        self._cache = hashes if hashes is not None else {}

    def use(self, key, provenance, what, fingerprint=None):
        if not key:
            return key
        k = str(key)
        self.items[k] = (provenance, what)
        if k not in self._cache:
            if os.path.isfile(k):
                self._cache[k] = sha256_file(k)
            elif fingerprint is not None:
                self._cache[k] = hashlib.sha256(
                    json.dumps(fingerprint, sort_keys=True, default=str).encode("utf-8")
                ).hexdigest()
        return key

    def fingerprints(self):
        return {p: self._cache.get(p) for p in sorted(self.items)}

    def table(self):
        if not self.items:
            return "No artifact supplied content for this document."
        out = ["| Artifact | What it supplied | Provenance | sha256 |", "|---|---|---|---|"]
        for k in sorted(self.items):
            prov, what = self.items[k]
            h = self._cache.get(k)
            out.append(f"| `{k}` | {what} | `{prov}` | `{h[:12]}…` |" if h
                       else f"| `{k}` | {what} | `{prov}` | — |")
        return "\n".join(out)


BUILD_PGMS = {"IGYCRCTL", "IEWL", "IEWBLINK", "DFHMAPS", "DFHECP1$", "DSNHPC", "ASMA90",
              "IKJEFT01", "IKJEFT1B", "DFHEAP1$"}


class Gen:
    def __init__(self, docs_root, date=None, app_name=None):
        self.docs = docs_root
        self.date = date or TODAY
        with open(os.path.join(docs_root, "00-manifest", "evidence-pack.json"),
                  encoding="utf-8") as fh:
            self.pack = json.load(fh)
        self.hashes = {}
        idx_path = os.path.join(docs_root, "00-manifest", "evidence-index.json")
        idx, _err = None, None
        if os.path.isfile(idx_path):
            try:
                idx = json.load(open(idx_path, encoding="utf-8"))
            except (ValueError, OSError):
                idx = None
        if idx:
            for a in idx.get("artifacts", []):
                if a.get("path") and a.get("sha256"):
                    self.hashes[a["path"]] = a["sha256"]

        self.P = self.pack.get("programs") or {}
        self.APP_AGG = self.pack.get("application") or {}
        self.PROGRAMS = sorted(self.P)
        self.APP, self.APP_SRC = derive_app_name(self.pack, app_name)
        self.FEATURES = derive_features(self.pack)
        self.FIXED = fixed_sets()
        self.SUBS = sub_rows()
        self.scope_programs = self.PROGRAMS
        self.scope_feature = None

    # ---- provenance resolution helper ----
    def lbl(self, field):
        if isinstance(field, dict):
            return doc_provenance_label(field.get("provenance"), field.get("source"))
        return doc_provenance_label(field)

    def cite(self, rec, key, field, what, fingerprint=None):
        rec.use(key, self.lbl(field), what,
                fingerprint=fingerprint if fingerprint is not None else field)

    # ---------------- shared blocks ----------------
    def coverage(self, rec):
        total = len(self.PROGRAMS)
        n = len(self.scope_programs)
        rec.use("evidence-pack.json#programs", "source-read-verified",
                "program roster and per-program evidence availability",
                fingerprint=sorted(self.PROGRAMS))
        lines = ["## Coverage", "",
                 f"Content below is grounded in **{n} of {total}** programs" +
                 (f" resolved to the **{self.scope_feature['name']}** feature"
                  if self.scope_feature else "") + ".", ""]
        if self.scope_feature:
            lines.append(f"- Feature grouping: {self.scope_feature['groupingCriterion']} — "
                         f"`Assumption — not tool-verified`")
        with_ev = [p for p in self.scope_programs
                  if any(k in self.P.get(p, {}) for k in EVIDENCE_CATEGORIES)]
        without = [p for p in self.scope_programs if p not in with_ev]
        lines.append(f"- **With at least one grounded evidence field ({len(with_ev)})**: "
                    f"{', '.join(with_ev) or '—'}")
        if without:
            lines.append(f"- **In scope, no evidence gathered yet ({len(without)})**: "
                        f"{', '.join(without)}")
        lines += ["", "Absence of evidence for a program is not evidence about that program. "
                      "Unrepresented programs are named, never characterised.", ""]
        return "\n".join(lines)

    def program_table(self, rec):
        rec.use("program-inventory.csv (via evidence-pack.json)", "source-read-verified",
               "program name, language, file path", fingerprint=sorted(self.scope_programs))
        out = ["| Program | Language | Size (bytes) | Evidence fields present |",
               "|---|---|---|---|"]
        for p in self.scope_programs:
            e = self.P.get(p, {})
            present = [k for k in EVIDENCE_CATEGORIES if k in e]
            out.append(f"| `{p}` | {esc(e.get('language') or '—')} | "
                      f"{e.get('sizeBytes', '—')} | {', '.join(present) or '—'} |")
        return "\n".join(out)

    def inventory(self, rec):
        counts = collections.Counter()
        for p in self.scope_programs:
            fp = self.P.get(p, {}).get("filePath")
            if fp:
                ext = os.path.splitext(fp)[1].lstrip(".").lower() or "(none)"
                counts[ext] += 1
            lang = self.P.get(p, {}).get("language")
            if lang:
                counts[f"lang:{lang}"] += 0  # language tracked separately below
        if not counts:
            return None
        rec.use("evidence-pack.json#programs[].filePath", "source-read-verified",
               "file extension classification", fingerprint=sorted(counts.items()))
        out = ["| Extension | Programs |", "|---|---|"]
        for k in sorted((k for k in counts if not k.startswith("lang:")), key=lambda x: -counts[x]):
            out.append(f"| `.{k}` | {counts[k]} |")
        out += ["", f"{len(self.scope_programs)} program(s) classified in this scope."]
        return "\n".join(out)

    def run_ctx(self, rec):
        rec.use("evidence-pack.json", "source-read-verified",
               "run identity, MCP reachability, workspace/docs roots")
        mcp = self.pack.get("mcp") or {}
        return "\n".join([
            "| Field | Value |", "|---|---|",
            f"| Application | {esc(self.APP)} (`{self.APP_SRC}`) |",
            f"| Workspace root | `{self.pack.get('workspaceRoot')}` |",
            f"| Docs root | `{self.pack.get('docsRoot')}` |",
            f"| Extraction root reused | `{self.pack.get('extractionRoot') or 'none'}` |",
            f"| MCP reachable | `{mcp.get('reachable')}` |",
            f"| MCP server version | `{mcp.get('serverVersion') or 'unknown'}` |",
            f"| Z Understand configured | `{mcp.get('zUnderstandConfigured')}` |",
            f"| Skill version | `{self.pack.get('skillVersion')}` |",
            f"| Programs in evidence pack | {len(self.PROGRAMS)} |",
        ])

    def datadict(self, rec):
        rows = []
        for p in self.scope_programs:
            dd = self.P.get(p, {}).get("dataDictionary")
            entries = (dd or {}).get("entries") or []
            if not entries:
                continue
            self.cite(rec, f"evidence-pack:programs.{p}.dataDictionary", dd,
                     f"data dictionary entries for {p}", fingerprint=entries)
            for e in entries:
                if isinstance(e, dict):
                    rows.append((p, e))
        if not rows:
            return None
        out = ["| Program | Field | Type | Description | Status |", "|---|---|---|---|---|"]
        for p, e in rows[:250]:
            out.append(f"| `{p}` | `{esc(e.get('name'))}` | `{esc(e.get('type'))}` | "
                      f"{esc(e.get('shortDescription') or e.get('longDescription') or '—')} | "
                      f"{esc(e.get('status') or '—')} |")
        if len(rows) > 250:
            out.append(f"| … {len(rows) - 250} further field(s) | | | | |")
        progs = sorted({p for p, _ in rows})
        out += ["", f"**{len(rows)} field(s)** across **{len(progs)} program(s)**. "
                    f"`status: draft` entries are machine-generated pending SME review "
                    f"in `17-qa-validation/dd-review-queue.md`."]
        return "\n".join(out)

    def business_narrative(self, rec):
        out, found = [], False
        for p in self.scope_programs:
            br = self.P.get(p, {}).get("businessRules")
            text = (br or {}).get("text", "").strip() if br else ""
            if not text:
                continue
            found = True
            key = f"evidence-pack:programs.{p}.businessRules"
            self.cite(rec, key, br, f"business narrative for {p}", fingerprint=text)
            label = self.lbl(br)
            out += [f"#### {p}", "", text,
                   f"\n[source: {esc(br.get('source') or 'generate_documentation(business)')} "
                   f"-> `{p}`] `{label}`", ""]
        return "\n".join(out) if found else None

    def architecture(self, rec):
        parts = []
        found = False
        for p in self.scope_programs:
            an = self.P.get(p, {}).get("architectureNotes")
            text = (an or {}).get("text", "").strip() if an else ""
            if not text:
                continue
            found = True
            key = f"evidence-pack:programs.{p}.architectureNotes"
            self.cite(rec, key, an, f"architecture narrative for {p}", fingerprint=text)
            label = self.lbl(an)
            parts += [f"#### {p}", "", text,
                     f"\n[source: {esc(an.get('source') or 'generate_documentation(architect)')} "
                     f"-> `{p}`] `{label}`", ""]
        deps = self.deps(rec)
        jmap = self.jcl_ops(rec, header=False)
        tail = [x for x in (deps, jmap) if x]
        if not found and not tail:
            return None
        return "\n\n".join(([("\n".join(parts))] if found else []) + tail)

    def deps(self, rec):
        rows = []
        for p in self.scope_programs:
            for d in self.P.get(p, {}).get("dependencies") or []:
                if not isinstance(d, dict):
                    continue
                key = f"evidence-pack:programs.{p}.dependencies"
                self.cite(rec, key, d, f"dependency edges for {p}", fingerprint=d)
                rows.append((p, d.get("target"), d.get("kind"), self.lbl(d)))
        if not rows:
            return None
        out = ["| Program | Target | Kind | Provenance |", "|---|---|---|---|"]
        for p, t, k, prov in sorted(set(rows)):
            out.append(f"| `{p}` | `{esc(t)}` | {esc(k)} | `{prov}` |")
        out += ["", f"{len(rows)} dependency edge(s) across "
                   f"{len({p for p, *_ in rows})} program(s)."]
        return "\n".join(out)

    def lineage(self, rec):
        rows = []
        for p in self.scope_programs:
            for d in self.P.get(p, {}).get("dependencies") or []:
                if not isinstance(d, dict):
                    continue
                kind = str(d.get("kind") or "").upper()
                if kind in ("FILE", "DATASET", "VSAM", "DB2", "QSAM", "TABLE"):
                    key = f"evidence-pack:programs.{p}.dependencies"
                    self.cite(rec, key, d, f"dataset/table access for {p}")
                    rows.append((p, d.get("target"), kind))
        if not rows:
            return None
        out = ["| Program | Dataset/Table | Kind |", "|---|---|---|"]
        for p, t, k in sorted(set(rows)):
            out.append(f"| `{p}` | `{esc(t)}` | {k} |")
        out += ["", "Lineage is recorded at program-and-dataset level, per "
                   "`references/z-substitutions.md`'s stated granularity limit — per-field "
                   "read/transform/write chains require `get_variables`/`get_expanded_source` "
                   "output not present for every program in scope."]
        return "\n".join(out)

    def complexity(self, rec, n=20):
        ranking = [r for r in (self.APP_AGG.get("complexityRanking") or [])
                  if r.get("programName") in self.scope_programs]
        if not ranking:
            return None
        rec.use("evidence-pack.json#application.complexityRanking", "z-workflow-verified",
               "per-program cyclomatic complexity (Z Code Scan)", fingerprint=ranking)
        out = ["| Program | Complexity |", "|---|---|"]
        for r in ranking[:n]:
            out.append(f"| `{esc(r['programName'])}` | {r['complexity']} |")
        if len(ranking) > n:
            out.append(f"| … {len(ranking) - n} further program(s) | |")
        return "\n".join(out)

    def quality_findings(self, rec, n=30):
        rows = []
        for p in self.scope_programs:
            zcs = self.P.get(p, {}).get("zCodeScan")
            for f in (zcs or {}).get("findings") or []:
                if isinstance(f, dict):
                    self.cite(rec, f"evidence-pack:programs.{p}.zCodeScan", zcs,
                            f"Z Code Scan findings for {p}", fingerprint=zcs.get("findings"))
                    rows.append((p, f.get("name") or f.get("id") or "finding",
                               f.get("severity") or "—"))
        if not rows:
            return None
        out = ["| Program | Finding | Severity |", "|---|---|---|"]
        for p, name, sev in rows[:n]:
            out.append(f"| `{p}` | {esc(name)} | {esc(sev)} |")
        if len(rows) > n:
            out.append(f"| … {len(rows) - n} further finding(s) | | |")
        return "\n".join(out)

    def entrypoints(self, rec, n=10):
        parts = []
        link = self.linkage(rec, n=n, header=False)
        bms = self.bms_maps(rec, n=3, header=False)
        if link:
            parts.append("### Called-program interfaces (LINKAGE SECTION)\n\n" + link)
        if bms:
            parts.append("### Online screen entry points (BMS)\n\n" + bms)
        return "\n\n".join(parts) if parts else None

    def linkage(self, rec, n=10, header=True):
        L = self.APP_AGG.get("linkage") or {}
        members = {k: v for k, v in (L.get("members") or {}).items() if k in self.scope_programs}
        if not members:
            return None
        out = []
        if header:
            out.append(f"**{len(members)} program(s)** declare a LINKAGE SECTION in scope, "
                      f"**{sum(v['itemCount'] for v in members.values())} item(s)** total.\n")
        out += ["| Program | Items | LINKAGE at line |", "|---|---|---|"]
        for k in sorted(members)[:n]:
            v = members[k]
            rec.use(v["path"], "source-read-verified", f"LINKAGE SECTION of {k}")
            out.append(f"| `{k}` | {v['itemCount']} | {v['line']} |")
        if len(members) > n:
            out.append(f"| … {len(members) - n} further program(s) | | |")
        first = sorted(members)[0]
        fv = members[first]
        out += ["", f"Signature of `{first}`:", "",
               "| Level | Name | PIC | Line |", "|---|---|---|---|"]
        for it in fv["items"][:12]:
            out.append(f"| {it['level']} | `{it['name']}` | `{it['pic'] or '—'}` | {it['line']} |")
        return "\n".join(out)

    def bms_maps(self, rec, n=3, header=True):
        B = self.APP_AGG.get("bms") or {}
        members = B.get("members") or {}
        if not members:
            return None
        out = []
        if header:
            out.append(f"**{B['memberCount']} BMS mapset(s)**, **{B['mapCount']} map(s)**, "
                      f"**{B['namedFieldCount']} named field(s)** — the request/response "
                      f"contract for an online transaction.\n")
        for k in sorted(members)[:n]:
            v = members[k]
            rec.use(v["path"], "source-read-verified", f"screen field layout in {k}")
            out.append(f"#### `{k}` — mapset `{v.get('mapset')}`\n")
            for mp, fields in v["maps"].items():
                named = [f for f in fields if f["field"] != "(unnamed literal)"]
                out += [f"Map `{mp}` — {len(fields)} field(s) ({len(named)} named):", "",
                       "| Field | Length | Row | Col | Attributes |", "|---|---|---|---|---|"]
                for f in named[:10]:
                    out.append(f"| `{f['field']}` | {f['length'] or '—'} | {f['row'] or '—'} | "
                              f"{f['col'] or '—'} | `{f['attrb'] or '—'}` |")
                out.append("")
        if len(members) > n:
            out.append(f"… {len(members) - n} further mapset(s) in the codebase.")
        return "\n".join(out)

    def error_handling(self, rec, n=15):
        parts = []
        narrative = []
        for p in self.scope_programs:
            eh = self.P.get(p, {}).get("errorHandling")
            text = (eh or {}).get("text", "").strip() if eh else ""
            if not text:
                continue
            key = f"evidence-pack:programs.{p}.errorHandling"
            self.cite(rec, key, eh, f"error-handling narrative for {p}", fingerprint=text)
            label = self.lbl(eh)
            narrative += [f"#### {p}", "", text,
                         f"\n[source: {esc(eh.get('source') or 'generate_documentation(developer)')} "
                         f"-> `{p}`] `{label}`", ""]
        if narrative:
            parts.append("\n".join(narrative))
        E = self.APP_AGG.get("errorHandlingConstructs") or {}
        members = {k: v for k, v in (E.get("members") or {}).items() if k in self.scope_programs}
        if members:
            total = sum(v["total"] for v in members.values())
            by = collections.Counter()
            for v in members.values():
                by.update(v["counts"])
            tbl = [f"**{total} error-handling construct(s)** across **{len(members)} program(s)** "
                  f"in scope, {len(by)} distinct kind(s):", "",
                  "| Construct | Occurrences |", "|---|---|"]
            for k, v in by.most_common():
                tbl.append(f"| `{k}` | {v} |")
            top = sorted(members.items(), key=lambda kv: -kv[1]["total"])[:n]
            tbl += ["", "| Program | Constructs | Kinds |", "|---|---|---|"]
            for k, v in top:
                rec.use(v["path"], "source-read-verified", f"error-handling constructs in {k}")
                tbl.append(f"| `{k}` | {v['total']} | "
                          f"{', '.join(f'`{x}`' for x in sorted(v['counts']))} |")
            parts.append("\n".join(tbl))
        return "\n\n".join(parts) if parts else None

    def jcl_ops(self, rec, n=12, header=True):
        jmap = [e for e in (self.APP_AGG.get("jclJobToProgramMap") or [])
               if e.get("invokes") in self.scope_programs or self.scope_feature is None]
        if not jmap:
            return None
        for e in jmap[: n * 4]:
            self.cite(rec, f"jcl-job-map:{e.get('job')}", e, f"job-to-program map entry ({e.get('job')})")
        by_job = collections.OrderedDict()
        for e in jmap:
            by_job.setdefault(e["job"], []).append(e["invokes"])
        out = []
        if header:
            out.append(f"**{len(by_job)} job(s)** invoke **{len(jmap)} step(s)** across programs "
                      f"in scope.\n")
        out += ["| Job | Programs invoked |", "|---|---|"]
        for job in sorted(by_job)[:n]:
            out.append(f"| `{job}` | {', '.join(f'`{p}`' for p in sorted(set(by_job[job])))} |")
        if len(by_job) > n:
            out.append(f"| … {len(by_job) - n} further job(s) | |")
        return "\n".join(out)

    def build_notes(self, rec):
        jcl = self.APP_AGG.get("jcl") or {}
        members = jcl.get("members") or {}
        if not members:
            return None
        build = {}
        for k, v in members.items():
            hits = [s for s in v["steps"] if s["invokes"] in BUILD_PGMS]
            if hits or re.search(r"CMP|COMPIL|LINK|BIND", k, re.I):
                build[k] = {"path": v["path"], "steps": v["steps"], "buildSteps": hits}
        if not build:
            return None
        out = [f"**{len(build)} build/compile/link member(s)** identified by the utilities they "
              f"invoke.\n", "| Member | Steps | Build/link steps |", "|---|---|---|"]
        for k in sorted(build):
            v = build[k]
            rec.use(v["path"], "source-read-verified", f"compile/link steps in {k}")
            bs = ", ".join(f"`{s['invokes']}`" for s in v["buildSteps"][:4]) or "—"
            out.append(f"| `{k}` | {len(v['steps'])} | {bs} |")
        out += ["", f"Promotion between environments and load-library concatenation at runtime "
                   f"are not in the codebase: `{NA}`."]
        return "\n".join(out)

    def codeflow(self, rec, n=10):
        out = []
        for p in self.scope_programs:
            cf = self.P.get(p, {}).get("codeFlow") or {}
            paras = cf.get("paragraphs")
            cflow = cf.get("controlFlow")
            explain = self.P.get(p, {}).get("explain")
            if not (paras or cflow or explain):
                continue
            block = [f"#### {p}", ""]
            if paras:
                key = f"evidence-pack:programs.{p}.codeFlow.paragraphs"
                self.cite(rec, key, paras, f"paragraph index for {p}")
                items = paras.get("items") or []
                block.append(f"- **{len(items)} paragraph(s)** indexed by `get_paragraphs`.")
            if cflow:
                key = f"evidence-pack:programs.{p}.codeFlow.controlFlow"
                self.cite(rec, key, cflow, f"control-flow graph for {p}")
                block.append("- Control-flow graph available from `get_control_flow`.")
            if explain:
                key = f"evidence-pack:programs.{p}.explain"
                self.cite(rec, key, explain, f"explain_code narrative for {p}",
                        fingerprint=explain.get("paragraphs"))
                for para, text in list((explain.get("paragraphs") or {}).items())[:n]:
                    block.append(f"  - `{esc(para)}`: {esc((text or '').strip())} "
                               f"`{self.lbl(explain)}`")
            out.append("\n".join(block))
        return "\n\n".join(out) if out else None

    def open_gaps(self, rec):
        gaps = {p: v for p, v in (self.pack.get("evidenceGaps") or {}).items()
               if p in self.scope_programs}
        if not gaps:
            return None
        rec.use("evidence-pack.json#evidenceGaps", "source-read-verified",
               "recorded evidence gaps per program", fingerprint=gaps)
        out = [f"**{len(gaps)} program(s) in scope have at least one recorded evidence gap** — "
              f"fields no MCP tool call or source read has produced yet, kept explicit rather "
              f"than silently omitted.\n", "| Program | Missing evidence |", "|---|---|"]
        for p in sorted(gaps):
            out.append(f"| `{p}` | {', '.join(gaps[p])} |")
        out += ["", "These are decisions/evidence the run left implicit — handoff items for the "
                   "next `extract_evidence.py` pass, not defects in this document."]
        return "\n".join(out)

    # ---- honesty-first table: headings matching one of these are unavailable no matter what a
    # generic builder might superficially answer. Ported from the AWS-evidence port's `HARD_NA`
    # with Z-specific reasons (bobz-v3-foundations.md §4f item 1, z-substitutions.md's "no
    # equivalent" rows, evidence-plans.md's "not available without Z Understand" notes).
    HARD_NA = [
        (r"target|future.?state|to.?be state|cloud|aws service|landing zone|migration target",
         "target-state design is a forward-engineering decision, outside this skill's "
         "reverse-engineering scope"),
        (r"owner|stakeholder|\bteam\b|persona|raci|organis|organiz|responsib|governance",
         "no ownership, stakeholder or organisational data exists in the evidence pack — "
         "z-substitutions.md's 'Organisation and people' items require inference labelled "
         "`Assumption — not tool-verified`, which this heading does not request"),
        (r"securit|threat|vulnerab|\bcve\b|iso ?5055|penetration|encryption at rest|access control "
         r"polic",
         "Z Code Scan produces no CVE mapping or ISO 5055 characteristic scoring, and there is "
         "no security posture assessment tool in this evidence set"),
        (r"cost|budget|licen|pricing|\broi\b|\btco\b|financial",
         "no cost or licensing data in the evidence set"),
        (r"\bsla\b|uptime|availabilit|\bkpi\b|telemetr|benchmark|performance metric",
         "no runtime telemetry, SLA or performance data — Z Premium Package analyses source, "
         "not a running system"),
        (r"retention|privacy|sensitiv|gdpr|\bpii\b|data classification",
         "no data classification or retention policy in the evidence set"),
        (r"\btest coverage|coverage metric|\bqa\b test",
         "no test-coverage tool output in the evidence set (checked-in test JCL, if any, is a "
         "job inventory item, not a coverage metric)"),
        (r"\brpo\b|\brto\b|standby|offsite|hot site",
         "recovery point/time objectives are runtime configuration, absent from both the Z "
         "Premium Package output and the codebase"),
        (r"dashboard|\bapm\b|log aggregat|distributed trac",
         "no runtime monitoring or log-aggregation tooling exists in the evidence set"),
        (r"resource requirement|staffing|effort estimate|timeline|milestone",
         "no schedule, capacity or resourcing data in the evidence set"),
        (r"database schema.*(ddl|constraint|trigger|index)|constraint.{0,10}trigger|row count|"
         r"\bdb size\b",
         "DB2/IMS DDL, constraints, triggers and row counts require DBA tooling outside Bob"),
        (r"rate limit|throttl|\bquota\b",
         "the closest Z equivalent, CICS MAXTASKS/transaction class, is usually configured "
         "outside the repository"),
        (r"docker|kubernetes|container|cloud config",
         "LPAR, CICS region and PROCLIB definitions are usually outside the repository"),
        (r"(capabilit|feature|architect|technolog|process).{0,12}gap|gap.{0,12}(capabilit|feature)",
         "a gap assessment compares current state against a target state; no target model "
         "exists in the evidence set, and inventing one would be forward engineering"),
    ]

    def builders(self):
        return [
            (r"data entit|attribute|data dictionar|\bfield\b|schema|key table|column|data model|"
             r"\bvariable|data element",
             self.datadict, "datadict"),
            (r"lineage|data flow|transformation",
             self.lineage, "lineage"),
            (r"business rule|validation|policy|rule inventory|constraint|requirement|user stor|"
             r"acceptance criteri|process|workflow|sequence|journey|scenario",
             self.business_narrative, "business_narrative"),
            (r"complexity|technical debt|hotspot|risk assessment(?!.{0,20}cost)|\beffort\b",
             self.complexity, "complexity"),
            (r"issue|finding|violation|defect|anti.?pattern|static analysis|code smell|"
             r"code quality",
             self.quality_findings, "quality_findings"),
            (r"architecture|structure|layer|component|logical|physical|integration|landscape|"
             r"pattern|topolog",
             self.architecture, "architecture"),
            (r"dependenc|coupling|call graph",
             self.deps, "deps"),
            (r"entry point|\bapi\b|endpoint|integration point|message spec|payload|\binterface",
             self.entrypoints, "entrypoints"),
            (r"error|exception|fault|failure mode",
             self.error_handling, "error_handling"),
            (r"conditional|restart|\bcond=|job control|return code|checkpoint|monitor|alert|"
             r"observab|logging|operational|disaster recovery|failover",
             self.jcl_control, "jcl_control"),
            (r"deploy|build|compile|link|pipeline|ci.?cd|packaging|promotion|release",
             self.build_notes, "build_notes"),
            (r"screen|\bmap\b|\bbms\b|field layout|user interface|request.{0,10}response",
             self.bms_maps, "bms_maps"),
            (r"linkage|signature|parameter|called program|program interface",
             self.linkage, "linkage"),
            (r"schedul|\bjob\b|\bbatch\b|\bstep\b|runbook|operations",
             self.jcl_ops, "jcl_ops"),
            (r"open question|assumption|gap identif|gap analys",
             self.open_gaps, "open_gaps"),
            (r"technolog|tech stack|language|extension|directory",
             self.inventory, "inventory"),
            (r"paragraph|control flow|explain",
             self.codeflow, "codeflow"),
            (r"inventor|classification|file type|asset|capabilit|feature catalog|"
             r"function inventor|\bscope\b|module organi",
             self.program_table, "program_table"),
            (r"overview|summar|context|introduction|purpose|repositor",
             self.run_ctx, "run_ctx"),
        ]

    def jcl_control(self, rec):
        """Conditional execution, restart, ABEND handling and DR-relevant recovery logic."""
        jcl = self.APP_AGG.get("jcl") or {}
        if not jcl.get("memberCount"):
            return self.error_handling(rec)
        cond, restart = jcl.get("withCond") or [], jcl.get("withRestart") or []
        out = [f"- **Conditional execution** (`COND=`): present in **{len(cond)}** of "
              f"{jcl['memberCount']} JCL member(s).", ""]
        if cond:
            out += ["| Member | Condition | Line |", "|---|---|---|"]
            for k in cond[:10]:
                v = jcl["members"][k]
                rec.use(v["path"], "source-read-verified", f"COND= logic in {k}")
                for c in v["cond"][:2]:
                    out.append(f"| `{k}` | `COND={c['value']}` | {c['line']} |")
        out += ["", f"- **Restart points** (`RESTART=`): **{len(restart)}** member(s)." +
               (f" Present in: {', '.join(f'`{x}`' for x in restart)}."
                if restart else " No member carries an active `RESTART=`."), ""]
        out.append(f"Runtime recovery configuration — offsite copies, standby capacity, numeric "
                  f"RPO/RTO targets — is outside this evidence set entirely: `{NA}`.")
        return "\n".join(out)

    # ---------------- resolver ----------------
    def resolve(self, heading, rec):
        h = re.sub(r"[^a-z0-9 ]", " ", heading.lower()).strip()

        for pat, reason in self.HARD_NA:
            if re.search(pat, h):
                return f"`{NA}` — {reason}", "na", "hard-na"

        for pat, fn, name in self.builders():
            if re.search(pat, h):
                v = fn(rec)
                if v:
                    return v, "grounded", name
                return (f"`{NA}` — the `{name}` evidence this heading needs is not present for "
                       f"any program in scope", "na", name)

        reason = sub_lookup(self.SUBS, heading)
        if reason:
            return f"`{NA}` — {reason}", "na", "substitutions"

        return f"`{NA}` — no builder in this suite answers this heading", "na", "none"

    # ---------------- self-check (enforced) ----------------
    def self_check(self, text, heads, rec):
        fails = []
        if "## Coverage" not in text:
            fails.append("no Coverage note")
        if f"{len(self.scope_programs)} of {len(self.PROGRAMS)}" not in text:
            fails.append("coverage denominator absent")
        if "## Evidence Index" not in text:
            fails.append("no Evidence Index")
        for h in heads:
            if f"## {h}" not in text:
                fails.append(f"template heading dropped: {h}")
        leaks = ["Not available from AWS Transform analysis", "atx-artifact-verified",
                "requirements-derived", "Not extracted by this run", "`tool-verified`"]
        for bad in leaks:
            if bad in text:
                fails.append(f"non-Bob vocabulary leaked: {bad}")
        for k, (prov, _what) in rec.items.items():
            if prov not in DOC_PROVENANCE_VALUES:
                fails.append(f"artifact '{k}' carries an unrecognised provenance label: {prov!r}")
        if not rec.items:
            fails.append("no artifact recorded as read")
        return fails

    # ---------------- build one document ----------------
    def build(self, doc, feature=None):
        pt = doc["pt"]
        self.scope_feature = feature
        self.scope_programs = feature["programs"] if feature else self.PROGRAMS
        rec = Rec(self.hashes)
        heads, fam = section_set(doc["tpl"], pt, self.FIXED)

        header_name = pt.replace("_", " ").title()
        if feature:
            header_name += f" — {feature['name']}"
        L = [f"# {header_name}", "",
            f"**Application:** {self.APP}  ",
            f"**Generated:** {self.date}  ",
            "**Generated by:** IBM Bob — Z Premium Package workflows  ",
            f"**Evidence plan:** `{doc['z_plan']}`  ",
            f"**Document:** {pt} (catalog #{doc['n']}, level L{doc['lvl']})  ",
            f"**Section set:** {len(heads)} section(s), template family {fam} "
            f"(see `references/template-families.md`)", "",
            "> Every statement below is grounded in a BobZ MCP tool result or a source read "
            "obtained this run. Ungrounded fields read the fixed marker below.", "",
            f"> `{NA}` — this document's single unavailable marker "
            "(`references/grounding-contract.md` rule 3). It never distinguishes 'the evidence "
            "does not exist' from 'this run did not gather it' — BobZ's MCP surface answers "
            "per-program structural questions directly, so that AWS-evidence-port distinction "
            "does not apply here.", ""]
        if not (self.pack.get("mcp") or {}).get("zUnderstandConfigured"):
            L += ["> **Z Understand caveat.** No Z Understand server is configured — every "
                 "`get_project_*`-backed section reads unavailable rather than approximated.", ""]

        L += [self.coverage(rec), "---", ""]

        counts = collections.Counter()
        emitted = {}
        if not heads:
            L += ["## Content", "", f"`{NA}` — template supplies no section set", ""]
            counts["na"] += 1
        for h in heads:
            body, kind, _builder = self.resolve(h, rec)
            if kind == "grounded":
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
             f"**Sections:** {counts['grounded']} grounded · {counts['na']} unavailable · "
             f"{sum(counts.values())} total", ""]
        text = "\n".join(L)
        return text, counts, fam, rec, heads


# ---------------------------------------------------------------------------
# Ledger / manifest I/O
# ---------------------------------------------------------------------------

def read_ledger(path) -> dict:
    rows = {}
    if os.path.isfile(path):
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("doc_key"):
                    rows[r["doc_key"]] = r
    return rows


def write_ledger(path, rows: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LEDGER_COLUMNS)
        w.writeheader()
        for k in sorted(rows, key=lambda k: (int(rows[k].get("level") or 9), k)):
            w.writerow({c: rows[k].get(c, "") for c in LEDGER_COLUMNS})


def is_complete(row: dict) -> bool:
    return (row.get("evidence_gathered") == "Y" and row.get("generated") == "Y"
            and row.get("self_check_passed") == "Y")


def next_batch_id(rows: dict) -> str:
    mx = 0
    for r in rows.values():
        m = re.match(r"batch-(\d+)$", r.get("batch_id") or "")
        if m:
            mx = max(mx, int(m.group(1)))
    return f"batch-{mx + 1}"


def write_manifests(docs_root, ledger: dict, g: Gen, generated_at: str, batch_results: list):
    M = os.path.join(docs_root, "00-manifest")
    os.makedirs(M, exist_ok=True)

    by_status = collections.Counter()
    for r in ledger.values():
        by_status["complete" if is_complete(r) else (r.get("notes") or "pending")] += 1

    man_path = os.path.join(M, "documentation-manifest.json")
    man = {}
    if os.path.isfile(man_path):
        try:
            man = json.load(open(man_path, encoding="utf-8"))
        except (ValueError, OSError):
            man = {}
    man.update({
        "generatedAt": generated_at,
        "docsRoot": docs_root,
        "application": {"name": g.APP, "nameSource": g.APP_SRC},
        "mcp": g.pack.get("mcp"),
        "coverage": {
            "programsInPack": len(g.PROGRAMS),
            "featuresDerived": [f["name"] for f in g.FEATURES],
        },
        "documents": {
            "total": len(ledger),
            "complete": sum(1 for r in ledger.values() if is_complete(r)),
            "byLevel": dict(collections.Counter(r.get("level") for r in ledger.values())),
        },
        "documentList": sorted(ledger.values(), key=lambda r: (int(r.get("level") or 9),
                                                                r.get("doc_key") or "")),
    })
    json.dump(man, open(man_path, "w", encoding="utf-8"), indent=1)

    log_path = os.path.join(M, "generation-log.md")
    lines = [f"## Batch at {generated_at}", "",
            "| doc_key | Status | Grounded | Unavailable | Artifacts | Output |",
            "|---|---|---|---|---|---|"]
    for r in batch_results:
        lines.append(f"| `{r['doc_key']}` | {r['status']} | {r['grounded']} | {r['na']} | "
                    f"{r['artifacts']} | `{r['output_path']}` |")
    lines.append("")
    prior = read_text(log_path) or "# Generation Log\n\n"
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write(prior + "\n".join(lines) + "\n")


def write_document_evidence(docs_root, fingerprints: dict, generated_at: str):
    p = os.path.join(docs_root, "00-manifest", "document-evidence.json")
    prior = {}
    if os.path.isfile(p):
        try:
            prior = json.load(open(p, encoding="utf-8")).get("documents", {})
        except (ValueError, OSError):
            prior = {}
    prior.update(fingerprints)
    json.dump({"generatedAt": generated_at, "documents": prior},
             open(p, "w", encoding="utf-8"), indent=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels")
    ap.add_argument("--only")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--docs-root", default=None)
    ap.add_argument("--app-name", default=os.environ.get("BOBZ_APP_NAME"))
    args = ap.parse_args()

    docs_root = args.docs_root or default_docs_root()

    want_levels = None
    if args.levels:
        try:
            want_levels = {int(x) for x in args.levels.split(",")}
        except ValueError:
            ap.error(f"--levels must be a comma-separated list of integers, got {args.levels!r}")

    pack_path = os.path.join(docs_root, "00-manifest", "evidence-pack.json")
    if not os.path.isfile(pack_path):
        print(f"BLOCKED: {pack_path} not found — run extract_evidence.py first", file=sys.stderr)
        return 1
    try:
        g = Gen(docs_root, app_name=args.app_name)
    except (ValueError, OSError) as e:
        print(f"BLOCKED: could not load {pack_path}: {e}", file=sys.stderr)
        return 1

    ledger_path = os.path.join(docs_root, "00-manifest", "document-ledger.csv")
    ledger = read_ledger(ledger_path)
    batch_id = next_batch_id(ledger)

    failed = 0
    batch_results = []
    fingerprints = {}

    for doc in catalog():
        if want_levels is not None and doc["lvl"] not in want_levels:
            continue
        if args.only and doc["pt"] != args.only:
            continue

        feature_scoped, _txt = prompt_scope_info(doc["tpl"])
        targets = [(f, f"{doc['pt']}::{f['slug']}") for f in g.FEATURES] if feature_scoped \
            else [(None, doc["pt"])]

        for feature, doc_key in targets:
            prior_row = ledger.get(doc_key)
            if not args.force and prior_row and is_complete(prior_row):
                print(f"  L{doc['lvl']} {doc_key:40} skipped (complete; --force to regenerate)")
                continue

            text, counts, fam, rec, heads = g.build(doc, feature)
            fails = g.self_check(text, heads, rec)

            base_out = doc["out"]
            if feature:
                stem = os.path.splitext(base_out)[0]
                out_rel = f"{stem}/{feature['slug']}.md"
            else:
                out_rel = base_out
            out_path = os.path.join(docs_root, out_rel)

            if fails:
                failed += 1
                print(f"  L{doc['lvl']} {doc_key:40} SELF-CHECK FAILED -> not filed: "
                     f"{fails[:2]}")
                ledger[doc_key] = {
                    "doc_key": doc_key, "level": str(doc["lvl"]),
                    "scope": f"feature:{feature['name']}" if feature else "application",
                    "feature_name": feature["name"] if feature else "—",
                    "z_plan": doc["z_plan"], "output_path": out_rel,
                    "evidence_gathered": "Y" if rec.items else "N",
                    "generated": "Y", "self_check_passed": "N",
                    "reviewed": (prior_row or {}).get("reviewed", "N"),
                    "batch_id": batch_id, "run_date": TODAY,
                    "notes": "; ".join(fails)[:500],
                }
                continue

            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(text)

            ledger[doc_key] = {
                "doc_key": doc_key, "level": str(doc["lvl"]),
                "scope": f"feature:{feature['name']}" if feature else "application",
                "feature_name": feature["name"] if feature else "—",
                "z_plan": doc["z_plan"], "output_path": out_rel,
                "evidence_gathered": "Y" if rec.items else "N",
                "generated": "Y", "self_check_passed": "Y",
                "reviewed": (prior_row or {}).get("reviewed", "N"),
                "batch_id": batch_id, "run_date": TODAY,
                "notes": f"{counts['grounded']} grounded, {counts['na']} unavailable, "
                        f"family {fam}",
            }
            fingerprints[doc_key] = rec.fingerprints()
            batch_results.append({"doc_key": doc_key, "status": "complete",
                                  "grounded": counts["grounded"], "na": counts["na"],
                                  "artifacts": len(rec.items), "output_path": out_rel})
            print(f"  L{doc['lvl']} {doc_key:40} {counts['grounded']:2}g {counts['na']:2}u "
                 f"{len(rec.items):3} artifacts -> filed")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_ledger(ledger_path, ledger)
    write_manifests(docs_root, ledger, g, now, batch_results)
    if fingerprints:
        write_document_evidence(docs_root, fingerprints, now)

    filed = len(batch_results)
    print(f"\n{filed} filed this batch, {failed} failed self-check "
         f"({len(ledger)} rows in the ledger)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
