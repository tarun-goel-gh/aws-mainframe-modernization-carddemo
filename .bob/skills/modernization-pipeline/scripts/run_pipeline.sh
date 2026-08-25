#!/usr/bin/env bash
# End-to-end driver: mainframe codebase -> BobZ knowledge extraction -> 31 application documents
# -> a local, disclosure-scanned zip. No AWS anywhere: no S3, no presigned URL, no bucket policy.
#
# Nine phases, one persistent extraction root, one persistent docs root, one pipeline-scoped run
# state. Written for macOS bash 3.2, so no associative arrays and no ${var,,}.
#
#   1 preflight       inventory (script) + MCP reachability probe (agent-written, script only reads it)
#   2 extract         STOP for the agent: run cobol-knowledge-extraction batch after batch via MCP
#   3 extract-verify  cobol-knowledge-extraction/scripts/verify_extraction.py — Gate B
#   4 reuse-snapshot  index bob-z-knowledge-extract/ artifacts + sha256 fingerprints for reuse
#   5 coverage        z-app-documentation/scripts/build_coverage.py — Gate C
#   6 evidence        z-app-documentation/scripts/extract_evidence.py
#   7 generate        z-app-documentation/scripts/generate_docs.py
#   8 package         zip bob-z-app-docs/, refuse on a disclosure-scan hit
#   9 publish         STOP for the agent: an optional, confirmed, plain file copy
#
# This script NEVER calls an MCP tool. Phases 2 and 9 need the agent to act on its own turn — the
# script recognizes that, prints what to do, and exits 3 rather than faking a result.
#
# Usage:
#   run_pipeline.sh --scope Cobol/ --app-name CardDemo
#   run_pipeline.sh --offline                          # document an existing bob-z-knowledge-extract/
#   run_pipeline.sh --resume 20260824-101500 --from extract-verify
#
# Options:
#   --scope S            path | @filelist | inventory.csv | glob, forwarded to build_inventory.py
#   --workspace-root DIR default '.'
#   --extraction-root DIR default '<workspace-root>/bob-z-knowledge-extract'
#   --docs-root DIR      default '<workspace-root>/bob-z-app-docs'
#   --app-name NAME      forwarded to generate_docs.py; default derived, never invented
#   --force              forwarded to extract_evidence.py / generate_docs.py
#   --publish-to PATH    destination hint shown in the phase-9 stop marker; the script never copies
#   --run-id TS          use this stamp instead of the current time
#   --resume TS          reuse this pipeline's own recorded run state; phases already ok/partial/
#                        skipped are skipped. extractionRoot/docsRoot are persistent, not stamped
#                        per run, so this resumes bookkeeping, not a folder pick.
#   --from PHASE         start at this phase (skip earlier ones)
#   --only PHASE         run exactly one phase
#   --offline            skip phase 2 (extract); document whatever bob-z-knowledge-extract/ holds
#   --no-publish         run phases 1-8 and stop before the phase-9 marker
#   --dry-run            print the plan and exit without touching anything
#   --keep-going         continue after a fatal phase failure instead of stopping
#
# Exit codes: 0 every selected phase met its contract | 1 a phase failed | 2 bad usage |
#             3 the run stopped at an agent-required phase (2 or 9) — not a failure
#
# Phase 7 (generate) and phase 5 (coverage) can legitimately come back "partial" when evidence is
# thin. That is a reportable state, not a driver failure, so the run continues.

set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COBOL_SCRIPTS="$(cd "$SELF_DIR/../../cobol-knowledge-extraction/scripts" 2>/dev/null && pwd || echo "")"
ZAPP_SCRIPTS="$(cd "$SELF_DIR/../../z-app-documentation/scripts" 2>/dev/null && pwd || echo "")"

SCOPE=""; WORKSPACE_ROOT="."; EXTRACTION_ROOT=""; DOCS_ROOT=""
APP_NAME=""; FORCE=0; PUBLISH_TO=""
RUN_ID=""; RESUME=""; FROM_PHASE=""; ONLY_PHASE=""
OFFLINE=0; NO_PUBLISH=0; DRY_RUN=0; KEEP_GOING=0

