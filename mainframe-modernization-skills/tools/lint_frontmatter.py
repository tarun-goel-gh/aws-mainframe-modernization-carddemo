#!/usr/bin/env python3
"""Validate SKILL.md front matter in src/ and in each built variant.

Usage: lint_frontmatter.py [--src-only]
Exit:  0 valid | 1 violations

Deliberately NOT checked: description wording or length. Tempting, but `description` is the surface both
Claude Code and Codex match a skill against, and a lint that nudges people to shorten it degrades
activation. The build already folds `compatibility` into it, which makes it longer on purpose.
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "skills")
DIST = os.path.join(ROOT, "dist")
RUNTIMES = os.path.join(ROOT, "runtimes")

sys.path.insert(0, os.path.join(ROOT, "tools"))
from build import load_recipe, split_frontmatter  # noqa: E402

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
TOKEN = re.compile(r"\{\{[A-Z_]+\}\}")
RUNTIME_LITERAL = re.compile(r"\.(?:kiro|claude|codex)/skills")

problems = []


def fail(where, message):
    problems.append(f"{where}: {message}")


def top_level(fm_lines):
    """Top-level key -> joined value, preserving nothing but the text."""
    out, current = {}, None
    for line in fm_lines:
        if not line.startswith((" ", "\t")) and ":" in line:
            key, _, value = line.partition(":")
            current = key.strip()
            out[current] = value.strip()
        elif current and line.strip():
            out[current] = (out[current] + " " + line.strip()).strip()
    return out


def nested_keys(fm_lines):
    """Set of dotted keys, one level deep — enough for metadata.*."""
    found, parent = set(), None
    for line in fm_lines:
        if not line.startswith((" ", "\t")) and ":" in line:
            parent = line.split(":", 1)[0].strip()
            found.add(parent)
        elif line.startswith((" ", "\t")) and ":" in line and parent:
            child = line.split(":", 1)[0].strip().lstrip("- ")
            found.add(f"{parent}.{child}")
    return found


def skill_files(root):
    if not os.path.isdir(root):
        return
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name, "SKILL.md")
        if os.path.isfile(path):
            yield name, path


def check_src():
    changelog = ""
    cl_path = os.path.join(ROOT, "CHANGELOG.md")
    if os.path.isfile(cl_path):
        changelog = open(cl_path, encoding="utf-8").read()

    skills = list(skill_files(SRC))
    if not skills:
        print("lint_frontmatter: src/skills has no SKILL.md — nothing to check")
        return

    for name, path in skills:
        rel = os.path.relpath(path, ROOT)
        text = open(path, encoding="utf-8").read()
        fm_lines, _ = split_frontmatter(text)
        if fm_lines is None:
            fail(rel, "no front matter, or it does not open on line 1")
            continue

        fm = top_level(fm_lines)
        keys = nested_keys(fm_lines)

        for required in ("name", "description"):
            if not fm.get(required):
                fail(rel, f"`{required}` is required by the Agent Skills standard and is missing/empty")

        if fm.get("name") and fm["name"] != name:
            fail(rel, f"`name` is {fm['name']!r} but the directory is {name!r} — "
                      "a mismatch makes the skill unloadable on some hosts")

        version = fm.get("metadata.version") or _find_nested(fm_lines, "metadata", "version")
        if version:
            v = version.strip().strip("\"'")
            if not SEMVER.match(v):
                fail(rel, f"metadata.version {v!r} is not semver")
            elif changelog and v not in changelog:
                fail(rel, f"metadata.version {v} does not appear in CHANGELOG.md — "
                          "a behaviour change must not ship unmentioned")
        else:
            fail(rel, "metadata.version is missing")

        # Runtime-specific paths must be tokens in source, or one variant silently stops working.
        for lineno, line in enumerate(text.splitlines(), 1):
            if RUNTIME_LITERAL.search(line):
                fail(f"{rel}:{lineno}",
                     "literal runtime skills path — use {{SKILLS_ROOT}}")

        _ = keys


def _find_nested(fm_lines, parent, child):
    in_parent = False
    for line in fm_lines:
        if not line.startswith((" ", "\t")):
            in_parent = line.split(":", 1)[0].strip() == parent
            continue
        if in_parent and ":" in line:
            k, _, v = line.partition(":")
            if k.strip() == child:
                return v.strip()
    return None


def check_variant(runtime):
    recipe_path = os.path.join(RUNTIMES, runtime, "runtime.yaml")
    if not os.path.isfile(recipe_path):
        return
    recipe = load_recipe(recipe_path)
    skills_path = (recipe.get("install") or {}).get("project_scope")
    fm_policy = recipe.get("frontmatter") or {}
    drops = fm_policy.get("drop") or []
    adds = fm_policy.get("add") or {}

    root = os.path.join(DIST, runtime, skills_path or "")
    skills = list(skill_files(root))
    if not skills:
        return

    for name, path in skills:
        rel = os.path.relpath(path, ROOT)
        text = open(path, encoding="utf-8").read()
        fm_lines, _ = split_frontmatter(text)
        if fm_lines is None:
            fail(rel, "no front matter in built variant")
            continue

        keys = nested_keys(fm_lines)
        fm = top_level(fm_lines)

        for dropped in drops:
            if dropped in keys:
                fail(rel, f"`{dropped}` should have been dropped for {runtime}")

        for key, value in (adds or {}).items():
            expected = value.get(name) if isinstance(value, dict) else value
            if expected is None:
                continue
            if key not in keys:
                fail(rel, f"`{key}` should have been added for {runtime}")
            elif fm.get(key) != str(expected):
                fail(rel, f"`{key}` is {fm.get(key)!r}, expected {str(expected)!r}")

        if not fm.get("description"):
            fail(rel, "`description` empty after the compatibility fold")

        if "compatibility" in drops and "Requirements:" not in fm.get("description", ""):
            fail(rel, "`compatibility` was dropped but its content is not in `description` — "
                      "the prerequisite gate was lost")

    # No unresolved tokens anywhere in the variant, not just in front matter.
    for dirpath, dirnames, filenames in os.walk(os.path.join(DIST, runtime)):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for fname in sorted(filenames):
            fpath = os.path.join(dirpath, fname)
            try:
                body = open(fpath, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for m in set(TOKEN.findall(body)):
                fail(os.path.relpath(fpath, ROOT), f"unresolved token {m}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-only", action="store_true")
    args = ap.parse_args()

    check_src()
    if not args.src_only:
        for runtime in sorted(os.listdir(RUNTIMES)):
            if os.path.isdir(os.path.join(RUNTIMES, runtime)):
                check_variant(runtime)

    for p in problems:
        print(f"  {p}")
    print(f"lint_frontmatter: {len(problems)} violation(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
