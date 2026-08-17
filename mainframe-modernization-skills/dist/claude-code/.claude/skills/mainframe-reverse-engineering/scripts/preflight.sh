#!/usr/bin/env bash
# Preflight environment checks for AWS Transform mainframe reverse engineering.
# Deterministic. Emits a JSON summary on stdout; human notes on stderr.
#
# Read-only with one declared exception: when --upload-bucket is supplied, a single small
# probe object is written and immediately deleted, because a bucket policy that grants
# s3:PutObject cannot be inferred from metadata alone and a documentation run that fails at
# the upload step after producing 31 documents wastes the whole run.
#
# Usage:
#   preflight.sh --profile <aws-profile> [--region <region>] [--bucket <bucket>]
#                [--upload-bucket <bucket>] [--upload-prefix <prefix>] [--intend-public]
#                [--min-ttl-min N] [--expected-run-min N]
#
# --bucket        the AWS Transform job bucket that artifacts are READ from.
# --upload-bucket a separate bucket the documentation zip is WRITTEN to. Deliberately a
#                 different flag: publishing a deliverable into the bucket that holds the raw
#                 source analysis is how a narrow share turns into a broad exposure.
# --intend-public check whether a public-read policy could actually be applied, and say so
#                 loudly. Does not itself change any policy.
#
# Exit codes: 0 all required checks passed | 1 a required check failed | 2 bad usage
#
# Always pass --profile and --region explicitly. A shell with an empty AWS_PROFILE silently
# falls back to the default profile, which is frequently expired, and surfaces confusing
# errors such as ExpiredToken or "HeadObject 400 Bad Request".
#
# It also checks for a poisoned environment. If AWS_CREDENTIAL_EXPIRATION is exported and
# its timestamp has passed, every AWS call fails with "Credentials were refreshed, but the
# refreshed credentials are still expired" EVEN WITH valid fresh keys, because botocore
# treats env credentials carrying an expiry as refreshable and refuses the stale set. This
# is usually self-inflicted by `eval "$(aws configure export-credentials --format env)"`
# in a long-lived shell, and it masquerades as an expired login or a skewed clock.

set -uo pipefail

PROFILE=""; REGION=""; BUCKET=""; MIN_TTL_MIN=15; EXPECTED_RUN_MIN=""
UPLOAD_BUCKET=""; UPLOAD_PREFIX="atx-app-docs"; INTEND_PUBLIC=0
FAILED=0

usage() { sed -n '2,30p' "$0" >&2; exit 2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)          PROFILE="${2:-}"; shift 2 ;;
    --region)           REGION="${2:-}"; shift 2 ;;
    --bucket)           BUCKET="${2:-}"; shift 2 ;;
    --upload-bucket)    UPLOAD_BUCKET="${2:-}"; shift 2 ;;
    --upload-prefix)    UPLOAD_PREFIX="${2:-}"; shift 2 ;;
    --intend-public)    INTEND_PUBLIC=1; shift ;;
    --min-ttl-min)      MIN_TTL_MIN="${2:-}"; shift 2 ;;
    --expected-run-min) EXPECTED_RUN_MIN="${2:-}"; shift 2 ;;
    -h|--help)          usage ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
done

[[ -n "$PROFILE" ]] || { echo "ERROR: --profile is required" >&2; usage; }

# The profile is the reference. Region is derived from it unless overridden, so callers
# supply one identifier and the account's own configuration decides where to look.
REGION_SOURCE="flag"
if [[ -z "$REGION" ]]; then
  REGION="$(aws configure get region --profile "$PROFILE" 2>/dev/null || true)"
  REGION_SOURCE="profile"
fi
if [[ -z "$REGION" ]]; then
  REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-}}"
  REGION_SOURCE="environment"
fi
if [[ -z "$REGION" ]]; then
  echo "ERROR: no region configured for profile '$PROFILE'." >&2
  echo "       Set one with: aws configure set region <region> --profile $PROFILE" >&2
  echo "       or pass --region explicitly." >&2
  exit 1
