# Template Families and Section Sets

The 31 templates were ported verbatim from the origin service, and they are **not uniformly
structured**. Extracting the section set the wrong way produces documents whose headings are
inline sub-labels, or documents with no sections at all.

This file records how to read each family and declares the section sets for the templates that
supply none. It exists because the distinction is load-bearing and was previously discoverable
only by reading the generator source.

---

## The three families

| Family | Count | How the section set is expressed | How to extract |
|---|---|---|---|
| **A — output structure** | 4 | an `OUTPUT STRUCTURE` block containing markdown headings | take the `##` headings after `OUTPUT STRUCTURE`, strip leading `n.` numbering, drop any heading that is a `{placeholder}` |
| **B — bold labels** | 24 | bold labels at line start, which *are* the section set | take `^\*\*(.+)\*\*$`, strip trailing `:`, reject anything containing `**` (those are inline `Label:** value` fragments) or longer than 70 characters |
| **C — stub** | 3 | nothing — the origin service supplied no output structure | use the fixed section set declared below |

### Family A members

`application_inventory`, `as_is_assessment`, `executive_summary`, `stakeholder_analysis`

These also contain `DISCOVERY TASKS` / `ANALYSIS TASKS` blocks. Those are instructions to the
generator, **not** sections to render. Only headings after `OUTPUT STRUCTURE` count.

### Family B members

The remaining 24. Their bold labels are genuine headings — for example `**Data Entity
Inventory**`, `**Attributes**`, `**Relationships**`. Note that `executive_summary` (family A)
*also* contains 25 bold strings, but they are inline labels such as `Assessment:** ❌ **Not
Recommended`; that is why family A must be tested before family B.

### Family C members and their declared section sets

The origin service's templates for these supply a topic list but no output structure, so model
output would vary run to run. The sets below restore determinism. They are editorial decisions
and are open to revision — change them here, not in the generator.

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

`business_capabilities` and `architecture_decisions` were already flagged as stubs in the Bob
port's analysis. `business_features` is a third stub that analysis did not name.

---

## Duplicate headings within one template

Several templates contain two headings that legitimately resolve to the same evidence. For
example `data_dictionary` has both `Data Entity Inventory` and `Attributes`, and both are
answered by the data dictionary artifact.

Emit the evidence **once**, then cross-reference:

> See **Data Entity Inventory** above — the same evidence answers this heading. Repeating it
> here would add no information.

Rendering the same table twice is padding, which the determinism rules forbid. The heading must
still appear, because the section set is fixed.