PHASE_IDS="preflight extract extract-verify reuse-snapshot coverage evidence generate package publish"
AGENT_PHASES="extract publish"
PHASE_TOTAL=9

usage() { sed -n '2,44p' "$0" >&2; exit 2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scope)           SCOPE="${2:-}"; shift 2 ;;
    --workspace-root)  WORKSPACE_ROOT="${2:-}"; shift 2 ;;
    --extraction-root) EXTRACTION_ROOT="${2:-}"; shift 2 ;;
    --docs-root)       DOCS_ROOT="${2:-}"; shift 2 ;;
    --app-name)        APP_NAME="${2:-}"; shift 2 ;;
    --force)           FORCE=1; shift ;;
    --publish-to)      PUBLISH_TO="${2:-}"; shift 2 ;;
    --run-id)          RUN_ID="${2:-}"; shift 2 ;;
    --resume)          RESUME="${2:-}"; shift 2 ;;
    --from)            FROM_PHASE="${2:-}"; shift 2 ;;
    --only)            ONLY_PHASE="${2:-}"; shift 2 ;;
    --offline)         OFFLINE=1; shift ;;
    --no-publish)      NO_PUBLISH=1; shift ;;
    --dry-run)         DRY_RUN=1; shift ;;
    --keep-going)      KEEP_GOING=1; shift ;;
    -h|--help)         usage ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
done

in_list() { # in_list <needle> <space separated haystack>
  case " $2 " in *" $1 "*) return 0 ;; *) return 1 ;; esac
}

for p in $FROM_PHASE $ONLY_PHASE; do
  in_list "$p" "$PHASE_IDS" || { echo "ERROR: unknown phase '$p'. Known: $PHASE_IDS" >&2; exit 2; }
done

# ---------- resolve the persistent roots ----------
# Unlike atx-pipeline, extractionRoot and docsRoot are NOT stamped per run: BobZ's own ledgers
# (extraction-status.csv, document-ledger.csv) already make a re-run resumable, and stamping a
# fresh folder every time would throw away the mcp-cache/ that makes 31 documents affordable. Only
# this pipeline's own bookkeeping (pipeline-run-log.md, pipeline-run-state.json) is per invocation.
WORKSPACE_ROOT="$(cd "$WORKSPACE_ROOT" 2>/dev/null && pwd || echo "$WORKSPACE_ROOT")"
[[ -n "$EXTRACTION_ROOT" ]] || EXTRACTION_ROOT="$WORKSPACE_ROOT/bob-z-knowledge-extract"
[[ -n "$DOCS_ROOT" ]]       || DOCS_ROOT="$WORKSPACE_ROOT/bob-z-app-docs"

if [[ -n "$RESUME" ]]; then
  RUN_ID="$RESUME"
fi
[[ -n "$RUN_ID" ]] || RUN_ID="$(date +%Y%m%d-%H%M%S)"

MANIFEST_DIR="$DOCS_ROOT/00-manifest"
RUN_LOG="$MANIFEST_DIR/pipeline-run-log.md"
RUN_STATE="$MANIFEST_DIR/pipeline-run-state.json"
PROBE_FILE="$MANIFEST_DIR/mcp-capability-probe.json"
ZIP_PATH="$(dirname "$DOCS_ROOT")/$(basename "$DOCS_ROOT")-$RUN_ID.zip"

require_script() { # require_script <path> — a missing sibling script is a real, reportable failure
  if [[ ! -f "$1" ]]; then
    echo "missing script: $1" >&2
    echo "(cobol-knowledge-extraction / z-app-documentation v2.0.0 may not have shipped its" >&2
    echo " scripts/ folder yet — this is a real prerequisite, not something this script can work" >&2
    echo " around)" >&2
    return 1
  fi
  return 0
}

# ---------- guardrails ----------
if (( NO_PUBLISH )) && [[ -n "$PUBLISH_TO" ]]; then
  echo "NOTE: --no-publish stops before phase 9; --publish-to will not be used." >&2
fi

# ---------- phase selection ----------
PRIOR_OK=""
if [[ -n "$RESUME" && -f "$RUN_STATE" ]]; then
  PRIOR_OK="$(python3 - "$RUN_STATE" <<'PY' 2>/dev/null || echo ""
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(0)
print(" ".join(k for k, v in (d.get("phases") or {}).items()
                if v.get("status") in ("ok", "partial", "skipped")))
