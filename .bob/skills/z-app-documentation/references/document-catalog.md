# Document Catalog — 31 documents across 9 levels

Ported 1:1 from `cast-integration/src/cast_integration_service/prompts/all_prompts.py::PROMPT_REGISTRY`.
The `CAST plan` column records the original CAST MCP tool plan; the `Z plan` column is its
Z Premium Package replacement. No CAST MCP server is used by this skill.

| # | Level | prompt_type | Z plan | CAST plan (origin) | Output file | Template |
|---|---|---|---|---|---|---|
| 1 | 0 — Discovery & Assessment | `application_inventory` | `z-discovery` | `discovery` | `L0-discovery/application-inventory.md` | `references/prompts/0-application_inventory.md` |
| 2 | 0 — Discovery & Assessment | `as_is_assessment` | `z-quality` | `quality` | `L0-discovery/as-is-assessment.md` | `references/prompts/0-as_is_assessment.md` |
| 3 | 1 — Business Context | `executive_summary` | `z-discovery` | `discovery` | `L1-business-context/executive-summary.md` | `references/prompts/1-executive_summary.md` |
| 4 | 1 — Business Context | `stakeholder_analysis` | `z-business` | `business` | `L1-business-context/stakeholder-analysis.md` | `references/prompts/1-stakeholder_analysis.md` |
| 5 | 1 — Business Context | `business_capabilities` | `z-business` | `business` | `L1-business-context/business-capabilities.md` | `references/prompts/1-business_capabilities.md` |
| 6 | 1 — Business Context | `business_features` | `z-business` | `business` | `L1-business-context/business-features.md` | `references/prompts/1-business_features.md` |
| 7 | 2 — Business Documentation | `business_requirements` | `z-business` | `business` | `L2-business-documentation/business-requirements.md` | `references/prompts/2-business_requirements.md` |
| 8 | 2 — Business Documentation | `user_stories` | `z-business` | `business` | `L2-business-documentation/user-stories.md` | `references/prompts/2-user_stories.md` |
| 9 | 2 — Business Documentation | `business_process` | `z-business` | `business` | `L2-business-documentation/business-process.md` | `references/prompts/2-business_process.md` |
| 10 | 2 — Business Documentation | `feature_catalog` | `z-business` | `business` | `L2-business-documentation/feature-catalog.md` | `references/prompts/2-feature_catalog.md` |
| 11 | 2 — Business Documentation | `business_rules` | `z-module` | `module` | `L2-business-documentation/business-rules.md` | `references/prompts/2-business_rules.md` |
| 12 | 3 — Technical Documentation | `system_architecture` | `z-structure` | `architecture` | `L3-technical-documentation/system-architecture.md` | `references/prompts/3-system_architecture.md` |
| 13 | 3 — Technical Documentation | `technical_specs` | `z-module` | `module` | `L3-technical-documentation/technical-specs.md` | `references/prompts/3-technical_specs.md` |
| 14 | 3 — Technical Documentation | `code_structure` | `z-module` | `module` | `L3-technical-documentation/code-structure.md` | `references/prompts/3-code_structure.md` |
| 15 | 3 — Technical Documentation | `build_deployment` | `z-operations` | `discovery` | `L3-technical-documentation/build-deployment.md` | `references/prompts/3-build_deployment.md` |
| 16 | 4 — Design & Decisions | `architecture_decisions` | `z-structure` | `architecture` | `L4-design/architecture-decisions.md` | `references/prompts/4-architecture_decisions.md` |
| 17 | 4 — Design & Decisions | `component_design` | `z-module` | `module` | `L4-design/component-design.md` | `references/prompts/4-component_design.md` |
| 18 | 4 — Design & Decisions | `security_architecture` | `z-quality` | `quality` | `L4-design/security-architecture.md` | `references/prompts/4-security_architecture.md` |
| 19 | 5 — Data | `data_dictionary` | `z-data` | `data` | `L5-data/data-dictionary.md` | `references/prompts/5-data_dictionary.md` |
| 20 | 5 — Data | `database_schema_full` | `z-data` | `data` | `L5-data/database-schema-full.md` | `references/prompts/5-database_schema_full.md` |
| 21 | 5 — Data | `data_lineage` | `z-data` | `data` | `L5-data/data-lineage.md` | `references/prompts/5-data_lineage.md` |
| 22 | 6 — Integration & Interfaces | `integration_architecture` | `z-integration` | `integration` | `L6-integration/integration-architecture.md` | `references/prompts/6-integration_architecture.md` |
| 23 | 6 — Integration & Interfaces | `api_documentation` | `z-api` | `api` | `L6-integration/api-documentation.md` | `references/prompts/6-api_documentation.md` |
| 24 | 6 — Integration & Interfaces | `message_specs` | `z-integration` | `integration` | `L6-integration/message-specs.md` | `references/prompts/6-message_specs.md` |
| 25 | 7 — Operations | `operations_manual` | `z-operations` | `discovery` | `L7-operations/operations-manual.md` | `references/prompts/7-operations_manual.md` |
| 26 | 7 — Operations | `monitoring_alerting` | `z-operations` | `discovery` | `L7-operations/monitoring-alerting.md` | `references/prompts/7-monitoring_alerting.md` |
| 27 | 7 — Operations | `disaster_recovery` | `z-operations` | `discovery` | `L7-operations/disaster-recovery.md` | `references/prompts/7-disaster_recovery.md` |
| 28 | 8 — Modernization | `modernization_strategy` | `z-structure` | `architecture` | `L8-modernization/modernization-strategy.md` | `references/prompts/8-modernization_strategy.md` |
| 29 | 8 — Modernization | `target_architecture` | `z-structure` | `architecture` | `L8-modernization/target-architecture.md` | `references/prompts/8-target_architecture.md` |
| 30 | 8 — Modernization | `gap_analysis` | `z-structure` | `architecture` | `L8-modernization/gap-analysis.md` | `references/prompts/8-gap_analysis.md` |
| 31 | 8 — Modernization | `migration_roadmap` | `z-structure` | `architecture` | `L8-modernization/migration-roadmap.md` | `references/prompts/8-migration_roadmap.md` |

## Level summary

| Level | Name | Documents |
|---|---|---|
| 0 | Discovery & Assessment | 2 |
| 1 | Business Context | 4 |
| 2 | Business Documentation | 5 |
| 3 | Technical Documentation | 4 |
| 4 | Design & Decisions | 3 |
| 5 | Data | 3 |
| 6 | Integration & Interfaces | 3 |
| 7 | Operations | 3 |
| 8 | Modernization | 4 |
| **Total** | | **31** |
