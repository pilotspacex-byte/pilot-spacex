---
name: summarize
description: Summarize content in various formats (bullet points, brief, detailed)
---

# Summarize Skill

Generate summaries of notes, issues, PR discussions, or documentation in multiple formats.

## Quick Start

Use this skill when:
- User requests summary (`/summarize`)
- Long note/issue needs TLDR
- PR review summary needed

**Example**:
```
Content: [Long discussion about authentication redesign - 500 words]

Summary (brief):
"Redesign auth to use JWT tokens instead of sessions. Requires DB schema
changes and API updates. Estimated 2 weeks. Security audit needed."

Summary (bullet):
- Replace session cookies with JWT tokens
- Update DB schema for refresh tokens
- Modify login/logout API endpoints
- Conduct security review before deployment
- Estimated: 2 weeks (1 backend + 1 testing)
```

## Workflow

1. **Analyze Content**
   - Identify content type (note, issue, PR, docs)
   - Extract key points and decisions
   - Detect action items and owners
   - Find technical details and requirements

2. **Choose Summary Format**
   - **Bullet**: Quick scan, action-oriented
   - **Brief**: Single paragraph TLDR
   - **Detailed**: Multi-paragraph with sections
   - **Executive**: Business-focused, non-technical

3. **Generate Summary**
   - Preserve critical information (dates, numbers, names)
   - Maintain technical accuracy
   - Highlight decisions and action items
   - Include confidence tag if summarizing recommendations

4. **Validate Completeness**
   - No information loss of critical facts
   - Preserves author intent
   - Maintains chronological order if relevant

## Output Format

```json
{
  "format": "bullet",
  "summary": "- Point 1\n- Point 2\n- Point 3",
  "confidence": "RECOMMENDED",
  "word_count": {
    "original": 500,
    "summary": 45,
    "compression_ratio": 0.09
  },
  "key_points": [
    {"type": "decision", "text": "Use JWT tokens"},
    {"type": "action", "text": "Security audit needed", "owner": "security-team"},
    {"type": "estimate", "text": "2 weeks development"}
  ],
  "missing_info": [
    "Timeline for security audit not specified",
    "Rollback strategy not discussed"
  ]
}
```

## Examples

### Example 1: Issue Summary (Bullet Format)
**Input**:
```
Issue: "Implement OAuth 2.0 login"
Description: [300 word description of OAuth flow, requirements, providers]
Comments: [5 comments discussing implementation approach]
```

**Output**:
```json
{
  "format": "bullet",
  "summary": "**Objective**: Add OAuth 2.0 login with Google and GitHub\n\n**Key Requirements**:\n- Support Google and GitHub providers\n- Store OAuth tokens securely in Supabase Vault\n- Maintain existing email/password login\n- Auto-link OAuth accounts to existing users by email\n\n**Technical Approach**:\n- Use Supabase Auth OAuth providers\n- Add oauth_providers table for token storage\n- Implement account linking logic\n\n**Timeline**:\n- Backend: 3 days\n- Frontend: 2 days\n- Testing: 1 day\n- Total: 1 week\n\n**Concerns**:\n- Security review needed before production\n- Consider rate limiting for OAuth endpoints",
  "confidence": "RECOMMENDED"
}
```

### Example 2: Note Summary (Brief Format)
**Input**:
```
[500 word brainstorming note about redesigning the dashboard]
```

**Output**:
```json
{
  "format": "brief",
  "summary": "Dashboard redesign focuses on three areas: (1) real-time activity feed showing recent updates, (2) advanced filtering by project/priority/assignee, and (3) customizable widgets for metrics. Proposed implementation uses WebSocket for real-time updates and MobX for state management. Estimated 2 sprints, with design phase in Sprint 1 and development in Sprint 2. Key risk: performance with 1000+ activity items, requires pagination strategy.",
  "confidence": "RECOMMENDED",
  "word_count": {
    "original": 500,
    "summary": 82,
    "compression_ratio": 0.16
  }
}
```