PY
)"
fi

reached_from=0
[[ -n "$FROM_PHASE" ]] || reached_from=1

should_run() { # should_run <phase>
  local p="$1"
  if [[ -n "$ONLY_PHASE" ]]; then [[ "$p" == "$ONLY_PHASE" ]] && return 0 || return 1; fi
  [[ "$p" == "$FROM_PHASE" ]] && reached_from=1
  (( reached_from )) || return 1
  if (( OFFLINE )) && [[ "$p" == "extract" ]]; then return 1; fi
  if (( NO_PUBLISH )) && [[ "$p" == "publish" ]]; then return 1; fi
  if in_list "$p" "$PRIOR_OK" && [[ -z "$FROM_PHASE" ]]; then return 1; fi
  return 0
}

skip_reason() { # why a phase was not selected, for an honest plan and log
  local p="$1"
  if [[ -n "$ONLY_PHASE" && "$p" != "$ONLY_PHASE" ]]; then echo "not --only"; return; fi
  if (( OFFLINE )) && [[ "$p" == "extract" ]]; then echo "--offline"; return; fi
  if (( NO_PUBLISH )) && [[ "$p" == "publish" ]]; then echo "--no-publish"; return; fi
  if in_list "$p" "$PRIOR_OK"; then echo "already ok in pipeline-run-state.json"; return; fi
  echo "before --from $FROM_PHASE"
}

# ---------- plan ----------
echo ""
echo "BobZ modernization pipeline (no AWS)"
echo "  run id           : $RUN_ID"
echo "  workspace root   : $WORKSPACE_ROOT"
echo "  extraction root  : $EXTRACTION_ROOT  (persistent)"
echo "  docs root        : $DOCS_ROOT  (persistent)"
[[ -n "$SCOPE" ]] && echo "  scope            : $SCOPE"
(( OFFLINE )) && echo "  mode             : --offline (phase 2 skipped)"
echo ""
echo "  plan:"
i=0
for p in $PHASE_IDS; do
  i=$((i+1))
  if should_run "$p"; then
    if in_list "$p" "$AGENT_PHASES"; then
      printf '    %d/%d %-12s run   (agent-required — script prints a STOP marker)\n' "$i" "$PHASE_TOTAL" "$p"
    else
      printf '    %d/%d %-12s run\n' "$i" "$PHASE_TOTAL" "$p"
    fi
  else
    printf '    %d/%d %-12s skip  (%s)\n' "$i" "$PHASE_TOTAL" "$p" "$(skip_reason "$p")"
  fi
done
echo ""
reached_from=0; [[ -n "$FROM_PHASE" ]] || reached_from=1   # reset after the planning pass

if (( DRY_RUN )); then echo "--dry-run: nothing executed."; exit 0; fi

mkdir -p "$MANIFEST_DIR"

# ---------- logging ----------
if [[ ! -f "$RUN_LOG" ]]; then
  {
    echo "# Pipeline run log"
    echo ""
    echo "Run id \`$RUN_ID\`. extractionRoot and docsRoot are persistent across runs; only this"
    echo "log and \`pipeline-run-state.json\` are stamped per invocation."
    echo ""
    echo "| # | phase | status | elapsed | exit | detail |"
    echo "|---|---|---|---|---|---|"
  } > "$RUN_LOG"
fi

# Phase stdout is captured outside docsRoot: phase 8 zips docsRoot, and scratch output left inside
# it would become archive content that the disclosure scan then has to reason about for no reason.
SCRATCH_DIR="$(mktemp -d -t bobzrun 2>/dev/null || echo "${TMPDIR:-/tmp}/bobzrun.$$")"
mkdir -p "$SCRATCH_DIR"
cleanup_scratch() { [[ -n "${SCRATCH_DIR:-}" ]] && rm -rf "$SCRATCH_DIR"; }
trap cleanup_scratch EXIT INT TERM

now_ms() { python3 -c 'import time;print(int(time.time()*1000))'; }