fi

note() { printf '  %s\n' "$*" >&2; }
declare -a RESULTS=()

# add_result <name> <ok|warn|fail> <detail>
add_result() {
  local name="$1" status="$2" detail="$3"
  detail="${detail//\\/\\\\}"; detail="${detail//\"/\\\"}"
  detail="$(printf '%s' "$detail" | tr '\n' ' ')"
  RESULTS+=("{\"check\":\"$name\",\"status\":\"$status\",\"detail\":\"$detail\"}")
  case "$status" in
    ok)   note "[ ok ] $name" ;;
    warn) note "[warn] $name — $detail" ;;
    fail) note "[FAIL] $name — $detail"; FAILED=1 ;;
  esac
}

echo "Preflight: profile=$PROFILE region=$REGION (from $REGION_SOURCE) bucket=${BUCKET:-<discover>}" >&2

# ---------- tooling ----------
if command -v aws >/dev/null 2>&1; then
  AWS_VER="$(aws --version 2>&1 | head -1)"
  case "$AWS_VER" in
    aws-cli/2*) add_result aws_cli ok "$AWS_VER" ;;
    *)          add_result aws_cli warn "expected v2, found: $AWS_VER" ;;
  esac
else
  add_result aws_cli fail "aws CLI not found on PATH"
fi

command -v unzip   >/dev/null 2>&1 && add_result unzip   ok "present" || add_result unzip   fail "unzip not found on PATH"
command -v python3 >/dev/null 2>&1 && add_result python3 ok "$(python3 --version 2>&1)" || add_result python3 fail "python3 not found on PATH"
command -v git     >/dev/null 2>&1 && add_result git     ok "present" || add_result git     warn "git absent — github intake mode unavailable"

# Everything below needs the CLI.
if ! command -v aws >/dev/null 2>&1; then
  printf '{"ok":false,"profile":"%s","region":"%s","checks":[%s]}\n' \
    "$PROFILE" "$REGION" "$(IFS=,; echo "${RESULTS[*]}")"
  exit 1
fi

# ---------- environment hygiene (run before identity: it explains identity failures) ----------
# A stale AWS_CREDENTIAL_EXPIRATION makes valid credentials look expired. Detect it, say so
# in terms that match the error the caller will otherwise see, and drop the whole inherited
# credential set so this script's own checks resolve cleanly from the profile.
ENV_POISON=""
if [[ -n "${AWS_CREDENTIAL_EXPIRATION:-}" ]]; then
  EXP_LEFT="$(python3 - "$AWS_CREDENTIAL_EXPIRATION" <<'PY' 2>/dev/null || echo ""
import sys, datetime
raw = sys.argv[1].replace("Z", "+00:00")
try:
    exp = datetime.datetime.fromisoformat(raw)
except ValueError:
    sys.exit(1)
if exp.tzinfo is None:
    exp = exp.replace(tzinfo=datetime.timezone.utc)
