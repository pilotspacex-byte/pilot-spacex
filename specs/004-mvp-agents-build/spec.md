# Feature Specification: MVP AI Agents Build with Claude Agent SDK

**Feature Branch**: `004-mvp-agents-build`
**Created**: 2026-01-25
**Status**: Draft
**Input**: Refactor and build all MVP AI agents to use Claude Agent SDK as the primary orchestration layer, replacing the current custom implementation with direct provider API calls.

## Executive Summary

This feature migrates the Pilot Space AI layer from a custom orchestration implementation (using direct `anthropic` and `google.generativeai` API calls) to the Claude Agent SDK. The migration introduces MCP (Model Context Protocol) tools for database, GitHub, and search access, implements human-in-the-loop approval flows for critical actions (DD-003), and establishes BYOK (Bring Your Own Key) secure storage (DD-002).

**Key Benefits**:
- Unified agent orchestration with `query()` for one-shot tasks and `ClaudeSDKClient` for multi-turn conversations
- 15 MCP tools enabling agents to access Pilot Space data, GitHub, and semantic search (12 read-only, 3 write)
- Human-in-the-loop approval preventing unintended destructive AI actions
- Proper provider routing per DD-011 (Claude for code analysis, OpenAI for embeddings)
- Cost tracking and session management for multi-turn conversations

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Uses AI Context for Issue Understanding (Priority: P1)

A developer opens an issue in Pilot Space and wants comprehensive AI-generated context to understand the implementation requirements. The AI Context agent analyzes the issue, searches related documentation, finds relevant code, identifies similar past issues, and generates a step-by-step implementation guide with Claude Code prompts.

**Why this priority**: This is the core value proposition of Pilot Space's "Note-First" AI-augmented workflow. Without AI context generation, developers lack the intelligent assistance that differentiates Pilot Space from traditional issue trackers.

**Independent Test**: Can be fully tested by creating an issue and requesting AI context generation. Delivers value by providing actionable implementation guidance.

**Acceptance Scenarios**:

1. **Given** a developer views an issue with title and description, **When** they click "Generate AI Context", **Then** the system streams a multi-turn analysis including issue summary, related documentation, code references, similar issues, and implementation guide within 30 seconds.

2. **Given** AI context generation is in progress, **When** the developer views the issue detail panel, **Then** they see real-time streaming updates with progress indicators for each analysis phase (analyzing, searching docs, finding code, checking similar issues, generating guide).

3. **Given** AI context has been generated, **When** the developer views the Claude Code prompts section, **Then** each task includes a ready-to-use prompt that can be copied to Claude Code for implementation.

4. **Given** the workspace has no Anthropic API key configured, **When** a developer requests AI context, **Then** the system displays a clear message directing them to workspace settings to configure their API key.

---

### User Story 2 - Developer Receives Ghost Text Suggestions While Writing Notes (Priority: P1)

A developer is writing in the Note Canvas and pauses typing. The system provides intelligent text completion suggestions (ghost text) that continue their thought naturally, appearing as grayed-out text after the cursor.

**Why this priority**: Ghost text is fundamental to the Note-First workflow, providing real-time AI assistance during the brainstorming phase where issues emerge naturally from thinking.

**Independent Test**: Can be fully tested by typing in a note and pausing. Delivers value by reducing cognitive load and accelerating documentation.

**Acceptance Scenarios**:

1. **Given** a developer is typing in a note block, **When** they pause for 500ms, **Then** ghost text suggestions appear within 2 seconds showing a natural continuation of their text.

2. **Given** ghost text is displayed, **When** the developer presses Tab, **Then** the suggestion is accepted and becomes part of the document.

3. **Given** ghost text is displayed, **When** the developer presses Escape or continues typing, **Then** the suggestion disappears.

4. **Given** the cursor is in a code block, **When** ghost text triggers, **Then** the suggestion provides valid code completion matching the programming language.

---

### User Story 3 - Team Lead Reviews AI-Generated PR Analysis (Priority: P1)

A team lead receives a notification that an AI PR review has been completed for a pull request linked to a Pilot Space project. They view the comprehensive review covering architecture, security, code quality, performance, and documentation aspects.

