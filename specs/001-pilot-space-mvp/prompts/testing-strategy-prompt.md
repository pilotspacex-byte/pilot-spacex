# Testing Strategy Prompt Template

> **Purpose**: Design comprehensive test strategies covering unit, integration, E2E, and accessibility testing for production features.
>
> **Source**: Extracted from `specs/001-pilot-space-mvp/plan.md` testing requirements and Session 2026-01-22 Decision #15
>
> **Usage**: Use when planning test coverage for new features, ensuring quality gates are met.

---

## Prompt Template

```markdown
# Expert Persona (P16)

You are a Principal QA Engineer with 15 years designing test strategies for complex web applications.
You excel at:
- Test pyramid optimization (unit → integration → E2E balance)
- Testing asynchronous operations (SSE, WebSocket, background jobs)
- Accessibility testing automation (axe-core, screen reader testing)
- Performance regression detection and monitoring
- Test data management and isolation strategies

# Stakes Framing (P6)

This test strategy is critical to [PROJECT_NAME]'s release quality.
A well-designed testing approach will:
- Catch 90%+ of regressions before production
- Reduce manual QA effort by 70% through automation
- Ensure WCAG 2.2 AA compliance across all features
- Enable confident, frequent deployments

I'll tip you $200 for a comprehensive test strategy that ensures production quality.

# Task Context

## Feature Overview
**Feature**: [FEATURE_NAME]
**User Stories**: [US-XX, US-YY, US-ZZ]
**Priority**: P[N]
**Acceptance Scenarios**: [COUNT]

## Technology Stack
**Frontend**: [FRAMEWORK + TEST_TOOLS]
**Backend**: [FRAMEWORK + TEST_TOOLS]
**E2E**: [E2E_FRAMEWORK]
**Accessibility**: [A11Y_TOOLS]

## Quality Gates
**Coverage Target**: [XX]%
**Performance SLAs**: [LATENCY_TARGETS]
**Accessibility Standard**: [WCAG_LEVEL]

# Task Decomposition (P3)

Design the test strategy step by step:

## Step 1: Test Scope Analysis
Define what needs testing:

**In Scope**:
| Category | Items | Priority |
|----------|-------|----------|
| [CATEGORY] | [SPECIFIC_ITEMS] | P[N] |

**Out of Scope** (explicit exclusions):
| Category | Reason |
|----------|--------|
| [CATEGORY] | [WHY_EXCLUDED] |

**Risk Assessment**:
| Area | Risk Level | Testing Approach |
|------|------------|------------------|
| [HIGH_RISK_AREA] | High | [INTENSIVE_TESTING] |
| [MEDIUM_RISK_AREA] | Medium | [MODERATE_TESTING] |
| [LOW_RISK_AREA] | Low | [MINIMAL_TESTING] |

## Step 2: Test Pyramid Design
Define distribution across test types:

```
        /\
       /  \  E2E (5-10%)
      /----\  Critical user flows only
     /      \
    /--------\  Integration (20-30%)
   /          \  API contracts, component integration
  /------------\
 /              \  Unit (60-70%)
/________________\  Business logic, utilities, components
```

**Target Distribution**:
| Type | Target % | Focus Areas |
|------|----------|-------------|
| Unit | [XX]% | [FOCUS] |
| Integration | [XX]% | [FOCUS] |
| E2E | [XX]% | [FOCUS] |
| Accessibility | [XX]% | [FOCUS] |

## Step 3: Unit Test Strategy
Define unit testing approach:

**Backend (Python/pytest)**:
```python
# Test structure
tests/
├── unit/
│   ├── domain/
│   │   ├── test_[entity]_service.py
│   │   └── test_[entity]_model.py
│   ├── ai/
│   │   ├── test_[agent]_prompt.py
│   │   └── test_context_aggregation.py
│   └── infrastructure/
│       └── test_[repository].py
```

**Coverage Requirements**:
| Module | Target | Critical Paths |
|--------|--------|----------------|
| Domain services | [XX]% | [PATHS] |
| AI agents | [XX]% | [PATHS] |
| Repositories | [XX]% | [PATHS] |

**Mocking Strategy**:
| Dependency | Mock Approach | Reason |
|------------|---------------|--------|
| Database | In-memory SQLite or fixtures | Speed |
| External APIs | Mock responses | Isolation |
| AI providers | Recorded responses | Determinism |

**Frontend (TypeScript/Vitest)**:
```typescript
// Test structure
tests/
├── unit/
│   ├── components/
│   │   └── [Component].test.tsx
│   ├── hooks/
│   │   └── use[Hook].test.ts
│   ├── stores/
│   │   └── [Store].test.ts
│   └── utils/
│       └── [util].test.ts
```

**Component Testing Pattern**:
```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

