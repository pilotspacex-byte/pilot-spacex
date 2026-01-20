# Plane Project Management Tool - Complete Feature Analysis

## Overview

Plane is a comprehensive open-source project management tool built with a monorepo architecture combining React/TypeScript frontends with a Django REST API backend. The system provides enterprise-grade project management, collaboration, and workflow automation capabilities.

---

## CORE FEATURES

### 1. Work Items (Issues)

The Work Items feature is the core of Plane's project management system, providing a comprehensive system for creating, managing, and tracking work across teams.

**Creation and Management:**
Issues are created with rich metadata including name, description (with HTML support), priority levels (Urgent/High/Medium/Low/None), custom states, multiple assignees, labels, start/due dates, and story point estimates. Each issue receives a unique sequential identifier (e.g., "PROJ-123") that's automatically generated per project. The system supports bulk operations for batch updates and maintains complete version history for audit purposes.

**Complex Relationships:**
Issues support hierarchical parent-child relationships (sub-issues) enabling breakdown of large work items. The relation system includes blocking dependencies, duplicate tracking, "relates to" links, and temporal constraints (start before/after, finish before/after). Relations are bidirectional - creating "blocked by" automatically creates the reverse "blocks" relationship.

**Collaboration Features:**
Rich threaded comments with HTML formatting, emoji reactions, edit history, and @mentions for notifications. Activity streams capture every change with before/after states, enabling complete audit trails. Users can subscribe to issues for updates, vote on issues for prioritization, and attach files or external links.

**Display and Organization:**
Issues can be viewed through multiple layouts (List, Kanban, Calendar, Gantt, Spreadsheet) with configurable grouping by state, priority, assignees, labels, or dates. Advanced filtering supports combinations of any field with operators like equals, contains, greater than. Users customize which properties display in their views.

**Data Integrity:**
HTML content is sanitized to prevent XSS attacks. Date validation ensures start dates don't exceed due dates. Assignees and labels are validated to belong to the project. PostgreSQL advisory locks ensure unique sequential IDs even with concurrent creates. Soft deletion pattern maintains referential integrity while allowing recovery.

**Dependencies:** Cycles, Modules, Projects, Users, Labels, States

---

### 2. Cycles (Sprints)

The Cycles feature enables sprint management with time-boxed iterations for organizing development work.

**Lifecycle Management:**
Cycles progress through defined states: Draft (no dates, for planning), Upcoming (scheduled future start), Current (active between start/end dates), Completed (past end date), and Archived (historical record). Status is automatically calculated based on current time relative to cycle dates, respecting project timezone settings.

**Issue Organization:**
Issues are added to cycles individually or in bulk. Cross-cycle movement transfers issues between sprints while maintaining history. Issues cannot be added to completed cycles. The system tracks which issues are started, unstarted, in backlog, completed, or cancelled within each cycle.

**Progress Analytics:**
Real-time progress calculation tracks issue distribution across state groups. Progress percentage excludes cancelled items from the denominator. The system supports two estimation modes: issue count and story points. Burndown charts show remaining work with ideal vs. actual trend lines plotted daily. Burnup charts show cumulative completed work. Distribution analytics break down progress by assignee and label.

**Transfer Workflow:**
When cycles complete, the system captures a comprehensive progress snapshot, identifies incomplete issues, and optionally transfers them to a target cycle. All movements are logged for audit trails with team notifications.

**Personalization:**
Each user can customize their view of cycle work through saved filters, display preferences, layout choices, and visible properties. Cycles can be marked as favorites for quick access.

**Dependencies:** Projects, Issues, Users, Workspace

---

### 3. Modules

Modules allow teams to group related issues into logical units within projects, functioning as epics or feature areas.

**Organization Structure:**
Modules are created with name, description, status (Backlog/Planned/In Progress/Paused/Completed/Cancelled), designated lead, target dates, and team members. Float-based ordering enables drag-and-drop reordering. Modules support natural alphanumeric sorting and can be archived to preserve historical records.

**Issue Grouping:**
Issues link to modules through a many-to-many relationship - a single issue can belong to multiple modules. Bulk operations allow adding multiple issues at once. The system tracks issue state distribution within each module (completed, started, unstarted, backlog, cancelled).

**Team Assignment:**
Each module has a designated lead (single owner) and a members list for team capacity planning. This is distinct from issue assignees - module members indicate who's working on the module overall.

**Progress Tracking:**
The system calculates completion percentage as (completed + cancelled) / total issues. When projects use estimate points, modules track total, completed, and remaining points. Distribution analytics show progress breakdown by assignees and labels with visual burndown charts.

**Dependencies:** Projects, Issues, Users, Workspace

---

### 4. Pages (Documentation & Notes)

The Pages feature provides rich-text documentation with real-time collaboration capabilities.

**Content Creation:**
Pages support a rich text editor powered by TipTap/ProseMirror with customizable extensions. Content is stored in multiple formats: HTML for display, JSON for structure, and binary for efficient synchronization. Pages can have custom colors, logo properties, and labels for organization.

**Real-Time Collaboration:**
Multiple users can edit simultaneously using WebSocket-based synchronization powered by HocusPocus and Y.js CRDTs (Conflict-free Replicated Data Types). Changes from one user instantly appear on all collaborators' screens without conflicts. The system handles network instability with automatic reconnection and offline editing via IndexedDB caching.

