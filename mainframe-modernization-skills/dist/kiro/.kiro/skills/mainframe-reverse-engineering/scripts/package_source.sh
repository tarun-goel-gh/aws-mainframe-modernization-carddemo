#!/usr/bin/env bash
# Package mainframe source into the zip layout AWS Transform expects.
#
# Usage:
#   package_source.sh --src <dir> --out <zip> [--app <name>] [--glossary <csv>]
#                     [--upload s3://bucket/prefix/] [--profile P --region R]
#                     [--max-unknown-share 0.10] [--force]
#
# Produces: <out> (zip), <out>.sha256, and inventory.csv beside <out>.
# Exit codes: 0 ok | 1 gate failure | 2 bad usage
#
# Layout produced (top-level folder is zipped, per AWS guidance):
#   app/cobol|copybooks|jcl|bms|cics|db2|ims|pli|asm|other/...
#   glossary.csv (root, optional but recommended)

set -euo pipefail

SRC=""; OUT=""; APP="app"; GLOSSARY=""; UPLOAD=""; PROFILE=""; REGION=""
MAX_UNKNOWN_SHARE="0.10"; FORCE=0

usage() { sed -n '2,17p' "$0" >&2; exit 2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src)                SRC="${2:-}"; shift 2 ;;
    --out)                OUT="${2:-}"; shift 2 ;;
    --app)                APP="${2:-}"; shift 2 ;;
    --glossary)           GLOSSARY="${2:-}"; shift 2 ;;
    --upload)             UPLOAD="${2:-}"; shift 2 ;;
    --profile)            PROFILE="${2:-}"; shift 2 ;;
    --region)             REGION="${2:-}"; shift 2 ;;
    --max-unknown-share)  MAX_UNKNOWN_SHARE="${2:-}"; shift 2 ;;
    --force)              FORCE=1; shift ;;
    -h|--help)            usage ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
done

[[ -n "$SRC" && -n "$OUT" ]] || { echo "ERROR: --src and --out are required" >&2; usage; }
[[ -d "$SRC" ]] || { echo "ERROR: source directory not found: $SRC" >&2; exit 2; }
command -v zip >/dev/null 2>&1 || { echo "ERROR: zip not found on PATH" >&2; exit 2; }

OUT_DIR="$(cd "$(dirname "$OUT")" 2>/dev/null && pwd || true)"
[[ -n "$OUT_DIR" ]] || { mkdir -p "$(dirname "$OUT")"; OUT_DIR="$(cd "$(dirname "$OUT")" && pwd)"; }
OUT="$OUT_DIR/$(basename "$OUT")"
INVENTORY="$OUT_DIR/inventory.csv"

STAGE="$(mktemp -d)"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

ROOT="$STAGE/$APP"
mkdir -p "$ROOT"/{cobol,copybooks,jcl,bms,cics,db2,ims,pli,asm,scheduler,other,data,docs}

# classify <lowercased-extension> -> bucket
#
# Buckets fall into three groups, which the unknown-share gate treats differently:
#   input artifacts  cobol copybooks jcl bms cics db2 ims pli asm scheduler other UNKNOWN
#   companions       data docs                (shipped, excluded from the share)
#   noise            dropped entirely
#
# `.txt` deliberately stays UNKNOWN rather than being guessed as data: AWS guidance is to
# leave uncertain files as blank or .txt and let Transform classify them, so they belong in
# the numerator as work still to do.
classify() {
  case "$1" in
    cbl|cob|cobol)            echo cobol ;;
    cpy)                      echo copybooks ;;
    jcl|prc|proc|inc|ctl)     echo jcl ;;
    bms)                      echo bms ;;
    csd)                      echo cics ;;
    dcl|sql|ddl)              echo db2 ;;
    psb|dbd|ims|mfs)          echo ims ;;
    pl1|pl1_copy)             echo pli ;;
    asm|mac)                  echo asm ;;
    ca7|controlm)             echo scheduler ;;
    nat|rex|rexx|ezt)         echo other ;;
    ps|dat|init|seq|vsam)     echo data ;;
    md|pdf)                   echo docs ;;
    gitkeep|gitignore|ds_store) echo noise ;;
    *)                        echo UNKNOWN ;;
  esac
}

echo "file,extension,classification,bytes,relative_path" > "$INVENTORY"