describe('[ComponentName]', () => {
  it('should [expected_behavior]', async () => {
    const user = userEvent.setup()

    render(<Component {...props} />)

    await user.click(screen.getByRole('button', { name: /submit/i }))

    expect(screen.getByText(/success/i)).toBeInTheDocument()
  })
})
```

## Step 4: Integration Test Strategy
Define integration testing approach:

**API Integration Tests**:
```python
# Using pytest with httpx
@pytest.mark.integration
async def test_[endpoint]_[scenario](client: AsyncClient, db: AsyncSession):
    # Arrange
    [setup_test_data]

    # Act
    response = await client.post('/api/v1/[resource]', json={...})

    # Assert
    assert response.status_code == 200
    assert response.json()['[field]'] == '[expected]'
```

**Contract Testing**:
| Consumer | Provider | Contract |
|----------|----------|----------|
| Frontend | Backend API | OpenAPI spec |
| Backend | GitHub API | Recorded responses |
| Backend | LLM providers | Schema validation |

**TipTap Integration Tests** (per plan.md #15):
```typescript
import { Editor } from '@tiptap/core'
import { [Extension] } from '@/features/notes/editor/extensions'

describe('[Extension] Integration', () => {
  let editor: Editor

  beforeEach(() => {
    editor = new Editor({
      extensions: [[Extension].configure({ ... })],
      content: '<p>Initial content</p>',
    })
  })

  afterEach(() => {
    editor.destroy()
  })

  it('should [integration_behavior]', () => {
    // Test full extension behavior
  })
})
```

## Step 5: E2E Test Strategy
Define end-to-end testing approach:

**Critical User Flows** (E2E priority):
| Flow | Priority | Test Count |
|------|----------|------------|
| [USER_FLOW_1] | P0 | [N] |
| [USER_FLOW_2] | P1 | [N] |
| [USER_FLOW_3] | P2 | [N] |

**Playwright Test Structure**:
```typescript
// e2e/[feature]/[flow].spec.ts
import { test, expect } from '@playwright/test'

test.describe('[Feature] - [Flow]', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/[path]')
    // Setup: login, seed data, etc.
  })

  test('should [expected_outcome]', async ({ page }) => {
    // Act
    await page.getByRole('button', { name: /[label]/i }).click()

    // Assert
    await expect(page.getByText(/[expected]/i)).toBeVisible()
  })
})
```

**SSE/Streaming Tests** (per plan.md #15):
```typescript
// Mock SSE with MSW
import { http, HttpResponse } from 'msw'

