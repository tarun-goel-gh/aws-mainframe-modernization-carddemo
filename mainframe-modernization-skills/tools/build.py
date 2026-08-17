#!/usr/bin/env python3
"""Build dist/<runtime>/ from src/skills/ + runtimes/<runtime>/.

Usage:
  build.py --all
  build.py --runtime claude-code
  build.py --all --quiet

Exit: 0 built | 1 build error | 2 bad usage

Why a build rather than three maintained copies: of the files under src/skills/, all but a handful are
byte-identical across runtimes. The real difference is a set of path and prose tokens, three
front-matter keys, and one MCP setup fragment. Three hand-maintained trees would drift over that.

THE INVARIANT: the build is deterministic. Same src/, same dist/, byte for byte. `make check-drift`
rebuilds and diffs against what is committed, and that is the only thing making committed generated
output safe. Hence sorted walks, no timestamps, no absolute paths in output.

No third-party dependencies, which rules out PyYAML — so the recipe files are read by a deliberately
small parser (`load_recipe`) that supports only the subset of YAML they use. That is a constraint on
the recipes, not a general YAML implementation, and it fails loudly on anything outside the subset.
"""
import argparse
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "skills")
RUNTIMES = os.path.join(ROOT, "runtimes")
DIST = os.path.join(ROOT, "dist")

# Never copied into a variant.
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}
EXCLUDE_EXTS = {".pyc", ".pyo"}

TOKEN_RE = re.compile(r"\{\{([A-Z_]+)\}\}")
INCLUDE_RE = re.compile(r"^[ \t]*<!--[ \t]*@include:[ \t]*([A-Za-z0-9_-]+)[ \t]*-->[ \t]*$",
                        re.MULTILINE)
# Substitution applies to text, not binaries. Everything here is text anyway; the guard is for safety.
TEXT_EXTS = {".md", ".py", ".sh", ".json", ".yaml", ".yml", ".toml", ".txt", ".csv", ".cfg"}


# ---------------------------------------------------------------- recipe parsing

def load_recipe(path):
    """Parse the subset of YAML the runtime recipes use.

    Supports: nested mappings by indentation, `- ` sequences, scalars, quoted strings, comments,
    booleans, null, and inline `{}`/`[]` empties. Anything else raises, because a recipe that silently
    half-parses would produce a variant that is wrong in a way nobody notices.
    """
    root = {}
    stack = [(-1, root)]

    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue

            indent = len(line) - len(line.lstrip(" "))
            body = line.strip()

            # Strip trailing comments, but not a '#' inside quotes.
            if "#" in body:
                in_s = in_d = False
                for i, ch in enumerate(body):
                    if ch == "'" and not in_d:
                        in_s = not in_s
                    elif ch == '"' and not in_s:
                        in_d = not in_d
                    elif ch == "#" and not in_s and not in_d:
                        body = body[:i].rstrip()
                        break
            if not body:
                continue

            while stack and indent <= stack[-1][0]:
                stack.pop()
            if not stack:
                raise ValueError(f"{path}:{lineno}: indentation underflow")
            parent = stack[-1][1]

            if body.startswith("- "):
                # A _Pending is valid here: it creates its list on first append, which is how a
                # `key:` followed by `- item` lines becomes a sequence rather than a mapping.
                if not isinstance(parent, (list, _Pending)):
                    raise ValueError(f"{path}:{lineno}: sequence item outside a sequence")
                parent.append(_scalar(body[2:].strip()))
                continue

            if ":" not in body:
                raise ValueError(f"{path}:{lineno}: expected 'key: value' — got {body!r}")

            key, _, value = body.partition(":")
            key, value = key.strip(), value.strip()

            if value in ("", "|", ">"):
                # A nested block follows. Peek is unnecessary: the next line's indentation decides
                # whether this becomes a mapping or a sequence.
                container = _Pending(key, parent)
                stack.append((indent, container))
                continue

            # Pass the parent itself, not parent.container: a _Pending creates its container lazily on
            # first assignment, and reaching past it yields None before that has happened.
            _assign(parent, key, _scalar(value))

    return _materialise(root)


class _Pending:
    """A key whose child container type is not yet known."""

    def __init__(self, key, parent):
        self.key = key
        self.parent = parent
        self.container = None

    def append(self, item):
        if self.container is None:
            self.container = []
            _assign_parent(self)
        self.container.append(item)

    def __setitem__(self, key, value):
        if self.container is None:
            self.container = {}
            _assign_parent(self)
        self.container[key] = value


def _assign_parent(pending):
    target = pending.parent
    if isinstance(target, _Pending):
        target[pending.key] = pending.container
    else:
        _assign(target, pending.key, pending.container)


def _assign(obj, key, value):
    if isinstance(obj, _Pending):
        obj[key] = value
    elif isinstance(obj, dict):
        obj[key] = value
    else:
        raise ValueError(f"cannot assign {key!r} into {type(obj).__name__}")


