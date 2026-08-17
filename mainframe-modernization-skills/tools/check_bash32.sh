#!/usr/bin/env bash
# Fail if any shell script uses a bash 4 construct. macOS ships bash 3.2, which is the floor.
#
# This is not pedantry. `${req,,}` shipped in a real script and produced a `bad substitution` that
# aborted the enclosing compound command, so `usage` never ran and a MISSING REQUIRED ARGUMENT did not
# stop the script. `bash -n` parses the construct without complaint and it fails only when the branch
# executes, so a syntax check does not catch it.
#
# Comments are stripped before matching. The first version of this check flagged three comments that
# explained the rule, and a lint that cries wolf gets ignored.
#
# Usage: check_bash32.sh [path ...]     default: src/skills tools tests
# Exit:  0 clean | 1 a construct was found

set -uo pipefail

PATHS=("$@")
if [[ ${#PATHS[@]} -eq 0 ]]; then
  PATHS=(src/skills tools tests)
fi

EXISTING=()
for p in "${PATHS[@]}"; do
  [[ -e "$p" ]] && EXISTING+=("$p")
done
if [[ ${#EXISTING[@]} -eq 0 ]]; then
  echo "check_bash32: nothing to scan (no such paths yet)"
  exit 0
fi

python3 - "${EXISTING[@]}" <<'PY'
import os, re, sys

# Each pattern is a construct bash 3.2 does not have.
CONSTRUCTS = [
    (re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*,,\}"),   "${var,,} lowercase expansion"),
    (re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\^\^\}"), "${var^^} uppercase expansion"),
    (re.compile(r"\bdeclare\s+-A\b"),                  "declare -A associative array"),
    (re.compile(r"\blocal\s+-A\b"),                    "local -A associative array"),
    (re.compile(r"\bmapfile\b"),                       "mapfile"),
    (re.compile(r"\breadarray\b"),                     "readarray"),
]

# This checker necessarily contains the constructs it looks for, as pattern literals. Scanning itself
# would report six findings that are not defects — the same cry-wolf failure the comment stripping
# above exists to prevent.
SELF = "check_bash32.sh"

files = []
for root in sys.argv[1:]:
    if os.path.isfile(root):
        if root.endswith(".sh") and os.path.basename(root) != SELF:
            files.append(root)
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__", "node_modules"}]
        files.extend(os.path.join(dirpath, f) for f in filenames
                     if f.endswith(".sh") and f != SELF)

hits = 0
for path in sorted(files):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            # Drop whole-line and trailing comments. Naive about '#' inside quotes, which is
            # acceptable: the cost is a missed detection in a rare case, not a false alarm.
            code = line.split("#", 1)[0]
            if not code.strip():
                continue
            for pattern, label in CONSTRUCTS:
                m = pattern.search(code)
                if m:
                    print(f"  {path}:{lineno}  {label}  ->  {m.group(0)}")
                    hits += 1

print(f"check_bash32: {len(files)} script(s) scanned, {hits} bash-4 construct(s)")
sys.exit(1 if hits else 0)
PY