print(int((exp - datetime.datetime.now(datetime.timezone.utc)).total_seconds() // 60))
PY
)"
  if [[ -n "$EXP_LEFT" ]] && (( EXP_LEFT < 0 )); then
    ENV_POISON="AWS_CREDENTIAL_EXPIRATION is set to ${AWS_CREDENTIAL_EXPIRATION} (${EXP_LEFT#-}m in the past)"
    add_result env_credential_expiration fail \
      "$ENV_POISON — every AWS call will report 'Credentials were refreshed, but the refreshed credentials are still expired' even with valid keys. Unset AWS_CREDENTIAL_EXPIRATION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and AWS_SESSION_TOKEN, or prefix commands with: env -u AWS_CREDENTIAL_EXPIRATION -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN"
  else
    add_result env_credential_expiration warn \
      "AWS_CREDENTIAL_EXPIRATION is exported (${AWS_CREDENTIAL_EXPIRATION}); it will poison this shell once it passes"
  fi
else
  add_result env_credential_expiration ok "not set"
fi

# Resolve from the profile alone, ignoring any inherited static credentials.
unset AWS_CREDENTIAL_EXPIRATION AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
export AWS_PROFILE="$PROFILE"
export AWS_REGION="$REGION"

# ---------- profile ----------
if aws configure list-profiles 2>/dev/null | grep -qx "$PROFILE"; then
  add_result profile_exists ok "$PROFILE"
else
  add_result profile_exists warn "profile '$PROFILE' not in configure list-profiles (may still resolve via env)"
fi

# ---------- identity ----------
IDENTITY_JSON="$(aws sts get-caller-identity --output json 2>&1)"
if [[ $? -eq 0 ]] && printf '%s' "$IDENTITY_JSON" | grep -q '"Account"'; then
  ACCOUNT_ID="$(printf '%s' "$IDENTITY_JSON" | python3 -c 'import json,sys;print(json.load(sys.stdin)["Account"])' 2>/dev/null || echo unknown)"
  ARN="$(printf '%s' "$IDENTITY_JSON" | python3 -c 'import json,sys;print(json.load(sys.stdin)["Arn"])' 2>/dev/null || echo unknown)"
  add_result sts_identity ok "account=$ACCOUNT_ID arn=$ARN"
else
  ACCOUNT_ID="unknown"; ARN="unknown"
  case "$IDENTITY_JSON" in
    *ExpiredToken*|*expired*) add_result sts_identity fail "credentials expired — refresh SSO login for profile '$PROFILE'" ;;
    *)                        add_result sts_identity fail "$(printf '%s' "$IDENTITY_JSON" | head -1)" ;;
  esac
fi

# ---------- credential headroom ----------
# Only meaningful for SSO/role sessions with a cached expiry.
EXP="$(aws configure export-credentials --format process 2>/dev/null \
        | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("Expiration",""))' 2>/dev/null || true)"
if [[ -n "${EXP:-}" ]]; then
  MINS_LEFT="$(python3 - "$EXP" <<'PY' 2>/dev/null || echo ""
import sys,datetime
raw=sys.argv[1].replace("Z","+00:00")
try:
    exp=datetime.datetime.fromisoformat(raw)
except ValueError:
    sys.exit(1)
