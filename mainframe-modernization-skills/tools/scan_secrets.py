#!/usr/bin/env python3
"""Fail if credential material, principal identity, or customer specifics are committed.

Two modes, because they answer different questions:

  default     Secrets and identity that must never appear anywhere. A published archive once carried
              an assumed-role ARN including an SSO permission set name and a corporate email address,
              so this runs over the whole repository including fixtures.

  --generic   Customer-specific identifiers that must not appear in the SOURCE. Worked examples
              naming a real job, bucket or program belong in docs/EXAMPLES.md, where they are clearly
              examples. This mode is scoped to src/, runtimes/, templates/, tools/ and tests/.

The AWS account id is in the --generic list, not the default list. It legitimately appears in
generated documents and in docs/EXAMPLES.md; what must never happen is a script or template carrying
one.

Usage:
  scan_secrets.py [--generic] [path ...]
Exit: 0 clean | 1 findings | 2 bad usage
"""
import argparse
import os
import re
import sys

# Never acceptable anywhere in the repository.
# Every pattern requires a plausible VALUE, not merely the key name. Documentation that names
# `X-Amz-Security-Token=` while explaining this scanner must not trip it — otherwise the scanner
# reports its own docs, gets muted, and stops protecting anything.
SECRET_PATTERNS = [
    (re.compile(r"arn:aws:(?:sts|iam)::\d{12}:(?:assumed-role|user)/[A-Za-z0-9_+=,.@:/-]+"),
     "IAM/STS principal identity"),
    (re.compile(r"\bASIA[0-9A-Z]{16}\b"), "temporary access key id"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "long-term access key id"),
    (re.compile(r"X-Amz-Security-Token=[A-Za-z0-9%/+_-]{20,}"), "presigned URL session token"),
    (re.compile(r"X-Amz-Signature=[a-f0-9]{32,}"), "presigned URL signature"),
    (re.compile(r"aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{30,}"),
     "secret key assignment"),
    (re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"), "private key"),
    # A corporate address is a person's identity, not configuration. Placeholder and example domains
    # are exempt so templates and documentation can show the shape.
    (re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.(?:com|org)\b|company\.com\b|localhost\b)"
                r"[A-Za-z0-9-]+\.[A-Za-z]{2,}\b"),
     "email address"),
]

# Not acceptable in source; fine in docs/EXAMPLES.md.
# Identifiers that are self-evidently placeholders. A 12-digit number or UUID made of one repeated
# character cannot be a real account or resource, and neither can AWS's documented example account.
# Without this, a synthetic fixture using 222222222222 is indistinguishable from a leak, and the usual
# resolution — exempting the fixture directory — would remove the check exactly where it matters most.
PLACEHOLDER = re.compile(
    r"^(?:123456789012"                       # AWS documentation example account
    r"|(\d)\1{11}"                            # 12 identical digits
    r"|([0-9a-f])\2{7}-(?:([0-9a-f])\3{3}-){3}([0-9a-f])\4{11}"  # UUID of one repeated hex digit
    r"|0{8}-0{4}-0{4}-0{4}-0{12})$",
    re.I,
)

GENERIC_PATTERNS = [
    (re.compile(r"\b\d{12}\b"), "bare 12-digit AWS account id"),
    (re.compile(r"\bace-(?:modernization|prod)[a-z0-9-]*\b", re.I), "customer bucket or profile name"),
    (re.compile(r"\bCardDemo\b|\bcarddemo\b"), "customer application name"),
    (re.compile(r"\b(?:COACTUP|COACTVW|CBPAUP0[A-Z]|COTRTUPC|CBSTM03A|CBTRN03C)\b"),
     "customer program name"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"),
     "job or workspace UUID"),
]

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".atx", "dist"}
SKIP_FILES = {"SHA256SUMS"}

# Deny-list, not an allow-list. An allow-list of text extensions is a blind spot by construction: the
# file that actually leaked was `.phase-preflight.out`, and an extension allow-list skipped it. Scan
# everything that is not demonstrably binary, and sniff for NUL bytes to catch the rest.
SKIP_EXTS = {
    ".zip", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".tar", ".jar", ".class",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".pdf",
    ".woff", ".woff2", ".ttf", ".eot", ".so", ".dylib", ".dll", ".pyc", ".o", ".a",
}

# Lines carrying this marker are exempt. Used for the placeholder-shaped strings a template needs.
ALLOW_MARKER = "scan-secrets: allow"

MAX_BYTES = 2 * 1024 * 1024


def is_probably_binary(path) -> bool:
    """NUL in the first chunk. Cheap, and enough to skip what the extension list misses."""
    try:
        with open(path, "rb") as fh:
            return b"\0" in fh.read(4096)
    except OSError:
        return True


def iter_files(roots):
    for root in roots:
        if os.path.isfile(root):
            yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in sorted(filenames):
                if name in SKIP_FILES:
                    continue
                if os.path.splitext(name)[1].lower() in SKIP_EXTS:
                    continue
                path = os.path.join(dirpath, name)
                if is_probably_binary(path):
                    continue
                yield path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--generic", action="store_true",
                    help="scan for customer-specific identifiers instead of secrets")
    ap.add_argument("paths", nargs="*", default=["."])
    args = ap.parse_args()

    roots = args.paths or ["."]
    patterns = GENERIC_PATTERNS if args.generic else SECRET_PATTERNS
    label = "generic" if args.generic else "secrets"

    # This file necessarily contains the strings it searches for, as pattern literals. Scanning itself
    # reports findings that are not defects, and a scanner that reports itself gets muted.
    self_path = os.path.abspath(__file__)

    findings = []
    scanned = 0
    for path in sorted(iter_files(roots)):
        if os.path.abspath(path) == self_path:
            continue
        # docs/EXAMPLES.md is where customer-specific illustrations are allowed to live.
        if args.generic and os.path.basename(path) == "EXAMPLES.md":
            continue
        try:
            if os.path.getsize(path) > MAX_BYTES:
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        scanned += 1
        for lineno, line in enumerate(lines, 1):
            if ALLOW_MARKER in line:
                continue
            for pattern, desc in patterns:
                m = pattern.search(line)
                if m and not PLACEHOLDER.match(m.group(0)):
                    findings.append((path, lineno, desc, m.group(0)[:48]))

    for path, lineno, desc, sample in findings:
        # The matched text is truncated rather than printed whole: a scanner that echoes a secret in
        # CI logs has moved the problem rather than solved it.
        print(f"  {path}:{lineno}  {desc}  [{sample[:12]}…]")

    print(f"scan_secrets({label}): {scanned} file(s) scanned, {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
