# Document Catalog — 31 documents across 9 levels

Ported 1:1 from `cast-integration/src/cast_integration_service/prompts/all_prompts.py::PROMPT_REGISTRY`
via the Bob `z-app-documentation` skill. The `ATX plan` column names the evidence plan in
`references/evidence-plans.md`; the `CAST plan` column records the origin service's plan so all
three ports stay comparable. Evidence comes from `mainframe-reverse-engineering` output only — no
CAST MCP server, no Bob, no live AWS Transform calls.

| # | Level | prompt_type | ATX plan | CAST plan (origin) | Output file | Template |
|---|---|---|---|---|---|---|
| 1 | 0 — Discovery & Assessment | `application_inventory` | `atx-discovery` | `discovery` | `L0-discovery/application-inventory.md` | `references/prompts/0-application_inventory.md` |
| 2 | 0 — Discovery & Assessment | `as_is_assessment` | `atx-quality` | `quality` | `L0-discovery/as-is-assessment.md` | `references/prompts/0-as_is_assessment.md` |
| 3 | 1 — Business Context | `executive_summary` | `atx-discovery` | `discovery` | `L1-business-context/executive-summary.md` | `references/prompts/1-executive_summary.md` |
| 4 | 1 — Business Context | `stakeholder_analysis` | `atx-business` | `business` | `L1-business-context/stakeholder-analysis.md` | `references/prompts/1-stakeholder_analysis.md` |
| 5 | 1 — Business Context | `business_capabilities` | `atx-business` | `business` | `L1-business-context/business-capabilities.md` | `references/prompts/1-business_capabilities.md` |
| 6 | 1 — Business Context | `business_features` | `atx-business` | `business` | `L1-business-context/business-features.md` | `references/prompts/1-business_features.md` |
| 7 | 2 — Business Documentation | `business_requirements` | `atx-business` | `business` | `L2-business-documentation/business-requirements.md` | `references/prompts/2-business_requirements.md` |
| 8 | 2 — Business Documentation | `user_stories` | `atx-business` | `business` | `L2-business-documentation/user-stories.md` | `references/prompts/2-user_stories.md` |
| 9 | 2 — Business Documentation | `business_process` | `atx-business` | `business` | `L2-business-documentation/business-process.md` | `references/prompts/2-business_process.md` |
| 10 | 2 — Business Documentation | `feature_catalog` | `atx-business` | `business` | `L2-business-documentation/feature-catalog.md` | `references/prompts/2-feature_catalog.md` |
| 11 | 2 — Business Documentation | `business_rules` | `atx-module` | `module` | `L2-business-documentation/business-rules.md` | `references/prompts/2-business_rules.md` |
| 12 | 3 — Technical Documentation | `system_architecture` | `atx-structure` | `architecture` | `L3-technical-documentation/system-architecture.md` | `references/prompts/3-system_architecture.md` |
| 13 | 3 — Technical Documentation | `technical_specs` | `atx-module` | `module` | `L3-technical-documentation/technical-specs.md` | `references/prompts/3-technical_specs.md` |
| 14 | 3 — Technical Documentation | `code_structure` | `atx-module` | `module` | `L3-technical-documentation/code-structure.md` | `references/prompts/3-code_structure.md` |
| 15 | 3 — Technical Documentation | `build_deployment` | `atx-operations` | `discovery` | `L3-technical-documentation/build-deployment.md` | `references/prompts/3-build_deployment.md` |
| 16 | 4 — Design & Decisions | `architecture_decisions` | `atx-structure` | `architecture` | `L4-design/architecture-decisions.md` | `references/prompts/4-architecture_decisions.md` |
| 17 | 4 — Design & Decisions | `component_design` | `atx-module` | `module` | `L4-design/component-design.md` | `references/prompts/4-component_design.md` |
| 18 | 4 — Design & Decisions | `security_architecture` | `atx-quality` | `quality` | `L4-design/security-architecture.md` | `references/prompts/4-security_architecture.md` |
| 19 | 5 — Data | `data_dictionary` | `atx-data` | `data` | `L5-data/data-dictionary.md` | `references/prompts/5-data_dictionary.md` |
| 20 | 5 — Data | `database_schema_full` | `atx-data` | `data` | `L5-data/database-schema-full.md` | `references/prompts/5-database_schema_full.md` |
| 21 | 5 — Data | `data_lineage` | `atx-data` | `data` | `L5-data/data-lineage.md` | `references/prompts/5-data_lineage.md` |
| 22 | 6 — Integration & Interfaces | `integration_architecture` | `atx-integration` | `integration` | `L6-integration/integration-architecture.md` | `references/prompts/6-integration_architecture.md` |
| 23 | 6 — Integration & Interfaces | `api_documentation` | `atx-api` | `api` | `L6-integration/api-documentation.md` | `references/prompts/6-api_documentation.md` |
| 24 | 6 — Integration & Interfaces | `message_specs` | `atx-integration` | `integration` | `L6-integration/message-specs.md` | `references/prompts/6-message_specs.md` |
| 25 | 7 — Operations | `operations_manual` | `atx-operations` | `discovery` | `L7-operations/operations-manual.md` | `references/prompts/7-operations_manual.md` |
| 26 | 7 — Operations | `monitoring_alerting` | `atx-operations` | `discovery` | `L7-operations/monitoring-alerting.md` | `references/prompts/7-monitoring_alerting.md` |
| 27 | 7 — Operations | `disaster_recovery` | `atx-operations` | `discovery` | `L7-operations/disaster-recovery.md` | `references/prompts/7-disaster_recovery.md` |
| 28 | 8 — Modernization | `modernization_strategy` | `atx-structure` | `architecture` | `L8-modernization/modernization-strategy.md` | `references/prompts/8-modernization_strategy.md` |
| 29 | 8 — Modernization | `target_architecture` | `atx-structure` | `architecture` | `L8-modernization/target-architecture.md` | `references/prompts/8-target_architecture.md` |
| 30 | 8 — Modernization | `gap_analysis` | `atx-structure` | `architecture` | `L8-modernization/gap-analysis.md` | `references/prompts/8-gap_analysis.md` |
| 31 | 8 — Modernization | `migration_roadmap` | `atx-structure` | `architecture` | `L8-modernization/migration-roadmap.md` | `references/prompts/8-migration_roadmap.md` |

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