now=datetime.datetime.now(datetime.timezone.utc)
print(int((exp-now).total_seconds()//60))
PY
)"
  if [[ -n "$MINS_LEFT" ]]; then
    if (( MINS_LEFT < 0 )); then
      add_result cred_ttl fail "credentials already expired"
    elif (( MINS_LEFT < MIN_TTL_MIN )); then
      add_result cred_ttl warn "only ${MINS_LEFT}m remaining (< ${MIN_TTL_MIN}m) — refresh before a long run"
    elif [[ -n "$EXPECTED_RUN_MIN" ]] && (( MINS_LEFT < EXPECTED_RUN_MIN )); then
      # Headroom shorter than the work. Not fatal: extraction runs server-side and survives a
      # local credential lapse. What matters is holding valid credentials at each download.
      add_result cred_ttl warn \
        "${MINS_LEFT}m remaining but this run is expected to need ~${EXPECTED_RUN_MIN}m. The server-side run survives a local lapse; re-authenticate before each artifact download. To extend, raise the permission set's SessionDuration (aws sso-admin update-permission-set --session-duration PT8H, max PT12H) and the Identity Center session duration."
    else
      add_result cred_ttl ok "${MINS_LEFT}m remaining"
    fi
  else
    add_result cred_ttl warn "could not parse expiry '$EXP'"
  fi
else
  add_result cred_ttl warn "no expiry exposed (static or unsupported credential type)"
fi

# ---------- bucket ----------
if [[ -n "$BUCKET" ]]; then
  LOC_JSON="$(aws s3api get-bucket-location --bucket "$BUCKET" --output json 2>&1)"
  if [[ $? -eq 0 ]]; then
    BLOC="$(printf '%s' "$LOC_JSON" | python3 -c 'import json,sys;v=json.load(sys.stdin).get("LocationConstraint");print(v or "us-east-1")' 2>/dev/null || echo unknown)"
    if [[ "$BLOC" == "$REGION" ]]; then
      add_result bucket_region ok "$BUCKET in $BLOC"
    else
      add_result bucket_region warn "bucket is in $BLOC but region flag is $REGION — keep all calls in the bucket's region"
    fi

    if aws s3 ls "s3://$BUCKET" --page-size 1 >/dev/null 2>&1; then
      add_result bucket_read ok "listable"
    else
      add_result bucket_read fail "cannot list s3://$BUCKET with this principal"
    fi

    CORS_JSON="$(aws s3api get-bucket-cors --bucket "$BUCKET" --output json 2>&1)"
    if [[ $? -eq 0 ]] && printf '%s' "$CORS_JSON" | grep -q 'transform\.'; then
      add_result bucket_cors ok "transform origins present"
    else
      add_result bucket_cors warn "no CORS rule for https://*.transform.<region>.on.aws — console inline viewing/compare will not work (does not affect this skill's downloads)"
    fi
  else
    add_result bucket_region fail "$(printf '%s' "$LOC_JSON" | head -1)"
  fi
else
  add_result bucket_read warn "no --bucket supplied; skipped bucket checks"
fi

# ---------- upload bucket (documentation deliverable destination) ----------
# Only exercised when --upload-bucket is supplied, so extraction-only runs are unaffected.
UPLOAD_PUBLIC_POSTURE="not-checked"
if [[ -n "$UPLOAD_BUCKET" ]]; then

  # The read bucket holds the raw source analysis, spec bundles and data dictionary. Sharing a
  # deliverable out of it means any policy widening reaches all of that too.
  if [[ -n "$BUCKET" && "$UPLOAD_BUCKET" == "$BUCKET" ]]; then
    add_result upload_bucket_separation warn \
      "upload bucket is the same bucket the job artifacts are read from ($BUCKET) — a share-scoped policy here also covers transform-output/. Prefer a dedicated bucket."
  else
    add_result upload_bucket_separation ok "distinct from the artifact bucket"
  fi

  if ULOC_JSON="$(aws s3api get-bucket-location --bucket "$UPLOAD_BUCKET" --output json 2>&1)"; then
    UBLOC="$(printf '%s' "$ULOC_JSON" | python3 -c 'import json,sys;v=json.load(sys.stdin).get("LocationConstraint");print(v or "us-east-1")' 2>/dev/null || echo unknown)"
    if [[ "$UBLOC" == "$REGION" ]]; then
      add_result upload_bucket_region ok "$UPLOAD_BUCKET in $UBLOC"
    else
      add_result upload_bucket_region warn "upload bucket is in $UBLOC but region is $REGION — presigned URLs must be generated against $UBLOC or they return SignatureDoesNotMatch"
    fi

    # Write probe. Metadata cannot tell us whether this principal may PutObject, and finding
    # out after 31 documents have been generated is the expensive way to learn it.
    # --body must be a real file path: the CLI rejects /dev/null as a blob source, which would
    # otherwise report a permission failure that does not exist.
    PROBE_KEY="${UPLOAD_PREFIX%/}/.preflight-write-probe-$$"
    PROBE_FILE="$(mktemp -t atxprobe)" || PROBE_FILE=""
    if [[ -n "$PROBE_FILE" ]]; then
      printf 'preflight write probe\n' > "$PROBE_FILE"
      PROBE_ERR="$(aws s3api put-object --bucket "$UPLOAD_BUCKET" --key "$PROBE_KEY" \
                     --body "$PROBE_FILE" 2>&1 >/dev/null)"
      if [[ -z "$PROBE_ERR" ]]; then
        add_result upload_bucket_write ok "PutObject accepted at s3://$UPLOAD_BUCKET/${UPLOAD_PREFIX%/}/"
        aws s3api delete-object --bucket "$UPLOAD_BUCKET" --key "$PROBE_KEY" >/dev/null 2>&1 \
          || add_result upload_bucket_cleanup warn "probe object left behind at s3://$UPLOAD_BUCKET/$PROBE_KEY — delete it manually"
      else
        add_result upload_bucket_write fail \
          "cannot PutObject to s3://$UPLOAD_BUCKET/${UPLOAD_PREFIX%/}/ — the upload phase would fail after the documents are built. $(printf '%s' "$PROBE_ERR" | head -1)"
      fi
      rm -f "$PROBE_FILE"
    else
      add_result upload_bucket_write warn "could not create a local temp file for the write probe; upload permission unverified"
    fi

    # Public-access posture. Reported whether or not public sharing is intended, because the
    # answer changes what the upload actually exposes.
    if UPAB_JSON="$(aws s3api get-public-access-block --bucket "$UPLOAD_BUCKET" --output json 2>&1)"; then
      UPAB_ALL_OFF="$(printf '%s' "$UPAB_JSON" | python3 -c '
import json, sys
c = json.load(sys.stdin).get("PublicAccessBlockConfiguration") or {}
keys = ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")
print("yes" if all(c.get(k) is False for k in keys) else "no")' 2>/dev/null || echo unknown)"
      UPAB_BLOCK_POLICY="$(printf '%s' "$UPAB_JSON" | python3 -c '
import json, sys
c = json.load(sys.stdin).get("PublicAccessBlockConfiguration") or {}
print("yes" if c.get("BlockPublicPolicy") else "no")' 2>/dev/null || echo unknown)"
    else
      case "$UPAB_JSON" in
        *NoSuchPublicAccessBlockConfiguration*)
          UPAB_ALL_OFF="yes"; UPAB_BLOCK_POLICY="no" ;;
        *) UPAB_ALL_OFF="unknown"; UPAB_BLOCK_POLICY="unknown" ;;
      esac
    fi

    if [[ "$UPAB_BLOCK_POLICY" == "yes" ]]; then
      UPLOAD_PUBLIC_POSTURE="blocked"
    elif [[ "$UPAB_ALL_OFF" == "yes" ]]; then
      UPLOAD_PUBLIC_POSTURE="unguarded"
    else
      UPLOAD_PUBLIC_POSTURE="partial"
    fi

    if (( INTEND_PUBLIC )); then
      case "$UPLOAD_PUBLIC_POSTURE" in
        blocked) add_result upload_bucket_public fail \
          "public sharing was requested but BlockPublicPolicy is enabled on $UPLOAD_BUCKET, so a public-read policy will be rejected. Either use a presigned URL (no policy change needed) or disable it deliberately: aws s3api put-public-access-block --bucket $UPLOAD_BUCKET --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false" ;;
        unguarded) add_result upload_bucket_public warn \
          "all four Block Public Access settings are OFF on $UPLOAD_BUCKET — a public policy will take effect immediately with no guardrail. The documentation contains the AWS account id, bucket names, program and JCL names, business rules and the data dictionary. Confirm that is intended for anonymous access." ;;
        *) add_result upload_bucket_public warn \
          "Block Public Access is partially enabled on $UPLOAD_BUCKET; a public policy may or may not apply. Verify before relying on the link." ;;
      esac
    else
      case "$UPLOAD_PUBLIC_POSTURE" in
        blocked)   add_result upload_bucket_public ok "BlockPublicPolicy enabled — presigned URLs still work and nothing can be made anonymously readable by accident" ;;
        unguarded) add_result upload_bucket_public warn "all four Block Public Access settings are OFF on $UPLOAD_BUCKET; nothing structural prevents a later policy from exposing the uploaded zip" ;;
        *)         add_result upload_bucket_public ok "Block Public Access partially enabled" ;;
      esac
    fi

    # An existing wildcard policy means the upload is exposed the moment it lands, with no
    # further action from this pipeline.
    if UPOL_JSON="$(aws s3api get-bucket-policy --bucket "$UPLOAD_BUCKET" --output json 2>&1)"; then
      if printf '%s' "$UPOL_JSON" | python3 -c '
