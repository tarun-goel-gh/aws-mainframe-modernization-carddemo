# mainframe-modernization-skills
#
# One source in src/, three published variants in dist/. Everything here is deterministic: the same
# src/ must always produce the same dist/, which is what lets CI verify the committed output.

SHELL      := /bin/bash
RUNTIMES   := kiro claude-code codex
PYTHON     ?= python3
# Where `make dev` drops the Kiro variant for dogfooding. Defaults to the parent workspace.
DEV_TARGET ?= ..

.DEFAULT_GOAL := help

.PHONY: help build clean check check-drift check-scripts check-bash32 check-frontmatter \
        check-secrets check-links check-generic test dev dist-clean

help: ## Show this help
	@# [a-z0-9-] not [a-z-]: without the digits this silently omitted check-bash32, hiding a gate.
	@grep -hE '^[a-z0-9-]+:.*?## ' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n",$$1,$$2}'

build: ## Generate dist/ for every runtime from src/ + runtimes/
	@$(PYTHON) tools/build.py --all

dist-clean: ## Remove generated output
	@rm -rf dist/*/ && echo "dist/ cleared"

clean: dist-clean ## Remove generated output and Python residue
	@find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

# ---------------------------------------------------------------- checks

check: check-scripts check-bash32 check-frontmatter check-generic check-secrets \
       check-links check-drift ## Run every gate CI runs
	@echo "all checks passed"

check-drift: ## dist/ must match a fresh build — catches hand-edited variants
	@# Two distinct questions. First: is the build deterministic? That needs no git and is checked by
	@# rebuilding over a snapshot. Second: does COMMITTED dist/ match a fresh build? That needs git,
	@# and `git diff` on an untracked tree exits 0 — so without the tracking check below this target
	@# reported success while verifying nothing at all.
	@rm -rf .drift-snapshot && cp -R dist .drift-snapshot
	@$(PYTHON) tools/build.py --all --quiet
	@diff -r .drift-snapshot dist >/dev/null 2>&1 \
	  || { echo "ERROR: the build is not deterministic — two runs of build.py differ."; \
	       diff -rq .drift-snapshot dist | head -10; rm -rf .drift-snapshot; exit 1; }
	@rm -rf .drift-snapshot
	@echo "  determinism ok: two builds of src/ are byte-identical"
	@git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
	  || { echo "ERROR: not a git repository, so committed dist/ cannot be verified. Run 'git init'."; exit 1; }
	@test -n "$$(git ls-files dist/)" \
	  || { echo "ERROR: dist/ is not tracked by git, so drift cannot be detected."; \
	       echo "       'git diff' exits 0 on untracked files and this check would pass vacuously."; \
	       echo "       Commit dist/ (it is deliberately not gitignored) and re-run."; exit 1; }
	@git diff --exit-code -- dist/ \
	  || { echo "ERROR: dist/ differs from a fresh build. Edit src/, never dist/."; exit 1; }
	@echo "drift ok: build is deterministic and committed dist/ matches"

check-scripts: ## Python compiles, shell parses
	@$(PYTHON) -m compileall -q src/skills tools >/dev/null
	@for f in $$(find src/skills tools -name '*.sh'); do bash -n "$$f" || exit 1; done
	@echo "scripts ok"

check-bash32: ## No bash 4 constructs; macOS ships bash 3.2
	@bash tools/check_bash32.sh

check-frontmatter: ## SKILL.md front matter valid, and no Kiro-only keys in other variants
	@$(PYTHON) tools/lint_frontmatter.py

check-secrets: ## No credentials or principal identity anywhere in the repo
	@$(PYTHON) tools/scan_secrets.py .

check-generic: ## No customer-specific identifiers outside docs/EXAMPLES.md
	@$(PYTHON) tools/scan_secrets.py --generic src runtimes templates tools

check-links: ## Relative links in Markdown resolve
	@$(PYTHON) tools/check_links.py

test: ## Golden run against the synthetic fixture
	@# Exit 3 means "no fixture, skipped" and must not fail the target — otherwise the absence of a
	@# fixture is indistinguishable from a failing test.
	@bash tests/run_golden.sh; rc=$$?; \
	  if [ $$rc -eq 3 ]; then echo "test: skipped"; exit 0; else exit $$rc; fi

# ---------------------------------------------------------------- dev

dev: ## Build the Kiro variant straight into $(DEV_TARGET)/.kiro/skills
	@$(PYTHON) tools/build.py --runtime kiro
	@mkdir -p $(DEV_TARGET)/.kiro/skills
	@cp -R dist/kiro/.kiro/skills/. $(DEV_TARGET)/.kiro/skills/
	@echo "kiro variant installed into $(DEV_TARGET)/.kiro/skills"