**Why this priority**: Unified PR Review (DD-006) is a core differentiator, combining architecture and code review into one AI-powered analysis that saves reviewer time and improves code quality.

**Independent Test**: Can be fully tested by linking a GitHub repository, creating a PR, and triggering AI review. Delivers value by providing structured, comprehensive code review feedback.

**Acceptance Scenarios**:

1. **Given** a pull request is opened in a linked GitHub repository, **When** the team lead requests AI review, **Then** the system generates a comprehensive review covering all five aspects (architecture, security, code quality, performance, documentation) with severity indicators.

2. **Given** AI review identifies critical issues, **When** the review is displayed, **Then** critical issues are prominently shown with location (file:line), issue description, suggested fix, and rationale.

3. **Given** AI review is complete, **When** the team lead clicks "Post to GitHub", **Then** the review is posted as a GitHub PR comment with appropriate review status (Approve, Request Changes, or Comment).

4. **Given** the PR diff exceeds 5000 lines, **When** AI review is requested, **Then** the system processes the review in chunks and provides a complete analysis.

---

### User Story 4 - Developer Extracts Issues from Note Content (Priority: P2)

A developer has written extensive notes during a brainstorming session and wants to extract actionable issues from the content. The AI identifies potential issues, suggests titles, descriptions, priorities, and labels, presenting them with confidence tags.

**Why this priority**: Issue extraction bridges the Note-First workflow to actionable work items, enabling the natural transition from thinking to doing.

**Independent Test**: Can be fully tested by writing a note with action items and extracting issues. Delivers value by automating issue creation from unstructured content.

**Acceptance Scenarios**:

1. **Given** a note contains actionable content, **When** the developer clicks "Extract Issues", **Then** the system identifies potential issues and displays them with title, description, priority, labels, and confidence tags (Recommended/Default/Alternative).

2. **Given** extracted issues are displayed, **When** the developer selects issues to create, **Then** the system prompts for approval before creating the issues (per DD-003 human-in-the-loop).

3. **Given** the developer approves issue creation, **When** issues are created, **Then** each issue is linked back to the source note blocks.

4. **Given** an extracted issue has "Recommended" confidence tag, **When** displayed in the extraction panel, **Then** it appears prominently with a one-click accept option.

---

### User Story 5 - Admin Configures Workspace AI Settings (Priority: P2)

A workspace administrator sets up AI capabilities by configuring API keys for different providers (Anthropic required, OpenAI required for search, Google optional for latency-sensitive tasks).

**Why this priority**: BYOK configuration is the foundation for all AI features. Without proper key configuration, no AI capabilities function.

**Independent Test**: Can be fully tested by navigating to workspace settings and configuring API keys. Delivers value by enabling all AI features for the workspace.

**Acceptance Scenarios**:

1. **Given** an admin opens workspace AI settings, **When** they view the provider configuration section, **Then** they see clear indicators of which providers are required (Anthropic, OpenAI) vs optional (Google).

2. **Given** an admin enters an API key, **When** they save, **Then** the system validates the key by making a test call and displays success/failure feedback.

3. **Given** API keys are configured, **When** stored, **Then** keys are encrypted and never displayed in plaintext after initial entry.

4. **Given** an admin views cost tracking, **When** they open the AI usage dashboard, **Then** they see aggregated costs by agent type, user, and time period.

---

### User Story 6 - Developer Views Margin Annotations on Note Blocks (Priority: P2)

While reading a note, a developer sees AI-generated suggestions appearing in the right margin next to relevant blocks. These annotations provide improvements, questions, and references without interrupting the main content.

**Why this priority**: Margin annotations enhance the Note-First experience by providing contextual AI suggestions that improve content quality.

**Independent Test**: Can be fully tested by viewing a note with AI annotations enabled. Delivers value by surfacing improvement opportunities.

**Acceptance Scenarios**:

1. **Given** a developer focuses on a note block, **When** annotation generation completes, **Then** relevant suggestions appear in the right margin within 3 seconds.

2. **Given** a margin annotation is displayed, **When** the developer clicks it, **Then** they see the full suggestion with type (suggestion/improvement/question/reference) and confidence score.

3. **Given** multiple annotations exist for a block, **When** displayed, **Then** they are ordered by confidence score with highest first.