import json, sys
raw = json.load(sys.stdin).get("Policy") or "{}"
pol = json.loads(raw)
for st in pol.get("Statement") or []:
    if st.get("Effect") != "Allow":
        continue
    p = st.get("Principal")
    if p == "*" or (isinstance(p, dict) and "*" in str(p.get("AWS", ""))):
        sys.exit(0)
sys.exit(1)' 2>/dev/null; then
        add_result upload_bucket_existing_policy warn \
          "$UPLOAD_BUCKET already has a bucket policy allowing Principal '*' — anything uploaded is anonymously readable on arrival, before any --public flag is used"
      else
        add_result upload_bucket_existing_policy ok "bucket policy present, no anonymous Allow"
      fi
    else
      case "$UPOL_JSON" in
        *NoSuchBucketPolicy*) add_result upload_bucket_existing_policy ok "no bucket policy" ;;
        *) add_result upload_bucket_existing_policy warn "could not read bucket policy: $(printf '%s' "$UPOL_JSON" | head -1)" ;;
      esac
    fi
  else
    add_result upload_bucket_region fail "$(printf '%s' "$ULOC_JSON" | head -1)"
  fi
fi

# ---------- account setup discovery ----------
# Setup (Transform onboarding, connector, Neptune knowledge graph, IAM roles) is a
# precondition this skill verifies, never provisions. These probes are best-effort: a
# missing read permission is a warning, not a failure, because AWS Transform itself is
# the authority on connector state.

