#!/usr/bin/env python3
"""Verify relative Markdown links resolve, and code fences balance.

Cheap, and it catches the most common rot in a documentation set that cross-references itself. Absolute
URLs are not fetched — this is a structural check, not a link checker.

Usage: check_links.py [path ...]     default: docs README.md CHANGELOG.md src runtimes
Exit:  0 clean | 1 problems
"""
import os
import re
import sys

REL_LINK = re.compile(r"\]\((\.\.?/[^)#\s]+)")
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".atx"}
DEFAULT_ROOTS = ["docs", "README.md", "CHANGELOG.md", "src", "runtimes", "templates"]


def markdown_files(roots):
    for root in roots:
        if not os.path.exists(root):
            continue
        if os.path.isfile(root):
            if root.endswith(".md"):
                yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if name.endswith(".md"):
                    yield os.path.join(dirpath, name)


def main() -> int:
    roots = sys.argv[1:] or DEFAULT_ROOTS
    problems = 0
    checked = 0

    for path in sorted(markdown_files(roots)):
        checked += 1
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()

        if text.count("```") % 2:
            print(f"  {path}: unbalanced code fence")
            problems += 1

        base = os.path.dirname(path)
        for link in REL_LINK.findall(text):
            target = os.path.normpath(os.path.join(base, link))
            if not os.path.exists(target):
                print(f"  {path}: broken relative link -> {link}")
                problems += 1

    print(f"check_links: {checked} document(s) checked, {problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