def _materialise(obj):
    if isinstance(obj, _Pending):
        return _materialise(obj.container if obj.container is not None else {})
    if isinstance(obj, dict):
        return {k: _materialise(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_materialise(v) for v in obj]
    return obj


def _scalar(text):
    if text in ("{}", "[]"):
        return {} if text == "{}" else []
    if text in ("null", "~", ""):
        return None
    if text in ("true", "True"):
        return True
    if text in ("false", "False"):
        return False
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


# ---------------------------------------------------------------- front matter

def split_frontmatter(text):
    """Return (frontmatter_lines, body). Front matter must open on the very first line."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 3)
    if end == -1:
        return None, text
    return text[4:end + 1].splitlines(), text[end + 5:]


def drop_keys(fm_lines, drops):
    """Remove top-level and dotted keys, preserving the order and formatting of what remains.

    Line-based on purpose. Round-tripping through a parser would reflow `description`, and both
    Claude Code and Codex match a skill against that text — reflowing it changes activation behaviour.
    """
    top = {d for d in drops if "." not in d}
    nested = {}
    for d in drops:
        if "." in d:
            parent, _, child = d.partition(".")
            nested.setdefault(parent, set()).add(child)

    out = []
    skip_block = None          # top-level key whose continuation lines are being dropped
    current_parent = None      # top-level key currently open, for nested drops

    for line in fm_lines:
        indented = line.startswith((" ", "\t"))

        if not indented and ":" in line:
            key = line.split(":", 1)[0].strip()
            current_parent = key
            if key in top:
                skip_block = key
                continue
            skip_block = None
            out.append(line)
            continue

        if not indented and line.strip() and skip_block:
            # A non-key line at column 0 ends the dropped block.
            skip_block = None

        if skip_block:
            continue

        if indented and current_parent in nested and ":" in line:
            child = line.split(":", 1)[0].strip().lstrip("- ")
            if child in nested[current_parent]:
                continue

        out.append(line)
    return out


def fold_compatibility(fm_lines):
    """Move `compatibility` into `description` for runtimes that do not support the key.

    Not a cosmetic move. `compatibility` states the prerequisites, and on Claude Code and Codex
    `description` is the only text the runtime reads when deciding whether to load a skill. Dropping
    the key without folding it would let an agent begin a run whose preconditions are absent.
    """
    compat = _collect_value(fm_lines, "compatibility")
    if not compat:
        return fm_lines

    out = []
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        if not line.startswith((" ", "\t")) and line.split(":", 1)[0].strip() == "description":
            desc, consumed = _collect_block(fm_lines, i)
            merged = f"{desc.rstrip().rstrip('.')}. Requirements: {compat}"
            out.append("description: " + _fold(merged, indent=2))
            i += consumed
            continue
        out.append(line)
        i += 1
    return out


def _collect_value(fm_lines, key):
    for i, line in enumerate(fm_lines):
        if not line.startswith((" ", "\t")) and line.split(":", 1)[0].strip() == key:
            value, _ = _collect_block(fm_lines, i)
            return value.strip()
    return None


def _collect_block(fm_lines, start):
    """Value at fm_lines[start], joining any indented continuation lines. Returns (value, n_lines)."""
    first = fm_lines[start].split(":", 1)[1].strip()
    parts = [first] if first not in ("", "|", ">") else []
    n = 1
    while start + n < len(fm_lines) and fm_lines[start + n].startswith((" ", "\t")):
        parts.append(fm_lines[start + n].strip())
        n += 1
    return " ".join(p for p in parts if p), n


def _fold(text, indent=2, width=100):
    """Wrap a long scalar as a YAML continuation block. Deterministic given the same input."""
    words = text.split()
    lines, current = [], ""
    for w in words:
        candidate = f"{current} {w}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = w
        else:
            current = candidate
    if current:
        lines.append(current)
    pad = " " * indent
    return ("\n" + pad).join(lines)


def add_keys(fm_lines, additions, skill):
    """Append runtime-specific keys. Values may be a scalar or a per-skill mapping."""
    out = list(fm_lines)
    for key, value in (additions or {}).items():
        if isinstance(value, dict):
            if skill not in value:
                continue
            resolved = value[skill]
        else:
            resolved = value
        if resolved is None:
            continue
        out.append(f"{key}: {resolved}")
    return out


# ---------------------------------------------------------------- transforms

def substitute(text, tokens, where):
    out = TOKEN_RE.sub(lambda m: tokens.get(m.group(1), m.group(0)), text)
    leftover = sorted(set(TOKEN_RE.findall(out)))
    if leftover:
        # A silently unsubstituted token becomes a literal `{{...}}` in a shipped instruction.
        raise ValueError(f"{where}: unresolved token(s): {', '.join(leftover)}")
    return out


def apply_includes(text, fragments, where, used):
    def repl(match):
        name = match.group(1)
        if name not in fragments:
            raise ValueError(f"{where}: @include '{name}' has no fragment for this runtime")
        used.add(name)
        return fragments[name].rstrip("\n")

    return INCLUDE_RE.sub(repl, text)


# ---------------------------------------------------------------- build

def load_fragments(runtime_dir):
    out = {}
    frag_dir = os.path.join(runtime_dir, "fragments")
    if not os.path.isdir(frag_dir):
        return out
    for name in sorted(os.listdir(frag_dir)):
        if name.endswith(".md"):
            with open(os.path.join(frag_dir, name), encoding="utf-8") as fh:
                out[name[:-3]] = fh.read()
    return out


def build_runtime(runtime, quiet=False):
    runtime_dir = os.path.join(RUNTIMES, runtime)
    recipe_path = os.path.join(runtime_dir, "runtime.yaml")
    if not os.path.isfile(recipe_path):
        raise ValueError(f"no recipe at {recipe_path}")

    recipe = load_recipe(recipe_path)
    install = recipe.get("install") or {}
    skills_path = install.get("project_scope")
    if not skills_path:
        raise ValueError(f"{runtime}: install.project_scope is required")

    tokens = dict(recipe.get("tokens") or {})
    tokens.update(recipe.get("prose_tokens") or {})
    fm_policy = recipe.get("frontmatter") or {}
    drops = fm_policy.get("drop") or []
    adds = fm_policy.get("add") or {}
    fragments = load_fragments(runtime_dir)
    used_fragments = set()

    out_root = os.path.join(DIST, runtime)
    if os.path.isdir(out_root):
        shutil.rmtree(out_root)
    skills_out = os.path.join(out_root, skills_path)
    os.makedirs(skills_out, exist_ok=True)

    n_files = 0
    for dirpath, dirnames, filenames in os.walk(SRC):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_NAMES)
        rel_dir = os.path.relpath(dirpath, SRC)
        target_dir = skills_out if rel_dir == "." else os.path.join(skills_out, rel_dir)
        os.makedirs(target_dir, exist_ok=True)

        # Which skill this file belongs to, for per-skill front-matter additions.
        skill = rel_dir.split(os.sep)[0] if rel_dir != "." else None

        for name in sorted(filenames):
            if name in EXCLUDE_NAMES or os.path.splitext(name)[1] in EXCLUDE_EXTS:
                continue
            src_file = os.path.join(dirpath, name)
            dst_file = os.path.join(target_dir, name)
            rel_display = os.path.join(rel_dir, name) if rel_dir != "." else name

            if os.path.splitext(name)[1] not in TEXT_EXTS:
                shutil.copyfile(src_file, dst_file)
                n_files += 1
                continue

            with open(src_file, encoding="utf-8") as fh:
                text = fh.read()

            text = apply_includes(text, fragments, rel_display, used_fragments)

            if name == "SKILL.md":
                fm_lines, body = split_frontmatter(text)
                if fm_lines is None:
                    raise ValueError(f"{rel_display}: SKILL.md has no front matter")
                if "compatibility" in drops:
                    fm_lines = fold_compatibility(fm_lines)
                fm_lines = drop_keys(fm_lines, drops)
                fm_lines = add_keys(fm_lines, adds, skill)
                text = "---\n" + "\n".join(fm_lines) + "\n---\n" + body

            text = substitute(text, tokens, rel_display)

            with open(dst_file, "w", encoding="utf-8") as fh:
                fh.write(text)
            shutil.copymode(src_file, dst_file)
            n_files += 1

    unused = sorted(set(fragments) - used_fragments)
    if unused and not quiet:
        print(f"  note: fragment(s) never included: {', '.join(unused)}")

    # MCP config, for the runtimes that ship one. Kiro does not: the Power supplies the server.
    mcp = recipe.get("mcp") or {}
    if mcp.get("ships_config"):
        src_cfg = os.path.join(runtime_dir, mcp["config_source"])
        dst_cfg = os.path.join(out_root, mcp["config_dest"])
        os.makedirs(os.path.dirname(dst_cfg), exist_ok=True)
        shutil.copyfile(src_cfg, dst_cfg)
        n_files += 1

    if not quiet:
        print(f"  {runtime:14} {n_files:3} file(s) -> dist/{runtime}/{skills_path}")
    return n_files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true")
    g.add_argument("--runtime")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(SRC) or not os.listdir(SRC):
        print("build: src/skills is empty — nothing to build", file=sys.stderr)
        return 1

    runtimes = (sorted(d for d in os.listdir(RUNTIMES)
                       if os.path.isfile(os.path.join(RUNTIMES, d, "runtime.yaml")))
                if args.all else [args.runtime])

    if not args.quiet:
        print("building:")
    try:
        for runtime in runtimes:
            build_runtime(runtime, quiet=args.quiet)
    except (ValueError, OSError) as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
