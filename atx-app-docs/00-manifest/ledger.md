# Document Ledger

31 documents. Last generated 2026-08-14T09:52:35Z.

| # | Level | prompt_type | Plan | Status | Grounded | Evidence absent | Not extracted | Artifacts |
|---|---|---|---|---|---|---|---|---|
| 1 | L0 | `application_inventory` | `atx-discovery` | partial | 12 | 3 | 0 | 13 |
| 2 | L0 | `as_is_assessment` | `atx-quality` | partial | 7 | 7 | 0 | 13 |
| 3 | L1 | `executive_summary` | `atx-discovery` | partial | 2 | 9 | 0 | 2 |
| 4 | L1 | `stakeholder_analysis` | `atx-business` | partial | 1 | 1 | 0 | 2 |
| 5 | L1 | `business_capabilities` | `atx-business` | partial | 4 | 2 | 0 | 10 |
| 6 | L1 | `business_features` | `atx-business` | partial | 4 | 1 | 0 | 10 |
| 7 | L2 | `business_requirements` | `atx-business` | complete | 7 | 0 | 0 | 14 |
| 8 | L2 | `user_stories` | `atx-business` | partial | 4 | 2 | 0 | 8 |
| 9 | L2 | `business_process` | `atx-business` | partial | 5 | 2 | 0 | 20 |
| 10 | L2 | `feature_catalog` | `atx-business` | partial | 4 | 4 | 0 | 16 |
| 11 | L2 | `business_rules` | `atx-module` | partial | 3 | 3 | 0 | 26 |
| 12 | L3 | `system_architecture` | `atx-structure` | complete | 6 | 0 | 0 | 4 |
| 13 | L3 | `technical_specs` | `atx-module` | partial | 4 | 1 | 0 | 12 |
| 14 | L3 | `code_structure` | `atx-module` | partial | 2 | 3 | 0 | 4 |
| 15 | L3 | `build_deployment` | `atx-operations` | partial | 4 | 1 | 0 | 20 |
| 16 | L4 | `architecture_decisions` | `atx-structure` | partial | 3 | 3 | 0 | 8 |
| 17 | L4 | `component_design` | `atx-module` | partial | 3 | 2 | 0 | 16 |
| 18 | L4 | `security_architecture` | `atx-quality` | unavailable | 0 | 5 | 0 | 2 |
| 19 | L5 | `data_dictionary` | `atx-data` | partial | 3 | 2 | 0 | 4 |
| 20 | L5 | `database_schema_full` | `atx-data` | partial | 3 | 2 | 0 | 4 |
| 21 | L5 | `data_lineage` | `atx-data` | partial | 3 | 3 | 0 | 4 |
| 22 | L6 | `integration_architecture` | `atx-integration` | complete | 5 | 0 | 0 | 24 |
| 23 | L6 | `api_documentation` | `atx-api` | partial | 3 | 3 | 0 | 14 |
| 24 | L6 | `message_specs` | `atx-integration` | complete | 5 | 0 | 0 | 30 |
| 25 | L7 | `operations_manual` | `atx-operations` | partial | 4 | 2 | 0 | 20 |
| 26 | L7 | `monitoring_alerting` | `atx-operations` | partial | 2 | 4 | 0 | 9 |
| 27 | L7 | `disaster_recovery` | `atx-operations` | partial | 3 | 3 | 0 | 9 |
| 28 | L8 | `modernization_strategy` | `atx-structure` | unavailable | 0 | 6 | 0 | 2 |
| 29 | L8 | `target_architecture` | `atx-structure` | partial | 2 | 5 | 0 | 5 |
| 30 | L8 | `gap_analysis` | `atx-structure` | partial | 2 | 4 | 0 | 9 |
| 31 | L8 | `migration_roadmap` | `atx-structure` | partial | 1 | 7 | 0 | 3 |

## Status summary

| Status | Meaning | Documents |
|---|---|---|
| partial | written, some headings unavailable | 25 |
| complete | every template heading grounded | 4 |
| unavailable | written, but no heading could be grounded despite its plan having evidence | 2 |

## Which builder answered how many sections

A flat distribution is the healthy signal. One builder dominating across the suite means headings are being answered by evidence that does not address them.

| Builder | Sections |
|---|---|
| `architecture` | 17 |
| `jcl_control` | 12 |
| `reqs` | 10 |
| `run_ctx` | 9 |
| `workflows` | 8 |
| `inventory` | 7 |
| `error_handling` | 6 |
| `entrypoints` | 5 |
| `rules` | 5 |
| `datadict` | 5 |
| `src_inv` | 4 |
| `complexity` | 4 |
| `oqs` | 4 |
| `deps` | 3 |
| `fn_table` | 3 |
| `lineage` | 3 |
| `build_jcl` | 2 |
| `interfaces` | 2 |
| `bms_maps` | 1 |
| `jcl_ops` | 1 |
