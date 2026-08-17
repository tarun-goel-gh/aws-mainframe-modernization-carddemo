#!/usr/bin/env bash
# End-to-end driver: AWS Transform spec artifacts -> 31 application documents -> shareable zip.
#
# Nine phases, one timestamped run folder, one progress line each. Written for macOS bash 3.2,
# so no associative arrays and no ${var,,}.
#
#   1 preflight          credentials, artifact bucket, upload bucket
#   2 fetch-specs        download spec_gen zips from the job bucket
#   3 verify-split       scope-check the bundle and split it per business function
#   4 snapshot-analysis  mirror the analysis artifacts that the documents are grounded in
#   5 coverage           prerequisite gate + business-function coverage matrix
#   6 evidence           load every shared artifact once into the evidence pack
#   7 generate           compose, self-check and file the documents
#   8 package            zip the run folder
#   9 publish            upload the zip and emit a link
#
# Usage:
#   run_pipeline.sh --profile P --bucket B --job-id J [--upload-bucket U] [options]
#   run_pipeline.sh --offline                          # re-document an existing .atx/mfre
#   run_pipeline.sh --resume 20260813-142530 --from generate
#
# Options:
#   --profile P          AWS profile. Required unless --offline.
#   --region R           defaults to the profile's configured region
#   --bucket B           AWS Transform job bucket, read-only
#   --job-id J           AWS Transform job id
#   --mfre DIR           upstream run directory (default .atx/mfre)
#   --app-name NAME      application name for document headers (default: derived from upstream)
#   --docs-root DIR      override the run folder entirely
#   --run-id TS          use this stamp instead of the current time
#   --resume TS|DIR      reuse a previous run folder and skip phases already recorded ok
#   --from PHASE         start at this phase (skip earlier ones)
#   --only PHASE         run exactly one phase
#   --offline            skip every phase that needs AWS (1,2,3,4,9)
#   --upload-bucket U    bucket the zip is written to. Must differ from --bucket for --public.
#   --upload-prefix P    key prefix (default atx-app-docs)
#   --public             make the uploaded zip anonymously readable. Opt-in, prefix-scoped.
#   --expires-in N       presigned URL lifetime in seconds (default 604800, the SigV4 maximum)
#   --no-upload          run phases 1-8 and stop before publishing
#   --dry-run            print the plan and exit without touching anything
#   --force              regenerate documents already marked complete
#   --keep-going         continue after a fatal phase failure instead of stopping
#
# Exit codes: 0 every selected phase met its contract | 1 a phase failed | 2 bad usage
#
# Phase 3 exits 1 whenever AWS Transform delivered fewer functions than were discovered. That is
# a real and expected state for this codebase, not a driver failure, so it is recorded as
# `partial` and the pipeline continues. Documenting a partial estate honestly is the point of the
# coverage matrix.

set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MFRE_SCRIPTS="$(cd "$SELF_DIR/../../mainframe-reverse-engineering/scripts" 2>/dev/null && pwd || echo "")"

PROFILE=""; REGION=""; BUCKET=""; JOB_ID=""
MFRE=".atx/mfre"; DOCS_ROOT=""; RUN_ID=""; RESUME=""; APP_NAME=""
FROM_PHASE=""; ONLY_PHASE=""; OFFLINE=0
UPLOAD_BUCKET=""; UPLOAD_PREFIX="atx-app-docs"; PUBLIC=0; EXPIRES_IN=604800
NO_UPLOAD=0; DRY_RUN=0; FORCE=0; KEEP_GOING=0

PHASE_IDS="preflight fetch-specs verify-split snapshot-analysis coverage evidence generate package publish"
AWS_PHASES="preflight fetch-specs verify-split snapshot-analysis publish"
PHASE_TOTAL=9