**Hierarchy and Organization:**
Pages support nested hierarchies through parent-child relationships, creating tree structures for documentation. When parent pages are archived, descendants are automatically archived. Pages can be filtered by public (team-visible), private (owner-only), or archived status.

**Version Control:**
Each content update creates a PageVersion record capturing the complete state. The system maintains up to 20 versions per page with automatic cleanup of older versions. Users can browse version history and restore any previous version. A separate PageLog tracks all embedded content (mentions, images, links, issue references).

**Access Control:**
Public pages are visible to all project members with edit access for members or higher. Private pages are visible only to the owner. Page owners and admins can lock pages to prevent modifications. Deletion requires a two-step process: archive first, then delete.

**Dependencies:** Projects (optional), Users, Labels, Real-time Server

---

### 5. Views (Filtered Issue Lists)

Views provide customizable, saved perspectives on issues with sophisticated filtering and multiple visualization formats.

**View Definition:**
Views combine rich filtering, sorting, display configuration, and layout preferences into reusable saved queries. They exist at project level (specific to individual projects) or workspace level (cross-project visibility). Each view has an owner, name, description, and optional emoji/logo.

**Filtering System:**
Views support complex filter expressions combining multiple conditions with logical operators. Filters include issue properties (state, priority), people (assignees, creators, subscribers), labels, dates (with relative expressions like "2 weeks from now"), cycles, modules, and relationships. Operators include equals, not equals, contains, is in, greater/less than.

**Display Configuration:**
Layout types include List (sortable columns), Kanban (card-based columns with drag-and-drop), Calendar (monthly/weekly by dates), Spreadsheet (grid-based bulk editing), and Gantt (timeline with dependencies). Issues can be grouped and sub-grouped by state, priority, labels, assignees, dates, or project. Visible properties are configurable per view.

**Access and Sharing:**
Views can be private (owner-only) or public (visible to all members). Users can favorite views for quick access. Workspace-level views aggregate issues across multiple projects with types like "all-issues," "assigned-to-me," "created-by-me."

**Dependencies:** Projects, Issues, Users, Workspace

---

### 6. Analytics & Insights

Analytics provides real-time data visualization and project insights for tracking progress and team productivity.

**Issue Distribution:**
Analyze issues across dimensions including state groups, priority levels, assignees, labels, and time periods. Visualize work distribution to identify bottlenecks and imbalances.

**Progress Charts:**
Burndown charts show remaining work against ideal trend lines. Burnup charts display cumulative completed work. Both support issue count and story point metrics with daily granularity.

**Cycle and Module Analytics:**
Track completion rates, velocity trends, and scope changes across sprints. Compare performance between cycles. Analyze module progress with breakdown by team members and categories.

**Custom Queries:**
Save custom analytics configurations for repeated analysis. Export data for external reporting. Filter by date ranges, projects, team members, and issue attributes.

**Dependencies:** Projects, Issues, Cycles, Modules

---

### 7. Intake Management

Intake provides an external request submission and triage system for managing incoming work requests.

**Submission System:**
External users or stakeholders submit issues through a customizable intake form. Forms can be embedded or shared as public links. Submissions capture standard issue fields plus custom metadata.

**Triage Workflow:**
Incoming requests enter a pending state for review. Triagers can accept (convert to project issue), reject (with reason), snooze (defer for later), or mark as duplicate. Status tracking shows the lifecycle of each request.

**Integration:**
Accepted intake issues automatically become project issues with full functionality. The system maintains the connection between intake submissions and resulting issues for tracking.

**Dependencies:** Projects, Issues, Users

---

### 8. Stickies (Quick Notes)

Stickies provide a lightweight collaborative notes workspace for quick capture and organization.

**Quick Capture:**
Create notes with rich text content instantly without the overhead of formal documentation. Custom colors provide visual organization and categorization.

**Organization:**
Notes exist at the workspace level, accessible across projects. Owner management and sorting capabilities help organize growing collections of quick notes.

**Dependencies:** Workspace, Users

---

### 9. Drafts

Drafts allow saving work-in-progress issues before publishing to the project.

**Draft Preservation:**
Save incomplete issues with partial information without cluttering the project backlog. Drafts maintain all issue properties including assignees, labels, modules, and cycles.

**Conversion:**
Convert drafts to published issues when ready, automatically applying all saved properties. Drafts can be edited and refined over multiple sessions before publication.

**Dependencies:** Workspace, Projects (optional), Issues

---

### 10. Archives

Archives maintain historical records of completed work while keeping active views clean.

**Archival System:**
Issues, cycles, and modules can be archived rather than deleted. Archived items are excluded from normal listings but remain accessible through dedicated archive views. Full historical data is preserved for reference and reporting.

**Restoration:**
Archived items can be restored to active status when needed. The system maintains all relationships and history through the archive/restore cycle.

**Dependencies:** Issues, Cycles, Modules

---

### 11. Labels

Labels provide tagging and categorization for issues and pages.

**Workspace Management:**
Labels are defined at the workspace level and available across all projects. Each label has a name, color, and optional description. Color-coding provides visual categorization in issue lists.

