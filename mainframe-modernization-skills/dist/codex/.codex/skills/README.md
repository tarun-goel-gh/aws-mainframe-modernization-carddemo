# Mainframe modernization skills

Five skills that take a mainframe codebase through AWS Transform reverse engineering and out the
other side as a 31-document application knowledge base.

```
COBOL/JCL source
      │
      ▼
┌─────────────────────────────┐
│ mainframe-reverse-engineering│  drives AWS Transform: intake, discovery,
│                             │  business-logic extraction, requirements
└─────────────────────────────┘
      │  .atx/mfre/  (state.json, specs/, analysis/, discovery/)
      ▼
┌─────────────────────────────┐
│ atx-app-documentation       │  the documentation model: 31 documents,
│                             │  grounding contract, coverage matrix
└─────────────────────────────┘
      │  .atx/app-docs-<run-id>/  +  .zip
      ▼
   published deliverable
```

The two skills above hold all the behaviour. The three below are entry points — thin wrappers that
give an action a name a user can invoke.

| Skill | Invoke when |
|---|---|
| [`mainframe-reverse-engineering`](mainframe-reverse-engineering/README.md) | reverse engineering, assessing or decomposing a mainframe with AWS Transform |
| [`atx-app-documentation`](atx-app-documentation/README.md) | you need the documentation model itself: what the 31 documents are, how grounding works |
| [`atx-pipeline`](atx-pipeline/README.md) | **run the whole thing** end to end, fetch → documents → published zip |
| [`atx-generate-docs`](atx-generate-docs/README.md) | generate documents from an MFRE run that already exists locally |
| [`atx-docs-status`](atx-docs-status/README.md) | ask what is documented, what is missing, what is stale |

`z-app-documentation` is a separate lineage: the same 31-document model sourced from Bob IDE and the
Z Premium Package instead of AWS Transform. It shares no code with the `atx-*` skills and is not part
of this workflow.

---

## Which one do I want?

- **Starting from source, nothing run yet** → `mainframe-reverse-engineering`
- **AWS Transform job finished, want documents** → `atx-pipeline`
- **`.atx/mfre/` already local, just re-generate** → `atx-pipeline --offline`, or `/generate-docs`
- **Want to know coverage before spending time** → `/docs-status`
- **Understanding *why* a document says "Not available"** → `atx-app-documentation`, grounding contract

---

## Layout

```
.codex/skills/
├── README.md                        this file
├── MIGRATION.md                     porting the suite to Claude Code / Codex
├── mainframe-reverse-engineering/
│   ├── SKILL.md                     behaviour, gates G0-G4, rules
│   ├── README.md
│   ├── references/                  6 files: preflight, intake, discovery,
│   │                                extraction, hitl-tasks, state-and-reporting
│   └── scripts/                     7 executables
├── atx-app-documentation/
│   ├── SKILL.md                     the 9-step documentation pipeline
│   ├── README.md
│   ├── references/
│   │   ├── prompts/                 31 document templates
│   │   ├── document-catalog.md       the 31 documents, levels L0-L8
│   │   ├── grounding-contract.md     provenance vocabulary, honesty rules
│   │   ├── evidence-plans.md         9 atx-* evidence plans
│   │   ├── atx-substitutions.md
│   │   └── template-families.md      3 section-set families A/B/C
│   └── scripts/
│       ├── run_pipeline.sh          the 9-phase driver
│       ├── build_coverage.py        prerequisite gate + coverage matrix
│       ├── extract_evidence.py      one pass over shared artifacts
│       └── generate_docs.py         compose, self-check, file
├── atx-pipeline/                    entry point + workflow README
├── atx-generate-docs/               entry point
└── atx-docs-status/                 entry point
```

Output never lands in a skill folder. Everything is written under `.atx/`, which is gitignored:

```
.atx/mfre/                       the reverse-engineering run
.atx/app-docs-<YYYYMMDD-HHMMSS>/ one documentation run
.atx/app-docs-<...>.zip          the deliverable
.atx/app-docs-latest ──────────► the newest run
```

---

## Shared conventions

**Nothing provisions AWS.** Both skills verify preconditions and refuse to proceed; neither creates
a Transform workspace, a connector, or a Neptune cluster.

**Scope is enforced, not assumed.** `verify_spec.py` and `split_bundle.py` compare what was
delivered against what was *discovered* and fail when they differ. A bundle that looks complete on
its own terms still fails if functions are missing from the estate.

**Two distinct absence markers.** `Not available from AWS Transform analysis` means the evidence does
not exist. `Not extracted by this run` means it exists and the generator did not parse it. Collapsing
them would blame the evidence source for the tooling's gaps.

**Deterministic output.** Identical inputs produce byte-identical documents. Wall-clock fields are
confined to `generatedAt`, `docsRoot`, `run-log.md` and `run-state.json`.

**macOS bash 3.2.** No associative arrays, no `${var,,}`. The shell scripts are written to that
floor because it is what ships on macOS.

**Always pass `--profile` explicitly.** A shell with an empty `AWS_PROFILE` silently falls back to
the default profile, which is usually expired, and the resulting `ExpiredToken` looks like anything
but its actual cause.

---

## Provenance

This tree is **generated**. It is built from a single runtime-neutral source by the
`mainframe-modernization-skills` repository, which publishes a variant per supported agent runtime
from that same source.

Do not edit these files in place. An edit here is lost the next time the suite is reinstalled, and it
reaches nobody else. Change the source and rebuild.

Everything the skills write goes under `.atx/`, which should stay out of version control: run output
carries the AWS account id, bucket names and customer program names.