---

### User Story 7 - System Admin Reviews AI Approval Queue (Priority: P3)

A system administrator reviews pending AI actions that require human approval before execution, such as bulk issue creation or document publishing.

**Why this priority**: Human-in-the-loop approval (DD-003) ensures AI doesn't take destructive or high-impact actions without human consent.

**Independent Test**: Can be fully tested by triggering an action requiring approval and reviewing the queue.

**Acceptance Scenarios**:

1. **Given** an AI action requires approval, **When** the action is queued, **Then** the requesting user and workspace admins receive notifications with action details.

2. **Given** a pending approval request exists, **When** an admin views it, **Then** they see action type, description, AI confidence, affected items, and approve/reject buttons.

3. **Given** an admin approves a request, **When** they click "Approve & Execute", **Then** the AI action executes and results are logged.

4. **Given** an approval request expires (24 hours), **When** the expiration time passes, **Then** the request is marked as expired and the action is not executed.

---

### Edge Cases

- What happens when the AI provider rate limits are exceeded? System displays retry information and queues requests with exponential backoff.
- What happens when a multi-turn conversation session expires mid-conversation? System gracefully handles session timeout, preserves partial results, and allows restart.
- What happens when ghost text generation takes longer than 2 seconds? System cancels the request and waits for next typing pause.
- What happens when an approval request is submitted for an already-deleted item? System detects missing target and rejects the request with explanation.
- What happens when the GitHub repository is disconnected mid-PR review? System completes review with available data and notes incomplete analysis.
- What happens when multiple users trigger AI context for the same issue simultaneously? System deduplicates requests and shares the result.

## Requirements *(mandatory)*

### Functional Requirements

#### Infrastructure Layer

- **FR-001**: System MUST provide a secure storage mechanism for workspace API keys using encryption at rest.
- **FR-002**: System MUST validate API keys upon entry by making a test call to the respective provider.
- **FR-003**: System MUST implement human-in-the-loop approval for critical AI actions including: delete operations, bulk operations, issue creation from extraction, and document publishing.
- **FR-004**: System MUST track AI usage costs per workspace, user, agent type, and time period with provider-specific pricing calculations.
- **FR-005**: System MUST maintain multi-turn conversation sessions for agents requiring context continuity (AI Context, Conversation). Session limits: 20 messages maximum, 8000 tokens max history; older messages truncated FIFO when limits reached.
- **FR-006**: System MUST route AI tasks to appropriate providers based on task type: code analysis to Claude, latency-sensitive tasks to fast models, embeddings to OpenAI.
- **FR-007**: System MUST implement automatic failover when a primary provider is unavailable, falling back to configured alternatives. Retry policy: 3 attempts with exponential backoff (1s, 2s, 4s). Circuit breaker opens after 3 consecutive failures, attempts recovery after 30-second timeout (half-open state).

#### Agent Capabilities

- **FR-008**: System MUST provide ghost text completion that appears within 2 seconds of typing pause (500ms debounce).
- **FR-009**: System MUST provide margin annotations for note blocks that appear within 3 seconds of block focus.
- **FR-010**: System MUST extract structured issues from note content with title, description, priority, labels, and confidence tags.
- **FR-011**: System MUST generate comprehensive AI context for issues including: summary, related documentation, code references, similar issues, and Claude Code prompts.
- **FR-012**: System MUST perform unified PR review covering architecture, security, code quality, performance, and documentation aspects.
- **FR-013**: System MUST support multi-turn conversation with message history for contextual follow-up questions.
- **FR-014**: System MUST generate documentation from codebase context.
- **FR-015**: System MUST decompose complex issues into subtasks with dependency ordering.
- **FR-016**: System MUST detect potential duplicate issues using semantic similarity.
- **FR-017**: System MUST recommend assignees based on issue content and team expertise.
- **FR-018**: System MUST generate architecture diagrams from issue context.
- **FR-019**: System MUST enhance issue descriptions with additional context and structure.

#### Streaming & Real-time

- **FR-020**: System MUST stream all AI responses in real-time using Server-Sent Events (SSE) format.
- **FR-021**: System MUST display progress indicators during multi-phase AI operations (e.g., AI context generation phases).
- **FR-022**: System MUST allow cancellation of in-progress AI operations.

