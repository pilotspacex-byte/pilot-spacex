# Plane Database Schema & Data Flow Documentation

This document provides comprehensive documentation of Plane's database schema design, model relationships, and data flow architecture.

## Table of Contents

1. [Core Design Patterns](#core-design-patterns)
2. [Base Models & Mixins](#base-models--mixins)
3. [User & Authentication Models](#user--authentication-models)
4. [Workspace & Project Models](#workspace--project-models)
5. [Work Items (Issues) Models](#work-items-issues-models)
6. [Cycles & Modules Models](#cycles--modules-models)
7. [Pages (Wiki) Models](#pages-wiki-models)
8. [State & Workflow Models](#state--workflow-models)
9. [Integration Models](#integration-models)
10. [Supporting Models](#supporting-models)
11. [Data Flow Architecture](#data-flow-architecture)

---

## Core Design Patterns

### UUID Primary Keys
All models use UUID primary keys with `db_index=True` for efficient lookups:
```python
id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True, primary_key=True)
```

### Soft Deletion Pattern
Plane implements soft deletion across all models using a `deleted_at` timestamp:
- Records are never permanently deleted from the database
- `SoftDeletionManager` filters out soft-deleted records by default
- `all_objects` manager available for accessing deleted records
- Unique constraints include `deleted_at` to allow "re-creation" of deleted entities

### Audit Trail
All models inherit from `AuditModel` which provides:
- `created_at`: Auto-set on creation
- `updated_at`: Auto-updated on every save
- `created_by`: ForeignKey to User (auto-set via `crum.get_current_user()`)
- `updated_by`: ForeignKey to User (auto-set on updates)
- `deleted_at`: Soft deletion timestamp

### Change Tracking
`ChangeTrackerMixin` provides field-level change detection:
- Tracks specified fields via `TRACKED_FIELDS` list
- `changed_fields` property returns list of modified field names
- `has_changed(field_name)` checks specific field changes
- Used for syncing related models (e.g., `IssueComment` → `Description`)

---

## Base Models & Mixins

### TimeAuditModel
```
Fields:
- created_at: DateTimeField (auto_now_add)
- updated_at: DateTimeField (auto_now)
```

### UserAuditModel
```
Fields:
- created_by: FK → User (SET_NULL)
- updated_by: FK → User (SET_NULL)
```

### SoftDeleteModel
```
Fields:
- deleted_at: DateTimeField (nullable)

Managers:
- objects: SoftDeletionManager (excludes deleted)
- all_objects: Manager (includes deleted)
```

### BaseModel
Combines `TimeAuditModel` + `UserAuditModel` + `SoftDeleteModel` with UUID primary key.

### WorkspaceBaseModel
Extends `BaseModel` with:
```
Fields:
- workspace: FK → Workspace (CASCADE)
- project: FK → Project (CASCADE, nullable)
```

### ProjectBaseModel
Extends `BaseModel` with:
```
Fields:
- project: FK → Project (CASCADE)
- workspace: FK → Workspace (CASCADE, auto-set from project)
```

---

## User & Authentication Models

### User
**Table:** `users`

```
Primary Fields:
- id: UUID (PK)
- username: CharField(128) UNIQUE
- email: CharField(255) UNIQUE, nullable
- mobile_number: CharField(255), nullable

Identity Fields:
- display_name: CharField(255)
- first_name: CharField(255)
- last_name: CharField(255)
- avatar: TextField (URL)
- avatar_asset: FK → FileAsset
- cover_image: URLField(800)
- cover_image_asset: FK → FileAsset

Status Fields:
- is_superuser: Boolean (default: False)
- is_active: Boolean (default: True)
- is_staff: Boolean (default: False)
- is_email_verified: Boolean (default: False)
- is_password_autoset: Boolean (default: False)
- is_password_reset_required: Boolean (default: False)
- is_managed: Boolean (default: False)
- is_password_expired: Boolean (default: False)
- is_bot: Boolean (default: False)
- bot_type: CharField(30), nullable (WORKSPACE_SEED)
- is_email_valid: Boolean (default: False)

Tracking Fields:
- date_joined: DateTimeField (auto)
- created_at: DateTimeField (auto)
- updated_at: DateTimeField (auto)
- last_active: DateTimeField
- last_login_time: DateTimeField, nullable
- last_logout_time: DateTimeField, nullable
- last_login_ip: CharField(255)
- last_logout_ip: CharField(255)
- last_login_medium: CharField(20) (default: "email")
- last_login_uagent: TextField
- last_location: CharField(255)
- created_location: CharField(255)

Security Fields:
- token: CharField(64) (random token)
- token_updated_at: DateTimeField, nullable
- user_timezone: CharField(255) (default: "UTC")
- masked_at: DateTimeField, nullable
```

### Profile
**Table:** `profiles`

```
Fields:
- id: UUID (PK)
- user: OneToOne → User

General Settings:
- theme: JSONField (default: {})
- is_app_rail_docked: Boolean (default: True)
- language: CharField(255) (default: "en")
- start_of_the_week: PositiveSmallInteger (0-6, default: 0/Sunday)
- background_color: CharField(255) (random color)

Onboarding:
- is_tour_completed: Boolean (default: False)
- onboarding_step: JSONField (profile_complete, workspace_create, etc.)
- use_case: TextField, nullable
- role: CharField(300), nullable (job role)
- is_onboarded: Boolean (default: False)
- last_workspace_id: UUID, nullable

Mobile:
- is_mobile_onboarded: Boolean (default: False)
- mobile_onboarding_step: JSONField
- mobile_timezone_auto_set: Boolean (default: False)

Billing:
- billing_address_country: CharField(255) (default: "INDIA")
- billing_address: JSONField, nullable
- has_billing_address: Boolean (default: False)
- company_name: CharField(255)

Preferences:
- notification_view_mode: CharField (full/compact)
- is_smooth_cursor_enabled: Boolean (default: False)
- goals: JSONField (default: {})
- is_navigation_tour_completed: Boolean (default: False)
- has_marketing_email_consent: Boolean (default: False)
- is_subscribed_to_changelog: Boolean (default: False)
```

### Account (OAuth Connections)
**Table:** `accounts`

```
Fields:
- id: UUID (PK)
- user: FK → User (CASCADE)
- provider: CharField (google/github/gitlab)
- provider_account_id: CharField(255)
- access_token: TextField
- access_token_expired_at: DateTimeField, nullable
- refresh_token: TextField, nullable
- refresh_token_expired_at: DateTimeField, nullable
- last_connected_at: DateTimeField
- id_token: TextField
- metadata: JSONField (default: {})

Constraints:
- UNIQUE(provider, provider_account_id)
```

### Device
**Table:** `devices`

```
Fields:
- id: UUID (PK)
- user: FK → User (CASCADE)
- device_token: CharField(255)
- platform: CharField(30) (IOS/ANDROID/WEB)
- enabled: Boolean (default: True)
```

### DeviceSession
**Table:** `device_sessions`

```
Fields:
- id: UUID (PK)
- device: FK → Device (CASCADE)
- session_key: CharField(255)
- expires_at: DateTimeField, nullable
```

### APIToken
**Table:** `api_tokens`

```
Fields:
- id: UUID (PK)
- label: CharField(255) (auto-generated hex)
- description: TextField
- is_active: Boolean (default: True)
- last_used: DateTimeField, nullable
- token: CharField(255) UNIQUE (prefix: "plane_api_")
- user: FK → User (CASCADE)
- user_type: PositiveSmallInteger (0=Human, 1=Bot)
- workspace: FK → Workspace, nullable
- expired_at: DateTimeField, nullable
- is_service: Boolean (default: False)
- allowed_rate_limit: CharField(255) (default: "60/min")
```

### APIActivityLog
**Table:** `api_activity_logs`

```
Fields:
- id: UUID (PK)
- token_identifier: CharField(255)
- path: CharField(255)
- method: CharField(10)
- query_params: TextField, nullable
- headers: TextField, nullable
- body: TextField, nullable
- response_code: PositiveIntegerField
- response_body: TextField, nullable
- ip_address: GenericIPAddressField, nullable
- user_agent: CharField(512), nullable
```

---

## Workspace & Project Models

### Workspace
**Table:** `workspaces`

```
Fields:
- id: UUID (PK)
- name: CharField(80)
- logo: TextField, nullable
- logo_asset: FK → FileAsset, nullable
- owner: FK → User (CASCADE)
- slug: SlugField(48) UNIQUE, indexed
- organization_size: CharField(20), nullable
- timezone: CharField(255) (default: "UTC")
- background_color: CharField(255) (random)

Soft Delete Behavior:
- On soft delete, slug is appended with "__<timestamp>" to allow recreation
```

### WorkspaceMember
**Table:** `workspace_members`

```
Fields:
- id: UUID (PK)
- workspace: FK → Workspace (CASCADE)
- member: FK → User (CASCADE)
- role: PositiveSmallInteger (5=Guest, 15=Member, 20=Admin)
- company_role: TextField, nullable
- view_props: JSONField (filters, display_filters, display_properties)
- default_props: JSONField
- issue_props: JSONField (subscribed, assigned, created, all_issues)
- is_active: Boolean (default: True)
- getting_started_checklist: JSONField (default: {})
- tips: JSONField (default: {})
- explored_features: JSONField (default: {})

Constraints:
- UNIQUE(workspace, member) when deleted_at IS NULL
```

### WorkspaceMemberInvite
**Table:** `workspace_member_invites`

```
Fields:
- id: UUID (PK)
- workspace: FK → Workspace (CASCADE)
- email: CharField(255)
- accepted: Boolean (default: False)
- token: CharField(255)
- message: TextField, nullable
- responded_at: DateTimeField, nullable
- role: PositiveSmallInteger (default: 5/Guest)

Constraints:
- UNIQUE(email, workspace) when deleted_at IS NULL
```

### Team
**Table:** `teams`

```
Fields:
- id: UUID (PK)
- name: CharField(255)
- description: TextField
- workspace: FK → Workspace (CASCADE)
- logo_props: JSONField (default: {})

Constraints:
- UNIQUE(name, workspace) when deleted_at IS NULL
```

### Project
**Table:** `projects`

```
Fields:
- id: UUID (PK)
- name: CharField(255)
- description: TextField
- description_text: JSONField, nullable
- description_html: JSONField, nullable
- network: PositiveSmallInteger (0=Secret, 2=Public, default: 2)
- workspace: FK → Workspace (CASCADE)
- identifier: CharField(12), indexed (auto-uppercased)
- default_assignee: FK → User, nullable
- project_lead: FK → User, nullable
- emoji: CharField(255), nullable
- icon_prop: JSONField, nullable

Feature Flags:
- module_view: Boolean (default: False)
- cycle_view: Boolean (default: False)
- issue_views_view: Boolean (default: False)
- page_view: Boolean (default: True)
- intake_view: Boolean (default: False)
- is_time_tracking_enabled: Boolean (default: False)
- is_issue_type_enabled: Boolean (default: False)
- guest_view_all_features: Boolean (default: False)

Cover & Assets:
- cover_image: TextField, nullable
- cover_image_asset: FK → FileAsset, nullable
- logo_props: JSONField (default: {})

Configuration:
- estimate: FK → Estimate, nullable
- archive_in: Integer (0-12 months, default: 0)
- close_in: Integer (0-12 months, default: 0)
- default_state: FK → State, nullable
- archived_at: DateTimeField, nullable
- timezone: CharField(255) (inherits from workspace)
- external_source: CharField(255), nullable
- external_id: CharField(255), nullable

Constraints:
- UNIQUE(identifier, workspace) when deleted_at IS NULL
- UNIQUE(name, workspace) when deleted_at IS NULL
```

### ProjectMember
**Table:** `project_members`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- workspace: FK → Workspace (auto-set)
- member: FK → User (CASCADE), nullable
- comment: TextField, nullable
- role: PositiveSmallInteger (5=Guest, 15=Member, 20=Admin)
- view_props: JSONField
- default_props: JSONField
- preferences: JSONField (pages.block_display, navigation.default_tab)
- sort_order: Float (default: 65535)
- is_active: Boolean (default: True)

Constraints:
- UNIQUE(project, member) when deleted_at IS NULL

Side Effects:
- On creation, creates ProjectUserProperty with decremented sort_order
```

### ProjectIdentifier
**Table:** `project_identifiers`

```
Fields:
- project: OneToOne → Project (CASCADE)
- name: CharField(12), indexed
- workspace: FK → Workspace, nullable

Constraints:
- UNIQUE(name, workspace) when deleted_at IS NULL
```

---

## Work Items (Issues) Models

### Issue
**Table:** `issues`

```
Core Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- workspace: FK → Workspace (auto-set)
- name: CharField(255)
- description: JSONField (default: {})
- description_html: TextField (default: "<p></p>")
- description_stripped: TextField, nullable (auto-generated)
- description_binary: BinaryField, nullable (Y.js CRDT)

Hierarchy:
- parent: FK → Issue (CASCADE), self-referential, nullable
- sequence_id: Integer (auto-incremented per project)
- sort_order: Float (default: 65535)

Workflow:
- state: FK → State (CASCADE), nullable
- priority: CharField(30) (urgent/high/medium/low/none)
- type: FK → IssueType (SET_NULL), nullable

Estimates:
- point: Integer (0-12), nullable (deprecated)
- estimate_point: FK → EstimatePoint (SET_NULL), nullable

Dates:
- start_date: DateField, nullable
- target_date: DateField, nullable
- completed_at: DateTimeField, nullable (auto-set when state.group="completed")
- archived_at: DateField, nullable

Relationships:
- assignees: M2M → User (through IssueAssignee)
- labels: M2M → Label (through IssueLabel)

Flags:
- is_draft: Boolean (default: False)

External:
- external_source: CharField(255), nullable
- external_id: CharField(255), nullable

Managers:
- objects: Standard manager
- issue_objects: IssueManager (excludes triage, archived, draft, archived projects)

Sequence Generation:
- Uses PostgreSQL advisory lock (pg_advisory_xact_lock) per project
- Atomic increment via IssueSequence model
```

### IssueSequence
**Table:** `issue_sequences`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (SET_NULL), nullable
- sequence: PositiveBigInteger (indexed)
- deleted: Boolean (default: False)

Purpose:
- Maintains project-scoped issue numbering
- Persists sequence even after issue deletion
```

### IssueActivity
**Table:** `issue_activities`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (DO_NOTHING), nullable
- verb: CharField(255) (default: "created")
- field: CharField(255), nullable (e.g., "state", "priority")
- old_value: TextField, nullable
- new_value: TextField, nullable
- comment: TextField
- attachments: ArrayField(URLField, max=10)
- issue_comment: FK → IssueComment (DO_NOTHING), nullable
- actor: FK → User (SET_NULL), nullable
- old_identifier: UUID, nullable
- new_identifier: UUID, nullable
- epoch: Float, nullable (Unix timestamp)

Purpose:
- Complete audit trail of all issue changes
- Tracks field-level changes with old/new values
```

### IssueVersion
**Table:** `issue_versions`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (CASCADE)
- activity: FK → IssueActivity (SET_NULL), nullable
- owned_by: FK → User (CASCADE)
- last_saved_at: DateTimeField

Snapshot Fields (copies of Issue fields):
- parent: UUID, nullable
- state: UUID, nullable
- estimate_point: UUID, nullable
- name: CharField(255)
- priority: CharField(30)
- start_date: DateField, nullable
- target_date: DateField, nullable
- assignees: ArrayField(UUID)
- sequence_id: Integer
- labels: ArrayField(UUID)
- sort_order: Float
- completed_at: DateTimeField, nullable
- archived_at: DateField, nullable
- is_draft: Boolean
- type: UUID, nullable
- cycle: UUID, nullable
- modules: ArrayField(UUID)
- properties: JSONField (default: {})
- meta: JSONField (default: {})

Purpose:
- Point-in-time snapshots of issue state
- Enables historical reconstruction
```

### IssueDescriptionVersion
**Table:** `issue_description_versions`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (CASCADE)
- owned_by: FK → User (CASCADE)
- last_saved_at: DateTimeField
- description_binary: BinaryField, nullable
- description_html: TextField
- description_stripped: TextField, nullable
- description_json: JSONField (default: {})

Purpose:
- Tracks description changes separately from issue versions
- Supports rich text versioning with binary CRDT data
```

### IssueComment
**Table:** `issue_comments`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (CASCADE)
- actor: FK → User (CASCADE), nullable
- parent: FK → IssueComment (CASCADE), self-referential, nullable

Content:
- comment_stripped: TextField (auto-generated)
- comment_json: JSONField (default: {})
- comment_html: TextField (default: "<p></p>")
- description: OneToOne → Description (auto-synced)
- attachments: ArrayField(URLField, max=10)

Metadata:
- access: CharField (INTERNAL/EXTERNAL, default: INTERNAL)
- external_source: CharField(255), nullable
- external_id: CharField(255), nullable
- edited_at: DateTimeField, nullable

Tracked Fields:
- Uses ChangeTrackerMixin on comment_stripped, comment_json, comment_html
- Syncs changes to linked Description model
```

### IssueRelation
**Table:** `issue_relations`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (CASCADE)
- related_issue: FK → Issue (CASCADE)
- relation_type: CharField(20)

Relation Types:
- duplicate ↔ duplicate (symmetric)
- relates_to ↔ relates_to (symmetric)
- blocked_by ↔ blocking
- start_before ↔ start_after
- finish_before ↔ finish_after
- implemented_by ↔ implements

Constraints:
- UNIQUE(issue, related_issue) when deleted_at IS NULL
```

### IssueAssignee
**Table:** `issue_assignees`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (CASCADE)
- assignee: FK → User (CASCADE)

Constraints:
- UNIQUE(issue, assignee) when deleted_at IS NULL
```

### IssueLabel
**Table:** `issue_labels`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (CASCADE)
- label: FK → Label (CASCADE)
```

### IssueLink
**Table:** `issue_links`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (CASCADE)
- title: CharField(255), nullable
- url: TextField
- metadata: JSONField (default: {})
```

### IssueAttachment
**Table:** `issue_attachments`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (CASCADE)
- asset: FileField (upload path: {workspace_id}/{uuid}-{filename})
- attributes: JSONField (default: {})
- external_source: CharField(255), nullable
- external_id: CharField(255), nullable

Validation:
- File size limit enforced via FILE_SIZE_LIMIT setting
```

### IssueMention
**Table:** `issue_mentions`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (CASCADE)
- mention: FK → User (CASCADE)

Constraints:
- UNIQUE(issue, mention) when deleted_at IS NULL
```

### IssueSubscriber
**Table:** `issue_subscribers`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (CASCADE)
- subscriber: FK → User (CASCADE)

Constraints:
- UNIQUE(issue, subscriber) when deleted_at IS NULL
```

### IssueReaction
**Table:** `issue_reactions`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (CASCADE)
- actor: FK → User (CASCADE)
- reaction: TextField (emoji)

Constraints:
- UNIQUE(issue, actor, reaction) when deleted_at IS NULL
```

### CommentReaction
**Table:** `comment_reactions`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- comment: FK → IssueComment (CASCADE)
- actor: FK → User (CASCADE)
- reaction: TextField (emoji)

Constraints:
- UNIQUE(comment, actor, reaction) when deleted_at IS NULL
```

### IssueVote
**Table:** `issue_votes`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue: FK → Issue (CASCADE)
- actor: FK → User (CASCADE)
- vote: Integer (-1=DOWNVOTE, 1=UPVOTE)

Constraints:
- UNIQUE(issue, actor) when deleted_at IS NULL
```

---

## Cycles & Modules Models

### Cycle
**Table:** `cycles`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- workspace: FK → Workspace (auto-set)
- name: CharField(255)
- description: TextField
- start_date: DateTimeField, nullable
- end_date: DateTimeField, nullable
- owned_by: FK → User (CASCADE)
- view_props: JSONField (default: {})
- sort_order: Float (auto-decremented on creation)
- external_source: CharField(255), nullable
- external_id: CharField(255), nullable
- progress_snapshot: JSONField (default: {})
- archived_at: DateTimeField, nullable
- logo_props: JSONField (default: {})
- timezone: CharField(255) (default: "UTC")
- version: Integer (default: 1)

Sort Order Logic:
- New cycles get sort_order = smallest_existing - 10000
```

### CycleIssue
**Table:** `cycle_issues`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- cycle: FK → Cycle (CASCADE)
- issue: FK → Issue (CASCADE)

Constraints:
- UNIQUE(cycle, issue) when deleted_at IS NULL

Note:
- An issue can only be in one cycle at a time
```

### CycleUserProperties
**Table:** `cycle_user_properties`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- cycle: FK → Cycle (CASCADE)
- user: FK → User (CASCADE)
- filters: JSONField
- display_filters: JSONField
- display_properties: JSONField
- rich_filters: JSONField (default: {})

Constraints:
- UNIQUE(cycle, user) when deleted_at IS NULL
```

### Module
**Table:** `modules`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- workspace: FK → Workspace (auto-set)
- name: CharField(255)
- description: TextField
- description_text: JSONField, nullable
- description_html: JSONField, nullable
- start_date: DateField, nullable
- target_date: DateField, nullable

Status:
- status: CharField(20) - backlog/planned/in-progress/paused/completed/cancelled

Team:
- lead: FK → User (SET_NULL), nullable
- members: M2M → User (through ModuleMember)

Configuration:
- view_props: JSONField (default: {})
- sort_order: Float (auto-decremented on creation)
- external_source: CharField(255), nullable
- external_id: CharField(255), nullable
- archived_at: DateTimeField, nullable
- logo_props: JSONField (default: {})

Constraints:
- UNIQUE(name, project) when deleted_at IS NULL
```

### ModuleMember
**Table:** `module_members`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- module: FK → Module (CASCADE)
- member: FK → User (CASCADE)

Constraints:
- UNIQUE(module, member) when deleted_at IS NULL
```

### ModuleIssue
**Table:** `module_issues`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- module: FK → Module (CASCADE)
- issue: FK → Issue (CASCADE)

Constraints:
- UNIQUE(issue, module) when deleted_at IS NULL

Note:
- An issue can be in multiple modules simultaneously
```

### ModuleLink
**Table:** `module_links`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- module: FK → Module (CASCADE)
- title: CharField(255), nullable
- url: URLField
- metadata: JSONField (default: {})
```

### ModuleUserProperties
**Table:** `module_user_properties`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- module: FK → Module (CASCADE)
- user: FK → User (CASCADE)
- filters: JSONField
- display_filters: JSONField
- display_properties: JSONField
- rich_filters: JSONField (default: {})

Constraints:
- UNIQUE(module, user) when deleted_at IS NULL
```

---

## Pages (Wiki) Models

### Page
**Table:** `pages`

```
Fields:
- id: UUID (PK)
- workspace: FK → Workspace (CASCADE)
- name: TextField
- description: JSONField (default: {})
- description_binary: BinaryField, nullable (Y.js CRDT)
- description_html: TextField (default: "<p></p>")
- description_stripped: TextField, nullable (auto-generated)
- owned_by: FK → User (CASCADE)

Access Control:
- access: PositiveSmallInteger (0=Public, 1=Private, default: 0)
- is_locked: Boolean (default: False)

Hierarchy:
- parent: FK → Page (CASCADE), self-referential, nullable
- sort_order: Float (default: 65535)

Organization:
- color: CharField(255)
- labels: M2M → Label (through PageLabel)
- projects: M2M → Project (through ProjectPage)
- is_global: Boolean (default: False)

Display:
- view_props: JSONField (full_width: False)
- logo_props: JSONField (default: {})

Migration:
- moved_to_page: UUID, nullable
- moved_to_project: UUID, nullable
- archived_at: DateField, nullable

External:
- external_id: CharField(255), nullable
- external_source: CharField(255), nullable
```

### PageVersion
**Table:** `page_versions`

```
Fields:
- id: UUID (PK)
- workspace: FK → Workspace (CASCADE)
- page: FK → Page (CASCADE)
- owned_by: FK → User (CASCADE)
- last_saved_at: DateTimeField

Content:
- description_binary: BinaryField, nullable
- description_html: TextField (default: "<p></p>")
- description_stripped: TextField, nullable
- description_json: JSONField (default: {})
- sub_pages_data: JSONField (default: {})

Purpose:
- Point-in-time snapshots of page content
- Limited to 20 versions per page (managed by application)
```

### PageLog
**Table:** `page_logs`

```
Fields:
- id: UUID (PK)
- page: FK → Page (CASCADE)
- workspace: FK → Workspace (CASCADE)
- transaction: UUID (auto-generated)
- entity_identifier: UUID, nullable
- entity_name: CharField(30) (transaction type)
- entity_type: CharField(30), nullable

Entity Types:
- to_do, issue, image, video, file, link
- cycle, module, back_link, forward_link
- page_mention, user_mention

Indexes:
- entity_type
- entity_identifier
- entity_name
- (entity_type, entity_identifier)
- (entity_name, entity_identifier)

Constraints:
- UNIQUE(page, transaction)
```

### PageLabel
**Table:** `page_labels`

```
Fields:
- id: UUID (PK)
- label: FK → Label (CASCADE)
- page: FK → Page (CASCADE)
- workspace: FK → Workspace (CASCADE)
```

### ProjectPage
**Table:** `project_pages`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- page: FK → Page (CASCADE)
- workspace: FK → Workspace (CASCADE)

Constraints:
- UNIQUE(project, page) when deleted_at IS NULL
```

---

## State & Workflow Models

### State
**Table:** `states`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- workspace: FK → Workspace (auto-set)
- name: CharField(255)
- description: TextField
- color: CharField(255)
- slug: SlugField(100) (auto-generated)
- sequence: Float (default: 65535, auto-incremented by 15000)
- group: CharField(20) - StateGroup enum
- is_triage: Boolean (default: False)
- default: Boolean (default: False)
- external_source: CharField(255), nullable
- external_id: CharField(255), nullable

State Groups:
- backlog: Backlog
- unstarted: Unstarted
- started: Started
- completed: Completed
- cancelled: Cancelled
- triage: Triage

Managers:
- objects: StateManager (excludes triage states)
- all_state_objects: Manager (all states)
- triage_objects: TriageStateManager (triage only)

Constraints:
- UNIQUE(name, project) when deleted_at IS NULL

Default States (auto-created):
- Backlog (backlog, #60646C, default=True)
- Todo (unstarted, #60646C)
- In Progress (started, #F59E0B)
- Done (completed, #46A758)
- Cancelled (cancelled, #9AA4BC)
- Triage (triage, #4E5355)
```

### IssueType
**Table:** `issue_types`

```
Fields:
- id: UUID (PK)
- name: CharField(255)
- description: TextField
- logo_props: JSONField (default: {})
- is_active: Boolean (default: True)
- is_default: Boolean (default: False)
- level: PositiveSmallInteger (default: 0)
- workspace: FK → Workspace, nullable
```

### ProjectIssueType
**Table:** `project_issue_types`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- issue_type: FK → IssueType (CASCADE)
- is_default: Boolean (default: False)
- is_active: Boolean (default: True)
```

---

## Integration Models

### Webhook
**Table:** `webhooks`

```
Fields:
- id: UUID (PK)
- workspace: FK → Workspace (CASCADE)
- url: URLField(1024) - validated for http/https, no localhost
- is_active: Boolean (default: True)
- secret_key: CharField(255) (prefix: "plane_wh_")
- is_internal: Boolean (default: False)
- version: CharField(50) (default: "v1")

Event Subscriptions:
- project: Boolean (default: False)
- issue: Boolean (default: False)
- module: Boolean (default: False)
- cycle: Boolean (default: False)
- issue_comment: Boolean (default: False)

Constraints:
- UNIQUE(workspace, url) when deleted_at IS NULL

Security:
- Payload signed with HMAC-SHA256 using secret_key
```

### WebhookLog
**Table:** `webhook_logs`

```
Fields:
- id: UUID (PK)
- workspace: FK → Workspace (CASCADE)
- webhook: UUID (not FK to allow logging after webhook deletion)
- event_type: CharField(255), nullable
- request_method: CharField(10), nullable
- request_headers: TextField, nullable
- request_body: TextField, nullable
- response_status: TextField, nullable
- response_headers: TextField, nullable
- response_body: TextField, nullable
- retry_count: PositiveSmallInteger (default: 0)
```

### Integration
**Table:** `integrations`

```
Fields:
- id: UUID (PK)
- title: CharField(400)
- description: TextField
- provider: CharField(50)
- network: PositiveSmallInteger (default: 1)
- redirect_url: TextField
- webhook_url: TextField
- webhook_secret: TextField, nullable
- metadata: JSONField (default: {})
- verified: Boolean (default: False)
- avatar_url: URLField, nullable
```

### WorkspaceIntegration
**Table:** `workspace_integrations`

```
Fields:
- id: UUID (PK)
- workspace: FK → Workspace (CASCADE)
- integration: FK → Integration (CASCADE)
- api_token: FK → APIToken (SET_NULL), nullable
- actor: FK → User (SET_NULL), nullable
- metadata: JSONField (default: {})
- config: JSONField (default: {})
```

### SlackProjectSync
**Table:** `slack_project_syncs`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- workspace: FK → Workspace (auto-set)
- access_token: CharField(300)
- workspace_integration: FK → WorkspaceIntegration (CASCADE)
- team_name: CharField(300)
- team_id: CharField(30)
- channel: CharField(300)
- channel_id: CharField(100)
```

### GitHub Integration Models

**GithubRepository** (`github_repositories`)
```
Fields:
- project: FK → Project (CASCADE)
- name: CharField(500)
- url: URLField, nullable
- config: JSONField (default: {})
- repository_id: BigInteger
- owner: CharField(500)
```

**GithubRepositorySync** (`github_repository_syncs`)
```
Fields:
- project: FK → Project (CASCADE)
- repository: FK → GithubRepository (SET_NULL), nullable
- workspace_integration: FK → WorkspaceIntegration (CASCADE)
- actor: FK → User (SET_NULL), nullable
- credentials: JSONField (default: {})
- label: FK → Label (SET_NULL), nullable
```

**GithubIssueSync** (`github_issue_syncs`)
```
Fields:
- project: FK → Project (CASCADE)
- issue: FK → Issue (SET_NULL), nullable
- repository_sync: FK → GithubRepositorySync (SET_NULL), nullable
- github_issue_id: BigInteger
```

**GithubCommentSync** (`github_comment_syncs`)
```
Fields:
- project: FK → Project (CASCADE)
- issue_sync: FK → GithubIssueSync (SET_NULL), nullable
- repo_comment_id: BigInteger
- comment: FK → IssueComment (SET_NULL), nullable
```

---

## Supporting Models

### Label
**Table:** `labels`

```
Fields:
- id: UUID (PK)
- workspace: FK → Workspace (CASCADE)
- project: FK → Project (CASCADE), nullable
- name: CharField(255)
- description: TextField
- color: CharField(255) (default: random color)
- sort_order: Float (default: 65535)
- parent: FK → Label (SET_NULL), self-referential, nullable
- external_source: CharField(255), nullable
- external_id: CharField(255), nullable

Constraints:
- UNIQUE(name, project) when deleted_at IS NULL
```

### Estimate
**Table:** `estimates`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- name: CharField(255)
- description: TextField
- type: CharField(30) (categories/points)
- last_used: Boolean (default: False)
```

### EstimatePoint
**Table:** `estimate_points`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- estimate: FK → Estimate (CASCADE)
- key: PositiveSmallInteger
- value: CharField(255)
```

### Notification
**Table:** `notifications`

```
Fields:
- id: UUID (PK)
- workspace: FK → Workspace (CASCADE)
- project: FK → Project (CASCADE), nullable
- data: JSONField, nullable
- entity_identifier: UUID, nullable
- entity_name: CharField(255)
- title: TextField
- message: JSONField, nullable
- message_html: TextField (default: "<p></p>")
- message_stripped: TextField, nullable
- sender: CharField(255)
- triggered_by: FK → User (SET_NULL), nullable
- receiver: FK → User (SET_NULL), nullable
- read_at: DateTimeField, nullable
- snoozed_till: DateTimeField, nullable
- archived_at: DateTimeField, nullable
- is_inbox: Boolean (default: False)
```

### UserNotificationPreference
**Table:** `user_notification_preferences`

```
Fields:
- id: UUID (PK)
- user: FK → User (CASCADE)
- property_change: Boolean (default: True)
- state_change: Boolean (default: True)
- comment: Boolean (default: True)
- mention: Boolean (default: True)
- issue_completed: Boolean (default: True)
```

### FileAsset
**Table:** `file_assets`

```
Fields:
- id: UUID (PK)
- workspace: FK → Workspace (CASCADE)
- asset: FileField (upload path varies by entity type)
- attributes: JSONField (default: {})
- entity_type: CharField(100) - USER_AVATAR, USER_COVER, WORKSPACE_LOGO, etc.
- entity_identifier: UUID, nullable
- is_uploaded: Boolean (default: False)
- size: PositiveBigInteger (default: 0)
- storage_metadata: JSONField (default: {})
- is_deleted: Boolean (default: False)
- deleted_at: DateTimeField, nullable
- external_id: CharField(255), nullable
- external_source: CharField(255), nullable

Entity Types:
- USER_AVATAR, USER_COVER
- WORKSPACE_LOGO
- PROJECT_COVER
- ISSUE_ATTACHMENT, ISSUE_DESCRIPTION
- PAGE_DESCRIPTION
- COMMENT_DESCRIPTION
- DRAFT_ISSUE_ATTACHMENT, DRAFT_ISSUE_DESCRIPTION
```

### IssueView
**Table:** `issue_views`

```
Fields:
- id: UUID (PK)
- workspace: FK → Workspace (CASCADE)
- project: FK → Project (CASCADE), nullable
- name: CharField(255)
- description: TextField
- query: JSONField (default: {})
- access: PositiveSmallInteger (0=Private, 1=Public, default: 1)
- query_data: JSONField (default: {})
- filters: JSONField (default: {})
- display_filters: JSONField (default: {})
- display_properties: JSONField (default: {})
- sort_order: Float (default: 65535)
- logo_props: JSONField (default: {})
- owned_by: FK → User (SET_NULL), nullable
- is_locked: Boolean (default: False)
```

### Intake
**Table:** `intakes`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- name: CharField(255)
- description: TextField
- view_props: JSONField (default: {})
- is_default: Boolean (default: False)
- anchor: CharField(255), nullable

Constraints:
- UNIQUE(project, deleted_at)
```

### IntakeIssue
**Table:** `intake_issues`

```
Fields:
- id: UUID (PK)
- project: FK → Project (CASCADE)
- intake: FK → Intake (CASCADE)
- issue: FK → Issue (CASCADE)
- status: SmallInteger (-2=duplicate, -1=rejected, 0=snoozed, 1=accepted, 2=pending)
- snoozed_till: DateTimeField, nullable
- duplicate_to: FK → Issue (SET_NULL), nullable
- source: CharField(20) (IN_APP/EXTERNAL/EMAIL, default: IN_APP)
- external_source: CharField(255), nullable
- external_id: CharField(255), nullable

Constraints:
- UNIQUE(intake, issue, deleted_at)
```

### DraftIssue
**Table:** `draft_issues`

```
Fields:
- Same structure as Issue but for draft state
- workspace: FK → Workspace (CASCADE)
- project: FK → Project (SET_NULL), nullable
- name: CharField(255)
- description_html: TextField
- priority: CharField(30)
- state: UUID, nullable (stores state ID, not FK)
- etc.
```

### UserFavorite
**Table:** `user_favorites`

```
Fields:
- id: UUID (PK)
- workspace: FK → Workspace (CASCADE)
- user: FK → User (CASCADE)
- entity_type: CharField(100) - project, cycle, module, view, page
- entity_identifier: UUID, nullable
- entity_data: JSONField (default: {})
- is_folder: Boolean (default: False)
- name: CharField(255)
- parent: FK → UserFavorite (CASCADE), nullable
- sequence: SmallInteger (default: 65535)

Constraints:
- UNIQUE(workspace, user, entity_type, entity_identifier) when deleted_at IS NULL
```

### UserRecentVisit
**Table:** `recent_visits`

```
Fields:
- id: UUID (PK)
- workspace: FK → Workspace (CASCADE)
- user: FK → User (CASCADE)
- entity_type: CharField(100) - project, cycle, module, view, page
- entity_identifier: UUID, nullable
- visited_at: DateTimeField
```

---

## Data Flow Architecture

### Authentication Flow

```
User Request → Middleware Authentication
    ↓
Check Session/Token Type:
- Session: Django session authentication
- API Token: Validate "plane_api_" prefix, check expiry
- OAuth: Validate via Account model

    ↓
On Success: Set request.user, update last_active
On Failure: Return 401
```

### Issue Creation Flow

```
API Request (CreateIssueView)
    ↓
Validate Project Access (WorkspaceEntityPermission)
    ↓
Transaction Begin
    ↓
Acquire PostgreSQL Advisory Lock (pg_advisory_xact_lock)
    ↓
Get/Increment IssueSequence
    ↓
Create Issue with sequence_id
    ↓
Create IssueSequence record
    ↓
Transaction Commit
    ↓
Background Tasks (Celery):
- Create IssueActivity (verb="created")
- Send Notifications to subscribers
- Trigger Webhooks (if configured)
```

### Real-time Collaboration Flow (Pages/Issue Descriptions)

```
Editor Load
    ↓
WebSocket Connection (HocusPocus Server)
    ↓
Y.js Document Sync:
- Local changes → Y.js update
- Remote changes → Y.js merge (CRDT)
    ↓
Periodic Save (debounced):
- description_binary: Y.js state vector
- description_html: Rendered HTML
- description_stripped: Plain text (search)
    ↓
Version Creation:
- PageVersion/IssueDescriptionVersion
- Limited to 20 versions per entity
```

### Webhook Delivery Flow

```
Entity Change Event (Issue/Project/etc.)
    ↓
Celery Task: send_webhook
    ↓
For each active Webhook:
    ↓
Build Payload:
- event: "issue.created", etc.
- data: Serialized entity
- timestamp: ISO 8601
    ↓
Sign Payload (HMAC-SHA256 with secret_key)
    ↓
POST to webhook.url
    ↓
Log to WebhookLog:
- Success: response_status, response_body
- Failure: retry_count++, schedule retry
```

### Notification Flow

```
Triggering Event:
- Issue change (state, priority, assignee)
- Comment/mention
- Due date approaching

    ↓
Celery Task: create_notification
    ↓
Determine Recipients:
- Assignees
- Subscribers
- Mentioned users

    ↓
For each recipient (check UserNotificationPreference):
    ↓
Create Notification record
    ↓
Email Notification (if enabled):
- Queue EmailNotificationLog
- Send via configured email provider
    ↓
Push Notification (if Device registered):
- Send to device_token via platform (iOS/Android)
```

### Search & Filter Data Flow

```
Frontend Filter Request
    ↓
Build Query Parameters:
- filters: JSONField query
- display_filters: group_by, order_by
- display_properties: visible columns

    ↓
API View:
- Apply workspace/project filters
- Apply soft-delete exclusion
- Apply state/priority/assignee filters
- Exclude archived/draft (via IssueManager)

    ↓
QuerySet Optimization:
- select_related: state, project, parent
- prefetch_related: assignees, labels
- annotate: sub_issue_count, link_count

    ↓
Response: Paginated, serialized issues
```

### Permission Model

```
Role Hierarchy:
- Admin (20): Full access, manage members
- Member (15): Create/edit/delete own entities
- Guest (5): View only, limited to specific projects

Permission Check Flow:
Request → Check Workspace Membership
    ↓
Check Project Membership (if project-scoped)
    ↓
Check Entity Ownership (for destructive actions)
    ↓
Check Feature Flags (module_view, cycle_view, etc.)
    ↓
Allow/Deny
```

### Soft Deletion Cascade

```
Entity.delete(soft=True)
    ↓
Set deleted_at = timezone.now()
    ↓
Celery Task: soft_delete_related_objects
    ↓
Find Related Models (via ForeignKey CASCADE)
    ↓
For each related model:
- Set deleted_at = same timestamp
- Recursively process children
```

---

## Database Indexes

### Primary Indexes (Auto-created)
- All `id` fields (UUID primary keys)
- All foreign key fields

### Custom Indexes
- `users.email` (unique)
- `workspaces.slug` (unique)
- `projects.identifier` (indexed)
- `issues.sequence_id` (per-project)
- `api_tokens.token` (unique, indexed)
- `states.sequence` (ordering)
- `page_logs.entity_type`, `entity_identifier`, `entity_name` (composite)

### Unique Constraints with Soft Delete
Most unique constraints include `deleted_at IS NULL` condition to allow recreation:
```sql
CREATE UNIQUE INDEX ... WHERE deleted_at IS NULL;
```

---

## Performance Considerations

1. **Advisory Locks**: Issue sequence generation uses PostgreSQL advisory locks to prevent race conditions without table-level locking.

2. **Soft Deletion**: All queries use `SoftDeletionManager` by default, which adds `WHERE deleted_at IS NULL` to every query.

3. **JSONB Fields**: Extensive use of PostgreSQL JSONB for flexible metadata storage (view_props, filters, etc.).

4. **Y.js Binary Storage**: Real-time collaboration state stored as binary for efficient CRDT operations.

5. **Prefetch Optimization**: API views use `select_related` and `prefetch_related` to minimize N+1 queries.

6. **Background Processing**: All heavy operations (webhooks, notifications, soft delete cascades) are offloaded to Celery workers.
