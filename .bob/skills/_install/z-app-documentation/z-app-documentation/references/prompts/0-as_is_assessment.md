# As-Is Assessment

`prompt_type: as_is_assessment`

| Field | Value |
|---|---|
| Level | 0 — Discovery & Assessment |
| Evidence plan | `z-quality` (see `references/evidence-plans.md`) |
| Output file | `<docsRoot>/L0-discovery/as-is-assessment.md` |
| Ledger column | `as_is_assessment` |
| Template placeholders | `{application_name}`, `{current_date}`, `{generated_by}` |
| Scope | Application-scoped — one file per application |

## How to run this document

1. Read `references/grounding-contract.md` and apply it in full. It overrides every
   instruction in the template below.
2. Read `references/evidence-plans.md` and execute the **`z-quality`** plan. Gather all
   evidence **before** writing any section.
3. Apply `references/z-substitutions.md` wherever the template names a distributed-stack
   artifact (pom.xml, REST endpoint, Docker, npm, ORM, git log …). Use the Z equivalent.
   If no Z equivalent exists, render the heading with `Not available from Z Premium analysis`.
4. Fill the placeholders: `{application_name}` = resolved application name,
   `{current_date}` = today's date from context, `{generated_by}` =
   `IBM Bob — Z Premium Package workflows`.
5. Emit the document to the Output file above, then update the ledger.

## Prompt template — verbatim from `prompts/all_prompts.py::AS_IS_ASSESSMENT_PROMPT`

Reproduce the requested section set exactly: do not add, drop, or reorder headings.

---

# As-Is State Assessment

Generate a comprehensive current state assessment for {application_name}.

## DISCOVERY & ANALYSIS TASKS

Use available tools to thoroughly analyze:

1. **Code Quality Analysis**
   - Search for TODO, FIXME, HACK comments
   - Identify files over 500 lines
   - Find deeply nested code (multiple levels of indentation)
   - Detect duplicate code patterns
   - Check for error handling patterns
   - Look for deprecated API usage

2. **Performance Indicators**
   - Database query patterns (N+1 queries, missing indexes)
   - Look for caching implementations
   - Identify synchronous vs asynchronous operations
   - Find potential bottlenecks

3. **Architecture Analysis**
   - Identify architectural style (layered, microservices, monolith)
   - Map out component dependencies
   - Look for design patterns in use
   - Identify architectural smells (circular dependencies, god classes)

4. **Database Health**
   - Count tables without primary keys
   - Find tables without indexes
   - Identify very wide tables (>30 columns)
   - Look for unused tables
   - Check for proper normalization

5. **Integration Analysis**
   - Find all external API calls
   - Identify integration patterns (sync/async)
   - Look for retry logic and circuit breakers
   - Check for integration error handling

6. **Testing Coverage**
   - Find test files and count them
   - Calculate test-to-code ratio
   - Identify untested critical paths
   - Look for integration/e2e tests

7. **Security Assessment**
   - Search for SQL injection vulnerabilities
   - Look for XSS vulnerabilities
   - Find authentication/authorization code
   - Check for encryption usage
   - Identify sensitive data handling

## OUTPUT STRUCTURE

# As-Is State Assessment: {application_name}
**Assessment Date:** {current_date}
**Assessment Method:** Automated Analysis via {generated_by}

---

## Executive Summary

### Quick Stats
| Metric | Value | Health Status |
|--------|-------|---------------|
| Overall Health Score | [0-100] | 🔴/🟡/🟢 |
| Technical Debt Level | [Low/Medium/High/Critical] | 🔴/🟡/🟢 |
| Modernization Readiness | [Score 1-5] | 🔴/🟡/🟢 |
| Security Risk Level | [Low/Medium/High/Critical] | 🔴/🟡/🟢 |
| Maintenance Cost | [Low/Medium/High] | 🔴/🟡/🟢 |

### Key Findings
1. **[Most Critical Finding]** - [Brief description]
2. **[Second Critical Finding]** - [Brief description]
3. **[Third Critical Finding]** - [Brief description]

### Recommendation Priority
- 🔴 **Critical (Fix Immediately):** [count] issues
- 🟡 **Important (Fix Soon):** [count] issues
- 🟢 **Enhancement (Plan for Future):** [count] issues

---

## 1. Technology Stack Health Assessment