#### Data Access (MCP Tools)

- **FR-023**: AI agents MUST be able to retrieve complete issue context including related notes, links, and activity history.
- **FR-024**: AI agents MUST be able to retrieve note content with block structure.
- **FR-025**: AI agents MUST be able to create annotations for note blocks.
- **FR-026**: AI agents MUST be able to search the indexed codebase semantically.
- **FR-027**: AI agents MUST be able to retrieve project context including labels, states, and conventions.
- **FR-028**: AI agents MUST be able to retrieve GitHub PR details and diffs.
- **FR-029**: AI agents MUST be able to perform semantic search across workspace content.
- **FR-030**: AI agents MUST be able to find similar issues using embedding similarity.
- **FR-030a**: AI agents MUST be able to retrieve workspace members for assignee recommendations.
- **FR-030b**: AI agents MUST be able to retrieve page content with document structure.
- **FR-030c**: AI agents MUST be able to retrieve cycle context for sprint-aware suggestions.

#### Approval Flow

- **FR-031**: System MUST require approval for: create_sub_issues, extract_issues, publish_docs (configurable per project).
- **FR-032**: System MUST always require approval for: delete_workspace, delete_project, delete_issue, delete_note, merge_pr, bulk_delete (non-configurable).
- **FR-033**: System MUST auto-execute with notification for: suggest_labels, suggest_priority, post_pr_comments, send_notifications.
- **FR-034**: Approval requests MUST expire after 24 hours if not resolved.
- **FR-035**: System MUST log all AI actions (both auto-executed and approved) for audit purposes.

### Key Entities

- **WorkspaceAPIKey**: Stores encrypted API keys per workspace per provider (Anthropic, OpenAI, Google). Attributes: workspace reference, provider type, encrypted key value, validation status, last validated timestamp.

- **AIApprovalRequest**: Tracks pending human approvals for AI actions. Attributes: requesting user, workspace, action type, description, payload, confidence score, status (pending/approved/rejected/expired), expiration time, resolution details, resolved by user.

- **AICostRecord**: Records AI usage for billing and analytics. Attributes: user, workspace, agent type, provider, model, token counts (input/output), calculated cost in USD, duration in milliseconds, correlation ID.

- **AISession**: Manages multi-turn conversation state. Attributes: session ID, user, agent type, message history (max 20 messages, 8000 tokens), context data, total accumulated cost, created timestamp, last activity timestamp. TTL: 30 minutes inactivity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ghost text suggestions appear within 2 seconds (p95) of typing pause for 95% of requests.
- **SC-002**: AI context generation completes within 30 seconds for standard issues (p95).
- **SC-003**: PR review generates comprehensive analysis within 60 seconds for PRs under 1000 lines changed.
- **SC-004**: Issue extraction identifies actionable items with 80%+ precision (items marked "Recommended" are created by users 80% of the time).
- **SC-005**: All critical AI actions (delete, merge, bulk operations) are blocked until human approval with zero bypass incidents.
- **SC-006**: API keys are never exposed in logs, error messages, or API responses.
- **SC-007**: Cost tracking accuracy is within 1% of actual provider charges.
- **SC-008**: System gracefully degrades when providers are unavailable, with clear user feedback and automatic failover within 5 seconds.
- **SC-009**: Multi-turn conversation sessions maintain context for up to 30 minutes of inactivity.
- **SC-010**: All AI streaming endpoints deliver first token within 1 second of request initiation.

## Scope

### In Scope

1. **Infrastructure Layer**
   - MCP Server with Pilot Space tools (database_tools, github_tools, search_tools)
   - Secure key storage for BYOK API keys
   - Approval service for human-in-the-loop
   - Cost tracking with database persistence
   - Session management for multi-turn conversations
   - Provider selection with routing rules
   - Automatic failover between providers