# No associative arrays here on purpose: macOS ships bash 3.2, which lacks `declare -A`.
# Counts are derived from inventory.csv after the copy loop.

while IFS= read -r -d '' f; do
  rel="${f#"$SRC"/}"
  case "$rel" in
    .git/*|*/.git/*|.DS_Store|*/.DS_Store|__MACOSX/*) continue ;;
  esac

  base="$(basename "$f")"
  ext="${base##*.}"
  [[ "$base" == "$ext" ]] && ext=""            # no dot at all
  ext_lc="$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"

  # glossary/pdf config belong at the zip root, not in a type folder
  if [[ "$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]')" == "glossary.csv" && -z "$GLOSSARY" ]]; then
    cp "$f" "$STAGE/glossary.csv"
    echo "$base,csv,glossary-root,$(wc -c <"$f" | tr -d ' '),$rel" >> "$INVENTORY"
    continue
  fi
  if [[ "$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]')" == "pdf_config.json" ]]; then
    cp "$f" "$STAGE/pdf_config.json"
    echo "$base,json,pdf-config-root,$(wc -c <"$f" | tr -d ' '),$rel" >> "$INVENTORY"
    continue
  fi

  bucket="$(classify "$ext_lc")"

  if [[ "$bucket" == "noise" ]]; then
    echo "$base,${ext_lc:-<none>},noise,0,$rel" >> "$INVENTORY"
    continue
  fi

  if [[ "$bucket" == "UNKNOWN" ]]; then
    # Leave the name as-is. Transform classifies unknown/blank/.txt itself; inventing an
    # extension is worse than leaving it unclassified.
    dest="$ROOT/other"
  else
    dest="$ROOT/$bucket"
  fi

  # Preserve subpaths to avoid collisions between same-named members of different libraries.
  sub="$(dirname "$rel")"
  if [[ "$sub" != "." ]]; then
    mkdir -p "$dest/$sub"
    cp "$f" "$dest/$sub/$base"
  else
    cp "$f" "$dest/$base"
  fi

  echo "$base,${ext_lc:-<none>},$bucket,$(wc -c <"$f" | tr -d ' '),$rel" >> "$INVENTORY"
done < <(find "$SRC" -type f -print0)

# explicit glossary wins
if [[ -n "$GLOSSARY" ]]; then
  [[ -f "$GLOSSARY" ]] || { echo "ERROR: glossary not found: $GLOSSARY" >&2; exit 2; }
  cp "$GLOSSARY" "$STAGE/glossary.csv"
fi

# drop empty type folders so the zip reflects reality
find "$ROOT" -type d -empty -delete 2>/dev/null || true

# Derive counts from the inventory (bash 3.2 compatible: no associative arrays).
COUNTS_FILE="$(mktemp)"
python3 - "$INVENTORY" > "$COUNTS_FILE" <<'PY'
import csv, sys
from collections import Counter

rows = list(csv.DictReader(open(sys.argv[1], newline="", encoding="utf-8", errors="replace")))
c = Counter(r["classification"] for r in rows)

INPUT = ("cobol", "copybooks", "jcl", "bms", "cics", "db2", "ims",
         "pli", "asm", "scheduler", "other", "UNKNOWN")

# The unknown share measures classification quality of *input artifacts*. Data files,
# docs, and dropped noise are not source and would otherwise make a well-formed repo
# look badly classified.
inputs = sum(c.get(k, 0) for k in INPUT)
unknown = c.get("UNKNOWN", 0)

print(f"TOTAL_N={inputs}")
print(f"UNKNOWN_N={unknown}")
print(f"SHARE={(unknown / inputs if inputs else 0):.4f}")
print(f"N_data={c.get('data', 0)}")
print(f"N_docs={c.get('docs', 0)}")
print(f"N_noise={c.get('noise', 0)}")
for k in INPUT:
    print(f"N_{k}={c.get(k, 0)}")
PY
# shellcheck disable=SC1090
. "$COUNTS_FILE"
rm -f "$COUNTS_FILE"

total="$TOTAL_N"; unknown="$UNKNOWN_N"; share="$SHARE"
cobol_n="$N_cobol"; jcl_n="$N_jcl"

echo "--- input artifacts ---" >&2
for k in cobol copybooks jcl bms cics db2 ims pli asm scheduler other UNKNOWN; do
  eval "v=\${N_$k}"
  [[ "${v:-0}" -gt 0 ]] && printf '  %-11s %s\n' "$k" "$v" >&2
done
printf '  %-11s %s\n' TOTAL "$total" >&2
printf '  unknown share %s (limit %s)\n' "$share" "$MAX_UNKNOWN_SHARE" >&2
echo "--- companions (excluded from share) ---" >&2
printf '  %-11s %s\n' data "${N_data:-0}" >&2
printf '  %-11s %s\n' docs "${N_docs:-0}" >&2
printf '  %-11s %s (dropped)\n' noise "${N_noise:-0}" >&2
if [[ -f "$STAGE/glossary.csv" ]]; then
  echo "  glossary.csv present" >&2
else
  echo "  glossary.csv MISSING (recommended — improves extraction quality)" >&2
fi

# ---------- gate G1 ----------
gate_fail=0
if (( total == 0 )); then
  echo "GATE G1 FAIL: no files collected from $SRC" >&2; gate_fail=1
fi
if (( cobol_n == 0 && jcl_n == 0 )); then
  echo "GATE G1 FAIL: no COBOL or JCL found — nothing to reverse-engineer" >&2; gate_fail=1
fi
if [[ "$(python3 -c "print(1 if float('$share') > float('$MAX_UNKNOWN_SHARE') else 0)")" == "1" ]]; then
  if (( FORCE )); then
    echo "GATE G1 WARN: unknown share $share exceeds $MAX_UNKNOWN_SHARE — proceeding due to --force" >&2
  else
    echo "GATE G1 FAIL: unknown share $share exceeds $MAX_UNKNOWN_SHARE — classify files or re-run with --force" >&2
    gate_fail=1
  fi
fi
(( gate_fail == 0 )) || exit 1

# ---------- zip ----------
rm -f "$OUT"
( cd "$STAGE" && zip -q -r "$OUT" . -x '.DS_Store' )

if command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$OUT" | awk '{print $1}' > "$OUT.sha256"
elif command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$OUT" | awk '{print $1}' > "$OUT.sha256"
else
  echo "unavailable" > "$OUT.sha256"
fi
SHA="$(cat "$OUT.sha256")"

echo "packaged: $OUT" >&2
echo "sha256:   $SHA" >&2
echo "inventory: $INVENTORY" >&2

# ---------- optional upload ----------
UPLOADED_KEY=""
if [[ -n "$UPLOAD" ]]; then
  [[ -n "$PROFILE" && -n "$REGION" ]] || { echo "ERROR: --upload requires --profile and --region" >&2; exit 2; }
  dest="${UPLOAD%/}/$(basename "$OUT")"
  AWS_PROFILE="$PROFILE" AWS_REGION="$REGION" aws s3 cp "$OUT" "$dest" --no-progress >&2
  UPLOADED_KEY="$dest"
  echo "uploaded: $dest" >&2
fi

GLOSSARY_PRESENT=false
[[ -f "$STAGE/glossary.csv" ]] && GLOSSARY_PRESENT=true

python3 - "$OUT" "$SHA" "$INVENTORY" "$total" "$unknown" "$share" "$UPLOADED_KEY" \
         "$GLOSSARY_PRESENT" "$N_cobol" "$N_jcl" "$N_copybooks" "$N_bms" "$N_cics" \
         "$N_db2" "$N_ims" "$N_pli" "$N_asm" "$N_scheduler" "$N_other" \
         "${N_data:-0}" "${N_docs:-0}" "${N_noise:-0}" <<'PY'
import json, sys
a = sys.argv[1:]
zip_path, sha, inv, total, unknown, share, uploaded, glossary = a[0:8]
keys = ("cobol", "jcl", "copybooks", "bms", "cics", "db2", "ims",
        "pli", "asm", "scheduler", "other")
counts = {k: int(v) for k, v in zip(keys, a[8:8 + len(keys)]) if int(v) > 0}
data_n, docs_n, noise_n = (int(x) for x in a[8 + len(keys):8 + len(keys) + 3])
print(json.dumps({
    "zip": zip_path, "sha256": sha, "inventory": inv,
    "inputArtifacts": int(total), "unknownFiles": int(unknown),
    "unknownShare": float(share), "counts": counts,
    "companions": {"data": data_n, "docs": docs_n, "noiseDropped": noise_n},
    "glossary": glossary == "true",
    "uploadedTo": uploaded or None,
    "gate": "G1 pass",
}, indent=2))
PY
