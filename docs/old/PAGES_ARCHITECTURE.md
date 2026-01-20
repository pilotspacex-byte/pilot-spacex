# Pages (Documentation) Feature - Comprehensive Architecture Documentation

## Overview

The Pages feature in Plane is a collaborative documentation system that enables teams to create, edit, organize, and share rich-text documents with real-time synchronization. It integrates a Django REST backend with a React/TypeScript frontend using Y.js CRDTs for conflict-free collaborative editing through HocusPocus.

---

## Table of Contents

1. [Data Models](#data-models)
2. [API Endpoints](#api-endpoints)
3. [Business Logic & Access Control](#business-logic--access-control)
4. [Real-time Collaboration Architecture](#real-time-collaboration-architecture)
5. [Frontend Architecture](#frontend-architecture)
6. [Data Flow](#data-flow)
7. [Performance & Security](#performance--security)

---

## Data Models

### Core Page Model

**File**: `apps/api/plane/db/models/page.py`

```python
class Page(BaseModel):
    PRIVATE_ACCESS = 1
    PUBLIC_ACCESS = 0

    workspace = ForeignKey("db.Workspace", on_delete=CASCADE, related_name="pages")
    name = TextField(blank=True)

    # Content storage (triple format)
    description = JSONField(default=dict, blank=True)
    description_binary = BinaryField(null=True)  # Y.js binary format
    description_html = TextField(blank=True, default="<p></p>")
    description_stripped = TextField(blank=True, null=True)  # Full-text search

    # Ownership & permissions
    owned_by = ForeignKey(User, on_delete=CASCADE, related_name="pages")
    access = PositiveSmallIntegerField(choices=((0, "Public"), (1, "Private")), default=0)

    # Organization
    parent = ForeignKey("self", on_delete=CASCADE, null=True, related_name="child_page")
    color = CharField(max_length=255, blank=True)
    labels = ManyToManyField("db.Label", through="db.PageLabel")
    projects = ManyToManyField("db.Project", through="db.ProjectPage")

    # Status tracking
    archived_at = DateField(null=True)
    is_locked = BooleanField(default=False)
    is_global = BooleanField(default=False)

    # UI state
    view_props = JSONField(default={"full_width": False})
    logo_props = JSONField(default=dict)
    sort_order = FloatField(default=65535)
```

**Key Characteristics**:
- **Triple content format**: JSON (structure), HTML (rendering), binary (Y.js CRDT)
- **Hierarchical**: Pages can have parent-child relationships (sub-pages)
- **Multi-project**: A single page can be associated with multiple projects
- **Strip on save**: `description_stripped` auto-generated for full-text search

### Related Models

#### PageLog (Audit Trail)
```python
class PageLog(BaseModel):
    TYPE_CHOICES = (
        ("to_do", "To Do"),
        ("issue", "Issue"),
        ("image", "Image"),
        ("link", "Link"),
        ("page_mention", "Page Mention"),
        ("user_mention", "User Mention"),
    )

    transaction = UUIDField(default=uuid.uuid4)
    page = ForeignKey(Page, related_name="page_log", on_delete=CASCADE)
    entity_identifier = UUIDField(null=True)
    entity_name = CharField(max_length=30)
    workspace = ForeignKey("db.Workspace", on_delete=CASCADE)
```

#### PageVersion (History)
```python
class PageVersion(BaseModel):
    page = ForeignKey("db.Page", on_delete=CASCADE, related_name="page_versions")
    last_saved_at = DateTimeField(default=timezone.now)
    owned_by = ForeignKey(User, on_delete=CASCADE)
    description_binary = BinaryField(null=True)
    description_html = TextField(blank=True, default="<p></p>")
    description_json = JSONField(default=dict, blank=True)
```

---

## API Endpoints

### Page CRUD Operations

**Base Path**: `/api/workspaces/{slug}/projects/{project_id}/`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `pages/` | GET | List all pages in project |
| `pages/` | POST | Create new page |
| `pages/{page_id}/` | GET | Retrieve page details |
| `pages/{page_id}/` | PATCH | Update page metadata |
| `pages/{page_id}/` | DELETE | Soft delete archived page |

### Content Operations

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `pages/{page_id}/description/` | GET | Stream page content binary |
| `pages/{page_id}/description/` | PATCH | Update page content (HTML/binary/JSON) |

### Lifecycle Operations

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `pages/{page_id}/access/` | POST | Change page visibility (public/private) |
| `pages/{page_id}/lock/` | POST | Lock page (prevent edits) |
| `pages/{page_id}/lock/` | DELETE | Unlock page |
| `pages/{page_id}/archive/` | POST | Archive page and all descendants |
| `pages/{page_id}/archive/` | DELETE | Restore archived page |

### Versioning

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `pages/{page_id}/versions/` | GET | List all versions of page |
| `pages/{page_id}/versions/{version_id}/` | GET | Retrieve specific version snapshot |

---

## Business Logic & Access Control

### Permission Model

**File**: `apps/api/plane/app/permissions/page.py`

```python
class ProjectPagePermission(BasePermission):
    """
    1. User must be project member (ADMIN/MEMBER/GUEST)
    2. Page owner can access any page
    3. Private pages: only owner has access
    4. Public pages: project members can access
    """
```

**Role-based Action Matrix**:

| Action | Admin | Member | Guest |
|--------|-------|--------|-------|
| GET (read) | ✓ | ✓ | ✓ |
| POST (create) | ✓ | ✓ | ✗ |
| PATCH (edit) | ✓ | ✓ | ✗ |
| DELETE | ✓ | ✗ | ✗ |

### Content Editing Rules

1. **Locked Pages**: If `is_locked == True`, editing returns 400 error
2. **Archived Pages**: Archived pages cannot be edited
3. **Access Change**: Only page owner can change public/private access

### Archive Cascading

```python
def unarchive_archive_page_and_descendants(page_id, archived_at):
    """Recursive CTE to archive page and all child pages"""
    WITH RECURSIVE descendants AS (
        SELECT id FROM pages WHERE id = %s
        UNION ALL
        SELECT pages.id FROM pages, descendants
        WHERE pages.parent_id = descendants.id
    )
    UPDATE pages SET archived_at = %s WHERE id IN descendants
```

---

## Real-time Collaboration Architecture

### HocusPocus Integration

**File**: `apps/live/src/hocuspocus.ts`

```typescript
class HocusPocusServerManager {
  async initialize(): Promise<Hocuspocus> {
    this.server = new Hocuspocus({
      name: env.HOSTNAME,
      onAuthenticate,
      extensions: [
        new Database(),        // Persistence layer
        new TitleSyncExtension(), // Title synchronization
        new Logger(),
        new Redis()            // Multi-server sync
      ],
      debounce: 10000     // Save to DB every 10s
    });
  }
}
```

**Connection Flow**:
```
Client (Browser)
    ↓ WebSocket (wss://live.example.com)
    ↓ JWT Token Authentication
    ↓
HocusPocus Server
    ├→ Loads Y.js doc from Database
    ├→ Applies queued updates from Redis
    └→ Broadcasts changes to all connected clients
```

### Y.js CRDT Integration

**Data Structure**:
```typescript
const ydoc = new Y.Doc();
const yContent = ydoc.getXmlFragment("content");  // Main content
const yTitle = ydoc.getXmlFragment("title");      // Title field
const awareness = ydoc.getAwareness();            // Cursor positions
```

**Benefits**:
- **Conflict-free**: CRDT algorithms merge concurrent edits automatically
- **Offline-first**: Changes queue locally, sync when connection restored
- **Binary format**: Entire document fits in single `description_binary` field

### Database Extension

**File**: `apps/live/src/extensions/database.ts`

```typescript
class Database extends HocuspocusDatabase {
  async fetch({ context, documentName: pageId }): Promise<Uint8Array> {
    // Fetch binary from DB
    let binaryData = await service.fetchDescriptionBinary(pageId);

    // Fallback: If no binary, convert HTML → binary
    if (binaryData.byteLength === 0) {
      binaryData = getBinaryDataFromDocumentEditorHTMLString(
        pageDetails.description_html,
        pageDetails.name
      );
    }
    return binaryData;
  }

  async store({ state: pageBinaryData, documentName: pageId }): Promise<void> {
    const { contentBinaryEncoded, contentHTML, contentJSON } =
      getAllDocumentFormatsFromDocumentEditorBinaryData(pageBinaryData);

    await service.updateDescriptionBinary(pageId, {
      description_binary: contentBinaryEncoded,
      description_html: contentHTML,
      description: contentJSON
    });
  }
}
```

---

## Frontend Architecture

### MobX Store

**File**: `apps/web/core/store/pages/project-page.store.ts`

```typescript
interface IProjectPageStore {
  loader: "init-loader" | "mutation-loader" | undefined;
  data: Record<string, TProjectPage>;
  error: { title: string; description: string };
  filters: TPageFilters;

  // Computed
  isAnyPageAvailable: boolean;
  canCurrentUserCreatePage: boolean;

  // Actions
  fetchPagesList(workspaceSlug, projectId, pageType?): Promise<TPage[]>;
  fetchPageDetails(workspaceSlug, projectId, pageId): Promise<TPage>;
  createPage(pageData): Promise<TPage>;
  removePage(pageId): Promise<void>;
  movePage(workspaceSlug, projectId, pageId, newProjectId): Promise<void>;
}
```

### Base Page Instance

**File**: `apps/web/core/store/pages/base-page.ts`

```typescript
class BasePage {
  // Observables
  id: string;
  name: string;
  description_html: string;
  is_locked: boolean;
  access: EPageAccess;
  archived_at: string | null;

  // Computed
  get isCurrentUserOwner(): boolean;
  get canCurrentUserEditPage(): boolean;

  // Actions
  async updateTitle(title: string): Promise<void>;
  async updateDescription(document: TDocumentPayload): Promise<void>;
  async makePublic(): Promise<void>;
  async makePrivate(): Promise<void>;
  async lock(): Promise<void>;
  async unlock(): Promise<void>;
  async archive(): Promise<void>;
  async restore(): Promise<void>;
  async duplicate(): Promise<TPage>;
}
```

### Editor Component

**File**: `packages/editor/src/core/components/editors/document/collaborative-editor.tsx`

```typescript
function CollaborativeDocumentEditor(props) {
  const { provider, state, actions } = useCollaboration();

  const { editor, titleEditor } = useCollaborativeEditor({
    provider,        // HocusPocus provider
    editable,
    fileHandler,
    onChange,
    user
  });

  const shouldShowSyncLoader = state.isCacheReady && !state.isServerSynced;

  if (shouldShowSyncLoader) {
    return <DocumentSkeleton />;
  }

  return (
    <div>
      <TitleEditor editor={titleEditor} />
      <ContentEditor editor={editor} />
    </div>
  );
}
```

---

## Data Flow

### Collaborative Editing Flow

```
User Types in Editor
    ↓
TipTap Editor State Updated (local)
    ↓
Y.js CRDT Applies Change (local Y.js doc)
    ↓
WebSocket Message Sent to HocusPocus
    ↓
HocusPocus Merges with Other Clients' Changes
    ↓
Broadcast Update to All Connected Clients
    ↓
Client Y.js Docs Merge Changes (CRDT conflict resolution)
    ↓
Editor Content Reflected (debounced rendering)
    ↓
[Every 10s] HocusPocus Database Extension Persists to DB
    ↓
Database Saved (description_binary + HTML + JSON)
```

### Background Tasks

**Version Creation** (`apps/api/plane/bgtasks/page_version_task.py`):
```python
@shared_task
def page_version(page_id, existing_instance, user_id):
    """Creates version snapshot when description_html changes"""
    page = Page.objects.get(id=page_id)

    if existing_instance.get("description_html") != page.description_html:
        PageVersion.objects.create(
            page_id=page_id,
            description_html=page.description_html,
            description_binary=page.description_binary,
            owned_by_id=user_id
        )

    # Keep only 20 most recent versions
    if PageVersion.objects.filter(page_id=page_id).count() > 20:
        PageVersion.objects.filter(page_id=page_id)\
            .order_by("last_saved_at").first().delete()
```

**Transaction Auditing** (`apps/api/plane/bgtasks/page_transaction_task.py`):
```python
@shared_task
def page_transaction(new_description_html, old_description_html, page_id):
    """Audits mentions/embeds and creates backlinks"""
    old_components = extract_all_components(old_description_html)
    new_components = extract_all_components(new_description_html)

    # Create PageLog for new references
    # Delete PageLog for removed references
```

---

## Performance & Security

### Caching & Indexing

**Database Indexes**:
```python
class PageLog(Meta):
    indexes = [
        Index(fields=["entity_type"], name="pagelog_entity_type_idx"),
        Index(fields=["entity_identifier"], name="pagelog_entity_id_idx"),
    ]
```

### Debouncing

- Title changes: 2-second debounce before API call
- HocusPocus persistence: 10-second debounce
- Title updates from Y.js: Debounced via `TitleUpdateManager`

### Security Considerations

- JWT tokens validated on WebSocket connection
- Role-based access control (ADMIN/MEMBER/GUEST)
- Page-level access checks (private vs. public)
- HTML content sanitized via `validate_html_content()`

---

## File Reference Map

| Component | File Path |
|-----------|-----------|
| Data Models | `apps/api/plane/db/models/page.py` |
| API Views | `apps/api/plane/app/views/page/base.py` |
| Version Views | `apps/api/plane/app/views/page/version.py` |
| Permissions | `apps/api/plane/app/permissions/page.py` |
| Version Task | `apps/api/plane/bgtasks/page_version_task.py` |
| Transaction Task | `apps/api/plane/bgtasks/page_transaction_task.py` |
| Page Store | `apps/web/core/store/pages/project-page.store.ts` |
| Base Page | `apps/web/core/store/pages/base-page.ts` |
| Page Service | `apps/web/core/services/page/project-page.service.ts` |
| HocusPocus Server | `apps/live/src/hocuspocus.ts` |
| Database Extension | `apps/live/src/extensions/database.ts` |
| Title Sync | `apps/live/src/extensions/title-sync.ts` |
| Collaborative Editor | `packages/editor/src/core/components/editors/document/collaborative-editor.tsx` |
