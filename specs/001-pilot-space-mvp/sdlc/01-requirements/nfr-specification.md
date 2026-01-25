# Non-Functional Requirements (NFR) Specification

**Version**: 1.0 | **Date**: 2026-01-23 | **Branch**: `001-pilot-space-mvp`

---

## Overview

This document defines the non-functional requirements (quality attributes) for Pilot Space MVP. Each NFR includes measurable criteria, testing approach, and implementation guidance.

---

## 1. Performance Requirements

### NFR-001: API Read Latency
| Attribute | Value |
|-----------|-------|
| **Description** | API GET operations must respond quickly |
| **Target** | p95 < 500ms, p99 < 1s |
| **Measurement** | Server-side response time (excluding network) |
| **Testing** | Load testing with k6 at 100 concurrent users |
| **Implementation** | Query optimization, database indexing, Redis caching |

### NFR-002: API Write Latency
| Attribute | Value |
|-----------|-------|
| **Description** | API POST/PUT/DELETE operations must complete quickly |
| **Target** | p95 < 1s, p99 < 2s |
| **Measurement** | Server-side response time including database writes |
| **Testing** | Load testing with k6 at 50 concurrent writes |
| **Implementation** | Async processing, queue for non-critical operations |

### NFR-003: Ghost Text Response Time
| Attribute | Value |
|-----------|-------|
| **Description** | AI ghost text suggestions must appear quickly |
| **Target** | < 2s from 500ms typing pause |
| **Measurement** | Client-side time from trigger to first token |
| **Testing** | E2E tests with AI response mocking |
| **Implementation** | Gemini Flash for latency, response streaming |

### NFR-004: PR Review Completion
| Attribute | Value |
|-----------|-------|
| **Description** | AI PR review must complete within reasonable time |
| **Target** | < 5 minutes for typical PR |
| **Measurement** | Time from webhook to review posted |
| **Testing** | Integration tests with real GitHub PRs |
| **Implementation** | Claude Opus for quality, parallel file analysis |

### NFR-005: Search Latency
| Attribute | Value |
|-----------|-------|
| **Description** | Search results must return quickly |
| **Target** | < 2s for workspaces with 10K items |
| **Measurement** | Client-side time from query to results |
| **Testing** | Load testing with 10K document dataset |
| **Implementation** | Meilisearch with proper indexing |

### NFR-006: Note Canvas Performance
| Attribute | Value |
|-----------|-------|
| **Description** | Note canvas must maintain smooth rendering |
| **Target** | 60fps with 1000+ blocks |
| **Measurement** | Browser DevTools performance profiling |
| **Testing** | Performance tests with large documents |
| **Implementation** | @tanstack/react-virtual virtualization |

---

## 2. Availability Requirements

### NFR-007: Service Availability
| Attribute | Value |
|-----------|-------|
| **Description** | Platform must be available for users |
| **Target** | 99.5% monthly uptime (~3.6 hours/month downtime) |
| **Measurement** | External uptime monitoring |
| **Testing** | Chaos engineering, failover testing |
| **Implementation** | Supabase managed hosting, health checks |

### NFR-008: Recovery Time Objective (RTO)
| Attribute | Value |
|-----------|-------|
| **Description** | Time to recover from major outage |
| **Target** | 4 hours |
| **Measurement** | Time from incident detection to service restoration |
| **Testing** | Disaster recovery drills |
| **Implementation** | Automated backups, documented runbooks |

### NFR-009: Recovery Point Objective (RPO)
| Attribute | Value |
|-----------|-------|
| **Description** | Maximum acceptable data loss |
| **Target** | 1 hour |
| **Measurement** | Time between backup points |
| **Testing** | Backup/restore testing |
| **Implementation** | Supabase PITR (Point-in-Time Recovery) |

---

## 3. Scalability Requirements

### NFR-010: Concurrent Users
| Attribute | Value |
|-----------|-------|
| **Description** | Support simultaneous users per workspace |
| **Target** | 100 concurrent users without degradation |
| **Measurement** | Response times under load |
| **Testing** | Load testing with simulated user behavior |
| **Implementation** | Connection pooling, caching, horizontal scaling |

### NFR-011: Issue Volume
| Attribute | Value |
|-----------|-------|
| **Description** | Support large issue databases |
| **Target** | 50,000 issues per workspace |
| **Measurement** | Query performance at scale |
| **Testing** | Performance testing with seeded data |
| **Implementation** | Database indexing, pagination, archival |

### NFR-012: Workspace Limit
| Attribute | Value |
|-----------|-------|
| **Description** | Support multiple workspaces |
| **Target** | Unlimited workspaces per account |
| **Measurement** | No hard limits |
| **Testing** | Multi-tenant isolation testing |
| **Implementation** | Row-Level Security (RLS) |