2. **Agent Migration (12 Agents)**
   - GhostTextAgent: One-shot with Claude Haiku only, no fallback provider (cost-optimized, single provider)
   - MarginAnnotationAgent: One-shot with Claude Sonnet
   - IssueExtractorAgent: One-shot with Claude Sonnet
   - AIContextAgent: Multi-turn with Claude Opus
   - ConversationAgent: Multi-turn with Claude Sonnet
   - PRReviewAgent: One-shot with Claude Opus (unified review)
   - DocGeneratorAgent: One-shot with Claude Sonnet
   - TaskDecomposerAgent: One-shot with Claude Opus
   - DiagramGeneratorAgent: One-shot with Claude Sonnet
   - IssueEnhancerAgent: One-shot with Claude Sonnet
   - AssigneeRecommenderAgent: One-shot with Claude Haiku
   - DuplicateDetectorAgent: One-shot with Claude Sonnet

3. **SDK Orchestrator**
   - Replace custom AIOrchestrator with SDK-based orchestrator
   - Integrate approval flow for critical actions
   - Cost tracking for all agent executions
   - Session management for multi-turn agents

4. **API Layer**
   - SSE streaming endpoints for all agents
   - Approval request/resolution endpoints
   - Cost tracking endpoints per workspace/user

5. **Database Migrations**
   - workspace_api_keys table (encrypted BYOK storage)
   - ai_approval_requests table
   - ai_cost_records table
   - ai_sessions table

6. **Frontend Integration**
   - SSE client utilities with reconnection and error handling
   - MobX stores for AI state management (GhostText, AIContext, PRReview, Approval, Cost)
   - TipTap extensions for Ghost Text and Margin Annotations
   - AI Context panel with streaming phases and Claude Code prompt cards
   - PR Review panel with 5-aspect analysis display
   - Issue Extraction panel with confidence tags and approval modal
   - Workspace AI Settings page with BYOK key management
   - Approval Queue page with real-time updates
   - Cost Dashboard with usage analytics
   - Conversation UI with multi-turn chat

### Out of Scope

- RAG pipeline enhancement (embedding infrastructure improvements)
- GitHub webhook handlers (handled in GitHub integration feature)
- Workspace billing integration (cost tracking is for display only)
- Custom model fine-tuning or local model support

## Assumptions

- The Claude Agent SDK is available and installable via pip with the imports specified in the architecture document. Version constraint: `claude-agent-sdk>=1.0,<2.0` (minor version pin for stability).
- Supabase Vault is available for encryption at rest of API keys.
- Redis is available for session management.
- The repository layer (T074-T077) exists for MCP database tools to query.
- GitHub integration (T172-T192) exists for MCP GitHub tools to access PR data.
- Provider pricing remains stable at documented rates (pricing updates will require cost tracker updates).

## Dependencies

- **T040-T044**: Supabase Auth must be implemented for user context in agents.
- **T061**: Redis infrastructure must be available for SessionManager.
- **T074-T077**: Repository layer must exist for MCP database tools to function.
- **T172-T192**: GitHub integration must exist for MCP GitHub tools to access repository data.

## Clarifications

### Session 2026-01-25

- Q: Which provider should GhostTextAgent use for latency-sensitive text completion? → A: Claude Haiku only (no fallback) - prioritizing cost efficiency and single provider simplicity.
- Q: What circuit breaker thresholds for provider failover? → A: 3 consecutive failures to open circuit, 30 seconds timeout before half-open recovery attempt.
- Q: What retry configuration before circuit breaker failure? → A: 3 retries with exponential backoff (1s, 2s, 4s delays), ~7s max wait before failover.
- Q: What are multi-turn session message/token limits? → A: 20 messages max, 8000 tokens max history; older messages truncated when limits reached.
- Q: What version constraint for Claude Agent SDK dependency? → A: Pin to minor version (>=1.0,<2.0) - allows patch updates, blocks breaking changes.

## Design Decisions Referenced

- **DD-002**: BYOK (Bring Your Own Key) model - users provide their own API keys
- **DD-003**: Human-in-the-loop critical-only approval model
- **DD-006**: Unified PR Review combining architecture, code, security, performance, and documentation review
- **DD-011**: Provider routing - Claude for code analysis, fast models for latency-sensitive tasks, OpenAI for embeddings
- **DD-048**: AI confidence tags (Recommended/Default/Current/Alternative) for extracted suggestions
- **DD-066**: SSE for AI streaming responses
