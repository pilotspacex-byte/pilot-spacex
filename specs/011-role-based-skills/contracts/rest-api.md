# API Contracts: Role-Based Skills

**Feature**: 011-role-based-skills
**Created**: 2026-02-06

---

## Endpoint 1: GET /api/v1/role-templates

**Auth**: Required (Bearer)
**Source**: FR-001, US1

List all predefined SDLC role templates for the role selection UI.

**Request**: No body. No query parameters.

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| templates | array | List of role template objects |
| templates[].id | UUID | Template ID |
| templates[].role_type | string | Enum key (e.g., "developer") |
| templates[].display_name | string | Human-readable name |
| templates[].description | string | Brief role description |
| templates[].icon | string | Frontend icon identifier |
| templates[].sort_order | integer | Display order |
| templates[].version | integer | Template version number |
| templates[].default_skill_content | string | Default SKILL.md content for "Use Default" and "Reset to Default" |

**Errors**:

| Status | Code | When |
|--------|------|------|
| 401 | UNAUTHORIZED | Missing or invalid auth token |

---

## Endpoint 2: GET /api/v1/workspaces/{workspace_id}/role-skills

**Auth**: Required (Bearer + workspace member)
**Source**: FR-009, US6

Get the current user's role skills for a specific workspace. Returns all configured roles and their skill content.

**Request**: No body.

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| workspace_id | UUID (path) | Yes | Workspace ID or slug |

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| skills | array | List of user's role skills in this workspace |
| skills[].id | UUID | Skill record ID |
| skills[].role_type | string | Role type (e.g., "developer", "custom") |
| skills[].role_name | string | Display name |
| skills[].skill_content | string | Full SKILL.md markdown content |
| skills[].experience_description | string\|null | User's input for AI generation |
| skills[].is_primary | boolean | Primary role flag |
| skills[].template_version | integer\|null | Version of template used |
| skills[].template_update_available | boolean | True if template has newer version |
| skills[].word_count | integer | Computed word count of skill_content |
| skills[].created_at | datetime | Creation timestamp |
| skills[].updated_at | datetime | Last update timestamp |

**Errors**:

| Status | Code | When |
|--------|------|------|
| 401 | UNAUTHORIZED | Missing or invalid auth token |
| 403 | FORBIDDEN | User is not a member of workspace |
| 404 | NOT_FOUND | Workspace not found |

---

## Endpoint 3: POST /api/v1/workspaces/{workspace_id}/role-skills

**Auth**: Required (Bearer + workspace member, not guest)
**Source**: FR-002, FR-018, FR-020, US1, US6

Create a new role skill for the current user in a workspace. Used both during onboarding and from the Skills settings tab.

**Request**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| role_type | string | Yes | One of predefined types or "custom" |
| role_name | string | Yes | 1-100 chars |
| skill_content | string | Yes | 1-15000 chars (~2000 words max) |
| experience_description | string | No | Max 5000 chars |
| is_primary | boolean | No | Default false. If true and another primary exists, demotes the other. |

**Response (201)**:

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Created skill ID |
| role_type | string | Role type |
| role_name | string | Display name |
| skill_content | string | Full skill content |
| experience_description | string\|null | User's input |
| is_primary | boolean | Primary flag |
| template_version | integer\|null | Template version used |
| word_count | integer | Computed word count |
| created_at | datetime | Creation timestamp |

**Errors**:

| Status | Code | When |
|--------|------|------|
| 400 | VALIDATION_ERROR | skill_content exceeds 15000 chars |
| 400 | MAX_ROLES_EXCEEDED | User already has 3 roles in this workspace |
| 401 | UNAUTHORIZED | Missing or invalid auth token |
| 403 | FORBIDDEN | User is guest (FR-020) |
| 404 | NOT_FOUND | Workspace not found |
| 409 | CONFLICT | User already has this role_type in workspace |

---

## Endpoint 4: PUT /api/v1/workspaces/{workspace_id}/role-skills/{skill_id}

**Auth**: Required (Bearer + skill owner)
**Source**: FR-009, FR-010, US6

Update an existing role skill's content or metadata.