record() { # record <idx> <phase> <status> <elapsed_ms> <exit> <detail>
  local idx="$1" phase="$2" status="$3" ms="$4" code="$5" detail="$6"
  local secs; secs="$(python3 -c "print(f'{$ms/1000:.1f}s')")"
  printf '| %s | %s | %s | %s | %s | %s |\n' "$idx" "$phase" "$status" "$secs" "$code" "$detail" >> "$RUN_LOG"
  python3 - "$RUN_STATE" "$phase" "$status" "$ms" "$code" "$detail" "$RUN_ID" "$EXTRACTION_ROOT" "$DOCS_ROOT" <<'PY'
import json, os, sys
path, phase, status, ms, code, detail, run_id, extraction_root, docs_root = sys.argv[1:10]
try:
    d = json.load(open(path, encoding="utf-8"))
except Exception:
    d = {}
d["runId"] = run_id
d["extractionRoot"] = extraction_root
d["docsRoot"] = docs_root
d.setdefault("phases", {})
d["phases"][phase] = {"status": status, "elapsedMs": int(ms),
                      "exit": int(code), "detail": detail}
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as fh:
    json.dump(d, fh, indent=2, sort_keys=True)
    fh.write("\n")
os.replace(tmp, path)
PY
}

FAILED=0
AGENT_HIT=""
PHASE_IDX=0
LAST_DETAIL=""

# run_phase <phase> <allowed_extra_exit_codes> <command...>
run_phase() {
  local phase="$1"; shift
  local allowed="$1"; shift
  PHASE_IDX=$((PHASE_IDX+1))
  local idx="$PHASE_IDX"

  if ! should_run "$phase"; then
    printf '[%d/%d] %-12s skip     (%s)\n' "$idx" "$PHASE_TOTAL" "$phase" "$(skip_reason "$phase")"
    record "$idx" "$phase" "skipped" 0 0 "$(skip_reason "$phase")"
    return 0
  fi

  local tty=0; [[ -t 1 ]] && tty=1
  (( tty )) && printf '[%d/%d] %-12s ...' "$idx" "$PHASE_TOTAL" "$phase"
  local t0 t1 code out_file
  t0="$(now_ms)"
  out_file="$SCRATCH_DIR/phase-$phase.out"
  "$@" > "$out_file" 2>&1
  code=$?
  t1="$(now_ms)"
  local ms=$((t1 - t0))
  local secs; secs="$(python3 -c "print(f'{$ms/1000:.1f}s')")"

  local status detail
  detail="$LAST_DETAIL"; LAST_DETAIL=""
  if [[ $code -eq 0 ]]; then
    status="ok"
  elif [[ $code -eq 3 ]]; then
    status="AGENT"; AGENT_HIT="$phase"
  elif in_list "$code" "$allowed"; then
    status="partial"
  else
    status="FAILED"; FAILED=1
  fi
  [[ -n "$detail" ]] || detail="$(tail -3 "$out_file" | tr '\n|' '  ' | tr -s ' ' | cut -c1-160)"
  [[ -n "$detail" ]] || detail="-"

  (( tty )) && printf '\r'
  printf '[%d/%d] %-12s %-8s %7s  exit=%s\n' "$idx" "$PHASE_TOTAL" "$phase" "$status" "$secs" "$code"
  if [[ "$status" == "FAILED" ]]; then
    echo "        ---- output ----"
    sed 's/^/        /' "$out_file" | tail -20
    echo "        ----------------"
  elif [[ "$status" == "AGENT" ]]; then
    sed 's/^/        /' "$out_file"
  elif [[ "$status" == "partial" ]]; then
    echo "        $detail"
  fi
  record "$idx" "$phase" "$status" "$ms" "$code" "$detail"
}

# The phases are dependency-ordered. A fatal failure or an agent-required stop both mean later
# phases cannot meaningfully run yet, so both abort the chain unless the caller passed --keep-going.
ABORTED=""
abort_check() { # abort_check <next-phase-label>
  if [[ ( $FAILED -eq 1 || -n "$AGENT_HIT" ) ]] && ! (( KEEP_GOING )); then
    ABORTED="$1"
    return 1
  fi
  return 0
}

# ---------- phase bodies ----------