usage() { sed -n '2,48p' "$0" >&2; exit 2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)       PROFILE="${2:-}"; shift 2 ;;
    --region)        REGION="${2:-}"; shift 2 ;;
    --bucket)        BUCKET="${2:-}"; shift 2 ;;
    --job-id)        JOB_ID="${2:-}"; shift 2 ;;
    --mfre)          MFRE="${2:-}"; shift 2 ;;
    --app-name)      APP_NAME="${2:-}"; shift 2 ;;
    --docs-root)     DOCS_ROOT="${2:-}"; shift 2 ;;
    --run-id)        RUN_ID="${2:-}"; shift 2 ;;
    --resume)        RESUME="${2:-}"; shift 2 ;;
    --from)          FROM_PHASE="${2:-}"; shift 2 ;;
    --only)          ONLY_PHASE="${2:-}"; shift 2 ;;
    --offline)       OFFLINE=1; shift ;;
    --upload-bucket) UPLOAD_BUCKET="${2:-}"; shift 2 ;;
    --upload-prefix) UPLOAD_PREFIX="${2:-}"; shift 2 ;;
    --public)        PUBLIC=1; shift ;;
    --expires-in)    EXPIRES_IN="${2:-}"; shift 2 ;;
    --no-upload)     NO_UPLOAD=1; shift ;;
    --dry-run)       DRY_RUN=1; shift ;;
    --force)         FORCE=1; shift ;;
    --keep-going)    KEEP_GOING=1; shift ;;
    -h|--help)       usage ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
done

in_list() { # in_list <needle> <space separated haystack>
  case " $2 " in *" $1 "*) return 0 ;; *) return 1 ;; esac
}

for p in $FROM_PHASE $ONLY_PHASE; do
  in_list "$p" "$PHASE_IDS" || { echo "ERROR: unknown phase '$p'. Known: $PHASE_IDS" >&2; exit 2; }
done

# ---------- resolve the run folder ----------
# The stamp is computed exactly once and exported, so every step of one run writes to one folder
# even though each script can also compute its own default.
if [[ -n "$RESUME" ]]; then
  if [[ -d "$RESUME" ]]; then DOCS_ROOT="$RESUME"
  else DOCS_ROOT=".atx/app-docs-$RESUME"; fi
  [[ -d "$DOCS_ROOT" ]] || { echo "ERROR: --resume target '$DOCS_ROOT' does not exist" >&2; exit 2; }
  RUN_ID="$(basename "$DOCS_ROOT" | sed 's/^app-docs-//')"
fi
[[ -n "$RUN_ID" ]] || RUN_ID="$(date +%Y%m%d-%H%M%S)"
[[ -n "$DOCS_ROOT" ]] || DOCS_ROOT=".atx/app-docs-$RUN_ID"

MANIFEST_DIR="$DOCS_ROOT/00-manifest"
RUN_LOG="$MANIFEST_DIR/run-log.md"
RUN_STATE="$MANIFEST_DIR/run-state.json"
PUBLISH_NOTE="$MANIFEST_DIR/publish.md"
ZIP_PATH=".atx/app-docs-$RUN_ID.zip"

export ATX_DOCS_ROOT="$DOCS_ROOT"

# ---------- credential resolution for THIS process ----------
# preflight.sh and snapshot_analysis.sh each fix up their own environment, but they do it in their
# own subprocesses. The driver makes AWS calls directly in phases 2 and 9, and without this block
# they resolve against whatever the caller's shell had — typically the default profile, which is
# usually expired. That produced a preflight that passed followed by an ExpiredToken one second
# later, which reads like a race and is really just two different credential sources.
if [[ -n "$PROFILE" ]]; then
  unset AWS_CREDENTIAL_EXPIRATION AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
  export AWS_PROFILE="$PROFILE"
  if [[ -z "$REGION" ]]; then
    REGION="$(aws configure get region --profile "$PROFILE" 2>/dev/null || true)"
  fi
  [[ -n "$REGION" ]] && export AWS_REGION="$REGION" AWS_DEFAULT_REGION="$REGION"
fi

# ---------- guardrails ----------
if (( PUBLIC )); then
  [[ -n "$UPLOAD_BUCKET" ]] || { echo "ERROR: --public requires --upload-bucket" >&2; exit 2; }
  # Refused rather than warned. The artifact bucket holds the raw source analysis, the spec
  # bundles and the data dictionary; a prefix policy on it is one careless edit away from
  # exposing all of that. A deliverable gets its own bucket.
  if [[ -n "$BUCKET" && "$UPLOAD_BUCKET" == "$BUCKET" ]]; then
    echo "ERROR: refusing --public when the upload bucket is also the artifact bucket ($BUCKET)." >&2
    echo "       That bucket holds transform-output/ (source analysis, spec bundles, data" >&2
    echo "       dictionary). Use a dedicated bucket, or drop --public and share a presigned URL." >&2
    exit 2
  fi