**Request**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| role_name | string | No | 1-100 chars |
| skill_content | string | No | 1-15000 chars |
| is_primary | boolean | No | If true, demotes other primary |

**Response (200)**: Same shape as POST response.

**Errors**:

| Status | Code | When |
|--------|------|------|
| 400 | VALIDATION_ERROR | skill_content exceeds limit |
| 401 | UNAUTHORIZED | Missing or invalid auth token |
| 403 | FORBIDDEN | User does not own this skill |
| 404 | NOT_FOUND | Skill or workspace not found |

---

## Endpoint 5: DELETE /api/v1/workspaces/{workspace_id}/role-skills/{skill_id}

**Auth**: Required (Bearer + skill owner)
**Source**: FR-009, US6

Remove a role skill.

**Request**: No body.

**Response (204)**: No content.

**Errors**:

| Status | Code | When |
|--------|------|------|
| 401 | UNAUTHORIZED | Missing or invalid auth token |
| 403 | FORBIDDEN | User does not own this skill |
| 404 | NOT_FOUND | Skill or workspace not found |

---

## Endpoint 6: POST /api/v1/workspaces/{workspace_id}/role-skills/generate

**Auth**: Required (Bearer + workspace member, not guest)
**Source**: FR-003, FR-004, US2

Generate a role skill description using AI. Does NOT save — returns the generated content for preview. The user then calls POST (create) or PUT (update) to persist.

**Request**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| role_type | string | Yes | One of predefined types or "custom" |
| role_name | string | Yes | 1-100 chars |
| experience_description | string | Yes | 10-5000 chars (meaningful input required) |

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| skill_content | string | Generated SKILL.md content |
| word_count | integer | Word count of generated content |
| generation_model | string | Model used for generation |
| generation_time_ms | integer | Generation latency in ms |

**Errors**:

| Status | Code | When |
|--------|------|------|
| 400 | VALIDATION_ERROR | experience_description too short (<10 chars) |
| 401 | UNAUTHORIZED | Missing or invalid auth token |
| 403 | FORBIDDEN | User is guest |
| 422 | GENERATION_FAILED | AI provider unavailable or returned error |
| 429 | RATE_LIMITED | Too many generation requests (max 5/hour per user) |
| 503 | PROVIDER_UNAVAILABLE | AI provider circuit breaker open |

---

## Endpoint 7: POST /api/v1/workspaces/{workspace_id}/role-skills/{skill_id}/regenerate

**Auth**: Required (Bearer + skill owner)
**Source**: FR-003, FR-015, US6

Regenerate an existing skill with updated experience description. Returns preview — does NOT auto-save.

**Request**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| experience_description | string | Yes | 10-5000 chars |

**Response (200)**: Same shape as generate response, plus:

| Field | Type | Description |
|-------|------|-------------|
| previous_skill_content | string | Current skill content for comparison |

**Errors**: Same as generate endpoint, plus:

| Status | Code | When |
|--------|------|------|
| 404 | NOT_FOUND | Skill not found |

---

## Endpoint 8: PATCH /api/v1/auth/me (extend existing)

**Auth**: Required (Bearer)
**Source**: FR-011, US4

Update user profile. Extended to support `default_sdlc_role`. This extends the existing `PATCH /auth/me` endpoint in `backend/src/pilot_space/api/v1/routers/auth.py`.

**Request** (additional fields):

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| default_sdlc_role | string\|null | No | One of predefined role types, "custom", or null to clear |

**Response (200)**: Existing `UserProfileResponse` extended with:

| Field | Type | Description |
|-------|------|-------------|
| default_sdlc_role | string\|null | User's default SDLC role |

**Errors**: Existing error responses apply.

---

## Endpoint 9: POST /api/v1/workspaces/{workspace_id}/invitations (extend existing)

**Auth**: Required (Bearer + workspace admin)
**Source**: FR-012, US5

Create workspace invitation. Extended to support `suggested_sdlc_role`.

**Request** (additional fields):

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| suggested_sdlc_role | string | No | One of predefined role types or "custom" |

**Response**: Existing invitation response extended with:

| Field | Type | Description |
|-------|------|-------------|
| suggested_sdlc_role | string\|null | Owner's role hint |

**Errors**: Existing error responses apply.