**Application:**
Multiple labels can be applied to issues and pages. Labels support quick filtering - click a label to see all items with that tag. Multi-select enables filtering by combinations of labels.

**Dependencies:** Workspace, Issues, Pages

---

### 12. States

States define custom workflow stages for issue progression within projects.

**Workflow Definition:**
Each project defines its own states organized into groups: Triage, Backlog, Unstarted, Started, Completed, and Cancelled. States within groups can be reordered via drag-and-drop. Each state has a name, color, and sequence within its group.

**State Management:**
One state is designated as default for new issues. States determine issue progress calculations - completed states contribute to progress percentage. Kanban boards use states as columns by default.

**Dependencies:** Projects, Issues

---

### 13. Estimates & Points

Estimates provide story point systems for capacity planning and velocity tracking.

**Estimation Systems:**
Projects can define multiple estimation systems with custom point scales. Support for Fibonacci sequences (1, 2, 3, 5, 8, 13), sequential (1, 2, 3, 4, 5), t-shirt sizes, or fully custom scales.

**Application:**
Issues are assigned estimate points from the active system. Points aggregate in cycles and modules for capacity planning. Burndown charts can display points instead of issue counts.

**Dependencies:** Projects, Issues

---

### 14. Notifications

Notifications keep users informed of relevant activity across their workspace.

**Notification Types:**
Users receive notifications for issue updates on subscribed items, @mentions in comments and descriptions, replies to their comments, assignment changes, and due date reminders.

**Delivery Channels:**
In-app notifications appear in the notification center with badge counts. Email notifications are sent based on user preferences. Users can configure which events trigger notifications.

**Management:**
Notifications can be marked as read, archived, or snoozed for later. Snooze durations are configurable. Notification preferences are set per user with workspace-level overrides.

**Dependencies:** Users, Workspace, Projects, Issues

---

### 15. Comments & Discussions

Comments enable threaded discussions on issues for team collaboration.

**Rich Discussions:**
Comments support rich text formatting with HTML content, including code blocks, links, and embedded content. Threaded replies create nested conversations. Edit history tracks changes to comments.

**Engagement:**
@mentions in comments notify referenced users. Emoji reactions allow quick feedback without adding to the conversation. Comment counts display on issue cards for activity awareness.

**Activity Integration:**
Comments contribute to issue activity streams. The system tracks who commented and when for complete audit trails.

**Dependencies:** Issues, Users, Workspace

---

## WORKSPACE FEATURES

### 16. Workspace Management

Workspaces provide multi-tenant organization with team membership and access control.

**Workspace Structure:**
Each workspace is an isolated container for projects, issues, and team collaboration. Users can belong to multiple workspaces with different roles. Workspaces have customizable names, slugs (URL identifiers), and branding.

**Membership:**
Members join workspaces through invitations with role assignment: Admin (full control), Member (standard access), or Guest (limited access). Invitations can be sent via email with automatic onboarding. Members can be deactivated without deletion to preserve historical data.

**Teams:**
Create sub-groups within workspaces for organizing members. Teams can be assigned to modules or used for filtering views. Team membership is separate from workspace roles.

**Customization:**
Workspaces support custom themes with color schemes. Quick links provide shortcuts to frequently accessed resources. Home preferences customize the dashboard layout.

**Dependencies:** Users, Projects

---

### 17. Workspace Settings

Settings provide configuration and administration for workspace operations.

**Member Management:**
Invite new members, change roles, and deactivate accounts. View member activity and contribution metrics. Manage pending invitations.

**Integration Configuration:**
Configure workspace-level integrations (GitHub, Slack). Set up webhooks for external system notifications. Manage API tokens and access.

**Data Operations:**
Import data from other project management tools. Export workspace data for backup or migration. Configure data retention policies.

**Dependencies:** Workspace, Users

---

### 18. Workspace Views (Global Views)

Global Views provide cross-project visibility into issues across the entire workspace.

**Aggregated Visibility:**
See issues from all projects in a single view. Built-in views include "All Issues," "Assigned to Me," "Created by Me," and "Subscribed." Custom global views can filter and organize workspace-wide data.

**Filtering:**
Apply the same rich filtering available in project views across all workspace issues. Group by project to see distribution. Track work across team boundaries.

**Dependencies:** Workspace, Projects, Issues

---

### 19. User Profiles

Profiles provide identity and activity tracking for workspace members.

**Profile Information:**
Display name, avatar, and cover image for personalization. Contact information and role visibility. Timezone selection from 400+ supported zones for accurate scheduling.

**Activity History:**
Track issues created, assigned, and completed. View recent projects and contributions. Navigation history enables quick return to recent work.

**Dependencies:** Users, Workspace

---

## INTEGRATION & COLLABORATION FEATURES

### 20. Real-Time Collaboration

Real-time collaboration enables multiple users to simultaneously edit documents with automatic synchronization.

**Architecture:**
A dedicated Node.js live server handles WebSocket connections using HocusPocus (Y.js protocol). The system uses CRDTs (Conflict-free Replicated Data Types) to guarantee that all clients converge to identical content regardless of edit order or network timing.

**Simultaneous Editing:**
Multiple team members edit the same document with changes appearing instantly on all screens. Local edits execute immediately without waiting for the server. Operations are transmitted, merged, and broadcast to all connected clients.

