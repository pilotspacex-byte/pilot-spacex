# API Contracts: Workspace Feature Toggles

**Feature Branch**: `024-workspace-feature-toggles`
**Created**: 2026-03-18
**Base Path**: `/api/v1/workspaces/{workspace_id}/feature-toggles`

---

## Endpoints

### GET `/api/v1/workspaces/{workspace_id}/feature-toggles`

Retrieve the current feature toggle state for the workspace.

**Access**: All authenticated workspace members (any role).

**Response** `200 OK`:
```json
{
  "notes": true,
  "issues": false,
  "projects": false,
  "members": true,
  "docs": false,
  "skills": true,
  "costs": false,
  "approvals": false
}
```

**Errors**:
- `401 Unauthorized` — not authenticated
- `403 Forbidden` — not a workspace member
- `404 Not Found` — workspace does not exist

---

### PATCH `/api/v1/workspaces/{workspace_id}/feature-toggles`

Update one or more feature toggles. Only provided fields are updated; omitted fields remain unchanged.

**Access**: `owner` or `admin` role only.

**Request Body** (partial update):
```json
{
  "issues": true,
  "docs": true
}
```

All fields are optional booleans. At least one field must be provided.

**Response** `200 OK` (returns full updated state):
```json
{
  "notes": true,
  "issues": true,
  "projects": false,
  "members": true,
  "docs": true,
  "skills": true,
  "costs": false,
  "approvals": false
}
```

**Errors**:
- `401 Unauthorized` — not authenticated
- `403 Forbidden` — user is not admin/owner
- `404 Not Found` — workspace does not exist
- `422 Unprocessable Entity` — invalid field values (e.g., non-boolean)

---

## OpenAPI Schema

```yaml
openapi: 3.1.0
info:
  title: Workspace Feature Toggles API
  version: 1.0.0

paths:
  /api/v1/workspaces/{workspace_id}/feature-toggles:
    parameters:
      - name: workspace_id
        in: path
        required: true
        schema:
          type: string
          format: uuid

    get:
      operationId: getFeatureToggles
      summary: Get workspace feature toggles
      description: >
        Returns the current feature toggle state for all sidebar modules.
        Accessible to any authenticated workspace member.
      tags:
        - Workspace Settings
      responses:
        '200':
          description: Feature toggle state
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WorkspaceFeatureToggles'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'

    patch:
      operationId: updateFeatureToggles
      summary: Update workspace feature toggles
      description: >
        Partially update feature toggles. Only provided fields are changed.
        Restricted to workspace owner or admin.
      tags:
        - Workspace Settings
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/WorkspaceFeatureTogglesUpdate'
      responses:
        '200':
          description: Updated feature toggle state
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WorkspaceFeatureToggles'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '422':
          $ref: '#/components/responses/ValidationError'

components:
  schemas:
    WorkspaceFeatureToggles:
      type: object
      required:
        - notes
        - issues
        - projects
        - members
        - docs
        - skills
        - costs
        - approvals
      properties:
        notes:
          type: boolean
          description: Notes module enabled
        issues:
          type: boolean
          description: Issue tracker module enabled
        projects:
          type: boolean
          description: Project management module enabled
        members:
          type: boolean
          description: Member directory module enabled
        docs:
          type: boolean
          description: Documentation module enabled
        skills:
          type: boolean
          description: AI Skills module enabled
        costs:
          type: boolean
          description: AI cost tracking module enabled
        approvals:
          type: boolean
          description: AI approval workflow module enabled

    WorkspaceFeatureTogglesUpdate:
      type: object
      minProperties: 1
      properties:
        notes:
          type: boolean
        issues:
          type: boolean
        projects:
          type: boolean
        members:
          type: boolean
        docs:
          type: boolean
        skills:
          type: boolean
        costs:
          type: boolean
        approvals:
          type: boolean

  responses:
    Unauthorized:
      description: Authentication required
      content:
        application/problem+json:
          schema:
            type: object
            properties:
              type:
                type: string
              title:
                type: string
              status:
                type: integer
              detail:
                type: string
    Forbidden:
      description: Insufficient permissions
      content:
        application/problem+json:
          schema:
            type: object
            properties:
              type:
                type: string
              title:
                type: string
              status:
                type: integer
              detail:
                type: string
    NotFound:
      description: Workspace not found
      content:
        application/problem+json:
          schema:
            type: object
            properties:
              type:
                type: string
              title:
                type: string
              status:
                type: integer
              detail:
                type: string
    ValidationError:
      description: Request validation failed
      content:
        application/problem+json:
          schema:
            type: object
            properties:
              type:
                type: string
              title:
                type: string
              status:
                type: integer
              detail:
                type: string
```