### 1.1 Technology Currency
| Technology | Current Version | Latest Stable | Age | EOL Status | Risk |
|------------|----------------|---------------|-----|------------|------|
| [Language] | [version] | [version] | [years] | [date/Active] | 🔴/🟡/🟢 |
| [Framework] | [version] | [version] | [years] | [date/Active] | 🔴/🟡/🟢 |

**Analysis:**
- ⚠️ Technologies past EOL: [list]
- ⚠️ Technologies approaching EOL (<1 year): [list]
- ⚠️ Technologies >2 major versions behind: [list]

### 1.2 Dependency Health
| Category | Total | Outdated | Vulnerable | Deprecated |
|----------|-------|----------|------------|------------|
| Direct Dependencies | [count] | [count] | [count] | [count] |
| Transitive Dependencies | [count] | [count] | [count] | [count] |

## 2. Code Quality Assessment

### 2.1 Code Metrics
| Metric | Value | Industry Standard | Status |
|--------|-------|------------------|--------|
| Total Lines of Code | [count] | - | - |
| Comment Ratio | [%] | 15-25% | 🔴/🟡/🟢 |
| Average File Size | [lines] | <300 lines | 🔴/🟡/🟢 |
| Files > 500 lines | [count] | <5% | 🔴/🟡/🟢 |
| Maximum File Size | [lines] | <1000 | 🔴/🟡/🟢 |

### 2.2 Code Smells Detected
| Code Smell | Occurrences | Severity | Example Location |
|------------|-------------|----------|------------------|
| God Classes (>1000 lines) | [count] | 🔴 High | [file:line] |
| Long Methods (>100 lines) | [count] | 🟡 Medium | [file:line] |
| Deep Nesting (>5 levels) | [count] | 🟡 Medium | [file:line] |
| TODO/FIXME Comments | [count] | 🟢 Low | [file:line] |

### 2.3 Technical Debt Items
**High Priority:**
1. **[Issue]**
   - Location: [file:line]
   - Impact: [description]
   - Effort: [hours/days]
   - Recommendation: [action]

**Estimated Technical Debt:** [hours/days] of development work

## 3. Architecture Assessment

### 3.1 Architecture Style
**Current Architecture:** [Monolith / Distributed Monolith / Microservices / SOA]

**Architecture Characteristics:**
- Modularity: [Score 1-5] - [Explanation]
- Coupling: [Tight/Loose] - [Evidence]
- Cohesion: [High/Low] - [Evidence]
- Separation of Concerns: [Score 1-5] - [Explanation]

### 3.2 Design Patterns Identified
| Pattern | Usage | Location | Appropriateness |
|---------|-------|----------|-----------------|
| [Pattern] | [How used] | [files] | ✅ Good / ⚠️ Misused |

### 3.3 Architecture Violations
| Violation | Type | Impact | Location |
|-----------|------|--------|----------|
| Circular Dependency | Structural | High | [modules] |
| Layer Violation | Structural | Medium | [example] |

## 4. Database Health Assessment

### 4.1 Database Design Quality
| Metric | Value | Best Practice | Status |
|--------|-------|---------------|--------|
| Tables | [count] | - | - |
| Tables without PK | [count] | 0 | 🔴/🟡/🟢 |
| Tables without indexes | [count] | 0 | 🔴/🟡/🟢 |
| Very wide tables (>30 cols) | [count] | <10% | 🔴/🟡/🟢 |

### 4.2 Database Performance Indicators
| Indicator | Status | Details |
|-----------|--------|---------|
| Missing Indexes | 🔴/🟡/🟢 | [count] foreign keys without indexes |
| N+1 Query Patterns | ⚠️ | [locations in code] |

## 5. Performance Assessment

### 5.1 Performance Patterns
| Pattern | Present | Impact | Location |
|---------|---------|--------|----------|
| Caching | ✅/❌ | [High/Medium/Low] | [details] |
| Connection Pooling | ✅/❌ | High | [configuration] |
| Asynchronous Processing | ✅/❌ | High | [examples] |

### 5.2 Performance Anti-Patterns
| Anti-Pattern | Occurrences | Severity | Location |
|--------------|-------------|----------|----------|
| N+1 Queries | [count] | 🔴 High | [file:line] |
| Missing Connection Pooling | [Yes/No] | 🔴 High | [config] |
| SELECT * queries | [count] | 🟢 Low | [file:line] |

## 6. Security Assessment

