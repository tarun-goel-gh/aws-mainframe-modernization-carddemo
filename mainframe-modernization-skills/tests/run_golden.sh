#!/usr/bin/env bash
# Golden run: build the Kiro variant, document the synthetic fixture with it, and assert the recorded
# baseline plus determinism.
#
# Usage:
#   run_golden.sh              assert against tests/golden/baseline.txt
#   run_golden.sh --record     write baseline.txt from this run instead of asserting
#
# Exit: 0 pass | 1 assertion failed or run failed | 3 no fixture (skipped)
#
# The fixture's numbers are NOT the reference numbers from a real job. A small fixture grounds fewer
# sections, and that is correct — a generic tool should not carry one customer's figures in its test
# suite. See docs/BASELINES.md.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE="$REPO/tests/fixtures/mfre-synthetic"
GOLDEN_DIR="$REPO/tests/golden"
BASELINE="$GOLDEN_DIR/baseline.txt"
RECORD=0
[[ "${1:-}" == "--record" ]] && RECORD=1

if [[ ! -f "$FIXTURE/mfre/state.json" ]]; then
  echo "run_golden: no fixture at tests/fixtures/mfre-synthetic/mfre/state.json — skipping."
  echo "            See docs/BASELINES.md for the required shape and the cases it must exercise."
  exit 3
fi

WORK="$(mktemp -d -t atxgolden)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT INT TERM

# The pipeline resolves .atx/mfre AND app/ relative to the working directory, so the fixture is staged
# into a scratch workspace rather than the repository. A golden run must not write into the repo.
#
# The fixture is two-part on purpose: mfre/ is the upstream run, app/ is the application source that
# extract_evidence reads directly from the workspace. Without app/, the source-derived evidence (BMS
# maps, linkage, error handling) is silently absent and the baseline understates coverage.
mkdir -p "$WORK/.atx"
cp -R "$FIXTURE/mfre" "$WORK/.atx/mfre"
cp -R "$FIXTURE/app" "$WORK/app"

python3 "$REPO/tools/build.py" --runtime kiro --quiet || {
  echo "run_golden: build failed"; exit 1; }
SCRIPTS="$REPO/dist/kiro/.kiro/skills/atx-app-documentation/scripts"

run_once() {  # run_once <run-id>
  ( cd "$WORK" && bash "$SCRIPTS/run_pipeline.sh" --offline --force --run-id "$1" >"$WORK/$1.log" 2>&1 )
}

measure() {   # measure <run-id> -> "docs=N grounded=N absent=N notextracted=N statuses=... delivered=N/N"
  python3 - "$WORK/.atx/app-docs-$1" <<'PY'
import collections, json, os, re, sys
root = sys.argv[1]
man = os.path.join(root, "00-manifest")
rows = [l for l in open(os.path.join(man, "ledger.md"), encoding="utf-8")
        if re.match(r"^\| \d+ \|", l)]
g = a = n = 0
st = collections.Counter()
for line in rows:
    c = [x.strip() for x in line.strip().strip("|").split("|")]
    st[c[4]] += 1
    g += int(c[5]); a += int(c[6]); n += int(c[7])
m = json.load(open(os.path.join(man, "manifest.json"), encoding="utf-8"))
cov = m.get("coverage") or {}
app = (m.get("application") or {}).get("nameSource", "?")
print(f"docs={len(rows)}")
print(f"grounded={g}")
print(f"absent={a}")
print(f"notextracted={n}")
print("statuses=" + ",".join(f"{k}:{v}" for k, v in sorted(st.items())))
print(f"delivered={cov.get('delivered')}/{cov.get('discovered')}")
# Both the name and its source. Recording only the source would miss a regression in the derivation
# itself: a wrong name derived by the right mechanism still reports nameSource="derived from ...".
print(f"appName={(m.get('application') or {}).get('name')}")
print(f"appNameSource={app}")
PY
}

echo "run_golden: first run"
run_once A || { echo "run_golden: pipeline failed"; tail -20 "$WORK/A.log"; exit 1; }
echo "run_golden: second run, for determinism"
run_once B || { echo "run_golden: second pipeline run failed"; tail -20 "$WORK/B.log"; exit 1; }

ACTUAL="$(measure A)"

# Determinism over documents only. run-log.md and run-state.json carry wall-clock values, and
# manifest fields generatedAt/docsRoot are expected to differ.
if ! diff -r "$WORK/.atx/app-docs-A" "$WORK/.atx/app-docs-B" \
      -x '00-manifest' >/dev/null 2>&1; then
  echo "run_golden: FAIL — documents differ between two identical runs"
  diff -rq "$WORK/.atx/app-docs-A" "$WORK/.atx/app-docs-B" -x '00-manifest' | head -10
  exit 1
fi

# The archive must pass the disclosure gate. Phase 8 fails on a hit, so reaching here with a zip is
# the assertion; its absence means packaging refused.
if ! ls "$WORK/.atx/app-docs-A.zip" >/dev/null 2>&1; then
  echo "run_golden: FAIL — no archive produced; the disclosure gate may have refused to package"
  grep -i 'REFUSING' "$WORK/A.log" | head -5
  exit 1
fi

# The application name must be derived from the fixture, never a literal.
if grep -q 'appNameSource=operator-supplied' <<<"$ACTUAL"; then
  echo "run_golden: FAIL — fixture run should derive the app name, not receive one"
  exit 1
fi

if (( RECORD )); then
  mkdir -p "$GOLDEN_DIR"
  printf '%s\n' "$ACTUAL" > "$BASELINE"
  echo "run_golden: recorded baseline ->"
  sed 's/^/  /' "$BASELINE"
  exit 0
fi

if [[ ! -f "$BASELINE" ]]; then
  echo "run_golden: no baseline at tests/golden/baseline.txt — run with --record first."
  echo "run_golden: this run measured:"
  printf '%s\n' "$ACTUAL" | sed 's/^/  /'
  exit 1
fi

if diff <(printf '%s\n' "$ACTUAL") "$BASELINE" >/dev/null 2>&1; then
  echo "run_golden: PASS"
  printf '%s\n' "$ACTUAL" | sed 's/^/  /'
  exit 0
fi

echo "run_golden: FAIL — measurements differ from the recorded baseline"
echo "  expected (baseline)          actual (this run)"
diff -y <(cat "$BASELINE") <(printf '%s\n' "$ACTUAL") | sed 's/^/  /'
echo ""
echo "If this change is intended, re-record with --record and state the movement in CHANGELOG.md."
echo "docs/VERSIONING.md requires that: a document-content change without an evidence change is"
echo "indistinguishable from a regression otherwise."
exit 1