fi
if (( OFFLINE )) && [[ -n "$UPLOAD_BUCKET" ]] && ! (( NO_UPLOAD )); then
  echo "NOTE: --offline skips the publish phase; --upload-bucket will not be used." >&2
fi
if ! (( OFFLINE )); then
  if [[ -z "$PROFILE" ]] && [[ -z "$ONLY_PHASE" || $(in_list "$ONLY_PHASE" "$AWS_PHASES"; echo $?) -eq 0 ]]; then
    echo "ERROR: --profile is required unless --offline" >&2; exit 2
  fi
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
  if (( OFFLINE )) && in_list "$p" "$AWS_PHASES"; then return 1; fi
  if (( NO_UPLOAD )) && [[ "$p" == "publish" ]]; then return 1; fi
  if [[ "$p" == "publish" && -z "$UPLOAD_BUCKET" ]]; then return 1; fi
  if [[ "$p" == "fetch-specs" || "$p" == "verify-split" || "$p" == "snapshot-analysis" ]]; then
    if [[ -z "$BUCKET" || -z "$JOB_ID" ]]; then return 1; fi
  fi
  if in_list "$p" "$PRIOR_OK" && [[ -z "$FROM_PHASE" ]]; then return 1; fi
  return 0
}

skip_reason() { # why a phase was not selected, for an honest plan and log
  local p="$1"
  if [[ -n "$ONLY_PHASE" && "$p" != "$ONLY_PHASE" ]]; then echo "not --only"; return; fi
  if (( OFFLINE )) && in_list "$p" "$AWS_PHASES"; then echo "--offline"; return; fi
  if (( NO_UPLOAD )) && [[ "$p" == "publish" ]]; then echo "--no-upload"; return; fi
  if [[ "$p" == "publish" && -z "$UPLOAD_BUCKET" ]]; then echo "no --upload-bucket"; return; fi
  if in_list "$p" "$PRIOR_OK"; then echo "already done in this run folder"; return; fi
  if [[ "$p" == "fetch-specs" || "$p" == "verify-split" || "$p" == "snapshot-analysis" ]] \
     && [[ -z "$BUCKET" || -z "$JOB_ID" ]]; then echo "no --bucket/--job-id"; return; fi
  echo "before --from $FROM_PHASE"
}

# ---------- plan ----------
echo ""
echo "AWS Transform application documentation pipeline"
echo "  run id       : $RUN_ID"
echo "  run folder   : $DOCS_ROOT"
echo "  upstream     : $MFRE"
[[ -n "$PROFILE" ]] && echo "  aws          : profile=$PROFILE region=${REGION:-<from profile>} bucket=${BUCKET:-<none>}"
[[ -n "$UPLOAD_BUCKET" ]] && echo "  publish      : s3://$UPLOAD_BUCKET/${UPLOAD_PREFIX%/}/app-docs-$RUN_ID.zip$( ((PUBLIC)) && echo ' (PUBLIC)' || echo ' (presigned)')"
echo ""
echo "  plan:"
i=0
for p in $PHASE_IDS; do
  i=$((i+1))
  if should_run "$p"; then printf '    %d/%d %-18s run\n' "$i" "$PHASE_TOTAL" "$p"
  else printf '    %d/%d %-18s skip (%s)\n' "$i" "$PHASE_TOTAL" "$p" "$(skip_reason "$p")"; fi
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
    echo "Run id \`$RUN_ID\`. Times are wall clock; the documents themselves are deterministic,"
    echo "so this log and \`run-state.json\` are the only files that differ between two identical runs."
    echo ""
    echo "| # | phase | status | elapsed | exit | detail |"
    echo "|---|---|---|---|---|---|"
  } > "$RUN_LOG"
fi

# Per-phase stdout is captured to compose the log. It is deliberately captured OUTSIDE the run
# folder: the `package` phase zips that folder, and anything scratch left inside it ends up in an
# archive that may be published anonymously. preflight's output alone carries the caller's account
# id and assumed-role ARN, so this is a disclosure boundary, not a tidiness preference.
SCRATCH_DIR="$(mktemp -d -t atxrun 2>/dev/null || echo "${TMPDIR:-/tmp}/atxrun.$$")"
mkdir -p "$SCRATCH_DIR"
cleanup_scratch() { [[ -n "${SCRATCH_DIR:-}" ]] && rm -rf "$SCRATCH_DIR"; }
trap cleanup_scratch EXIT INT TERM

now_ms() { python3 -c 'import time;print(int(time.time()*1000))'; }