### Example 3: PR Discussion Summary (Detailed Format)
**Input**:
```
[PR #123 with 20 comments discussing architecture changes]
```

**Output**:
```json
{
  "format": "detailed",
  "summary": "## PR #123: Refactor authentication layer\n\n### Overview\nRefactors JWT authentication to support refresh token rotation and improves security posture.\n\n### Key Changes\n- Implements refresh token rotation per OWASP guidelines\n- Adds Redis caching for token blacklist\n- Updates API middleware to validate both access and refresh tokens\n\n### Discussion Highlights\n**Security** (@alice): Suggested adding rate limiting to token refresh endpoint (5 req/min per user). ✅ Implemented in latest commit.\n\n**Performance** (@bob): Raised concern about Redis latency. Resolution: Added connection pooling and 1s timeout.\n\n**Testing** (@charlie): Requested integration tests for token rotation. ✅ Added 8 test cases covering happy path and edge cases.\n\n### Decision Log\n- ✅ Use Redis for token blacklist (vs. database)\n- ✅ 15-minute access token TTL\n- ✅ 7-day refresh token TTL\n- ⏳ Deferred: Device fingerprinting (Phase 2)\n\n### Status\nReady for merge pending security team approval (requested 2024-01-25).",
  "confidence": "RECOMMENDED"
}
```

### Example 4: Documentation Summary (Executive Format)
**Input**:
```
[20-page technical architecture document]
```

**Output**:
```json
{
  "format": "executive",
  "summary": "**Business Impact**: New architecture reduces API response time by 60% (5s → 2s) and supports 10x user growth without infrastructure changes.\n\n**Investment**: 4 weeks development, $15k infrastructure costs (Redis cluster, CDN).\n\n**Key Benefits**:\n- Improved user experience (faster page loads)\n- Reduced server costs (efficient caching)\n- Better scalability (supports 100k concurrent users)\n\n**Risks**:\n- Migration downtime: 2 hours (mitigated with blue-green deployment)\n- Learning curve for team (mitigated with training sessions)\n\n**Timeline**: Design (1 week) → Development (2 weeks) → Testing (1 week) → Deploy (phased rollout over 2 weeks)\n\n**Recommendation**: Approve for Q1 roadmap. ROI positive within 6 months through reduced infrastructure costs.",
  "confidence": "RECOMMENDED"
}
```

## Summary Formats

| Format | Length | Use Case | Audience |
|--------|--------|----------|----------|
| **Bullet** | 50-100 words | Quick reference, action items | Developers, PMs |
| **Brief** | 80-150 words | TLDR, email summaries | All stakeholders |
| **Detailed** | 200-300 words | Comprehensive overview with sections | Technical leads |
| **Executive** | 150-200 words | Business impact, high-level decisions | Management, executives |

## Compression Guidelines

| Content Length | Target Compression | Max Summary Length |
|----------------|--------------------|--------------------|
| < 200 words | No summary needed | N/A |
| 200-500 words | 20-30% | 100-150 words |
| 500-1000 words | 10-20% | 100-200 words |
| 1000+ words | 5-15% | 150-300 words |

## Quality Checklist

✅ **Accuracy**: All facts and numbers preserved
✅ **Completeness**: No critical information lost
✅ **Clarity**: Non-technical stakeholders can understand
✅ **Actionable**: Decisions and next steps clear
✅ **Concise**: No redundancy or filler

❌ **Avoid**:
- Changing author's intent
- Omitting important caveats or risks
- Adding information not in source
- Using vague language ("some people think", "maybe")

## Integration Points

- **Note Canvas**: Auto-generate note summaries for previews
- **Issue Lists**: Show brief summaries instead of full descriptions
- **PR Reviews**: Summarize discussion threads
- **Activity Feed**: Summarize daily/weekly activity
- **Approval Flow**: Summaries are AUTO_EXECUTE (non-destructive)

## References

- Design Decision: DD-048 (Confidence Tagging)
- Compression Target: 10-30% of original length
- Readability: Flesch Reading Ease 60+ for executive summaries