**Conflict Resolution:**
When simultaneous edits occur at the same position, Y.js uses deterministic ordering based on client IDs and vector clocks. All clients resolve to the same content without data loss or manual conflict resolution.

**Offline Support:**
IndexedDB caches document state for offline editing. Changes sync automatically when connectivity returns. Users never lose work due to network issues.

**Presence Awareness:**
The infrastructure supports tracking user cursor positions, selections, and online status. Collaborators see who else is viewing or editing the document.

**Dependencies:** Pages, Users, Database

---

### 21. GitHub Integration

GitHub integration provides bidirectional synchronization between Plane and GitHub repositories.

**Repository Linking:**
Connect GitHub accounts via OAuth authentication. Link specific repositories to Plane projects. Import historical issues from repositories during setup.

**Issue Synchronization:**
Automatically create Plane issues from GitHub issues and pull requests. Bidirectional sync keeps status, labels, and comments aligned. Track which Plane issues correspond to GitHub issues.

**Comment Sync:**
Comments posted on GitHub sync to corresponding Plane issues. Team discussions stay connected across both platforms.

**Dependencies:** Projects, Issues, Workspace Integration

---

### 22. Slack Integration

Slack integration delivers notifications and enables issue creation from Slack workspaces.

**Workspace Connection:**
Connect Slack workspaces via OAuth. Configure which channels receive Plane notifications. Set up per-project channel integrations for targeted delivery.

**Notifications:**
Receive formatted notifications when issues are created, updated, or commented on. Share Plane issue links with proper context and preview.

**Dependencies:** Projects, Workspace Integration

---

### 23. Webhooks

Webhooks enable custom integrations with any external platform via HTTP callbacks.

**Event Subscription:**
Create webhooks that fire on project, issue, cycle, module, and comment events. Subscribe to specific event types. Configure unique endpoint URLs for each webhook.

**Delivery System:**
Payloads are signed using HMAC-SHA256 with a secret key for verification. Failed deliveries trigger automatic retries with exponential backoff (up to 5 attempts). After maximum failures, webhooks are deactivated with email notification.

**Management:**
Test webhooks with delivery logs showing request/response details. Regenerate secret keys for security rotation. Enable/disable webhooks without deletion.

**Dependencies:** Workspace, Projects, Events

---

### 24. Integrations Management

The integration system provides a framework for third-party application connections.

**Integration Marketplace:**
Available integrations (GitHub, Slack, etc.) are listed with installation status. OAuth authentication flows handle secure authorization. Configuration is stored per workspace.

**Scope Management:**
Each integration requests specific permissions (read:user, chat:write, etc.). Users approve scopes during OAuth authorization. Tokens are securely stored and refreshed as needed.

**Dependencies:** Workspace, Users

---

## PROJECT MANAGEMENT FEATURES

### 25. Projects

Projects are containers for organizing related issues, cycles, modules, and documentation.

**Project Setup:**
Create projects with name, identifier prefix (for issue keys), description, and cover image. Choose public (workspace visible) or private access. Assign a project lead and default assignee for new issues.

**Feature Flags:**
Enable or disable features per project: modules, cycles, pages, intake, time tracking, and issue types. Customize projects for team workflows without unused features.

**Team Management:**
Add project members with roles: Admin, Member, or Guest. Send invitations to bring new members. Configure member access to project settings.

**Customization:**
Custom identifier prefixes create meaningful issue keys. Project emoji and cover images provide visual identity. Description captures project purpose and context.

**Dependencies:** Workspace, Users

---

### 26. Project Settings

Settings configure detailed project behavior and features.

**General Settings:**
Edit project name, description, and cover image. Change access level (public/private). Configure default assignee and project lead.

**Feature Configuration:**
Toggle modules, cycles, pages, intake, and other features. Configure state workflow with custom states. Set up estimate point systems.

**Member Management:**
Invite members and assign roles. Remove members or change permissions. Configure guest access levels.

**Automation:**
Set auto-close rules to close completed issues after X days. Configure auto-archive rules for closed issues. Define custom automation conditions.

**Dependencies:** Projects, Workspace

---

### 27. Deploy Board / Public Sharing

Deploy Board enables public read-only sharing of project content.

**Public Access:**
Share issues, pages, and project data via unique public links. Configure what's visible on the public board. No authentication required for viewers.

**Engagement Options:**
Enable or disable comments on shared issues. Allow emoji reactions for feedback. Configure voting for community prioritization.

**Dependencies:** Projects, Issues, Pages, Intake

---

### 28. Automation

Automation provides rules-based automatic issue management.

**Auto-Close Rules:**
Automatically close issues that have been in completed state for a configured number of days. Keeps backlogs clean without manual maintenance.

**Auto-Archive Rules:**
Archive closed issues after a specified period. Moves resolved work to archives while preserving history.

**Custom Conditions:**
Define rules based on state transitions, time periods, and issue attributes. Automate repetitive maintenance tasks.

**Dependencies:** Projects, Issues, States

---

## DATA & FILE MANAGEMENT

### 29. File Assets & Uploads

File management handles attachments and media across the platform.

**Attachments:**
Upload files directly to issues with metadata tracking. Support for multiple file formats with type validation. File size limits configurable per instance.