### NFR-013: Team Size
| Attribute | Value |
|-----------|-------|
| **Description** | Support team sizes |
| **Target** | 5-100 members per workspace |
| **Measurement** | Permission and collaboration features work at scale |
| **Testing** | Functional testing with large teams |
| **Implementation** | Efficient member queries, cached permissions |

---

## 4. Security Requirements

### NFR-014: Encryption at Rest
| Attribute | Value |
|-----------|-------|
| **Description** | All stored data must be encrypted |
| **Target** | AES-256 encryption |
| **Measurement** | Security audit |
| **Testing** | Penetration testing |
| **Implementation** | Supabase managed encryption |

### NFR-015: Encryption in Transit
| Attribute | Value |
|-----------|-------|
| **Description** | All network communication encrypted |
| **Target** | TLS 1.3 |
| **Measurement** | SSL Labs score A+ |
| **Testing** | SSL/TLS scanning |
| **Implementation** | HTTPS everywhere, HSTS headers |

### NFR-016: API Rate Limiting
| Attribute | Value |
|-----------|-------|
| **Description** | Prevent API abuse |
| **Target** | 1000 requests/minute standard, 100/minute AI |
| **Measurement** | Rate limit headers in responses |
| **Testing** | Rate limit bypass testing |
| **Implementation** | Redis-based sliding window rate limiter |

### NFR-017: API Key Security
| Attribute | Value |
|-----------|-------|
| **Description** | BYOK API keys must be securely stored |
| **Target** | AES-256-GCM encryption in Supabase Vault |
| **Measurement** | Security audit |
| **Testing** | Key extraction attempts |
| **Implementation** | Supabase Vault, never in plaintext |

### NFR-018: Session Security
| Attribute | Value |
|-----------|-------|
| **Description** | Secure session management |
| **Target** | Access token 1h, refresh token 7d |
| **Measurement** | Token expiry testing |
| **Testing** | Session hijacking attempts |
| **Implementation** | Supabase Auth, HttpOnly cookies |

### NFR-019: Input Validation
| Attribute | Value |
|-----------|-------|
| **Description** | All inputs must be validated |
| **Target** | No injection vulnerabilities |
| **Measurement** | OWASP ZAP scan |
| **Testing** | Penetration testing |
| **Implementation** | Pydantic validation, parameterized queries |

### NFR-020: OWASP Compliance
| Attribute | Value |
|-----------|-------|
| **Description** | Address OWASP Top 10 vulnerabilities |
| **Target** | No critical/high findings |
| **Measurement** | Security scan results |
| **Testing** | OWASP ZAP, Snyk |
| **Implementation** | Security checklist, code review |

---

## 5. Accessibility Requirements

### NFR-021: WCAG Compliance Level
| Attribute | Value |
|-----------|-------|
| **Description** | Web Content Accessibility Guidelines compliance |
| **Target** | WCAG 2.1 Level AA |
| **Measurement** | Automated + manual accessibility audit |
| **Testing** | axe-core in CI, manual screen reader testing |
| **Implementation** | Design system with accessibility built-in |

### NFR-022: Keyboard Navigation
| Attribute | Value |
|-----------|-------|
| **Description** | All features accessible via keyboard |
| **Target** | 100% keyboard navigable |
| **Measurement** | Manual testing |
| **Testing** | Keyboard-only user testing |
| **Implementation** | Focus management, keyboard shortcuts |

### NFR-023: Screen Reader Support
| Attribute | Value |
|-----------|-------|
| **Description** | Compatible with screen readers |
| **Target** | Full support for NVDA, VoiceOver, JAWS |
| **Measurement** | Screen reader user testing |
| **Testing** | Manual testing with screen readers |
| **Implementation** | ARIA labels, roles, live regions |

### NFR-024: Color Contrast
| Attribute | Value |
|-----------|-------|
| **Description** | Sufficient color contrast for readability |
| **Target** | 4.5:1 for normal text, 3:1 for large text |
| **Measurement** | Color contrast checker |
| **Testing** | Automated contrast checking |
| **Implementation** | Design system color palette |

### NFR-025: Motion Preferences
| Attribute | Value |
|-----------|-------|
| **Description** | Respect user motion preferences |
| **Target** | Honor prefers-reduced-motion |
| **Measurement** | Manual testing |
| **Testing** | OS accessibility settings |
| **Implementation** | CSS media queries, Tailwind motion-* variants |

### NFR-026: Touch Targets
| Attribute | Value |
|-----------|-------|
| **Description** | Interactive elements sufficiently large |
| **Target** | Minimum 44x44px |
| **Measurement** | Design review |
| **Testing** | Mobile device testing |
| **Implementation** | Component size constraints |

---

## 6. Reliability Requirements

