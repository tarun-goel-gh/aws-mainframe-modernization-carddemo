# Code intake

AWS Transform requires the source as a **single `.zip` in S3**. The `assetLocation` you submit
to the "Specify resource location" task must point at that zip, not a folder or a repo.

Intake quality sets the ceiling on output quality. Every downstream artifact — business rules,
requirements, traceability — derives from what lands in this zip.

## Mode selection

Ask if the user has not said. Never guess between these.

| Mode | Ask for | Notes |
|---|---|---|
| `github` | repo URL, ref/branch, optional subpath | shallow clone; strip `.git`; honor private-repo auth already on the machine |
| `s3zip` | full `s3://bucket/key.zip` | validate in place; **do not** repackage |
| `local` | path in the workspace (default: workspace root) | most common for demos and PoCs |

Record `state.source.mode` and `origin`.

### github

```
git clone --depth 1 --branch <ref> <url> <tmp>/src
rm -rf <tmp>/src/.git
scripts/package_source.sh --src <tmp>/src --out .atx/mfre/source.zip --app <name>
```

Confirm the ref actually cloned matches what the user asked for, and record the commit sha in
`state.source.origin` so the run is reproducible.

### s3zip

Do not rebuild someone else's package. Validate:

```
aws s3api head-object --bucket <b> --key <k> --profile <p> --region <r>
```

- Object exists and is a zip
- Lives in (or is copied into) the **connector's** bucket — a zip in an unrelated bucket is
  not readable by the job
- Inspect the listing (`unzip -l`) to record an inventory without extracting

If the layout is poor (flat dump, no recognizable extensions), say so and offer to repackage.
Note the tradeoff plainly: repackaging improves classification but changes what the customer
believes they submitted.

### local

Scan the workspace first and show the user what was found before packaging. Signals worth
reporting: counts by extension, presence of `EXEC CICS` / `EXEC SQL`, copybook coverage,
IMS/DB2 artifacts.

## Required zip layout

Organize by artifact type, then zip the top-level folder:

```
<app>.zip
├── app/
│   ├── cobol/        *.cbl *.cob *.cobol
│   ├── copybooks/    *.cpy
│   ├── jcl/          *.jcl *.prc *.proc *.inc *.ctl
│   ├── bms/          *.bms
│   ├── cics/         *.csd
│   ├── db2/          *.dcl *.sql *.ddl
│   ├── ims/          *.psb *.dbd *.ims *.mfs
│   ├── pli/          *.pl1 *.pl1_copy
│   ├── asm/          *.asm *.mac
│   ├── scheduler/    *.ca7 *.controlm
│   ├── other/        *.nat *.rex *.rexx *.ezt
│   ├── data/         *.ps *.dat  (data extracts, not source)
│   └── docs/         *.md *.pdf
├── glossary.csv          ← optional, high value
└── pdf_config.json       ← optional, only for PDF documentation styling
```

Subpaths inside each bucket are preserved, so same-named members of different libraries do not
collide.

`scripts/package_source.sh` builds exactly this and refuses to produce a zip that would fail
gate G1.

## Extension classification

Input artifacts — these count toward classification quality:

| Bucket | Extensions |
|---|---|
| `cobol` | `.cbl` `.cob` `.cobol` |
| `copybooks` | `.cpy` |
| `jcl` | `.jcl` `.prc` `.proc` `.inc` `.ctl` |
| `bms` | `.bms` |
| `cics` | `.csd` |
| `db2` | `.dcl` `.sql` `.ddl` |
| `ims` | `.psb` `.dbd` `.ims` `.mfs` |
| `pli` | `.pl1` `.pl1_copy` |
| `asm` | `.asm` `.mac` |
| `scheduler` | `.ca7` `.controlm` |
| `other` | `.nat` `.rex` `.rexx` `.ezt` |

Companions — shipped alongside, but **excluded** from the unknown-share metric:

| Bucket | Extensions | Why excluded |
|---|---|---|
| `data` | `.ps` `.dat` `.init` `.seq` `.vsam` | data extracts, not source; counting them makes a well-formed repo look badly classified |
| `docs` | `.md` `.pdf` | context only |
| `noise` | `.gitkeep` `.gitignore` `.DS_Store` | dropped entirely |

**Schedulers are real inputs, not noise.** CA-7 `LJOB` reports must use the `.ca7` extension
and carry ANSI carriage-control characters in column 1 (produced with `DCB=RECFM=FBA`). They
feed decomposition and test planning. Missing them from the classifier is easy to do and
silently discards supported input.

Unknown extension: leave it blank or `.txt` and Transform will classify it. Do **not** invent an
extension — a wrong one is worse than none. `.txt` therefore stays in the `UNKNOWN` bucket
rather than being guessed as data, because it represents classification work still outstanding.
Files landing as `UNKNOWN`/`TXT` can be reclassified after the initial analysis loop completes
by uploading a classification JSON, but only those two classes are reclassifiable.

The unknown share is computed over input artifacts only:
`UNKNOWN ÷ (all input buckets + UNKNOWN)`.

## glossary.csv — reference only, and label it as such

A two-column CSV of abbreviation → meaning in the **zip root**. It feeds documentation
generation and business rule extraction, so extracted rules use the customer's vocabulary
instead of guessed expansions.

```csv
<ABBREV>,<expansion>
ACCT,Account
XREF,Cross Reference
SWOT,"Strengths, Weaknesses, Opportunities and Threats"
```

Quote any value containing a comma.

### Provenance is mandatory

Record `state.source.glossaryProvenance` as one of:

| Value | Meaning |
|---|---|
| `user-supplied` | the customer authored or reviewed it |
| `auto-drafted-unverified` | this skill drafted it from identifiers in the source |
| `absent` | no glossary |

If absent, **auto-draft one** — a draft beats nothing, because extraction otherwise guesses
silently. Build it from high-frequency identifiers, dataset name fragments, and copybook field
prefixes.

An auto-drafted glossary is **reference material only** and must be labelled as such
everywhere it could influence a reader:

- `state.source.glossaryProvenance = "auto-drafted-unverified"`
- every function bundle's `function-metadata.json` → `provenance.glossaryNote`
- every function bundle's `README.md` under Caveats
- the run report's Run context section

`scripts/split_bundle.py` and `scripts/build_report.py` emit that caveat automatically from the
provenance field, so setting the field correctly is the whole job.

Never invent an expansion you cannot justify from the code. A wrong entry propagates into every
requirement touching the term, and an unlabelled wrong entry is worse than a missing one —
it reads as authoritative.

## Data and support artifacts

- **Data files** (VSAM extracts, flat files) may accompany the source and help data analysis.
- **SMF records** — only for activity metrics, which this skill does not run. If added later:
  separate S3 folder, raw binary EBCDIC with RDW, `.zip` ≤600 MB or `.tar.gz`/`.gz` ≤5 GB,
  ≥13 months recommended.
- **Test data** — separate folder; out of scope here.

## Upload

```
aws s3 cp <app>.zip s3://<connector-bucket>/<prefix>/<app>.zip --profile <p> --region <r> --no-progress
```

Then record in state: `zipKey`, `zipSha256`, per-type file counts, total LOC estimate,
`glossary` boolean. The sha256 is what lets a later run prove it is looking at the same input.

## Gate G1

- [ ] Zip exists in the connector bucket, key recorded
- [ ] At least one COBOL or JCL file present (otherwise nothing to reverse-engineer)
- [ ] Unknown share ≤ 10% of input artifacts, or the user explicitly accepted more (`--force`)
- [ ] Layout uses artifact-type subfolders
- [ ] Inventory + sha256 in state
- [ ] Glossary present, or its absence explicitly acknowledged

Report the inventory as a table before moving on. This is the user's last cheap chance to
notice a whole missing library — after discovery, correcting it means re-running analysis.