NEPTUNE_N=0
if NEPTUNE_JSON="$(aws neptune describe-db-clusters --output json 2>&1)"; then
  NEPTUNE_N="$(printf '%s' "$NEPTUNE_JSON" \
    | python3 -c 'import json,sys;print(len(json.load(sys.stdin).get("DBClusters") or []))' 2>/dev/null || echo 0)"
  if [[ "${NEPTUNE_N:-0}" -gt 0 ]]; then
    NEPTUNE_DETAIL="$(printf '%s' "$NEPTUNE_JSON" | python3 -c '
import json, sys
cs = json.load(sys.stdin).get("DBClusters") or []
print("; ".join("%s [%s] %s" % (c.get("DBClusterIdentifier"), c.get("Status"),
                                c.get("EngineVersion")) for c in cs[:3]))' 2>/dev/null || echo "")"
    add_result neptune_cluster ok "$NEPTUNE_N in $REGION — $NEPTUNE_DETAIL"
  else
    add_result neptune_cluster warn "no Neptune cluster in $REGION — the mainframe reimagine connector needs one for the knowledge graph"
  fi
else
  case "$NEPTUNE_JSON" in
    *AccessDenied*|*UnauthorizedOperation*|*not\ authorized*)
      add_result neptune_cluster warn "no permission to describe Neptune clusters — verify the connector through AWS Transform instead" ;;
    *)
      add_result neptune_cluster warn "$(printf '%s' "$NEPTUNE_JSON" | head -1)" ;;
  esac
fi

# ---------- summary ----------
OK=true; [[ $FAILED -eq 0 ]] || OK=false
printf '{"ok":%s,"profile":"%s","region":"%s","regionSource":"%s","accountId":"%s","arn":"%s","bucket":"%s","uploadBucket":"%s","uploadPrefix":"%s","uploadPublicPosture":"%s","intendPublic":%s,"neptuneClusters":%s,"checks":[%s]}\n' \
  "$OK" "$PROFILE" "$REGION" "$REGION_SOURCE" "${ACCOUNT_ID:-unknown}" "${ARN:-unknown}" \
  "${BUCKET:-}" "${UPLOAD_BUCKET:-}" "${UPLOAD_PREFIX:-}" "$UPLOAD_PUBLIC_POSTURE" \
  "$( ((INTEND_PUBLIC)) && echo true || echo false )" "${NEPTUNE_N:-0}" \
  "$(IFS=,; echo "${RESULTS[*]}")"

[[ $FAILED -eq 0 ]] || exit 1
exit 0