### NFR-027: Error Rate
| Attribute | Value |
|-----------|-------|
| **Description** | API error rate threshold |
| **Target** | < 0.1% 5xx errors |
| **Measurement** | Error rate monitoring |
| **Testing** | Load testing, chaos engineering |
| **Implementation** | Error handling, circuit breakers |

### NFR-028: AI Fallback
| Attribute | Value |
|-----------|-------|
| **Description** | AI features degrade gracefully |
| **Target** | Fallback to alternate provider within 5s |
| **Measurement** | Provider failover testing |
| **Testing** | Provider outage simulation |
| **Implementation** | Provider routing with automatic failover |

### NFR-029: Data Integrity
| Attribute | Value |
|-----------|-------|
| **Description** | Data consistency across operations |
| **Target** | No data corruption or loss |
| **Measurement** | Data validation checks |
| **Testing** | Transaction testing, concurrent write testing |
| **Implementation** | Database transactions, optimistic locking |

---

## 7. Maintainability Requirements

### NFR-030: Code Coverage
| Attribute | Value |
|-----------|-------|
| **Description** | Test coverage threshold |
| **Target** | > 80% coverage |
| **Measurement** | Coverage reports |
| **Testing** | pytest-cov, Jest coverage |
| **Implementation** | Coverage gates in CI |

### NFR-031: File Size Limit
| Attribute | Value |
|-----------|-------|
| **Description** | Maximum file size for maintainability |
| **Target** | 700 lines maximum |
| **Measurement** | Pre-commit hook |
| **Testing** | CI enforcement |
| **Implementation** | Pre-commit hooks |

### NFR-032: Type Safety
| Attribute | Value |
|-----------|-------|
| **Description** | Static type checking |
| **Target** | 100% type coverage, strict mode |
| **Measurement** | Type checker reports |
| **Testing** | pyright, tsc strict mode |
| **Implementation** | CI quality gates |

### NFR-033: Documentation Coverage
| Attribute | Value |
|-----------|-------|
| **Description** | API and code documentation |
| **Target** | All public APIs documented |
| **Measurement** | Documentation review |
| **Testing** | Doc generation |
| **Implementation** | Docstrings, OpenAPI |

---

## 8. Usability Requirements

### NFR-034: Time to First Value
| Attribute | Value |
|-----------|-------|
| **Description** | Time for new user to create first issue |
| **Target** | < 5 minutes |
| **Measurement** | User testing |
| **Testing** | Onboarding flow testing |
| **Implementation** | Sample project, guided tour |

### NFR-035: Learning Curve
| Attribute | Value |
|-----------|-------|
| **Description** | Time to become proficient |
| **Target** | < 1 hour for basic workflows |
| **Measurement** | User testing |
| **Testing** | Usability studies |
| **Implementation** | Intuitive UI, contextual help |

### NFR-036: Error Messages
| Attribute | Value |
|-----------|-------|
| **Description** | Error messages are helpful |
| **Target** | All errors include actionable guidance |
| **Measurement** | Error message audit |
| **Testing** | Error scenario testing |
| **Implementation** | RFC 7807 Problem Details |

---

## 9. Browser Compatibility

### NFR-037: Supported Browsers
| Attribute | Value |
|-----------|-------|
| **Description** | Browser compatibility |
| **Target** | Latest 2 versions of Chrome, Firefox, Safari, Edge |
| **Measurement** | Browser testing |
| **Testing** | Cross-browser testing (Playwright) |
| **Implementation** | Feature detection, polyfills |

### NFR-038: Mobile Responsiveness
| Attribute | Value |
|-----------|-------|
| **Description** | Responsive design |
| **Target** | Functional on tablet (768px+), read-only on mobile |
| **Measurement** | Responsive testing |
| **Testing** | Device testing |
| **Implementation** | Tailwind breakpoints |

---

## Compliance Matrix

| Category | NFRs | Priority | Status |
|----------|------|----------|--------|
| Performance | NFR-001 to NFR-006 | P0 | Planned |
| Availability | NFR-007 to NFR-009 | P0 | Planned |
| Scalability | NFR-010 to NFR-013 | P1 | Planned |
| Security | NFR-014 to NFR-020 | P0 | Planned |
| Accessibility | NFR-021 to NFR-026 | P1 | Planned |
| Reliability | NFR-027 to NFR-029 | P1 | Planned |
| Maintainability | NFR-030 to NFR-033 | P2 | Planned |
| Usability | NFR-034 to NFR-036 | P2 | Planned |
| Compatibility | NFR-037 to NFR-038 | P2 | Planned |

---

## References

- [DESIGN_DECISIONS.md](../../../../docs/DESIGN_DECISIONS.md) - Architecture decisions
- [spec.md](../../spec.md) - Functional requirements
- [plan.md](../../plan.md) - Performance targets
