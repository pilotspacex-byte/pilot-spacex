# Notifications Feature - Comprehensive Architecture Documentation

## Overview

The Plane notifications system is a multi-layered, event-driven architecture that handles in-app notifications and email notifications across workspaces. The system captures issue-related events, broadcasts notifications to relevant stakeholders (assignees, subscribers, mentions), and provides a rich UI for notification management.

---

## Table of Contents

1. [Data Models](#data-models)
2. [API Endpoints](#api-endpoints)
3. [Business Logic](#business-logic)
4. [Background Tasks](#background-tasks)
5. [Frontend Architecture](#frontend-architecture)
6. [Data Flow](#data-flow)
7. [Performance & Security](#performance--security)

---

## Data Models

### Notification Model

**File**: `apps/api/plane/db/models/notification.py`

| Field | Type | Purpose |
|-------|------|---------|
| `workspace` | ForeignKey(Workspace) | Workspace context |
| `project` | ForeignKey(Project) | Related project (nullable) |
| `data` | JSONField | Structured event data |
| `entity_identifier` | UUIDField | ID of entity (e.g., issue ID) |
| `entity_name` | CharField(255) | Type of entity (e.g., "issue") |
| `title` | TextField | Short notification title |
| `message_html` | TextField | HTML-formatted message |
| `sender` | CharField(255) | Notification source channel |
| `triggered_by` | ForeignKey(User) | User who triggered notification |
| `receiver` | ForeignKey(User) | Target user |
| `read_at` | DateTimeField | When marked as read |
| `snoozed_till` | DateTimeField | When to reappear |
| `archived_at` | DateTimeField | When archived |

**Sender Types**:
- `in_app:issue_activities:created` - Activity on issue created by user
- `in_app:issue_activities:assigned` - Activity on assigned issue
- `in_app:issue_activities:subscribed` - Activity on subscribed issue
- `in_app:issue_activities:mentioned` - User mentioned

**Database Indexes**:
- `notif_receiver_status_idx`: [receiver, workspace, read_at, created_at]
- `notif_receiver_entity_idx`: [receiver, workspace, entity_name, read_at]
- `notif_receiver_state_idx`: [receiver, workspace, snoozed_till, archived_at]

### UserNotificationPreference Model

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `user` | ForeignKey(User) | Required | Owner of preferences |
| `workspace` | ForeignKey(Workspace) | Nullable | Workspace-level prefs |
| `property_change` | Boolean | True | Email on property changes |
| `state_change` | Boolean | True | Email on state changes |
| `comment` | Boolean | True | Email on new comments |
| `mention` | Boolean | True | Email on mentions |
| `issue_completed` | Boolean | True | Email on completion |

### EmailNotificationLog Model

| Field | Type | Purpose |
|-------|------|---------|
| `receiver` | ForeignKey(User) | Email recipient |
| `triggered_by` | ForeignKey(User) | Who caused notification |
| `entity_identifier` | UUIDField | Related entity ID |
| `data` | JSONField | Complete event payload |
| `processed_at` | DateTimeField | When batch processor ran |
| `sent_at` | DateTimeField | When email was sent |

---

## API Endpoints

### Notification CRUD

**Base Path**: `/api/workspaces/{slug}/users/notifications/`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/notifications/` | List notifications with filtering |
| GET | `/notifications/{pk}/` | Retrieve single notification |
| PATCH | `/notifications/{pk}/` | Update (snooze) |
| DELETE | `/notifications/{pk}/` | Delete notification |

**Query Parameters**:
- `snoozed`: Filter snoozed notifications
- `archived`: Filter archived notifications
- `read`: Filter by read status ("true"/"false")
- `type`: Comma-separated: "subscribed", "assigned", "created"
- `mentioned`: Filter mention notifications only
- `per_page`: Pagination size (max 300)
- `cursor`: Pagination cursor

### Read/Unread Operations

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/notifications/{pk}/read/` | Mark as read |
| DELETE | `/notifications/{pk}/read/` | Mark as unread |
| POST | `/notifications/mark-all-read/` | Bulk mark all read |

### Archive Operations

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/notifications/{pk}/archive/` | Archive notification |
| DELETE | `/notifications/{pk}/archive/` | Unarchive notification |

### Unread Count

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/notifications/unread/` | `{ total_unread_notifications_count, mention_unread_notifications_count }` |

### Preferences

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/users/me/notification-preferences/` | Get preferences |
| PATCH | `/users/me/notification-preferences/` | Update preferences |

---

## Business Logic

### Recipient Determination

The system identifies 4 recipient categories:

**1. Issue Subscribers**
- Users explicitly watching the issue
- Excludes newly mentioned users
- Excludes the actor

**2. Mentioned Users**
- Extracted from issue description HTML
- Extracted from comment HTML

**3. Comment Mentions**
- Diff calculation: new mentions vs old

**4. Auto-Subscribers**
- Mentioned users automatically added as subscribers

### Notification Filtering

**Activity Types Skipped**:
- cycle.activity.created/deleted
- module.activity.created/deleted
- issue_reaction.activity.created/deleted
- comment_reaction.activity.created/deleted
- issue_draft.activity.*

### Email Notification Eligibility

```python
send_email = False
if field == "state" and preference.state_change:
    send_email = True
elif field == "state" and preference.issue_completed and is_completed_state():
    send_email = True
elif field == "comment" and preference.comment:
    send_email = True
elif preference.property_change:
    send_email = True
```

---

## Background Tasks

### In-App Notification Generation

**File**: `apps/api/plane/bgtasks/notification_task.py`

```python
@shared_task
def notifications(
    type,
    issue_id,
    project_id,
    actor_id,
    subscriber,
    issue_activities_created,
    requested_data,
    current_instance,
):
    # 1. Parse activity data
    # 2. Extract mentions (old vs new)
    # 3. Build Notification records
    # 4. Build EmailNotificationLog records
    # 5. Bulk create both
```

### Email Notification Delivery

**File**: `apps/api/plane/bgtasks/email_notification_task.py`

**Batching Task** (`stack_email_notification`):
1. Fetch unprocessed EmailNotificationLog entries
2. Group by receiver → issue → actor
3. Call `send_email_notification.delay()` for each group

**Sending Task** (`send_email_notification`):
1. Acquire Redis lock (prevents duplicates)
2. Create email payload
3. Render HTML template
4. Send via SMTP
5. Update sent_at timestamp
6. Release lock

**Email Context**:
```python
{
    "data": template_data,
    "summary": "Updates were made...",
    "actors_involved": 2,
    "issue": {
        "issue_identifier": "PROJ-123",
        "name": "Issue Title",
        "issue_url": "https://..."
    },
    "comments": [{...}],
    "user_preference": "https://...settings/notifications/"
}
```

---

## Frontend Architecture

### TypeScript Types

**File**: `packages/types/src/workspace-notifications.ts`

```typescript
type TNotification = {
  id: string;
  title: string | undefined;
  data: TNotificationData | undefined;
  entity_identifier: string | undefined;
  entity_name: string | undefined;
  sender: string | undefined;
  triggered_by_details: IUserLite | undefined;
  read_at: string | undefined;
  archived_at: string | undefined;
  snoozed_till: string | undefined;
  is_mentioned_notification: boolean | undefined;
};

type TUnreadNotificationsCount = {
  total_unread_notifications_count: number;
  mention_unread_notifications_count: number;
};

type TNotificationFilter = {
  type: { assigned: boolean; created: boolean; subscribed: boolean };
  snoozed: boolean;
  archived: boolean;
  read: boolean;
};
```

### MobX Store - Notification Instance

**File**: `apps/web/core/store/notifications/notification.ts`

```typescript
class Notification {
  // Observables
  id: string;
  title: string;
  read_at: string | undefined;
  archived_at: string | undefined;
  snoozed_till: string | undefined;

  // Actions (Optimistic Update Pattern)
  markNotificationAsRead = async (workspaceSlug: string) => {
    const currentReadAt = this.read_at;
    try {
      this.store.workspaceNotification.setUnreadNotificationsCount("decrement");
      runInAction(() => {
        this.read_at = new Date().toISOString();
      });
      await workspaceNotificationService.markNotificationAsRead(...);
    } catch (error) {
      // Rollback on error
      runInAction(() => {
        this.read_at = currentReadAt;
      });
      this.store.workspaceNotification.setUnreadNotificationsCount("increment");
      throw error;
    }
  };
}
```

### MobX Store - Collection

**File**: `apps/web/core/store/notifications/workspace-notifications.store.ts`

```typescript
class WorkspaceNotificationStore {
  // Observables
  loader: ENotificationLoader | undefined;
  unreadNotificationsCount: TUnreadNotificationsCount;
  notifications: Record<string, INotification>;
  currentNotificationTab: TNotificationTab;
  paginationInfo: TNotificationPaginatedInfo | undefined;
  filters: TNotificationFilter;

  // Computed
  notificationIdsByWorkspaceId = (workspaceId: string) => {
    // Filter by workspace, tab, state, type filters
  };

  // Actions
  getUnreadNotificationsCount = async (workspaceSlug: string);
  getNotifications = async (workspaceSlug, loader, queryParamType);
  markAllNotificationsAsRead = async (workspaceSlug: string);
  updateFilters = (key: keyof TNotificationFilter, value: any);
  setCurrentNotificationTab = (tab: TNotificationTab);
}
```

### API Service

**File**: `packages/services/src/workspace/notification.service.ts`

```typescript
class WorkspaceNotificationService extends APIService {
  getUnreadCount(workspaceSlug): Promise<TUnreadNotificationsCount>
  list(workspaceSlug, params): Promise<TNotificationPaginatedInfo>
  update(workspaceSlug, notificationId, data): Promise<TNotification>
  markAsRead(workspaceSlug, notificationId): Promise<void>
  markAsUnread(workspaceSlug, notificationId): Promise<void>
  archive(workspaceSlug, notificationId): Promise<void>
  unarchive(workspaceSlug, notificationId): Promise<void>
  markAllAsRead(workspaceSlug, params): Promise<void>
}
```

---

## Data Flow

### Notification Trigger Flow

```
Issue Updated (API)
    ↓
Activity Tracking (issue_activities_task.py)
    ├─ Track field changes
    ├─ Build IssueActivity records
    └─ Call notifications.delay()
    ↓
Notification Processing (Async Celery)
    ├─ Identify recipients (subscribers, mentions)
    ├─ Generate Notification records
    ├─ Generate EmailNotificationLog records
    └─ Bulk create both
    ↓
In-App: Immediately available for UI
Email: Batched & sent asynchronously
```

### Notification Lifecycle States

```
Notification Created
  (read_at=null, archived_at=null, snoozed_till=null)
    ↓
ACTIVE STATE (In Inbox)
    ↓ (User actions)
┌─────────────┬───────────────┬─────────────────┐
│ Mark Read   │ Snooze        │ Archive         │
│ read_at=now │ snoozed_till  │ archived_at=now │
└─────────────┴───────────────┴─────────────────┘
    ↓ (User undo actions)
┌─────────────┬───────────────┬─────────────────┐
│ Mark Unread │ Unsnooze      │ Unarchive       │
│ read_at=null│ snoozed=null  │ archived_at=null│
└─────────────┴───────────────┴─────────────────┘
```

---

## Performance & Security

### Database Indexes

9 strategic indexes optimized for common queries:
- Single-field: entity_identifier, entity_name, read_at
- Composite: (receiver, workspace, read_at, created_at), etc.

### Bulk Operations

```python
Notification.objects.bulk_create(bulk_notifications, batch_size=100)
EmailNotificationLog.objects.bulk_create(bulk_email_logs, batch_size=100, ignore_conflicts=True)
```

### Email Batching

Instead of one email per activity:
1. Batch by receiver
2. Group by issue
3. Group by actor
4. One aggregated email

### Redis Lock for Idempotency

```python
lock_id = f"send_email_notif_{issue_id}_{receiver_id}_{ids_str}"
if acquire_lock(lock_id=lock_id):
    # Process email
else:
    return  # Duplicate already processing
```

### Access Control

- All endpoints require workspace-level authentication
- User can only access their own notifications
- No cross-user notification access

---

## File Reference Map

| Component | File Path |
|-----------|-----------|
| Model | `apps/api/plane/db/models/notification.py` |
| API Views | `apps/api/plane/app/views/notification/base.py` |
| Notification Task | `apps/api/plane/bgtasks/notification_task.py` |
| Email Task | `apps/api/plane/bgtasks/email_notification_task.py` |
| Frontend Store | `apps/web/core/store/notifications/workspace-notifications.store.ts` |
| Notification Instance | `apps/web/core/store/notifications/notification.ts` |
| Service | `packages/services/src/workspace/notification.service.ts` |
| Types | `packages/types/src/workspace-notifications.ts` |
| Constants | `packages/constants/src/notification.ts` |