**Media Support:**
Image uploads for pages, project covers, and user avatars. S3-compatible storage backend (AWS S3 or MinIO). CDN delivery for optimized performance.

**Organization:**
Attachments link to their parent entities (issues, pages, projects). Count aggregations display on issue cards. File history maintained for audit trails.

**Dependencies:** S3/Object Storage, Issues, Pages, Projects

---

### 30. Import/Export

Import and export capabilities enable data portability and migration.

**Import:**
Import data from other project management tools. Map fields from external systems to Plane entities. Async job processing handles large imports without blocking.

**Export:**
Export workspace or project data in CSV format. Download complete data sets for backup or migration. Configure which entities to include in exports.

**Job Management:**
Track import and export job progress. View job history with status and details. Retry failed jobs or cancel in-progress operations.

**Dependencies:** Projects, Issues, Users

---

## AUTHENTICATION & SECURITY

### 31. Authentication Systems

Plane supports multiple authentication methods for flexible user access.

**Email/Password:**
Traditional sign-up and sign-in with email and password. Password strength validation using zxcvbn library (minimum score 3/4). Secure password hashing with PBKDF2. Can be globally disabled via configuration.

**Magic Links:**
Passwordless authentication via email. 6-digit codes with 10-minute expiration stored in Redis. Rate limiting prevents abuse (3 attempts per code). Requires SMTP email configuration.

**OAuth Providers:**
Google, GitHub, GitLab, and Gitea OAuth 2.0 integration. GitHub supports optional organization membership validation. Profile data sync available (avatar, name). Tokens stored with refresh capability.

**Session Management:**
Device tracking captures user agent, IP address, and login timestamps. Separate session handling for app and admin interfaces. Configurable session timeouts and cookie security.

**Multi-Method Support:**
Single accounts can link multiple authentication methods. OAuth users can establish passwords. Seamless experience across sign-in methods.

**Dependencies:** Users, OAuth Providers

---

### 32. API Tokens

API tokens enable programmatic access to Plane data and operations.

**Token Management:**
Generate tokens with descriptive labels for identification. Tokens use "plane_api_" prefix with random UUID. Set optional expiration dates for security. Activate or deactivate tokens without deletion.

**Usage Tracking:**
System records when each token was last used. API activity logging captures requests, responses, and client information. Rate limiting protects against abuse (default 60 requests/minute).

**Service Tokens:**
Special tokens for bot/automation use cases with different rate limits. Workspace scoping limits token access to specific workspaces.

**Dependencies:** Users, Workspace

---

### 33. Admin Settings & Instance Management

God Mode provides system-wide administration for self-hosted instances.

**General Settings:**
Configure instance name, URL, and branding. Set up system-wide defaults and policies. Manage instance-level feature flags.

**Email Configuration:**
Configure SMTP settings for email delivery. Set sender addresses and templates. Test email configuration before deployment.

**Authentication Providers:**
Enable/disable authentication methods globally. Configure OAuth credentials for each provider. Set organization restrictions for GitHub.

**Instance Management:**
View and manage all workspaces. Monitor system health and usage. Configure storage and external service connections.

**Dependencies:** System Configuration

---

## ANALYTICS & REPORTING

### 34. Activity Tracking

Activity tracking provides comprehensive audit trails of all changes.

**Issue Activity:**
Every field change is captured with before/after values. Activity entries record who made the change and when. Supports undo/redo operations through version snapshots.

**Version History:**
IssueVersion captures full state snapshots at each change. Description versions maintain rich text history. Rollback to any previous version is supported.

**Page Tracking:**
PageLog records all content changes including embedded content. PageVersion maintains up to 20 snapshots per page. Complete audit trail for compliance requirements.

**Dependencies:** Issues, Pages, Users

---

### 35. Home Dashboard

The dashboard provides personalized workspace overview and quick access to important information.

**Quick Stats:**
View issues assigned to you, upcoming deadlines, and overdue items. See activity across your projects. Track personal productivity metrics.

**Recent Activity:**
Feed of recent changes across subscribed issues and projects. Quick navigation to recently visited items. Personalized based on your work patterns.

**Widgets:**
Personal tasks widget for quick action items. Recent projects for fast navigation. Onboarding guidance for new users.

**Dependencies:** Workspace, Projects, Issues, Cycles

---

## UI/UX FEATURES

### 36. Layouts & Views

Multiple display formats accommodate different work styles and use cases.

**List View:**
Traditional table-style display with sortable columns. Configurable visible columns. Inline editing for quick updates. Efficient for bulk scanning and updates.

**Kanban Board:**
Card-based columnar layout grouped by state, priority, or custom field. Drag-and-drop to move issues between columns. Visual WIP limits and swimlanes. Quick card creation within columns.

**Calendar View:**
Monthly and weekly views with issues plotted by dates. Visual timeline planning for deadlines. Drag to reschedule issues.

**Gantt Chart:**
Timeline visualization with start dates and durations. Dependency lines show relationships. Critical path analysis for project planning.

**Spreadsheet:**
Grid-based view with all properties as columns. Bulk editing across multiple issues. Excel-like experience for data-heavy work.

**Dependencies:** React, Tailwind CSS

---

### 37. Accessibility & Internationalization

Multi-language support and accessibility features ensure inclusive access.

