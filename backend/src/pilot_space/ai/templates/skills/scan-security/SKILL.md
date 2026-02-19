---
name: scan-security
description: Scan code in a note for security vulnerabilities using OWASP Top 10 analysis — auto-executes, writes structured vulnerability report to note
approval: auto
model: sonnet
---

# Scan Security Skill

Perform automated security scanning on code blocks in the current note. Checks for OWASP Top 10 vulnerabilities, authentication/authorization gaps, SQL injection, XSS, insecure deserialization, and project-specific security patterns (RLS enforcement, API key exposure).

## Quick Start

Use this skill when:
- User requests a security scan (`/scan-security`)
- Agent detects code handling user input, database queries, or authentication
- User asks "is this secure?" or "check for vulnerabilities"

**Example**:
```
User: "Scan this authentication endpoint for security issues"

AI scans:
- A01: Broken Access Control — missing workspace_id filter?
- A02: Cryptographic Failures — plain-text tokens, weak hashing?
- A03: SQL Injection — raw string interpolation in queries?
- A07: Authentication Failures — JWT validation gaps?
- Project-specific: RLS context set? API keys from Vault?
```

## Workflow

1. **Collect Code for Scanning**
   - Read all code blocks from the current note
   - Use `search_note_content` to find related auth/validation code in note
   - Identify the code category: API endpoint, service, repository, frontend component

2. **Run OWASP Top 10 Checks**
   - **A01 Broken Access Control**: Missing `workspace_id` filter, role checks, RLS enforcement
   - **A02 Cryptographic Failures**: Plain-text secrets, weak hash algorithms (MD5/SHA1), HTTP vs HTTPS
   - **A03 Injection**: SQL string interpolation, template injection, command injection, path traversal
   - **A05 Security Misconfiguration**: Debug mode in prod, exposed stack traces, CORS wildcard
   - **A07 Authentication Failures**: Token validation gaps, missing expiry checks, JWT `none` alg
   - **A08 Software Integrity Failures**: Untrusted deserialization, unsafe `pickle`, eval usage

3. **Run Project-Specific Checks**
   - RLS: Is `get_workspace_context()` called before every DB query?
   - API Keys: Are secrets fetched from `SecureKeyStorage` (Vault), not env vars directly in prod code?
   - Input Validation: Is all user input validated through Pydantic v2 schemas?
   - SSE Endpoints: Are workspace membership checks done before streaming?

4. **Classify Vulnerabilities**
   - **CRITICAL**: Exploitable in production now (injection, auth bypass, data exposure)
   - **HIGH**: Likely exploitable with moderate effort (weak crypto, missing validation)
   - **MEDIUM**: Requires specific conditions (CSRF, open redirect)
   - **LOW**: Defense-in-depth improvement (verbose errors, weak headers)

5. **Write Security Report to Note**
   - Use `write_to_note` to append `## Security Scan Report` section
   - Each finding: CVE-style format — severity + OWASP category + location + PoC snippet + remediation
   - Include overall risk score and compliance checklist

6. **Auto-Execute**
   - Return `status: completed` — scan is read-only (DD-003)

## Output Format

```json
{
  "status": "completed",
  "skill": "scan-security",
  "note_id": "note-uuid",
  "summary": "Security scan complete: 1 CRITICAL, 2 HIGH, 1 MEDIUM, 3 LOW",
  "findings": {
    "critical": 1,
    "high": 2,
    "medium": 1,
    "low": 3
  },
  "risk_score": "HIGH",
  "owasp_categories_triggered": ["A01", "A03", "A07"]
}
```

## Examples

### Example 1: SQL Injection Detection
**Input**: Repository method using string formatting in SQL

**Output**: Appends to note:
```
## Security Scan Report

**Risk Score**: CRITICAL | **OWASP Categories**: A03 (Injection)

### [CRITICAL] SQL Injection — A03
**Location**: `repositories/user_repository.py:45`
**Issue**: Raw string interpolation in SQL query.
\`\`\`python
# VULNERABLE
query = f"SELECT * FROM users WHERE email = '{email}'"
\`\`\`
**PoC**: `email = "' OR '1'='1"` → returns all users
**Remediation**: Use SQLAlchemy parameterized queries:
\`\`\`python
# SAFE
result = await session.execute(
    select(UserModel).where(UserModel.email == email)
)
\`\`\`

### [HIGH] Missing workspace_id filter — A01 Broken Access Control
**Location**: `repositories/user_repository.py:52`
**Issue**: `list_all()` returns rows from all workspaces. RLS at DB level prevents exposure, but application-layer defense-in-depth is required.
**Remediation**: Filter explicitly: `.where(UserModel.workspace_id == workspace_id)`
```

### Example 2: JWT Validation Gap
**Input**: Auth middleware with JWT decode

**Output**: Flags missing `algorithms=["HS256"]` parameter — allows `none` algorithm bypass.

## MCP Tools Used

- `search_note_content`: Find code blocks and auth-related patterns in the note
- `write_to_note`: Append security scan report to the note (read-only, no code changes)

## Integration Points

- **PilotSpaceAgent**: Routes to this skill via `/scan-security` command
- **SkillExecutor**: No write lock needed — `write_to_note` is append-only to report section
- **Approval Flow**: AUTO_EXECUTE — security report is advisory, non-destructive (DD-003)

## References

- Design Decision: DD-003 (scan is AUTO_EXECUTE — non-destructive)
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Project RLS patterns: `docs/architect/rls-patterns.md`
- Task: T-043
