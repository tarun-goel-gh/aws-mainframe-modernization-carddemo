# Worked examples

The one place in this repository where customer-specific identifiers are allowed. `make check-generic`
scans `src/`, `runtimes/`, `templates/`, `tools/` and `tests/` for account ids, bucket names, profile
names and program names, and exempts this file.

Everything below comes from a real run against the AWS CardDemo sample application.

---

## A full nine-phase run

```bash
aws sso login --profile <profile>

.kiro/skills/atx-app-documentation/scripts/run_pipeline.sh \
  --profile <profile> --region us-east-1 \
  --bucket <artifact-bucket> \
  --job-id <transform-job-id> \
  --upload-bucket <docs-bucket> \
  --upload-prefix generated-zip \
  --public
```

Observed output:

```
[1/9] preflight          ok         18.8s  exit=0
[2/9] fetch-specs        ok          2.8s  exit=0
[3/9] verify-split       partial     2.2s  exit=1
        5 bundle(s) staged, 7 function bundle(s) in specs/
[4/9] snapshot-analysis  ok         34.0s  exit=0
[5/9] coverage           ok          0.2s  exit=0
[6/9] evidence           ok          0.6s  exit=0
[7/9] generate           ok          0.4s  exit=0
[8/9] package            ok          0.4s  exit=0
[9/9] publish            ok          6.7s  exit=0
```

Phase 3's `partial` is the expected state for this application, not a failure. See below.

---

## A partially delivered estate

CardDemo's coverage matrix:

```
Discovered: 11 · scoped: 9 · delivered: 6
```

| Business function | Class | Reqs (F/N) | Rules | LOC |
|---|---|---|---|---|
| Account Balance and Transaction Processing | `delivered` | 286/4 | 286/328 | 8269 |
| Credit Card Record Management | `delivered` | 22/0 | 14/14 | 4218 |
| Customer and Account Data Export and Import | `delivered` | 22/1 | 37/37 | 1071 |
| Payment Authorization Processing and Fraud Review | `delivered` | 53/3 | 55/57 | 3590 |
| Transaction Type Reference Data Maintenance | `delivered` | 14/0 | 15/15 | 4288 |
| User Security Profile Management | `delivered` | 69/0 | 59/65 | 2848 |
| Master Data File Initialization | `scoped-no-spec` | — | — | 703 |
| Online Transaction Entry | `scoped-no-spec` | — | — | 1592 |
| Transaction Reporting and Statement Generation | `scoped-no-spec` | — | — | 2095 |
| Application Build and Deployment | `excluded-infrastructure` | — | — | 256 |
| System Administration and Infrastructure Setup | `excluded-infrastructure` | — | — | 6068 |

Three scoped functions returned **empty requirements**. Business rules extracted correctly — 18 rules
across 9 files in one case — but requirements generation emitted only an empty
`discovery/programs.yaml`. Reproduced twice sequentially, which ruled out batching and located the
fault AWS-side. The empty bundles were retained as support evidence.

Two functions were classified `excluded-infrastructure` by signal, not by name:

- *Application Build and Deployment* — compile/link toolchain, 256 LOC across 5 entry points, thin
  wrappers around utilities
- *System Administration and Infrastructure Setup* — CICS resource definition, DB2 DDL, RACF; file
  open/close, FTP, job submission

The resulting document set covers **6 of 11** discovered functions, and every count in it carries that
denominator.

---

## Competing bundles

`00-manifest/bundle-selection.md` from the same run:

| Business function | Kept from | Reqs | Bytes | Rejected |
|---|---|---|---|---|
| AccountBalanceandTransactionProcessing | `20260806_145108` | 294 | 81708 | `20260813_071942` (14 reqs, 8576 B) |
| ApplicationBuildandDeployment | `20260806_094211` | 27 | 10331 | — |
| CreditCardRecordManagement | `20260813_071942` | 22 | 7708 | — |

The first row is why selection is by requirement count rather than recency: the later attempt for that
function carried 14 requirements against the earlier 294. A newest-wins rule would have shipped the 14.

The second row is why it is not by size either — that bundle came from the *earliest* and smallest zip,
which a largest-wins rule would never have selected.

---

## Document outcome

```
31 documents
111 grounded / 90 evidence-absent / 0 not-extracted   (55%)
4 complete / 25 partial / 2 unavailable
```

`security_architecture` and `modernization_strategy` are `unavailable` with zero grounded sections,
because AWS Transform produces no evidence for either. Reported as such rather than written from
inference.

`0 not-extracted` is the figure to watch. It means every remaining gap is genuine evidence absence
rather than a parser that was never written.

---

## Application name derivation

CardDemo's upstream `sourceOrigin` was
`s3://<bucket>/aws-mainframe-modernization-carddemo-main.zip`, which derives to:

```
**Application:** aws-mainframe-modernization-carddemo
```

recorded in `manifest.json` as:

```json
"application": {
  "name": "aws-mainframe-modernization-carddemo",
  "nameSource": "derived from upstream sourceOrigin"
}
```

Pass `--app-name "CardDemo"` when the archive name is not the name the business uses. Before this was
derived it was a literal, and every document for every application claimed to be about CardDemo.

---

## Publishing

Presigned, against a one-hour SSO session:

```
## Share link
Presigned, expires in 604800 s from generation.
> The signing credentials expire in 3404s, before the requested 604800 s.
```

The link dies in 57 minutes regardless of `--expires-in`, because a presigned URL cannot outlive the
credentials that signed it.

Public, to a dedicated bucket:

```json
{
  "Sid": "AtxAppDocsPublicRead",
  "Effect": "Allow",
  "Principal": "*",
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::<docs-bucket>/generated-zip/*"
}
```

Verified anonymously with every AWS credential stripped from the environment: the documentation prefix
returned **200**, a sibling prefix in the same bucket **403**, and a bucket listing **403**.