**Language Support:**
Multiple language translations via @plane/i18n package. RTL (right-to-left) language support. Locale-aware date and number formatting.

**Accessibility:**
WCAG 2.2 AA compliance targets. Keyboard navigation throughout the interface. Screen reader support with ARIA labels. High contrast mode support.

**Dependencies:** i18n Library

---

### 38. Theme & Personalization

Customizable appearance adapts to user preferences.

**Theme Modes:**
Light and dark mode support. System preference detection. Per-user preference storage.

**Workspace Themes:**
Custom color schemes per workspace. Brand color integration. Theme persistence across sessions.

**Dependencies:** React, Tailwind CSS

---

### 39. Search & Command Palette

Global search and keyboard navigation accelerate common workflows.

**Search:**
Search issues, projects, and users across the workspace. Full-text search with relevance ranking. Recent searches for quick repeat queries.

**Command Palette:**
Keyboard-first navigation (Cmd/Ctrl+K). Quick actions without mouse. Navigate to any entity by typing. Create issues, switch projects, change views.

**Shortcuts:**
Comprehensive keyboard shortcuts for power users. Customizable bindings. Quick reference available in-app.

**Dependencies:** Issues, Projects, Users

---

## SHARED PACKAGES

### 40. Shared Packages & Libraries

Reusable packages provide consistent functionality across frontend applications.

| Package | Purpose |
|---------|---------|
| **@plane/types** | TypeScript type definitions for all domain models, API responses, and shared interfaces |
| **@plane/ui** | React component library with Button, Input, Modal, Dropdown, and form components with Storybook documentation |
| **@plane/services** | API service layer wrapping Axios with typed request/response handling for all backend endpoints |
| **@plane/hooks** | Custom React hooks for common patterns like useOutsideClick, useWindowSize, and state management |
| **@plane/constants** | Shared constants including API endpoints, enum values, and configuration defaults |
| **@plane/utils** | Utility functions for string formatting, date handling, color manipulation, and file operations |
| **@plane/editor** | TipTap-based rich text editor with Markdown support, real-time collaboration, and custom extensions |
| **@plane/i18n** | Internationalization framework with language files, translation utilities, and locale management |
| **@plane/shared-state** | MobX-based state management with global stores and context providers for cross-app state sharing |
| **@plane/tailwind-config** | Shared Tailwind CSS configuration with design tokens, color palette, and spacing scale |

---

## SUPPORTING SYSTEMS

### 41. Background Tasks & Workers

Asynchronous task processing handles long-running operations without blocking user requests.

**Email Tasks:**
User activation, password reset, invitation emails, and notification delivery. Templated email generation with user context. Delivery tracking and retry logic.

**Event Tasks:**
Webhook delivery with retry and backoff. External system synchronization (GitHub, Slack). Activity and notification creation from model changes.

**Data Tasks:**
Import and export job processing. Archive cleanup and maintenance. File processing and thumbnail generation.

**Sync Tasks:**
GitHub issue and comment synchronization. Page version creation and cleanup. Session and token cleanup.

**Dependencies:** RabbitMQ, Celery, Redis

---

### 42. Database & Persistence

PostgreSQL provides the primary data store with Django ORM.

**Data Model:**
Django ORM models with comprehensive relationships. Migration system for schema evolution. Soft deletion pattern (archived_at) for reversibility. Audit timestamps (created_at, updated_at) on all models.

**Performance:**
Strategic indexing for common query patterns. Full-text search capabilities. Query optimization with select_related and prefetch_related.

**Dependencies:** PostgreSQL

---

### 43. Caching & Session Management

Redis provides caching, session storage, and real-time features.

**Caching:**
Query result caching for expensive operations. Rate limiting counters and windows. Magic link code storage with TTL.

**Sessions:**
User session persistence. Device tracking data. Real-time presence information.

**Dependencies:** Redis

---

### 44. Storage & CDN

Object storage handles file uploads and delivery.

**Storage Backend:**
S3-compatible object storage (AWS S3 or MinIO). Configurable bucket and path prefixes. Secure signed URLs for access control.

**Delivery:**
CDN integration for optimized file delivery. Image optimization and resizing. Efficient upload handling with size limits.

**Dependencies:** AWS S3 or S3-compatible (MinIO)

---

## ARCHITECTURE SUMMARY

### Frontend Apps

| App | Port | Purpose |
|-----|------|---------|
| **Web** | 3000 | Main user application for project management, issue tracking, and collaboration |
| **Admin** | 3001 | Instance administration (God Mode) for system configuration and workspace management |
| **Space** | 3002 | Public read-only views for shared projects, issues, and intake forms |

### Backend Services

| Service | Purpose |
|---------|---------|
| **API** | Django REST API providing all data operations, authentication, and business logic |
| **Live** | Node.js real-time collaboration server for WebSocket connections and document synchronization |

### Data Flow

```
User Interface (Web/Admin/Space)
           ↓
    API Services Layer
           ↓
    Django REST API
           ↓
   PostgreSQL Database
           ↓
Redis Cache / RabbitMQ
           ↓
   Background Workers
           ↓
External Services (GitHub, Slack, Email, S3)
```

### Real-Time Collaboration Flow

