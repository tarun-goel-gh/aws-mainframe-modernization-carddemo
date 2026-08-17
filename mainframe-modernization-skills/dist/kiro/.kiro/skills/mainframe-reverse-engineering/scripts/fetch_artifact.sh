#!/usr/bin/env bash
# Download and unpack an AWS Transform artifact from S3.
#
# Usage:
#   fetch_artifact.sh --profile P --region R --bucket B --key KEY --dest DIR [--no-unzip] [--keep-zip]
#
# Exit codes: 0 ok | 1 download/unpack failure | 2 bad usage
#
# Downloads through the S3 API deliberately. Reading connector-backed assets through the MCP
# layer returns bytes as a text field, which corrupts binary zips.

set -euo pipefail

PROFILE=""; REGION=""; BUCKET=""; KEY=""; DEST=""; UNZIP=1; KEEP_ZIP=1

usage() { sed -n '2,11p' "$0" >&2; exit 2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)  PROFILE="${2:-}"; shift 2 ;;
    --region)   REGION="${2:-}"; shift 2 ;;
    --bucket)   BUCKET="${2:-}"; shift 2 ;;
    --key)      KEY="${2:-}"; shift 2 ;;
    --dest)     DEST="${2:-}"; shift 2 ;;
    --no-unzip) UNZIP=0; shift ;;
    --keep-zip) KEEP_ZIP=1; shift ;;
    --drop-zip) KEEP_ZIP=0; shift ;;
    -h|--help)  usage ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
done

[[ -n "$PROFILE" && -n "$REGION" && -n "$BUCKET" && -n "$KEY" && -n "$DEST" ]] \
  || { echo "ERROR: --profile --region --bucket --key --dest are all required" >&2; usage; }

export AWS_PROFILE="$PROFILE"
export AWS_REGION="$REGION"

BASE="$(basename "$KEY")"
mkdir -p "$DEST"
LOCAL="$DEST/$BASE"

echo "fetching s3://$BUCKET/$KEY" >&2

# Confirm existence and size first; a clear error here beats a confusing cp failure.
HEAD="$(aws s3api head-object --bucket "$BUCKET" --key "$KEY" --output json 2>&1)" || {
  echo "ERROR: head-object failed for s3://$BUCKET/$KEY" >&2
  printf '%s\n' "$HEAD" | head -3 >&2
  case "$HEAD" in
    *ExpiredToken*|*expired*)   echo "HINT: credentials expired — refresh SSO for profile '$PROFILE'" >&2 ;;
    *400*|*Bad*Request*)        echo "HINT: usually expired credentials or a region mismatch" >&2 ;;
    *404*|*Not*Found*)          echo "HINT: key does not exist — re-list the prefix" >&2 ;;
  esac
  exit 1
}

REMOTE_SIZE="$(printf '%s' "$HEAD" | python3 -c 'import json,sys;print(json.load(sys.stdin)["ContentLength"])' 2>/dev/null || echo 0)"

aws s3 cp "s3://$BUCKET/$KEY" "$LOCAL" --no-progress >&2 || {
  echo "ERROR: download failed" >&2; exit 1; }

LOCAL_SIZE="$(wc -c <"$LOCAL" | tr -d ' ')"
if [[ "$REMOTE_SIZE" != "0" && "$LOCAL_SIZE" != "$REMOTE_SIZE" ]]; then
  echo "ERROR: size mismatch (remote=$REMOTE_SIZE local=$LOCAL_SIZE)" >&2
  exit 1
fi

if command -v shasum >/dev/null 2>&1; then
  SHA="$(shasum -a 256 "$LOCAL" | awk '{print $1}')"
elif command -v sha256sum >/dev/null 2>&1; then
  SHA="$(sha256sum "$LOCAL" | awk '{print $1}')"
else
  SHA="unavailable"
fi

EXTRACTED=0
if (( UNZIP )) && [[ "$BASE" == *.zip ]]; then
  command -v unzip >/dev/null 2>&1 || { echo "ERROR: unzip not found on PATH" >&2; exit 1; }
  unzip -tq "$LOCAL" >/dev/null 2>&1 || { echo "ERROR: zip integrity test failed for $BASE" >&2; exit 1; }
  unzip -o -q "$LOCAL" -d "$DEST"
  EXTRACTED="$(unzip -Z1 "$LOCAL" | grep -cv '/$' || true)"
  echo "extracted $EXTRACTED file(s) into $DEST" >&2
  (( KEEP_ZIP )) || rm -f "$LOCAL"
fi

python3 - "$BUCKET" "$KEY" "$LOCAL" "$LOCAL_SIZE" "$SHA" "$DEST" "$EXTRACTED" "$KEEP_ZIP" <<'PY'
import json,os,sys
bucket,key,local,size,sha,dest,extracted,keep=sys.argv[1:9]
print(json.dumps({
 "bucket":bucket,"key":key,
 "localZip":(local if keep=="1" and os.path.exists(local) else None),
 "bytes":int(size),"sha256":sha,"dest":dest,
 "extractedFiles":int(extracted),"ok":True},indent=2))
PY