ph_preflight() {
  local script="$COBOL_SCRIPTS/build_inventory.py"
  require_script "$script" || return 1
  local args=(--workspace-root "$WORKSPACE_ROOT" --extraction-root "$EXTRACTION_ROOT" \
              --out-dir "$EXTRACTION_ROOT/00-manifest")
  [[ -n "$SCOPE" ]] && args+=(--scope "$SCOPE")
  python3 "$script" "${args[@]}" || return $?

  # The MCP reachability probe is the agent's job, never this script's: probing means a real
  # get_paragraphs/get_control_flow round-trip, and no script in this suite calls the MCP server.
  if (( OFFLINE )); then
    echo "inventory built; --offline given, MCP probe not required"
    LAST_DETAIL="offline: inventory built, MCP probe skipped"
    return 0
  fi
  if [[ ! -f "$PROBE_FILE" ]]; then
    echo "inventory built; MCP capability probe not found at:"
    echo "  $PROBE_FILE"
    echo "Run cobol-knowledge-extraction's Step 2 preflight — the agent makes one real"
    echo "get_paragraphs (or get_control_flow) call and writes this file — then re-run phase 1."
    return 1
  fi
  local reachable
  reachable="$(python3 - "$PROBE_FILE" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    print("false"); sys.exit(0)
print("true" if d.get("mcpReachable") else "false")
PY
)"
  if [[ "$reachable" != "true" ]]; then
    echo "probe file exists but records mcpReachable=false — the BobZ MCP server is unreachable."
    echo "Use --offline to document an existing bob-z-knowledge-extract/, or resolve connectivity"
    echo "and re-run cobol-knowledge-extraction's preflight."
    return 1
  fi
  echo "inventory built; MCP probe recorded reachable"
  LAST_DETAIL="inventory built; MCP probe reachable"
}

ph_extract() {
  echo "STOP - this phase requires the agent, not this script."
  echo ""
  echo "Run the cobol-knowledge-extraction skill (directly, or via /extract-batch) against the"
  echo "resolved scope, batch after batch, calling generate_data_dictionary / generate_documentation"
  echo "/ explain_code / z_code_scan / get_variables / get_paragraphs / get_control_flow directly —"
  echo "there is no job to launch and poll, so this script cannot do this work for you."
  echo ""
  echo "  workspace root : $WORKSPACE_ROOT"
  echo "  scope          : ${SCOPE:-<open workspace>}"
  echo "  extraction root: $EXTRACTION_ROOT"
  echo ""
  echo "Stop when every in-scope program is dd_generated=Y AND dd_approved=Y AND doc_generated=Y,"
  echo "or when the user accepts a named partial subset (Gate B). Then resume:"
  echo "  $0 --resume $RUN_ID --from extract-verify"
  return 3
}

ph_extract_verify() {
  local script="$COBOL_SCRIPTS/verify_extraction.py"
  require_script "$script" || return 1
  local ledger="$EXTRACTION_ROOT/00-manifest/extraction-status.csv"
  if [[ ! -f "$ledger" ]]; then
    echo "no $ledger yet — nothing extracted to verify. Run phase 2 (extract) first, or"
    echo "--offline against a workspace that already has one."
    return 1
  fi
  # Gate B: every claimed-complete (Y) flag must be backed by a real artifact on disk. This is a
  # real defect check, not a "coverage is thin" softness — verify_extraction.py's own contract is
  # exit 0 clean / exit 1 at least one defect, so a non-zero here fails the phase rather than
  # degrading to "partial".
  python3 "$script" --extraction-root "$EXTRACTION_ROOT"
}

