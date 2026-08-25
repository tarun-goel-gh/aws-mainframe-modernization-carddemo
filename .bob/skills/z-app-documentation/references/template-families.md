# Template Families and Section Sets

`references/prompts/*.md` are the same 31 templates ported verbatim from the origin CAST
integration service that `atx-app-documentation`'s prompts also came from — byte-for-byte the
same section-set shapes, just living in a different skill folder. They are **not uniformly
structured**. Extracting the section set the wrong way produces documents whose headings are
inline sub-labels, or documents with no sections at all.

This file records how `scripts/generate_docs.py` reads each family and declares the section sets
for the templates that supply none. It exists so that behaviour is reviewable from a file rather
than discoverable only by reading the generator source — the same reason
`atx-app-documentation/references/template-families.md` exists, and this file is derived directly
from `z-app-documentation`'s own `references/prompts/*.md` (not rediscovered from the AWS
original), because those files carry the exact same `OUTPUT STRUCTURE` blocks, bold-label lines,
or absence thereof.

---

## The three families

| Family | Count | How the section set is expressed | How to extract |
|---|---|---|---|
| **A — output structure** | 4 | an `OUTPUT STRUCTURE` block containing markdown `##` headings | take the `##` headings after the literal string `OUTPUT STRUCTURE`, strip any leading `N.` numbering, drop any heading that is a `{placeholder}` |
| **B — bold labels** | 24 | bold labels at line start, which *are* the section set | regex `^\*\*(.+)\*\*$`, strip a trailing `:`, reject any match containing a second `**` (inline `Label:** value` fragments) or longer than 70 characters |
| **C — stub** | 3 | nothing — the origin service supplied no output structure at all | use the fixed, declared section set below rather than parsing anything |

Family A must be tested before Family B, in that order, for every template — see the Family B
note below for why.

---

## Family A members

`application_inventory`, `as_is_assessment`, `executive_summary`, `stakeholder_analysis`

These four templates also contain `DISCOVERY TASKS` / `ANALYSIS TASKS` blocks. Those are
instructions to the generator, **not** sections to render. Only the `##` headings that appear
after the literal string `OUTPUT STRUCTURE` count as the section set.

Two of the Family C stub templates (`business_capabilities`, `architecture_decisions`) contain
the literal substring `OUTPUT STRUCTURE` inside their "Template gap" note — e.g. "supplies no
OUTPUT STRUCTURE" — not inside a real `OUTPUT STRUCTURE` block. A parser that matches on the bare
substring rather than on "a markdown heading block introduced by that literal string, followed by
`##` headings" will misclassify these two as Family A. Test for the block, not the string.

## Family B members

The remaining 24:

`business_requirements`, `user_stories`, `business_process`, `feature_catalog`, `business_rules`,
`system_architecture`, `technical_specs`, `code_structure`, `build_deployment`,
`component_design`, `security_architecture`, `data_dictionary`, `database_schema_full`,
`data_lineage`, `integration_architecture`, `api_documentation`, `message_specs`,
`operations_manual`, `monitoring_alerting`, `disaster_recovery`, `modernization_strategy`,
`target_architecture`, `gap_analysis`, `migration_roadmap`

Their bold labels are genuine headings — for example `**Business Requirements**`,
`**Business Rule Inventory**`, `**Rule Definition**`. A template can also contain bold strings
that are *not* section headings — inline value labels such as `**Generated:** {current_date}` —
which is exactly why Family A must be tested and excluded before Family B's regex runs: without
that ordering, `executive_summary`'s inline labels (`Assessment:** ❌ **Not Recommended`, and
similar) would be misread as a Family B section set for a Family A template.

## Family C members and their declared section sets

The origin service's templates for these three supply a topic list but no output structure, so
model output would vary run to run. The sets below restore determinism. They are carried forward
**verbatim** from `atx-app-documentation/references/template-families.md`, because they exist to
restore determinism to the same underlying stub templates ported from the same origin service —
not to reinterpret them for BobZ. They are editorial decisions and are open to revision — change
them here, not in `generate_docs.py`.

**`business_capabilities`**
1. Capability Inventory
2. Capability to Business Function Mapping
3. Current State Assessment
4. Capability Gaps
5. Modernization Impact per Capability
6. Open Questions

**`business_features`**
1. Feature Inventory
2. Feature to Entry Point Mapping
3. Feature Ownership
4. Feature Dependencies
5. Open Questions

**`architecture_decisions`**
1. Decision Log
2. Context and Drivers
3. Decisions Evidenced by the Codebase
4. Consequences
5. Decisions Deferred to Forward Engineering
6. Open Questions

`business_capabilities` and `architecture_decisions` were already flagged as stubs in
`PORTING-ANALYSIS.md`. `business_features` is a third stub — its prompt file carries a JSON
output contract for a feature-identification pass, not a document `OUTPUT STRUCTURE` block — and
gets the same fixed-set treatment here so its rendered document is exactly as deterministic as
the other two.

---

## Duplicate headings within one template

Several templates contain two headings that legitimately resolve to the same evidence. For
example `data_dictionary` has both `Data Entity Inventory` and `Attributes`, and both are
answered by the same data-dictionary artifact.

Emit the evidence **once**, then cross-reference:

> See **Data Entity Inventory** above — the same evidence answers this heading. Repeating it
> here would add no information.

Rendering the same table twice is padding, which the determinism rules forbid. The heading still
renders, because the section set is fixed.

---

## Parser contract `generate_docs.py` relies on

Family C section lists are parsed out of this file by matching a bold, inline-code
`` **`prompt_type`** `` line immediately followed by a numbered list (`1.`, `2.`, `3.` …) with no
blank line in between — exactly the format the three entries above use. Any edit to this file
that reformats those three entries without preserving that exact shape makes the parser find
nothing, and every stub document would silently get an empty section set instead of the declared
one. Family A and Family B section sets are parsed from `references/prompts/*.md` directly, per
the extraction rules in the table above — this file does not restate them.