```
Browser Editor
      ↓
WebSocket Connection
      ↓
HocusPocus Server
      ↓
Y.js CRDT Merge
      ↓
Database Persistence
```

---

## SUBSCRIPTION TIERS & PAID FEATURES

Plane offers five subscription tiers with progressively advanced features. The system uses a combination of backend license models, frontend edition-aware components, and project-level feature flags.

### Pricing Overview

| Tier | Monthly | Yearly | Target |
|------|---------|--------|--------|
| **FREE** | $0 | $0 | Individual/Small teams |
| **ONE** | Legacy | Legacy | Transitional tier |
| **PRO** | $8/seat | $6/seat | Growing teams |
| **BUSINESS** | $12/seat | $10/seat | Scaling organizations |
| **ENTERPRISE** | Custom | Custom | Large enterprises |

---

### FREE (Community Edition)

The free tier provides core project management functionality for individuals and small teams.

**Included Features:**
- Basic project management with unlimited projects
- Work items (issues) with full CRUD operations
- Basic state management and workflow
- Comments, reactions, and @mentions
- User invitations and basic roles (Admin, Member, Guest)
- Workspaces and teams
- Basic estimates (Points and Categories)
- Pages/Wiki with basic functionality
- Public views and pages (read-only)
- Discord community support

**Limits:**
- 12 members per workspace (Cloud)
- ~50 members (Self-hosted)
- 5GB storage
- 5MB max file size
- Limited time tracking (read-only)
- Limited bulk operations

---

### PRO ($8/month per seat)

Pro tier unlocks productivity features for growing teams with advanced tracking and integrations.

**All FREE features plus:**

**Dashboards & Reports:**
Advanced analytics dashboard with custom report generation, project analytics, and cycle burndown reports. Visualize team performance and track progress across multiple dimensions.

**Full Time Tracking:**
Complete time logging on issues with time estimates, time spent tracking, and time-based reports. Track where team effort is being spent and compare estimates to actuals.

**Bulk Operations:**
Batch editing capabilities for updating multiple issues simultaneously. Change states, assignees, labels, and other properties in bulk to save time on repetitive tasks.

**Teamspaces:**
Organize work across teams with team-level workspace separation. Control visibility across teams and manage cross-team dependencies.

**Trigger & Action (Basic Automation):**
Workflow automation with basic conditions and triggers. Set up rules that execute actions automatically when events occur (e.g., auto-assign when label added).

**Wikis:**
Full knowledge base functionality with page hierarchy, collaborative editing, rich media support, and 2-day version history.

**Popular Integrations:**
- GitHub integration with bidirectional sync
- Slack notifications and issue creation
- Webhook support for custom integrations
- Jira import capability

**Epics:**
High-level grouping of related issues for feature planning. Track progress across multiple modules and cycles.

**Custom Properties (Project-level):**
Add custom fields to issues at the project level for tracking project-specific data.

**Shared Views:**
Create and share saved views with team members. Standardize how teams see and filter their work.

**Dependencies in Gantt:**
Visualize issue dependencies in timeline view. See critical paths and manage delivery schedules.

**Work Item Types:**
Categorize issues as Bug, Feature, Task, or custom types with type-specific behaviors.

**SSO (OIDC/SAML):**
Enterprise single sign-on support for streamlined authentication.

**Limits:**
- Unlimited members
- 1TB storage
- 100MB max file size
- 5,000 automation runs/month
- 5 guests per paid member

---

### BUSINESS ($12/month per seat)

Business tier adds enterprise capabilities for scaling organizations with advanced workflow and compliance needs.

**All PRO features plus:**

**Project Templates:**
Pre-built project structures for quick setup. Create custom templates capturing states, labels, estimates, and default settings. Share templates across the workspace.

**Workflows & Approvals:**
Advanced workflow automation with multi-stage approval chains. Define approval processes for issues, changes, or any workflow state transitions.

**Decision & Loops Automation:**
Conditional logic in workflows with loop-based automation. Build complex business rules with decision trees and iterative processes.

**Custom Reports:**
Advanced report builder with custom metrics and KPIs. Schedule automated report generation and export to various formats.

**Nested Pages:**
Deep hierarchical page structures with multi-level organization. Page template inheritance and advanced documentation architecture.

**Intake Forms:**
Customizable request submission forms for external stakeholders. Configure form fields, automatic issue creation, and triage workflows.

**RBAC (Role-Based Access Control):**
Pre-defined roles with granular permissions. Control access to features and data at a detailed level.

**Baselines:**
Snapshot project state for comparison. Track scope changes and compare current progress against planned baselines.

**Advanced Analytics:**
Deep insights into team performance, velocity trends, and predictive analytics. Custom dashboards with advanced visualization.

**Workspace Activity Logs:**
Audit trail of all workspace activities. Track who did what and when for compliance and security.

**SLAs (Service Level Agreements):**
Define and track response and resolution time targets. Get alerts when SLAs are at risk.

**Limits:**
- Unlimited members
- 5TB storage
- 200MB max file size
- 10,000 automation runs/month
- 3-month page version history
- 5 guests per paid member

---

### ENTERPRISE (Custom Pricing)

Enterprise tier provides maximum flexibility, security, and support for large organizations.

**All BUSINESS features plus:**

