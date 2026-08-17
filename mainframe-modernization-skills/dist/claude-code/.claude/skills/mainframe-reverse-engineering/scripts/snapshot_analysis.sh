#!/usr/bin/env bash
# Snapshot an AWS Transform job's ANALYSIS artifacts to local disk.
#
# Usage:
#   snapshot_analysis.sh --profile P --region R --bucket B --job-id J [--dest DIR] [--dry-run]
#
# Exit codes: 0 ok (at least one prefix captured) | 1 nothing captured | 2 bad usage
#
# Why this exists
# ---------------
# Stage 4 already snapshots the business function catalog, and Stage 5 snapshots the spec
# bundles. Neither captures the *analysis* outputs — code analysis (per-file type, LOC,
# effective lines, cyclomatic complexity, classification, dependencies, missing files) and
# data analysis (data lineage with read/write/update/delete direction, and the field-level
# data dictionary). Those are the evidence base for anything that claims coverage, and they
# are the primary evidence source for the atx-app-documentation skill.
#
# Read-only against S3. Never deletes, never writes to the bucket.
#
# Environment hygiene: a stale AWS_CREDENTIAL_EXPIRATION in the caller's environment makes
# valid credentials report "refreshed credentials are still expired", so the inherited
# credential set is dropped and everything resolves from --profile.

set -uo pipefail

PROFILE=""; REGION=""; BUCKET=""; JOB_ID=""; DEST=".atx/mfre/analysis"; DRY=0

usage() { sed -n '2,10p' "$0" >&2; exit 2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="${2:-}"; shift 2 ;;
    --region)  REGION="${2:-}";  shift 2 ;;
    --bucket)  BUCKET="${2:-}";  shift 2 ;;
    --job-id)  JOB_ID="${2:-}";  shift 2 ;;
    --dest)    DEST="${2:-}";    shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) usage ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
done

# macOS ships bash 3.2, which has no ${var,,} lowercase expansion. It is not merely a cosmetic
# problem in a message: the bad substitution aborts the compound command, so `usage` never runs
# and a missing required argument fails to stop the script. Lowercase via tr instead.
for req in PROFILE BUCKET JOB_ID; do
  if [[ -z "${!req}" ]]; then
    echo "ERROR: --$(printf '%s' "$req" | tr '[:upper:]_' '[:lower:]-') is required" >&2
    usage
  fi
done

if [[ -z "$REGION" ]]; then
  REGION="$(aws configure get region --profile "$PROFILE" 2>/dev/null || true)"
  [[ -n "$REGION" ]] || { echo "ERROR: no region for profile '$PROFILE'; pass --region" >&2; exit 2; }
fi

unset AWS_CREDENTIAL_EXPIRATION AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
export AWS_PROFILE="$PROFILE" AWS_REGION="$REGION"

BASE="transform-output/${JOB_ID}"

# prefix : local subdir : what it holds
PREFIXES=(
  "results/:code-analysis:per-file classification, assets list, dependencies, missing-file list"
  "1/data_analysis/:data-analysis:data lineage and field-level data dictionary"
  "1/business-documentation/:business-documentation:generated business documentation"
  "1/artifact-slicing/:artifact-slicing:per-artifact slices used by extraction"
  "business-function-discovery/:business-function-discovery:business function catalog and graphs"
)

echo "Snapshot analysis: s3://$BUCKET/$BASE  ->  $DEST" >&2
echo "  profile=$PROFILE region=$REGION dry-run=$DRY" >&2

CAPTURED=0
declare -a SUMMARY=()

for entry in "${PREFIXES[@]}"; do
  IFS=':' read -r prefix subdir desc <<<"$entry"
  src="s3://$BUCKET/$BASE/$prefix"

  n="$(aws s3 ls "$src" --recursive 2>/dev/null | grep -c . || true)"
  if [[ "${n:-0}" -eq 0 ]]; then
    echo "  [skip] $prefix — not present" >&2
    SUMMARY+=("{\"prefix\":\"$prefix\",\"localDir\":\"$subdir\",\"objects\":0,\"captured\":false,\"note\":\"not present in this job\"}")
    continue
  fi

  if [[ $DRY -eq 1 ]]; then
    echo "  [dry ] $prefix — $n object(s) would go to $DEST/$subdir" >&2
    SUMMARY+=("{\"prefix\":\"$prefix\",\"localDir\":\"$subdir\",\"objects\":$n,\"captured\":false,\"note\":\"dry run\"}")
    CAPTURED=$((CAPTURED+1))
    continue
  fi

  mkdir -p "$DEST/$subdir"
  if aws s3 sync "$src" "$DEST/$subdir" --no-progress >/dev/null 2>&1; then
    got="$(find "$DEST/$subdir" -type f | grep -c . || true)"
    echo "  [ ok ] $prefix — $got file(s) -> $DEST/$subdir" >&2
    SUMMARY+=("{\"prefix\":\"$prefix\",\"localDir\":\"$subdir\",\"objects\":$got,\"captured\":true,\"description\":\"$desc\"}")
    CAPTURED=$((CAPTURED+1))
  else
    echo "  [FAIL] $prefix — sync failed" >&2
    SUMMARY+=("{\"prefix\":\"$prefix\",\"localDir\":\"$subdir\",\"objects\":0,\"captured\":false,\"note\":\"sync failed\"}")
  fi
done

# Unpack any zipped bundles so downstream consumers read files, not archives.
if [[ $DRY -eq 0 ]]; then
  while IFS= read -r z; do
    d="${z%.zip}"
    mkdir -p "$d" && unzip -o -q "$z" -d "$d" 2>/dev/null \
      && echo "  [ ok ] unpacked $(basename "$z")" >&2
  done < <(find "$DEST" -name '*.zip' -type f 2>/dev/null)
fi

if [[ $DRY -eq 0 && $CAPTURED -gt 0 ]]; then
  mkdir -p "$DEST"
  printf '{"jobId":"%s","bucket":"%s","region":"%s","capturedAt":"%s","prefixes":[%s]}\n' \
    "$JOB_ID" "$BUCKET" "$REGION" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "$(IFS=,; echo "${SUMMARY[*]}")" > "$DEST/snapshot-manifest.json"
  echo "  wrote $DEST/snapshot-manifest.json" >&2
fi

if [[ $CAPTURED -eq 0 ]]; then
  echo "ERROR: no analysis prefixes captured — check the job id and bucket" >&2
  exit 1
fi
exit 0