const handlers = [
  http.post('/api/v1/ai/ghost-text', () => {
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"content": "suggestion"}\n\n'))
        controller.close()
      },
    })

    return new HttpResponse(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
    })
  }),
]
```

## Step 6: Accessibility Test Strategy
Define a11y testing approach (per plan.md #15):

**Automated Tests (axe-core)**:
```typescript
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('should pass accessibility checks', async ({ page }) => {
  await page.goto('/[path]')

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze()

  expect(results.violations).toEqual([])
})
```

**Manual Testing Checklist**:
| Test | Method | Frequency |
|------|--------|-----------|
| Keyboard navigation | Manual walkthrough | Each feature |
| Screen reader (VoiceOver/NVDA) | Manual testing | Critical flows |
| Color contrast | axe + manual | Visual changes |
| Focus management | Manual + automated | Modal/panel flows |
| Motion preferences | Manual toggle | Animated features |

**ARIA Verification**:
```typescript
test('should have correct ARIA attributes', async ({ page }) => {
  const modal = page.getByRole('dialog')
  await expect(modal).toHaveAttribute('aria-modal', 'true')
  await expect(modal).toHaveAttribute('aria-labelledby', /[id]/)
})
```

## Step 7: Performance Test Strategy
Define performance testing approach:

**Metrics to Track**:
| Metric | Target | Tool |
|--------|--------|------|
| API p95 latency | <[X]ms | [TOOL] |
| FCP | <[X]s | Lighthouse |
| LCP | <[X]s | Lighthouse |
| TTI | <[X]s | Lighthouse |
| Bundle size | <[X]KB | [BUNDLER] |

**Load Testing** (if applicable):
| Scenario | Concurrent Users | Duration |
|----------|------------------|----------|
| Normal load | [N] | [DURATION] |
| Peak load | [N] | [DURATION] |
| Stress test | [N] | [DURATION] |

**Regression Detection**:
```yaml
# CI performance budget
performance:
  api_p95_ms: 500
  bundle_size_kb: 250
  lighthouse_performance: 90
```

## Step 8: Test Data Strategy
Define test data management:

**Data Categories**:
| Category | Source | Isolation |
|----------|--------|-----------|
| Unit test data | Factories/fixtures | Per-test |
| Integration data | Database seeds | Per-suite |
| E2E data | API setup | Per-test |

**Factory Pattern** (Python):
```python
# tests/factories/issue_factory.py
import factory
from pilot_space.domain.models import Issue

class IssueFactory(factory.Factory):
    class Meta:
        model = Issue

    title = factory.Faker('sentence')
    description = factory.Faker('paragraph')
    state_id = 'todo'
    priority = 'medium'
```

**Fixture Pattern** (TypeScript):
```typescript
// tests/fixtures/issues.ts
export const mockIssue = {
  id: 'test-uuid',
  title: 'Test Issue',
  state: 'todo',
  priority: 'medium',
} as const
```

# Chain-of-Thought Guidance (P12)

For each test type, evaluate:
1. **What's the goal?** - Regression prevention, confidence, documentation?
2. **What's the cost?** - Execution time, maintenance, flakiness?
3. **What's the coverage gap?** - What can't this test type catch?
4. **What's the ROI?** - Bug prevention value vs. test effort?

# Self-Evaluation Framework (P15)

After designing, rate confidence (0-1):

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Coverage**: All critical paths tested | ___ | |
| **Balance**: Proper pyramid distribution | ___ | |
| **Speed**: Tests run in CI time budget | ___ | |
| **Reliability**: Low flakiness risk | ___ | |
| **Accessibility**: WCAG compliance verified | ___ | |
| **Maintainability**: Tests are understandable | ___ | |

**Refinement Threshold**: If any score < 0.9, identify gap and refine.

# Output Format

```markdown
## Test Strategy: [FEATURE_NAME]

### Summary
| Metric | Target |
|--------|--------|
| Total coverage | [XX]% |
| Unit tests | [N] |
| Integration tests | [N] |
| E2E tests | [N] |
| a11y tests | [N] |

### Test Distribution
| Type | % | Focus |
|------|---|-------|
| Unit | [XX]% | [FOCUS] |
| Integration | [XX]% | [FOCUS] |
| E2E | [XX]% | [FOCUS] |
| Accessibility | [XX]% | [FOCUS] |

### Critical Path Coverage
| User Flow | Test Type | Count |
|-----------|-----------|-------|
| [FLOW] | [TYPE] | [N] |