**Private & Managed Deployments:**
Self-hosted on customer infrastructure with dedicated instances. Private deployment options with customer-managed hosting and full data sovereignty.

**GAC (Guest Access Controls):**
Granular access control for guest users beyond standard roles. Permission-level customization with feature-level guest restrictions.

**LDAP Support:**
LDAP directory integration for user authentication. Automatic user provisioning and enterprise directory synchronization.

**Databases & Formulas:**
Advanced data modeling with relational database features. Formula fields for calculated values and custom field types.

**Unlimited Automation Flows:**
No limits on workflow automation. Advanced automation editor with full workflow capability.

**Full-Suite Professional Services:**
- Dedicated support team
- Implementation assistance
- Custom development
- Training and onboarding
- Architecture consultation

**Custom Integrations:**
Build custom integrations with dedicated API support and custom webhook configurations.

**Advanced Security:**
- SOC 2 compliance support
- Custom data retention policies
- Advanced audit logging
- IP allowlisting

**Limits:**
- Unlimited everything
- Custom storage
- Custom file sizes
- Unlimited automations
- Unlimited page versions
- Custom guest policies

---

### Feature Comparison Matrix

| Feature | FREE | PRO | BUSINESS | ENTERPRISE |
|---------|------|-----|----------|------------|
| **Core Project Management** | ✓ | ✓ | ✓ | ✓ |
| **Work Items/Issues** | ✓ | ✓ | ✓ | ✓ |
| **Cycles/Sprints** | ✓ | ✓ | ✓ | ✓ |
| **Modules** | ✓ | ✓ | ✓ | ✓ |
| **Pages/Wiki** | Limited | ✓ | ✓ Full | ✓ Full |
| **Active Cycles (Workspace View)** | ✗ | ✓ | ✓ | ✓ |
| **Time Tracking** | Read-only | ✓ Full | ✓ Full | ✓ Full |
| **Bulk Operations** | Limited | ✓ Full | ✓ Full | ✓ Full |
| **Webhooks** | ✗ | ✓ | ✓ | ✓ |
| **Integrations** | ✗ | ✓ | ✓ | ✓ |
| **Jira Import** | ✗ | ✓ | ✓ | ✓ |
| **Dashboards** | ✗ | ✓ | ✓ | ✓ |
| **Analytics** | ✗ | Basic | Advanced | ✓ |
| **Teamspaces** | ✗ | ✓ | ✓ | ✓ |
| **Automations** | ✗ | 5,000/mo | 10,000/mo | Unlimited |
| **Epics** | ✗ | ✓ | ✓ | ✓ |
| **Custom Properties** | ✗ | Project | Workspace | ✓ |
| **Approvals** | ✗ | ✗ | ✓ | ✓ |
| **Project Templates** | ✗ | ✗ | ✓ | ✓ |
| **Nested Pages** | ✗ | ✗ | ✓ | ✓ |
| **Intake Forms** | ✗ | ✗ | ✓ | ✓ |
| **RBAC** | ✗ | ✗ | ✓ | ✓ |
| **Activity Logs** | ✗ | ✗ | ✓ | ✓ |
| **SSO (OIDC/SAML)** | ✗ | ✓ | ✓ | ✓ |
| **LDAP** | ✗ | ✗ | ✗ | ✓ |
| **GAC** | ✗ | ✗ | ✗ | ✓ |
| **Private Deployments** | ✗ | ✗ | ✗ | ✓ |
| **Professional Services** | ✗ | ✗ | ✗ | ✓ |

---

### Edition Architecture (CE vs EE)

Plane uses a hybrid Community Edition (CE) and Enterprise Edition (EE) architecture:

**Directory Structure:**
```
apps/web/
├── ce/                 # Community Edition components
│   ├── components/     # FREE tier UI components
│   └── store/          # FREE tier state management
│
└── ee/                 # Enterprise Edition components
    ├── components/     # PRO+ tier UI components
    └── store/          # PRO+ tier state management
```

**Feature Gating:**
- Frontend checks subscription tier before rendering premium components
- FREE users see upgrade prompts when accessing PRO+ features
- Backend validates permissions for premium API endpoints
- Project-level feature flags allow granular enablement

**Upgrade Flow:**
1. User attempts to access premium feature
2. System checks workspace subscription tier
3. If insufficient, displays upgrade modal with feature comparison
4. User redirects to checkout (Cloud) or license activation (Self-hosted)
5. Upon upgrade, features become immediately available

---

### Self-Hosted vs Cloud

| Aspect | Cloud (plane.so) | Self-Hosted |
|--------|------------------|-------------|
| **Hosting** | Managed by Plane | Customer infrastructure |
| **Updates** | Automatic | Manual |
| **Member Limits** | Plan-based | Infrastructure-based |
| **Payment** | Integrated billing | License key activation |
| **Support** | Included | Plan-based |
| **Data Location** | Plane servers | Customer control |
| **Customization** | Standard | Full access |

**Self-Hosted Considerations:**
- Community Edition available free for self-hosting
- Commercial licenses (Pro/Business/Enterprise) available for self-hosted
- Member limits are recommendations based on infrastructure capacity
- All features accessible based on license key

---

*This document provides a comprehensive overview of all features in the Plane project management platform, focusing on functionality, user capabilities, and business value delivered by each feature.*