record() { # record <idx> <phase> <status> <elapsed_ms> <exit> <detail>
  local idx="$1" phase="$2" status="$3" ms="$4" code="$5" detail="$6"
  local secs; secs="$(python3 -c "print(f'{$ms/1000:.1f}s')")"
  printf '| %s | %s | %s | %s | %s | %s |\n' "$idx" "$phase" "$status" "$secs" "$code" "$detail" >> "$RUN_LOG"
  python3 - "$RUN_STATE" "$phase" "$status" "$ms" "$code" "$detail" "$RUN_ID" "$DOCS_ROOT" <<'PY'
import json, os, sys
path, phase, status, ms, code, detail, run_id, root = sys.argv[1:9]
try:
    d = json.load(open(path, encoding="utf-8"))
except Exception:
    d = {}
d.setdefault("runId", run_id)
d.setdefault("docsRoot", root)
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
PHASE_IDX=0
LAST_DETAIL=""

# run_phase <phase> <allowed_extra_exit_codes> <command...>
run_phase() {
  local phase="$1"; shift
  local allowed="$1"; shift
  PHASE_IDX=$((PHASE_IDX+1))
  local idx="$PHASE_IDX"

  if ! should_run "$phase"; then
    printf '[%d/%d] %-18s skip     (%s)\n' "$idx" "$PHASE_TOTAL" "$phase" "$(skip_reason "$phase")"
    record "$idx" "$phase" "skipped" 0 0 "$(skip_reason "$phase")"
    return 0
  fi

  # The in-progress line is redrawn with \r, which only works on a terminal. Piped or captured
  # into a chat transcript it would leave "...[5/9] coverage ok" fragments, so emit it only
  # when stdout is a TTY.
  local tty=0; [[ -t 1 ]] && tty=1
  (( tty )) && printf '[%d/%d] %-18s ...' "$idx" "$PHASE_TOTAL" "$phase"
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
  elif in_list "$code" "$allowed"; then
    status="partial"
  else
    status="FAILED"; FAILED=1
  fi
  # Squeeze runs of whitespace: these are multi-line tool summaries and a markdown table cell
  # cannot carry newlines. Pipes are escaped for the same reason.
  [[ -n "$detail" ]] || detail="$(tail -3 "$out_file" | tr '\n|' '  ' | tr -s ' ' | cut -c1-120)"
  [[ -n "$detail" ]] || detail="-"

  (( tty )) && printf '\r'
  printf '[%d/%d] %-18s %-8s %7s  exit=%s\n' "$idx" "$PHASE_TOTAL" "$phase" "$status" "$secs" "$code"
  if [[ "$status" == "FAILED" ]]; then
    echo "        ---- output ----"
    sed 's/^/        /' "$out_file" | tail -20
    echo "        ----------------"
  elif [[ "$status" == "partial" ]]; then
    echo "        $detail"
  fi
  record "$idx" "$phase" "$status" "$ms" "$code" "$detail"
  [[ "$status" != "FAILED" ]]
}

# The phases are dependency-ordered, so pressing on after a fatal failure spends real time on work
# that cannot succeed — a credential failure in phase 2 otherwise leads straight into a 100 MB
# download in phase 4. `partial` is not a failure and never stops the run.
ABORTED=""
abort_check() { # abort_check <next-phase-label>
  if (( FAILED )) && ! (( KEEP_GOING )); then
    ABORTED="$1"
    return 1
  fi
  return 0
}

# ---------- phase bodies ----------

ph_preflight() {
  local args=(--profile "$PROFILE")
  [[ -n "$REGION" ]] && args+=(--region "$REGION")
  [[ -n "$BUCKET" ]] && args+=(--bucket "$BUCKET")
  [[ -n "$UPLOAD_BUCKET" ]] && args+=(--upload-bucket "$UPLOAD_BUCKET" --upload-prefix "$UPLOAD_PREFIX")
  (( PUBLIC )) && args+=(--intend-public)
  bash "$MFRE_SCRIPTS/preflight.sh" "${args[@]}"
}

ph_fetch_specs() {
  mkdir -p "$MFRE/specs-raw"
  aws s3 cp "s3://$BUCKET/transform-output/$JOB_ID/spec_gen/" "$MFRE/specs-raw/" \
    --recursive --exclude '*' --include '*.zip' --only-show-errors || return $?
  local n; n="$(ls -1 "$MFRE/specs-raw"/*.zip 2>/dev/null | wc -l | tr -d ' ')"
  [[ "$n" -gt 0 ]] || { echo "no spec zips found under s3://$BUCKET/transform-output/$JOB_ID/spec_gen/"; return 1; }
  echo "$n spec zip(s) downloaded"
}

ph_verify_split() {
  # Every zip, not the largest one. AWS Transform writes one bundle per generation attempt and
  # each carries only the functions that attempt produced, so the delivered estate is the UNION
  # across bundles. Picking a single zip by size or recency understates delivery — the largest
  # zip in this job holds one function while the estate has six.
  local raw="$MFRE/specs-raw" stage="$MFRE/specs-staging"
  rm -rf "$stage"; mkdir -p "$stage"

  local n=0 z base
  # Sorted by name, which is timestamp order, so a later attempt supersedes an earlier one for
  # any function present in both.
  for z in $(ls -1 "$raw"/*.zip 2>/dev/null | sort); do
    [[ -f "$z" ]] || continue
    base="$(basename "$z" .zip)"
    mkdir -p "$stage/$base"
    unzip -q -o "$z" -d "$stage/$base" || { echo "corrupt zip: $base"; return 1; }
    n=$((n+1))
  done
  [[ $n -gt 0 ]] || { echo "no spec zips in $raw"; return 1; }
  echo "staged $n bundle(s) from $raw"

  # Split each bundle into its OWN output, then choose between them. A per-bundle scope check
  # would report "1 of 9" for every bundle, which is noise: one attempt is expected to be
  # partial. The authoritative scope check is the union verify below.
  local d
  for d in "$stage"/*; do
    [[ -d "$d" ]] || continue
    local sargs=(--dir "$d" --out-dir "$d/__split" --source-root .)
    [[ -f "$MFRE/state.json" ]] && sargs+=(--state "$MFRE/state.json")
    python3 "$MFRE_SCRIPTS/split_bundle.py" "${sargs[@]}" >/dev/null 2>&1
  done

  # Richest attempt wins, NOT the newest. Successive AWS Transform generations of the same
  # function can lose depth dramatically — in this job one function came back with 294
  # requirements on the first attempt and 14 on a later one. Ordering by timestamp would let the
  # 14 silently replace the 294. The existing specs/ entry competes too, which makes a re-run
  # monotonic: the estate can improve or hold, never degrade.
  python3 - "$stage" "$MFRE/specs" "$MANIFEST_DIR/bundle-selection.md" <<'PY'
import os, re, glob, shutil, sys

stage, dest, report = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(dest, exist_ok=True)
REQ = re.compile(r"\bREQ-")


def score(bundle_dir):
    """(requirement count, bytes) for a per-function bundle directory."""
    reqs = glob.glob(os.path.join(bundle_dir, "spec", "*", "requirements.md"))
    if not reqs:
        return (0, 0)
    total = size = 0
    for p in reqs:
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        total += len(REQ.findall(text))
        size += os.path.getsize(p)
    return (total, size)


candidates = {}          # slug -> list of (score, label, path)


def offer(slug, label, path):
    candidates.setdefault(slug, []).append((score(path), label, path))


for entry in sorted(os.listdir(dest)):
    p = os.path.join(dest, entry)
    if os.path.isdir(p):
        offer(entry, "already in specs/", p)

for bundle in sorted(os.listdir(stage)):
    split_root = os.path.join(stage, bundle, "__split")
    if not os.path.isdir(split_root):
        continue
    for entry in sorted(os.listdir(split_root)):
        p = os.path.join(split_root, entry)
        if os.path.isdir(p):
            offer(entry, bundle, p)

rows = []
for slug in sorted(candidates):
    ranked = sorted(candidates[slug], key=lambda c: c[0], reverse=True)
    (reqs, size), label, path = ranked[0]
    contested = [r for r in ranked[1:] if r[0] != ranked[0][0]]
    if label != "already in specs/":
        target = os.path.join(dest, slug)
        if os.path.isdir(target):
            shutil.rmtree(target)
        shutil.copytree(path, target)
        zip_src = path.rstrip("/") + ".zip"
        if os.path.isfile(zip_src):
            shutil.copy2(zip_src, target + ".zip")
    rejected = ""
    if contested:
        rejected = "; ".join(f"{l} ({r} reqs, {s} B)" for (r, s), l, _ in contested)
    rows.append((slug, label, reqs, size, rejected))
    note = f"{slug}: kept {label} ({reqs} reqs, {size} B)"
    if rejected:
        note += f" over {rejected}"
    print("  " + note)

# Which extraction attempt each function's requirements came from. Without this the estate is a
# tree of files with no record of what it was chosen over, and the depth-loss problem becomes
# invisible again the next time someone looks.
os.makedirs(os.path.dirname(report), exist_ok=True)
with open(report, "w", encoding="utf-8") as fh:
    fh.write("# Bundle selection\n\n")
    fh.write("One AWS Transform generation attempt per candidate. The attempt with the most\n")
    fh.write("requirements wins, not the most recent one: later generations of the same function\n")
    fh.write("can lose substantial depth, so recency is not a proxy for quality.\n\n")
    fh.write("| Business function | Kept from | Requirements | Bytes | Rejected |\n")
    fh.write("|---|---|---|---|---|\n")
    for slug, label, reqs, size, rejected in rows:
        fh.write(f"| {slug} | {label} | {reqs} | {size} | {rejected or '—'} |\n")
    contested_n = sum(1 for r in rows if r[4])
    fh.write(f"\n{len(rows)} function bundle(s); {contested_n} had competing attempts.\n")
PY

  # One verify over the whole staging tree. find_function_dirs() walks for every spec/<Slug>/,
  # so this sees the union and --state supplies the discovered scope to measure it against.
  local vargs=(--dir "$stage" --source-root .)
  [[ -f "$MFRE/state.json" ]] && vargs+=(--state "$MFRE/state.json")
  python3 "$MFRE_SCRIPTS/verify_spec.py" "${vargs[@]}"
  local vcode=$?

  delivered="$(ls -1 "$MFRE/specs" 2>/dev/null | grep -v '\.zip$' | wc -l | tr -d ' ')"
  echo "specs/ now holds $delivered function bundle(s)"
  LAST_DETAIL="$n bundle(s) staged, $delivered function bundle(s) in specs/"
  return $vcode
}

ph_snapshot_analysis() {
  local args=(--profile "$PROFILE" --bucket "$BUCKET" --job-id "$JOB_ID" --dest "$MFRE/analysis")
  [[ -n "$REGION" ]] && args+=(--region "$REGION")
  bash "$MFRE_SCRIPTS/snapshot_analysis.sh" "${args[@]}"
}

ph_coverage() { python3 "$SELF_DIR/build_coverage.py" --mfre "$MFRE" --out-dir "$MANIFEST_DIR"; }
ph_evidence() { python3 "$SELF_DIR/extract_evidence.py" --mfre "$MFRE" --docs-root "$DOCS_ROOT"; }

ph_generate() {
  local args=(--docs-root "$DOCS_ROOT")
  (( FORCE )) && args+=(--force)
  # Left unset when not supplied, so generate_docs.py derives the name from upstream provenance
  # rather than having an empty string forced on it.
  [[ -n "$APP_NAME" ]] && args+=(--app-name "$APP_NAME")
  python3 "$SELF_DIR/generate_docs.py" "${args[@]}"
}

ph_package() {
  rm -f "$ZIP_PATH"
  # A run folder created by an older version of this script, reached via --resume, can still hold
  # scratch files. Clear them and exclude the pattern from the archive as well: the cost of a
  # redundant guard is nil next to publishing an account id and role ARN anonymously.
  rm -f "$MANIFEST_DIR"/.phase-*.out
  # An archive cannot contain a truthful record of its own publication, and a record from a
  # PREVIOUS publish is worse than none: re-packaging would bake a stale, possibly withdrawn URL
  # into the new archive. The publish phase rewrites this file immediately afterwards.
  rm -f "$PUBLISH_NOTE"
  # Zipped from .atx so the archive expands to app-docs-<id>/ rather than a bare tree, and the
  # archive is a sibling of the folder, never inside it.
  ( cd "$(dirname "$DOCS_ROOT")" \
    && zip -q -r "$(basename "$ZIP_PATH")" "$(basename "$DOCS_ROOT")" \
         -x '*/.phase-*.out' -x '*/.DS_Store' ) || return $?
  # Disclosure gate. The archive is the thing that leaves the machine, so it is the right place to
  # assert what may not leave. Credentials and role identity are never legitimate archive content;
  # the account id is, because the documents reference it by design and the user is told so.
  local leaks
  leaks="$(python3 - "$ZIP_PATH" <<'PY'
import re, sys, zipfile

# Secrets and identity that must never ship. The account id is deliberately absent from this list:
# it appears in the documents by design and is disclosed to the caller before publishing.
PATTERNS = [
    (r"arn:aws:(?:sts|iam)::\d{12}:(?:assumed-role|user)/", "IAM/STS principal identity"),
    (r"\bASIA[0-9A-Z]{16}\b", "temporary access key id"),
    (r"\bAKIA[0-9A-Z]{16}\b", "long-term access key id"),
    (r"X-Amz-Security-Token=", "presigned URL session token"),
    (r"aws_secret_access_key", "secret key assignment"),
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
    echo "REFUSING TO PACKAGE — the archive contains credential or identity material:"
    printf '%s\n' "$leaks" | sed 's/^/  /'
    echo "This archive may be published anonymously. Remove the offending files and re-run."
    rm -f "$ZIP_PATH"
    return 1
  fi

  local size sha files
  size="$(python3 -c "import os;print(f'{os.path.getsize('$ZIP_PATH')/1048576:.2f} MB')")"
  sha="$(shasum -a 256 "$ZIP_PATH" | cut -c1-16)"
  files="$(unzip -l "$ZIP_PATH" | tail -1 | awk '{print $2}')"
  echo "$ZIP_PATH  $size  $files files  sha256:$sha..."
  echo "disclosure gate: no credential or identity material in archive"
  LAST_DETAIL="$size, $files files, sha256 $sha, disclosure gate passed"
}

ph_publish() {
  local key="${UPLOAD_PREFIX%/}/app-docs-$RUN_ID.zip"
  aws s3 cp "$ZIP_PATH" "s3://$UPLOAD_BUCKET/$key" --only-show-errors || return $?
  echo "uploaded s3://$UPLOAD_BUCKET/$key"

  if (( PUBLIC )); then
    # Merge, never overwrite. put-bucket-policy replaces the whole document, so reading the
    # existing policy first is what stops this from silently deleting unrelated statements.
    local pol_file; pol_file="$(mktemp -t atxpol)"
    local existing; existing="$(aws s3api get-bucket-policy --bucket "$UPLOAD_BUCKET" \
                                 --output json 2>/dev/null | python3 -c \
                                 'import json,sys
try: print(json.load(sys.stdin).get("Policy") or "")
except Exception: print("")' 2>/dev/null || echo "")"
    python3 - "$UPLOAD_BUCKET" "${UPLOAD_PREFIX%/}" "$pol_file" <<PY
import json, sys
bucket, prefix, out = sys.argv[1:4]
existing = '''$existing'''.strip()
pol = json.loads(existing) if existing else {"Version": "2012-10-17", "Statement": []}
pol.setdefault("Version", "2012-10-17")
stmts = [s for s in (pol.get("Statement") or []) if s.get("Sid") != "AtxAppDocsPublicRead"]
stmts.append({
    "Sid": "AtxAppDocsPublicRead",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": f"arn:aws:s3:::{bucket}/{prefix}/*",
})
pol["Statement"] = stmts
open(out, "w", encoding="utf-8").write(json.dumps(pol))
PY
    aws s3api put-bucket-policy --bucket "$UPLOAD_BUCKET" --policy "file://$pol_file" || {
      rm -f "$pol_file"
      echo "public policy rejected — the object is uploaded but not anonymously readable"
      return 1
    }
    rm -f "$pol_file"
    local url="https://$UPLOAD_BUCKET.s3.amazonaws.com/$key"
    {
      echo "## Share link"
      echo ""
      echo "**Anonymously readable.** No expiry. The bucket policy grants \`s3:GetObject\` to"
      echo "\`Principal: \"*\"\` on \`${UPLOAD_PREFIX%/}/*\` in \`$UPLOAD_BUCKET\`."
      echo ""
      echo '```'
      echo "$url"
      echo '```'
      echo ""
      echo "To revoke, remove the \`AtxAppDocsPublicRead\` statement:"
      echo ""
      echo '```'
      echo "aws s3api get-bucket-policy --bucket $UPLOAD_BUCKET"
      echo "aws s3api delete-bucket-policy --bucket $UPLOAD_BUCKET   # if it is the only statement"
      echo '```'
    } > "$PUBLISH_NOTE"
    LAST_DETAIL="public: $url"
  else
    # A presigned URL cannot outlive the credentials that signed it. With SSO or any role
    # session, --expires-in is an upper bound the session silently overrides, so compare them.
    local ttl; ttl="$(aws configure export-credentials --format process 2>/dev/null | python3 -c '
import json, sys, datetime
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
exp = d.get("Expiration")
if not exp:
    sys.exit(0)
raw = exp.replace("Z", "+00:00")
try:
    e = datetime.datetime.fromisoformat(raw)
except ValueError:
    sys.exit(0)
if e.tzinfo is None:
    e = e.replace(tzinfo=datetime.timezone.utc)
print(int((e - datetime.datetime.now(datetime.timezone.utc)).total_seconds()))' 2>/dev/null || echo "")"
    local url
    url="$(aws s3 presign "s3://$UPLOAD_BUCKET/$key" --expires-in "$EXPIRES_IN" 2>&1)" || {
      echo "presign failed: $url"; return 1; }
    {
      echo "## Share link"
      echo ""
      echo "Presigned, expires in $EXPIRES_IN s from generation."
      echo ""
      echo '```'
      echo "$url"
      echo '```'
      if [[ -n "$ttl" ]] && [[ "$ttl" -lt "$EXPIRES_IN" ]]; then
        echo ""
        echo "> The signing credentials expire in ${ttl}s, before the requested $EXPIRES_IN s."
        echo "> A presigned URL cannot outlive the session that signed it, so this link dies"
        echo "> with the session regardless of --expires-in. For a long-lived link, sign with"
        echo "> an IAM user's long-term key, or use --public against a dedicated bucket."
      fi
    } > "$PUBLISH_NOTE"
    LAST_DETAIL="presigned, expires-in ${EXPIRES_IN}s$( [[ -n "$ttl" ]] && [[ "$ttl" -lt "$EXPIRES_IN" ]] && echo " (capped by session ttl ${ttl}s)")"
  fi
}

# ---------- execute ----------
START_MS="$(now_ms)"

run_phase preflight          ""  ph_preflight
abort_check fetch-specs       && run_phase fetch-specs        ""  ph_fetch_specs
abort_check verify-split      && run_phase verify-split       "1" ph_verify_split
abort_check snapshot-analysis && run_phase snapshot-analysis  ""  ph_snapshot_analysis
abort_check coverage          && run_phase coverage           ""  ph_coverage
abort_check evidence          && run_phase evidence           ""  ph_evidence
abort_check generate          && run_phase generate           ""  ph_generate
abort_check package           && run_phase package            ""  ph_package
abort_check publish           && run_phase publish            ""  ph_publish

if [[ -n "$ABORTED" ]]; then
  echo ""
  echo "  stopped before '$ABORTED': an earlier phase failed and later phases depend on it."
  echo "  Use --keep-going to run them anyway."
fi

# `latest` lets an ad-hoc script invocation land in the newest run without retyping a stamp.
ln -sfn "app-docs-$RUN_ID" ".atx/app-docs-latest" 2>/dev/null || true

END_MS="$(now_ms)"
TOTAL="$(python3 -c "print(f'{($END_MS-$START_MS)/1000:.1f}s')")"

echo ""
echo "  total $TOTAL"
if [[ -f "$MANIFEST_DIR/ledger.md" ]]; then
  DOCS_N="$(ls -1 "$DOCS_ROOT"/L*/*.md 2>/dev/null | wc -l | tr -d ' ')"
  echo "  documents  : $DOCS_N in $DOCS_ROOT"
fi
echo "  run log    : $RUN_LOG"
echo "  latest     : .atx/app-docs-latest -> app-docs-$RUN_ID"
[[ -f "$ZIP_PATH" ]] && echo "  archive    : $ZIP_PATH"

# Phase stdout is captured to compose the log, so anything the caller actually needs has to be
# reprinted here. The share link is the deliverable; losing it in a temp file that this script
# then deletes would make a successful publish useless.
if [[ -f "$PUBLISH_NOTE" ]]; then
  echo ""
  sed 's/^/  /' "$PUBLISH_NOTE" | grep -v '^  ```$'
fi
# Belt and braces: remove any scratch file an older version of this script left in the run folder,
# so a resumed run cannot publish one.
rm -f "$MANIFEST_DIR"/.phase-*.out
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
echo "  RESULT: all selected phases met their contract."
exit 0