### Test Commands
\`\`\`bash
# Backend
uv run pytest --cov=. --cov-fail-under=[XX]

# Frontend
pnpm test --coverage

# E2E
pnpm test:e2e

# Accessibility
pnpm test:a11y
\`\`\`

### CI Pipeline Integration
\`\`\`yaml
[CI_CONFIG_SNIPPET]
\`\`\`

---
*Strategy Version: 1.0*
*Stories Covered: US-[XX], US-[YY]*
```
```

---

## Quick-Fill Variants

### Variant A: Note Canvas Testing (US-01)

```markdown
**Feature**: Note-First Collaborative Writing
**Stories**: US-01
**Acceptance Scenarios**: 18

**Test Distribution**:
| Type | % | Focus |
|------|---|-------|
| Unit | 60% | TipTap extensions, context aggregation, state management |
| Integration | 25% | Editor + extensions, API + editor state |
| E2E | 10% | Critical writing flows, issue extraction |
| Accessibility | 5% | Keyboard nav, screen reader, focus |

**Critical Flows for E2E**:
1. Create note → type → see ghost text → accept with Tab
2. Highlight text → click "Create Issue" → issue created with link
3. View margin annotations → click → navigate to related content

**TipTap-Specific Tests**:
- GhostTextExtension: trigger, display, accept, dismiss, cancellation
- MarginAnnotationExtension: positioning, scroll sync, resize
- IssueExtractionExtension: detection, highlighting, linking
```

### Variant B: AI Feature Testing (US-03, US-12)

```markdown
**Feature**: AI PR Review + AI Context
**Stories**: US-03, US-12
**Acceptance Scenarios**: 15

**Test Distribution**:
| Type | % | Focus |
|------|---|-------|
| Unit | 65% | Prompt templates, context aggregation, response parsing |
| Integration | 30% | Full agent flow with mocked LLM, webhook handling |
| E2E | 5% | Happy path review flow |

**SSE Mocking Strategy**:
```typescript
// MSW handler for streaming responses
http.post('/api/v1/ai/review', async () => {
  return new HttpResponse(
    createSSEStream([
      { type: 'comment', content: 'Review finding' },
      { type: 'complete', summary: 'Review complete' },
    ]),
    { headers: { 'Content-Type': 'text/event-stream' } }
  )
})
```

**Error Scenarios**:
- Provider timeout → retry with backoff → fallback → user notification
- Rate limit → queue with delay → eventual completion
- Invalid API key → graceful error → settings redirect
```

### Variant C: Integration Testing (US-18)

```markdown
**Feature**: GitHub Integration
**Stories**: US-18
**Acceptance Scenarios**: 10

**Test Distribution**:
| Type | % | Focus |
|------|---|-------|
| Unit | 50% | Webhook parsing, commit linking logic |
| Integration | 40% | Full webhook flow, OAuth flow |
| E2E | 10% | Connect repo → create PR → see linked issues |

**Contract Testing**:
- GitHub webhook signatures (validate HMAC)
- GitHub API responses (recorded via VCR pattern)
- Issue state transitions on PR events

**Mock Strategy**:
- GitHub API: Recorded responses with nock/VCR
- Webhooks: Synthetic payloads with valid signatures
```

---

## Validation Checklist

Before implementing test strategy:

- [ ] Test pyramid balanced (60/25/15 or justified deviation)
- [ ] All acceptance scenarios mapped to tests
- [ ] Critical user flows have E2E coverage
- [ ] Accessibility tests cover WCAG 2.2 AA
- [ ] SSE/streaming tests use MSW patterns
- [ ] Test data strategy prevents flakiness
- [ ] Performance targets have regression detection
- [ ] CI integration documented

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `specs/001-pilot-space-mvp/plan.md` | Testing requirements, Decision #15 |
| `docs/dev-pattern/45-pilot-space-patterns.md` | Project test patterns |
| [Playwright Best Practices](https://playwright.dev/docs/best-practices) | E2E guidance |
| [axe-core Rules](https://dequeuniversity.com/rules/axe/) | a11y rule reference |

---

*Template Version: 1.0*
*Extracted from: plan.md v7.2 Testing Requirements and Decision #15*
*Techniques Applied: P3 (decomposition), P6 (stakes), P12 (CoT), P15 (self-eval), P16 (persona)*