### 6.1 Security Vulnerabilities
| Category | Finding | Severity | Location | Remediation |
|----------|---------|----------|----------|-------------|
| SQL Injection | [String concat] | 🔴 Critical | [file:line] | Use parameterized queries |
| XSS | [Unescaped output] | 🔴 Critical | [file:line] | Sanitize inputs |
| Hardcoded Secrets | [Passwords] | 🔴 Critical | [file:line] | Use secret management |

### 6.2 Authentication & Authorization
| Aspect | Implementation | Security Level | Issues |
|--------|----------------|----------------|--------|
| Authentication | [Method] | 🔴/🟡/🟢 | [issues] |
| Password Storage | [Method] | 🔴/🟡/🟢 | [issues] |
| Session Management | [Implementation] | 🔴/🟡/🟢 | [issues] |

## 7. Integration Health

### 7.1 Integration Patterns
| Integration | Pattern | Error Handling | Retry Logic | Circuit Breaker | Status |
|-------------|---------|----------------|-------------|-----------------|--------|
| [System A] | [Sync/Async] | ✅/❌ | ✅/❌ | ✅/❌ | 🔴/🟡/🟢 |

### 7.2 Integration Risks
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| No timeout configured | High | High | Add timeouts |
| Missing retry logic | Medium | High | Implement retry |

## 8. Testing Assessment

### 8.1 Test Coverage
| Test Type | Test Count | Code Coverage | Quality |
|-----------|------------|---------------|---------|
| Unit Tests | [count] | [%] | 🔴/🟡/🟢 |
| Integration Tests | [count] | [%] | 🔴/🟡/🟢 |
| E2E Tests | [count] | [%] | 🔴/🟡/🟢 |

### 8.2 Test Quality
| Quality Metric | Status | Notes |
|----------------|--------|-------|
| Tests are automated | ✅/❌ | [CI/CD integration] |
| Tests are independent | ✅/❌ | [interdependencies] |

## 9. Operational Readiness

### 9.1 Observability
| Capability | Implementation | Maturity |
|------------|----------------|----------|
| Logging | [Framework] | 🔴/🟡/🟢 |
| Metrics | [Tool] | 🔴/🟡/🟢 |
| Tracing | [Tool] | 🔴/🟡/🟢 |
| Alerting | [Tool] | 🔴/🟡/🟢 |

### 9.2 Deployment Automation
| Aspect | Status | Details |
|--------|--------|---------|
| Build Automation | ✅/❌ | [tool/script] |
| Automated Testing in CI | ✅/❌ | [coverage %] |
| Deployment Automation | ✅/❌ | [manual steps?] |

## 10. Modernization Readiness Matrix

| Dimension | Current State | Future State | Gap | Priority |
|-----------|---------------|--------------|-----|----------|
| **Technology Currency** | [description] | Modern stack | [gap] | 🔴/🟡/🟢 |
| **Architecture Style** | [Monolith] | Microservices | [gap] | 🔴/🟡/🟢 |
| **Cloud Readiness** | [On-prem] | Cloud-native | [gap] | 🔴/🟡/🟢 |

**Overall Modernization Readiness: [Low / Medium / High]**

## 11. Strategic Recommendations

### 11.1 Immediate Actions (0-3 months)
**Priority: CRITICAL**
1. **[Action]**
   - Rationale: [why]
   - Effort: [hours/days]
   - Impact: [benefit]

### 11.2 Short-term Actions (3-6 months)
**Priority: HIGH**
[List actions]

### 11.3 Medium-term Actions (6-12 months)
**Priority: MEDIUM**
[List actions]

## 12. Assessment Summary

### Health Score Breakdown
```
Overall Health: [X]/100

Technology Stack:    [X]/20  ████████░░ [%]
Code Quality:        [X]/20  ████████░░ [%]
Architecture:        [X]/15  ████████░░ [%]
Security:            [X]/15  ████████░░ [%]
Performance:         [X]/10  ████████░░ [%]
```

---

## GENERATION GUIDELINES

1. **Be Data-Driven:** Every assessment must be backed by actual findings
2. **Use Scoring:** Provide numerical scores for quantitative comparison
3. **Risk-Based Prioritization:** Highlight critical issues that pose immediate risks
4. **Actionable Recommendations:** Every finding should have concrete remediation
5. **Visual Indicators:** Use emoji (🔴🟡🟢) for quick visual scanning
6. **Comprehensive Coverage:** Examine all aspects
7. **Business Context:** Link technical findings to business impact
8. **Create Urgency:** Explain the cost of delay