ph_reuse_snapshot() {
  if [[ ! -d "$EXTRACTION_ROOT" ]]; then
    echo "no $EXTRACTION_ROOT — nothing to snapshot; z-app-documentation will start every"
    echo "program cold in phase 6 (evidence)."
    LAST_DETAIL="no extraction tree to snapshot"
    return 0
  fi
  python3 - "$EXTRACTION_ROOT" "$MANIFEST_DIR" <<'PY'
import hashlib, json, os, sys

extraction_root, manifest_dir = sys.argv[1], sys.argv[2]
# Same by-program artifact families extract_evidence.py harvests when reusing an extraction tree
# (bobz-v3-foundations.md §4e step 3) — fingerprinted here, once, so phase 6 (evidence) and
# phase 7 (generate) never have to re-hash the same files on every later run.
SUBDIRS = ["03-data-structures", "02-business-rules", "01-application-architecture",
           "10-error-handling", "05-dependencies", "08-jcl-batch", "11-code-quality"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


artifacts = []
for sub in SUBDIRS:
    d = os.path.join(extraction_root, sub)
    if not os.path.isdir(d):
        continue
    for dirpath, _dirs, files in os.walk(d):
        for fn in files:
            p = os.path.join(dirpath, fn)
            artifacts.append({"path": os.path.relpath(p, extraction_root).replace(os.sep, "/"),
                               "sha256": sha256(p)})

os.makedirs(manifest_dir, exist_ok=True)
out = os.path.join(manifest_dir, "reuse-snapshot.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump({"extractionRoot": extraction_root, "artifactCount": len(artifacts),
               "artifacts": sorted(artifacts, key=lambda a: a["path"])}, fh, indent=2)
print(f"{out}: {len(artifacts)} artifact(s) fingerprinted for reuse")
PY
}

ph_coverage() {
  local script="$ZAPP_SCRIPTS/build_coverage.py"
  require_script "$script" || return 1
  python3 "$script" --workspace-root "$WORKSPACE_ROOT" --extraction-root "$EXTRACTION_ROOT" \
    --docs-root "$DOCS_ROOT" --probe-file "$PROBE_FILE" --out-dir "$MANIFEST_DIR"
}

ph_evidence() {
  local script="$ZAPP_SCRIPTS/extract_evidence.py"
  require_script "$script" || return 1
  local args=(--workspace-root "$WORKSPACE_ROOT" --extraction-root "$EXTRACTION_ROOT" \
              --docs-root "$DOCS_ROOT")
  (( FORCE )) && args+=(--force)
  python3 "$script" "${args[@]}"
}

ph_generate() {
  local script="$ZAPP_SCRIPTS/generate_docs.py"
  require_script "$script" || return 1
  local args=(--docs-root "$DOCS_ROOT")
  [[ -n "$APP_NAME" ]] && args+=(--app-name "$APP_NAME")
  (( FORCE )) && args+=(--force)
  python3 "$script" "${args[@]}"
}

ph_package() {
  [[ -d "$DOCS_ROOT" ]] || { echo "no $DOCS_ROOT to package — run phases 5-7 first"; return 1; }
  rm -f "$ZIP_PATH"
  # Zipped from the parent of docsRoot so the archive expands to bob-z-app-docs/ (or its basename)
  # rather than a bare tree, and the archive is a sibling of the folder, never inside it.
  ( cd "$(dirname "$DOCS_ROOT")" \
    && zip -q -r "$(basename "$ZIP_PATH")" "$(basename "$DOCS_ROOT")" \
         -x '*/.DS_Store' -x '*/pipeline-run-log.md.tmp' ) || return $?

  # Disclosure gate. Generic secret/credential patterns, not AWS identity — this skill never
  # touches AWS, so there is no ARN or access-key-id pattern to catch here.
  local leaks
  leaks="$(python3 - "$ZIP_PATH" <<'PY'
import re, sys, zipfile

PATTERNS = [
    (r"(?i)password\s*[:=]\s*\S+", "hard-coded password"),
    (r"(?i)(api[_-]?key|secret)\s*[:=]\s*\S+", "API key / secret"),
    (r"-----BEGIN (RSA|EC|OPENSSH )?PRIVATE KEY-----", "embedded private key"),
    (r"(?i)(user\s*id|uid)\s*=.*password\s*=", "DB2/ODBC connection string with credentials"),
    (r"(?i)bearer\s+[A-Za-z0-9\-_.]{20,}", "bearer token"),
    (r"(?i)jdbc:[a-z0-9]+://[^;]*password=", "JDBC connection string with embedded password"),
]

hits = []
with zipfile.ZipFile(sys.argv[1]) as z:
    for info in z.infolist():
        if info.is_dir() or info.file_size > 8 * 1024 * 1024:
            continue
        try:
            text = z.read(info).decode("utf-8", "ignore")
        except Exception:
            continue
        for pat, label in PATTERNS:
            if re.search(pat, text):
                hits.append(f"{info.filename}: {label}")
for h in sorted(set(hits)):
    print(h)
PY
)"
  if [[ -n "$leaks" ]]; then
    echo "REFUSING TO PACKAGE — the archive contains secret or credential material:"
    printf '%s\n' "$leaks" | sed 's/^/  /'
    echo "This archive is meant to be copied to a local or network destination. Remove the"
    echo "offending content from the source artifact (never patch the zip) and re-run phase 8."
    rm -f "$ZIP_PATH"
    return 1
  fi

  local size files
  size="$(python3 -c "import os;print(f'{os.path.getsize('$ZIP_PATH')/1048576:.2f} MB')")"
  files="$(unzip -l "$ZIP_PATH" 2>/dev/null | tail -1 | awk '{print $2}')"
  echo "$ZIP_PATH  $size  $files files"
  echo "disclosure gate: no secret or credential material in archive"
  LAST_DETAIL="$size, $files files, disclosure gate passed"
}

ph_publish() {
  echo "STOP - this phase requires the agent, not this script."
  echo ""
  if [[ ! -f "$ZIP_PATH" ]]; then
    echo "$ZIP_PATH does not exist yet — run phase 8 (package) first."
    return 3
  fi
  echo "Gate D before doing anything else: state plainly what is in the archive — business rules,"
  echo "the full data dictionary (including status: draft entries no SME has approved yet),"
  echo "program and JCL names, and any Z Code Scan findings — and get the user to confirm a"
  echo "destination. There is no upload, no presigned URL, and no expiry here; a plain copy is"
  echo "permanent for as long as the destination keeps the file."
  echo ""
  if [[ -n "$PUBLISH_TO" ]]; then
    echo "Named destination: $PUBLISH_TO"
    echo "After Gate D passes, copy it yourself:"
    echo "  cp \"$ZIP_PATH\" \"$PUBLISH_TO\""
  else
    echo "No --publish-to destination was given. Ask the user for one, or stop here — publishing"
    echo "is optional."
  fi
  return 3
}

# ---------- execute ----------
START_MS="$(now_ms)"

run_phase preflight        ""  ph_preflight
abort_check extract        && run_phase extract        ""  ph_extract
abort_check extract-verify && run_phase extract-verify  ""  ph_extract_verify
abort_check reuse-snapshot && run_phase reuse-snapshot  ""  ph_reuse_snapshot
abort_check coverage       && run_phase coverage        "1" ph_coverage
abort_check evidence       && run_phase evidence        ""  ph_evidence
abort_check generate       && run_phase generate        "1" ph_generate
abort_check package        && run_phase package         ""  ph_package
abort_check publish        && run_phase publish         ""  ph_publish

if [[ -n "$ABORTED" ]]; then
  echo ""
  echo "  stopped before '$ABORTED': an earlier phase failed or needs the agent, and later phases"
  echo "  depend on it. Use --keep-going to run them anyway."
fi

END_MS="$(now_ms)"
TOTAL="$(python3 -c "print(f'{($END_MS-$START_MS)/1000:.1f}s')")"

echo ""
echo "  total $TOTAL"
echo "  extraction root : $EXTRACTION_ROOT"
echo "  docs root       : $DOCS_ROOT"
echo "  run log         : $RUN_LOG"
[[ -f "$ZIP_PATH" ]] && echo "  archive         : $ZIP_PATH"

# Belt and braces: an interrupted run can leave scratch output; never let it survive into a
# packaged archive on the next run.
cleanup_scratch

{
  echo ""
  echo "Total $TOTAL. Completed $(date -u +%Y-%m-%dT%H:%M:%SZ)."
} >> "$RUN_LOG"

if (( FAILED )); then
  echo ""
  echo "  RESULT: at least one phase failed. Fix it and resume without redoing the rest:"
  echo "    $0 --resume $RUN_ID --from <phase>"
  exit 1
fi
if [[ -n "$AGENT_HIT" ]]; then
  echo ""
  echo "  RESULT: stopped at '$AGENT_HIT' — this phase needs the agent, not a driver failure."
  exit 3
fi
echo "  RESULT: all selected phases met their contract."
exit 0
