/**
 * ChatInput - Compact auto-resizing contenteditable input with skill/agent menus
 * Follows shadcn/ui AI prompt input component pattern
 */

import { useCallback, useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useParams, useRouter } from 'next/navigation';
import type { KeyboardEvent } from 'react';
import { observer } from 'mobx-react-lite';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Sparkles, AtSign, History, Hash } from 'lucide-react';
import { cn } from '@/lib/utils';
import type {
  NoteContext,
  IssueContext,
  ProjectContext,
  SkillDefinition,
  AgentDefinition,
} from '../types';
import { TokenBudgetRing } from '@/components/ui/token-budget-ring';
import { ContextIndicator } from './ContextIndicator';
import { SkillMenu } from './SkillMenu';
import { useSkills } from '../hooks/useSkills';
import { AgentMenu } from './AgentMenu';
import { SectionMenu } from './SectionMenu';
import { SessionResumeMenu, type SessionSummary } from './SessionResumeMenu';
import type { HeadingItem } from '@/components/editor/AutoTOC';
import { WorkingIndicator } from './WorkingIndicator';
import { useAttachments } from '../hooks/useAttachments';
import { useDriveStatus } from '../hooks/useDriveStatus';
import { AttachmentButton } from './AttachmentButton';
import { DriveFilePicker } from './DriveFilePicker';
import { RecordButton } from './RecordButton';
import { AudioPlaybackPill } from './AudioPlaybackPill';
import { attachmentsApi } from '@/services/api/attachments';
import { EntityPicker } from './EntityPicker';
import { useRecentEntities } from '../hooks/useRecentEntities';
import type { RecentEntity } from '../hooks/useRecentEntities';
import { ModeSelector } from './ModeSelector';
import type { ChatMode } from './types';
import { SlashMenu } from './SlashMenu';
import type { SlashCommand } from './extensions/slash-extension';
// Phase 87 Plan 05 — quote-to-chat. QuoteBlock TipTap node is imported here
// so the future TipTap migration only needs to register it in a useEditor
// extensions array; today the runtime uses createQuoteBlockElement +
// serializeQuoteBlocksFromContainer for the contenteditable composer.
import {
  QuoteBlock,
  serializeQuoteBlocksFromContainer,
  serializeDocWithQuoteBlocks,
} from './extensions/quote-block-node';
import { useQuoteToChat } from '@/hooks/use-quote-to-chat';
// Reference QuoteBlock + serializeDocWithQuoteBlocks so static analysis treats
// them as used — they are part of the public API surface this file exposes
// for the upcoming TipTap migration.
void QuoteBlock;
void serializeDocWithQuoteBlocks;

/**
 * Recursively walks a contenteditable node tree to produce a serialized string.
 * Text nodes emit raw text; chip spans (with data-entity-type) emit @[Type:uuid];
 * <br> elements and block element boundaries (DIV, P) emit a newline character.
 * This ensures Shift+Enter-produced line breaks are preserved in the serialized value.
 */
function serializeNode(node: Node, isRoot = false): string {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.textContent ?? '';
  }
  if (node instanceof HTMLElement) {
    // Chip span — emit token directly (do not recurse into its children)
    if (node.dataset.entityType) {
      return `@[${node.dataset.entityType}:${node.dataset.entityId}]`;
    }
    // <br> — emit a newline
    if (node.tagName === 'BR') {
      return '\n';
    }
    // Block elements (DIV, P) produced by contenteditable wrap lines
    const isBlock = node.tagName === 'DIV' || node.tagName === 'P';
    let inner = '';
    for (const child of Array.from(node.childNodes)) {
      inner += serializeNode(child);
    }
    // Prefix a newline for non-root block elements so each nested div/p becomes a new line
    return isBlock && !isRoot ? '\n' + inner : inner;
  }
  return '';
}

function getSerializedValue(div: HTMLDivElement): string {
  return serializeNode(div, true);
}

// Helper: get text content before cursor in contenteditable (module-scope like getSerializedValue)
function getTextBeforeCursor(div: HTMLDivElement): string {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return '';
  const range = sel.getRangeAt(0).cloneRange();
  range.selectNodeContents(div);
  range.setEnd(sel.getRangeAt(0).startContainer, sel.getRangeAt(0).startOffset);
  return range.toString();
}

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (payload: {
    attachmentIds: string[];
    attachments: Array<{ attachmentId: string; filename: string; mimeType: string; sizeBytes: number; source: 'local' | 'google_drive' }>;
    voiceAudioUrl?: string | null;
    /** Phase 87 Plan 02 — slash invokes (/standup /digest) force a mode for one submit. */
    modeOverride?: ChatMode;
    /** Phase 87 Plan 02 — marker for inline-invoke slash commands (e.g. "standup"). */
    command?: string;
  }) => void;
  isStreaming?: boolean;
  isDisabled?: boolean;
  autoFocus?: boolean;
  noteContext?: NoteContext | null;
  issueContext?: IssueContext | null;
  projectContext?: ProjectContext | null;
  onClearNoteContext?: () => void;
  onClearIssueContext?: () => void;
  onClearProjectContext?: () => void;
  /** Token budget usage percentage (0-100) for budget ring display */
  tokenBudgetPercent?: number;
  /** Tokens used in current session */
  tokensUsed?: number;
  /** Total token budget */
  tokenBudget?: number;
  /** Sessions available for /resume command */
  sessions?: SessionSummary[];
  /** Loading state for sessions */
  sessionsLoading?: boolean;
  /** Callback when a session is selected from /resume menu */
  onSelectSession?: (sessionId: string) => void;
  /** Callback when session search is performed */
  onSearchSessions?: (query: string) => void;
  /** Callback when user requests a new session */
  onNewSession?: () => void;
  /** Headings from current note for # section menu */
  noteHeadings?: HeadingItem[];
  /** Callback when user selects a section from # menu */
  onSelectSection?: (heading: HeadingItem) => void;
  /** Workspace ID for attachment uploads */
  workspaceId?: string;
  /** Session ID for attachment uploads */
  sessionId?: string;
  className?: string;
  /**
   * Phase 87 Plan 01 — composer surface variant.
   * - `chat` (default): rounded-[22px] px-4 py-3
   * - `homepage`: rounded-[28px] px-6 py-4 (consumed by Phase 88 hero)
   */
  surface?: 'chat' | 'homepage';
  /**
   * Phase 88 Plan 01 — collapse the left-side toolbar to the calm
   * launchpad surface. When true:
   *  - AttachmentButton hidden
   *  - SkillMenu / AgentMenu / SectionMenu / SessionResumeMenu triggers hidden
   *  - `/` slash and `@` mention keystroke triggers are no-ops
   *  - ModeSelector + the right-side controls remain
   *  - Toolbar height is unchanged (UI-SPEC §8 — calm whitespace, not a bug)
   *
   * Defaults to `false` so every existing chat-page caller keeps the full
   * toolbar. Only `<HomeComposer>` (Phase 88 Plan 02) passes `true`.
   */
  slimToolbar?: boolean;
  /**
   * Phase 87 Plan 01 — current conversation mode (per-session). When omitted
   * the mode selector is hidden (back-compat for unmigrated callers).
   */
  currentMode?: ChatMode;
  /** Phase 87 Plan 01 — invoked when the user picks a new mode. */
  onModeChange?: (mode: ChatMode) => void;
  /**
   * Phase 87 Plan 02 — workspace slug for slash-command route templates.
   * Falls back to `useParams().workspaceSlug` when not provided.
   */
  workspaceSlug?: string;
}

export const ChatInput = observer<ChatInputProps>(
  ({
    value,
    onChange,
    onSubmit,
    isStreaming = false,
    isDisabled = false,
    autoFocus = false,
    noteContext,
    issueContext,
    projectContext,
    onClearNoteContext,
    onClearIssueContext,
    tokenBudgetPercent,
    tokensUsed,
    tokenBudget = 8000,
    sessions = [],
    sessionsLoading = false,
    onSelectSession,
    onSearchSessions,
    onNewSession,
    onClearProjectContext,
    noteHeadings,
    onSelectSection,
    workspaceId,
    sessionId,
    className,
    surface = 'chat',
    slimToolbar = false,
    currentMode,
    onModeChange,
    workspaceSlug: workspaceSlugProp,
  }) => {
    // Phase 87 Plan 02 — slash command routing context
    const router = useRouter();
    const params = useParams<{ workspaceSlug?: string }>();
    const workspaceSlug = workspaceSlugProp ?? params?.workspaceSlug ?? '';
    const { skills: dynamicSkills } = useSkills(workspaceId);
    const { attachments, attachmentIds, addFile, addFromDrive, removeFile, reset } = useAttachments(
      {
        workspaceId: workspaceId ?? '',
        sessionId,
      }
    );
    const { data: driveStatus } = useDriveStatus(workspaceId);
    const [drivePickerOpen, setDrivePickerOpen] = useState(false);
    const [isDragOver, setIsDragOver] = useState(false);
    const [pendingAudioUrl, setPendingAudioUrl] = useState<string | null>(null);
    // Text in input before live recording started — used to restore on cancel or prepend on commit
    const preRecordTextRef = useRef('');
    const editableRef = useRef<HTMLDivElement>(null);
    const inputContainerRef = useRef<HTMLDivElement>(null);
    const skillCommandRef = useRef<HTMLDivElement>(null);
    const entityCommandRef = useRef<HTMLDivElement>(null);
    const [skillMenuOpen, setSkillMenuOpen] = useState(false);
    const [agentMenuOpen, setAgentMenuOpen] = useState(false);
    const [sectionMenuOpen, setSectionMenuOpen] = useState(false);
    const [resumeMenuOpen, setResumeMenuOpen] = useState(false);
    const [inputWidth, setInputWidth] = useState<number | null>(null);

    // Slash query state — tracks text typed after '/' in the chat input.
    // Phase 87 Plan 02 — drives SlashMenu (the new 11-command palette). The
    // legacy SkillMenu is no longer opened by '/' typing; it remains reachable
    // via the Sparkles toolbar button (which exposes /resume, /new, dynamic
    // skills) and via the SlashMenu '/skill' picker row.
    const slashQueryStartOffsetRef = useRef<number | null>(null);
    const [slashQuery, setSlashQuery] = useState<string | null>(null);
    const [slashMenuOpen, setSlashMenuOpen] = useState(false);
    const [slashAnchorRect, setSlashAnchorRect] = useState<DOMRect | null>(null);

    // When a skill close transitions to another menu (e.g. /resume),
    // skip the SkillMenu onOpenChange focus-restore to prevent the
    // deferred focus from closing the newly-opened menu.
    const skipFocusOnSkillCloseRef = useRef(false);

    // @ entity picker state (D-02)
    const atQueryStartOffsetRef = useRef<number | null>(null);
    const [atQuery, setAtQuery] = useState<string | null>(null);
    const [entityPickerOpen, setEntityPickerOpen] = useState(false);

    // Recent entities for picker (D-03)
    const { recentEntities, addEntity } = useRecentEntities(workspaceId ?? '');

    // Measure input container width for popover sizing
    useEffect(() => {
      if (inputContainerRef.current) {
        const resizeObserver = new ResizeObserver((entries) => {
          for (const entry of entries) {
            setInputWidth(entry.contentRect.width);
          }
        });
        resizeObserver.observe(inputContainerRef.current);
        return () => resizeObserver.disconnect();
      }
    }, []);

    // Auto-focus contenteditable when requested
    useEffect(() => {
      if (autoFocus && editableRef.current) {
        editableRef.current.focus();
      }
    }, [autoFocus]);

    // Phase 87 Plan 05 — quote-to-chat composer wiring.
    // 1. Mark composer as mounted so the QuoteToChatPill knows it can dispatch
    //    the event directly instead of queueing to window.__pilotPendingQuotes.
    useEffect(() => {
      const w = window as unknown as { __pilotChatComposerMounted?: boolean };
      w.__pilotChatComposerMounted = true;
      return () => {
        w.__pilotChatComposerMounted = false;
      };
    }, []);

    // 2. Listen for `pilot:quote-to-chat` events (and drain pending queue).
    //    The hook prepends a `data-quote-block` element into the contenteditable
    //    and triggers onChange so MobX/parent state stays in sync.
    useQuoteToChat({
      ref: editableRef,
      onChange,
      serialize: (root) => getSerializedValue(root),
    });

    // Sync contenteditable DOM when value prop changes (e.g., reset to '' after submit)
    useEffect(() => {
      if (!editableRef.current) return;
      const currentText = getSerializedValue(editableRef.current);
      if (value !== currentText) {
        editableRef.current.textContent = value;
      }
    }, [value]);

    // Detect #section trigger (only when note headings are available)
    useEffect(() => {
      if (!noteHeadings || noteHeadings.length === 0) return;
      const lastChar = value.slice(-1);
      const beforeLastChar = value.slice(-2, -1);

      if (lastChar === '#' && (beforeLastChar === '' || beforeLastChar === ' ')) {
        setSectionMenuOpen(true);
      }
    }, [value, noteHeadings]);

    const handleInput = useCallback(
      (e: React.FormEvent<HTMLDivElement>) => {
        const div = e.currentTarget;
        const serialized = getSerializedValue(div);
        onChange(serialized);

        // Slash trigger detection: track text after '/' at position 0 in first text node
        const sel = window.getSelection();
        if (sel && sel.rangeCount > 0) {
          // @ trigger detection for EntityPicker (D-02)
          const textBeforeCursor = getTextBeforeCursor(div);

          // Phase 88 Plan 01 — slimToolbar disables the slash + mention command
          // surfaces entirely (homepage launchpad calm-composer contract).
          if (slimToolbar) {
            return;
          }
          // Phase 87 Plan 02 — '/' at start of input opens SlashMenu (11-command
          // palette). Mid-word '/' (e.g. inside http://) does NOT trigger because
          // textBeforeCursor only starts with '/' when the slash is at position 0.
          if (textBeforeCursor.startsWith('/') && !/\s/.test(textBeforeCursor)) {
            const query = textBeforeCursor.slice(1); // text typed after '/'
            slashQueryStartOffsetRef.current = 0;
            setSlashQuery(query);
            // Anchor the SlashMenu popover to the input container's top-left
            // (we render above the composer). createPortal mounts to document.body.
            const rect = inputContainerRef.current?.getBoundingClientRect() ?? null;
            setSlashAnchorRect(rect);
            setSlashMenuOpen(true);
          } else if (slashMenuOpen) {
            // '/' prefix gone, or space was typed — close menu
            slashQueryStartOffsetRef.current = null;
            setSlashQuery(null);
            setSlashMenuOpen(false);
            setSlashAnchorRect(null);
          }
          const atIdx = textBeforeCursor.lastIndexOf('@');
          if (atIdx >= 0 && !/\s/.test(textBeforeCursor.slice(atIdx + 1))) {
            const query = textBeforeCursor.slice(atIdx + 1);
            atQueryStartOffsetRef.current = atIdx;
            setAtQuery(query);
            setEntityPickerOpen(true);
          } else {
            atQueryStartOffsetRef.current = null;
            setAtQuery(null);
            setEntityPickerOpen(false);
          }
        }
      },
      [onChange, slashMenuOpen, slimToolbar]
    );

    const handlePaste = useCallback(
      (e: React.ClipboardEvent<HTMLDivElement>) => {
        e.preventDefault();
        const text = e.clipboardData.getData('text/plain');
        document.execCommand('insertText', false, text);
      },
      []
    );

    const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragOver(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
      if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
        setIsDragOver(false);
      }
    }, []);

    const handleDrop = useCallback(
      (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragOver(false);
        const files = e.dataTransfer.files;
        for (const file of Array.from(files)) {
          void addFile(file);
        }
      },
      [addFile]
    );

    const handleConnectDrive = useCallback(async () => {
      if (!workspaceId) return;
      try {
        const callbackUrl = `${window.location.origin}/drive/callback`;
        const { auth_url } = await attachmentsApi.getDriveAuthUrl(workspaceId, callbackUrl);
        window.open(auth_url, '_blank', 'noopener,noreferrer');
        toast.success('Google OAuth tab opened — authorize and return here.');
      } catch {
        toast.error('Failed to get Google Drive authorization URL.');
      }
    }, [workspaceId]);

    const handleSkillSelect = useCallback(
      (skill: SkillDefinition) => {
        if (!editableRef.current) return;
        // Clear slash query state and close menu immediately
        setSlashQuery(null);
        setSkillMenuOpen(false);
        slashQueryStartOffsetRef.current = null;
        // Session-only skills retain their existing handling — they have no
        // detail page (no slug); they trigger session UX instead.
        // Special handling for /resume - open session picker instead
        if (skill.name === 'resume') {
          editableRef.current.textContent = '';
          onChange('');
          skipFocusOnSkillCloseRef.current = true;
          setResumeMenuOpen(true);
          return;
        }
        // Special handling for /new - start fresh session
        if (skill.name === 'new') {
          editableRef.current.textContent = '';
          onChange('');
          onNewSession?.();
          editableRef.current.focus();
          return;
        }
        // Phase 91 Plan 05 — repurpose: picking a skill from the chat composer
        // (Sparkles button → SkillMenu, or `/skill <name>` slash picker) now
        // NAVIGATES to the detail page instead of inserting `/skill ` into
        // the chat input. SKILL-04: discoverable from anywhere.
        editableRef.current.textContent = '';
        onChange('');
        const target = skill.slug
          ? `/${workspaceSlug}/skills/${skill.slug}`
          : `/${workspaceSlug}/skills`;
        router.push(target);
      },
      [onChange, onNewSession, setSkillMenuOpen, router, workspaceSlug]
    );

    const handleAgentSelect = useCallback(
      (agent: AgentDefinition) => {
        if (!editableRef.current) return;
        // Replace trailing '@' with '@agentname '
        const lastNode = editableRef.current.lastChild;
        if (lastNode?.nodeType === Node.TEXT_NODE && lastNode.textContent?.endsWith('@')) {
          lastNode.textContent = lastNode.textContent.slice(0, -1) + `@${agent.name} `;
        } else {
          editableRef.current.textContent = (editableRef.current.textContent ?? '') + `@${agent.name} `;
        }
        onChange(getSerializedValue(editableRef.current));
        editableRef.current.focus();
        // Move cursor to end
        const range = document.createRange();
        range.selectNodeContents(editableRef.current);
        range.collapse(false);
        window.getSelection()?.removeAllRanges();
        window.getSelection()?.addRange(range);
      },
      [onChange]
    );

    const handleSectionSelect = useCallback(
      (heading: HeadingItem) => {
        if (!editableRef.current) return;
        // Remove the # trigger char from input
        const lastNode = editableRef.current.lastChild;
        if (lastNode?.nodeType === Node.TEXT_NODE && lastNode.textContent?.endsWith('#')) {
          lastNode.textContent = lastNode.textContent.slice(0, -1).trim();
        }
        onChange(getSerializedValue(editableRef.current));
        onSelectSection?.(heading);
        editableRef.current.focus();
      },
      [onChange, onSelectSection]
    );

    const handleSessionSelect = useCallback(
      (sessionId: string) => {
        onSelectSession?.(sessionId);
        setResumeMenuOpen(false);
      },
      [onSelectSession]
    );

    const handleSkillCancel = useCallback(() => {
      setSlashQuery(null);
      slashQueryStartOffsetRef.current = null;
      editableRef.current?.focus();
    }, []);

    // Phase 87 Plan 02 — clear the typed '/{query}' from the contenteditable.
    const clearSlashTrigger = useCallback(() => {
      if (!editableRef.current) return;
      editableRef.current.textContent = '';
      onChange('');
      slashQueryStartOffsetRef.current = null;
      setSlashQuery(null);
      setSlashMenuOpen(false);
      setSlashAnchorRect(null);
    }, [onChange]);

    // Phase 87 Plan 02 — dispatch a chosen slash command. Routes via Next.js
    // for `route` / `picker` kinds; submits via onSubmit with modeOverride for
    // `invoke` kinds. Stub-tolerant routes still navigate (Next handles 404);
    // skill-missing toasts mirror the spec copy.
    const handleSlashSelect = useCallback(
      async (cmd: SlashCommand) => {
        clearSlashTrigger();
        editableRef.current?.focus();

        const emitSystemMessage = (text: string) => {
          // Local-only event. Plan 03 wires a MessageList listener; for now we
          // also surface a toast so the fallback is user-visible.
          if (typeof window !== 'undefined') {
            window.dispatchEvent(
              new CustomEvent('pilot:chat-system-message', { detail: { text } }),
            );
          }
          toast(text);
        };

        if (cmd.kind === 'route' || cmd.kind === 'picker') {
          const target = cmd.routeTemplate?.(workspaceSlug);
          if (!target) {
            emitSystemMessage(
              `Coming soon — \`${cmd.keyword}\` will open the ${cmd.id} composer.`,
            );
            return;
          }
          router.push(target);
          return;
        }

        if (cmd.kind === 'invoke' && cmd.invoke) {
          try {
            await cmd.invoke({
              workspaceSlug,
              router: { push: (p) => router.push(p) },
              submitMessage: async (payload) => {
                // Reuse the parent's submit pipeline. Forward modeOverride so
                // ChatView.handleSubmit honors `research` for /standup /digest
                // without permanently mutating the user's selected mode.
                onSubmit({
                  attachmentIds: [],
                  attachments: [],
                  voiceAudioUrl: null,
                  modeOverride: payload.mode,
                  command: payload.command,
                });
              },
              emitSystemMessage,
            });
          } catch {
            emitSystemMessage(
              cmd.id === 'standup'
                ? 'Standup skill is not installed in this workspace.'
                : 'Digest skill is not installed in this workspace.',
            );
          }
        }
      },
      [clearSlashTrigger, onSubmit, router, workspaceSlug],
    );

    const handleSlashClose = useCallback(() => {
      clearSlashTrigger();
      editableRef.current?.focus();
    }, [clearSlashTrigger]);

    const handleSectionCancel = useCallback(() => {
      if (!editableRef.current) return;
      const lastNode = editableRef.current.lastChild;
      if (lastNode?.nodeType === Node.TEXT_NODE && lastNode.textContent?.endsWith('#')) {
        lastNode.textContent = lastNode.textContent.slice(0, -1);
      }
      onChange(getSerializedValue(editableRef.current));
      editableRef.current.focus();
    }, [onChange]);

    const handleEntitySelect = useCallback(
      (entity: RecentEntity) => {
        if (!editableRef.current) return;

        // 1. Build the chip DOM node (D-01 + D-07)
        const chip = document.createElement('span');
        chip.contentEditable = 'false';
        chip.setAttribute('data-entity-type', entity.type);
        chip.setAttribute('data-entity-id', entity.id);
        chip.textContent = `@${entity.title}`;
        chip.className =
          'inline-flex items-center gap-1 mx-0.5 px-1.5 py-0.5 rounded-md ' +
          'bg-primary/10 text-primary text-xs font-medium select-none cursor-default';

        // 2. Find and remove '@{query}' text before cursor.
        // We must locate the @-trigger inside a Text node — Range.startOffset
        // means a child index when startContainer is an Element, not a character
        // offset. We walk back from the selection anchor to find a Text node that
        // contains the '@' trigger text and compute offsets within that node only.
        const sel = window.getSelection();
        let spaceNode: Text | null = null;
        if (sel && sel.rangeCount > 0) {
          try {
            const range = sel.getRangeAt(0);
            const atLen = 1 + (atQuery?.length ?? 0);

            // Resolve the Text node that holds the '@{query}' text
            let textNode: Text | null = null;
            let charOffset = 0;
            if (range.startContainer.nodeType === Node.TEXT_NODE) {
              textNode = range.startContainer as Text;
              charOffset = range.startOffset;
            } else if (range.startContainer instanceof Element) {
              // Caret is at a child-node boundary — inspect the child at startOffset - 1
              const child = range.startContainer.childNodes[range.startOffset - 1];
              if (child?.nodeType === Node.TEXT_NODE) {
                textNode = child as Text;
                charOffset = textNode.length;
              }
            }

            if (textNode !== null) {
              const deleteStart = Math.max(0, charOffset - atLen);
              range.setStart(textNode, deleteStart);
              range.setEnd(textNode, charOffset);
            }

            range.deleteContents();
            range.insertNode(chip);

            // 3. Insert trailing space after chip
            spaceNode = document.createTextNode(' ');
            range.setStartAfter(chip);
            range.collapse(true);
            range.insertNode(spaceNode);
          } catch {
            // DOMException guard — fall back: insert chip at cursor without deleting
            const range = sel.getRangeAt(0);
            range.insertNode(chip);
            spaceNode = document.createTextNode(' ');
            range.setStartAfter(chip);
            range.collapse(true);
            range.insertNode(spaceNode);
          }
        }

        // 4. Notify parent and update state (chip is in DOM at this point)
        onChange(getSerializedValue(editableRef.current));
        addEntity(entity);
        setAtQuery(null);
        setEntityPickerOpen(false);

        // 5. Place cursor after spaceNode (deferred so cmdk/Radix focus side-effects settle)
        const capturedSpaceNode = spaceNode;
        setTimeout(() => {
          if (!editableRef.current) return;
          editableRef.current.focus();
          if (capturedSpaceNode) {
            const newSel = window.getSelection();
            if (newSel) {
              const newRange = document.createRange();
              newRange.setStartAfter(capturedSpaceNode);
              newRange.collapse(true);
              newSel.removeAllRanges();
              newSel.addRange(newRange);
            }
          }
        }, 0);
      },
      [atQuery, onChange, addEntity]
    );

    const handleKeyDown = useCallback(
      (e: KeyboardEvent<HTMLDivElement>) => {
        // Forward Arrow/Enter keys to cmdk root when a menu is open
        // cmdk's internal keyboard handler is bound to its root div, but focus stays in the
        // contenteditable (outside cmdk). Dispatching a native KeyboardEvent on the cmdk root
        // lets React 18 event delegation pick it up and fire cmdk's synthetic onKeyDown handler.
        // Phase 87 Plan 02 — SlashMenu owns its own window-capture keydown, so
        // we must NOT also forward to a cmdk root (would double-fire / fight
        // with SlashMenu's selection state).
        if ((skillMenuOpen || entityPickerOpen) && !slashMenuOpen) {
          if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter') {
            e.preventDefault();
            const targetRef = skillMenuOpen ? skillCommandRef : entityCommandRef;
            if (targetRef.current) {
              targetRef.current.dispatchEvent(
                new KeyboardEvent('keydown', {
                  key: e.key,
                  bubbles: true,
                  cancelable: true,
                })
              );
            }
            return;
          }
        }

        // Escape: close skill menu (before entity picker check)
        if (e.key === 'Escape' && skillMenuOpen) {
          e.preventDefault();
          setSkillMenuOpen(false);
          setSlashQuery(null);
          slashQueryStartOffsetRef.current = null;
          editableRef.current?.focus();
          return;
        }

        // Escape: close entity picker, leave @{query} text in place (D-02)
        if (e.key === 'Escape' && entityPickerOpen) {
          e.preventDefault();
          setEntityPickerOpen(false);
          editableRef.current?.focus();
          return;
        }

        // Backspace: remove chip when cursor is immediately after one.
        // Two cases for "caret immediately after chip":
        //   A) startContainer is a Text node at offset 0 → check previousSibling
        //   B) startContainer is the contenteditable Element → check childNodes[startOffset - 1]
        if (e.key === 'Backspace') {
          const sel = window.getSelection();
          if (sel && sel.rangeCount > 0) {
            const range = sel.getRangeAt(0);
            if (range.collapsed) {
              let chipCandidate: ChildNode | null = null;
              const container = range.startContainer;

              if (container === editableRef.current) {
                // Case B: startOffset is a child index
                chipCandidate = editableRef.current.childNodes[range.startOffset - 1] ?? null;
              } else if (range.startOffset === 0) {
                // Case A: caret at start of a text/element node
                chipCandidate =
                  container === editableRef.current
                    ? editableRef.current.lastChild
                    : container.previousSibling;
              }

              if (
                chipCandidate instanceof HTMLElement &&
                chipCandidate.dataset.entityType
              ) {
                e.preventDefault();
                chipCandidate.remove();
                onChange(getSerializedValue(editableRef.current!));
              }
            }
          }
        }

        if (
          e.key === 'Enter' &&
          !e.shiftKey &&
          !skillMenuOpen &&
          !slashMenuOpen &&
          !agentMenuOpen &&
          !sectionMenuOpen &&
          !resumeMenuOpen &&
          !entityPickerOpen
        ) {
          e.preventDefault();
          const baseSerialized = editableRef.current
            ? getSerializedValue(editableRef.current)
            : value;
          // Phase 87 Plan 05 — lift any quote blocks into the leading
          // `> [!quote source=... section="..."]` markdown fence before submit.
          // serializeQuoteBlocksFromContainer prepends quote markdown and
          // returns the original serialized value when no quote blocks exist.
          const serialized = serializeQuoteBlocksFromContainer(
            editableRef.current,
            baseSerialized,
          );
          if (serialized.trim() && !isStreaming && !isDisabled) {
            const readyAttachments = attachments
              .filter((a) => a.status === 'ready' && a.attachmentId)
              .map((a) => ({
                attachmentId: a.attachmentId!,
                filename: a.filename,
                mimeType: a.mimeType,
                sizeBytes: a.sizeBytes,
                source: a.source,
              }));
            // If quote blocks contributed markdown, push the merged value to
            // the parent so it ends up in the API payload (parent reads
            // `value` to build the request body).
            if (serialized !== baseSerialized) {
              onChange(serialized);
            }
            onSubmit({ attachmentIds, attachments: readyAttachments, voiceAudioUrl: pendingAudioUrl });
            setPendingAudioUrl(null);
            reset();
          }
        }
      },
      [
        value,
        isStreaming,
        isDisabled,
        skillMenuOpen,
        slashMenuOpen,
        agentMenuOpen,
        sectionMenuOpen,
        resumeMenuOpen,
        entityPickerOpen,
        onSubmit,
        attachments,
        attachmentIds,
        pendingAudioUrl,
        reset,
        onChange,
      ]
    );

    // Phase 87 Plan 01 — Gemini composer shell. Outer wrapper holds the
    // borderless `#f0f4f9` surface; rounded-[22px] for chat, rounded-[28px]
    // for the homepage hero variant. NO border, NO shadow.
    const surfaceClasses =
      surface === 'homepage'
        ? 'rounded-[28px] px-6 py-4'
        : 'rounded-[22px] px-4 py-3';

    return (
      <>
        <div
          data-chat-composer
          className={cn(
            'relative bg-[#f0f4f9]',
            surfaceClasses,
            isStreaming && 'opacity-95',
            className
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {isDragOver && (
            <div
              className="absolute inset-0 z-20 flex items-center justify-center bg-background/80 border-2 border-dashed border-primary/50 rounded-[22px] pointer-events-none"
              data-testid="drop-overlay"
            >
              <span className="text-sm font-medium text-primary">Drop to attach</span>
            </div>
          )}
          <div className="space-y-2">
            {/* Context indicator */}
            <ContextIndicator
              noteContext={noteContext}
              issueContext={issueContext}
              projectContext={projectContext}
              onClearNoteContext={onClearNoteContext}
              onClearIssueContext={onClearIssueContext}
              onClearProjectContext={onClearProjectContext}
              attachments={attachments}
              onRemoveAttachment={removeFile}
            />

            {/* Audio playback pill — shown after voice transcription, before sending */}
            {pendingAudioUrl && (
              <AudioPlaybackPill
                audioUrl={pendingAudioUrl}
                onRemove={() => setPendingAudioUrl(null)}
              />
            )}

            {/* Input area - single container with inline toolbar */}
            <div className="relative" ref={inputContainerRef}>
              {/* Entity picker — positioned above the input via absolute bottom-full (D-06) */}
              <EntityPicker
                open={entityPickerOpen}
                onOpenChange={(open) => {
                  setEntityPickerOpen(open);
                  if (!open) {
                    setAtQuery(null);
                    atQueryStartOffsetRef.current = null;
                    setTimeout(() => editableRef.current?.focus(), 0);
                  }
                }}
                query={atQuery ?? ''}
                workspaceId={workspaceId ?? ''}
                recentEntities={recentEntities}
                onSelect={handleEntitySelect}
                width={inputWidth ?? undefined}
                commandRef={entityCommandRef}
              />

              <div
                role="textbox"
                aria-multiline="true"
                aria-label="Chat input"
                contentEditable={!isDisabled}
                suppressContentEditableWarning
                data-testid="chat-input"
                ref={editableRef}
                onInput={handleInput}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                className={cn(
                  // Phase 87 Plan 01: contenteditable inherits the composer
                  // shell — no own border / bg / radius. The Gemini surface
                  // wrapper above provides the visual chrome.
                  // Phase 94 Plan 02 (MIG-03): drop right-reserve at <640
                  // so the toolbar can wrap below the textarea.
                  'min-h-[40px] max-h-[160px] overflow-y-auto resize-none pb-10 sm:pb-0 sm:pr-20',
                  'bg-transparent text-base',
                  'outline-none',
                  'motion-safe:transition-colors',
                  'empty:before:content-[attr(data-placeholder)] empty:before:text-muted-foreground/70',
                  isStreaming && 'chat-input-working',
                  isDisabled && 'cursor-not-allowed opacity-50'
                )}
                data-placeholder="Ask anything, draft a topic, or type / for commands…"
              />

              {/* Inline toolbar buttons. Phase 94 Plan 02 (MIG-03): flex-wrap
                  + max-w-full so buttons reflow at very narrow widths
                  (the composer reserves pb-10 below 640 for this row). */}
              <div className="absolute bottom-1.5 right-2 flex max-w-[calc(100%-1rem)] flex-wrap items-center justify-end gap-0.5">
                <RecordButton
                  workspaceId={workspaceId ?? ''}
                  onTranscript={(text, audioUrl) => {
                    // Append committed transcript to the pre-recording text
                    const base = preRecordTextRef.current;
                    onChange(base + (base ? ' ' : '') + text);
                    preRecordTextRef.current = '';
                    setPendingAudioUrl(audioUrl);
                    setTimeout(() => editableRef.current?.focus(), 0);
                  }}
                  onPartialTranscript={(text) => {
                    // Save original text on first partial, then show live preview
                    if (!preRecordTextRef.current && !text) return;
                    if (!preRecordTextRef.current) {
                      preRecordTextRef.current = value;
                    }
                    const base = preRecordTextRef.current;
                    onChange(base + (base ? ' ' : '') + text);
                  }}
                  disabled={isDisabled || isStreaming || !workspaceId}
                />
                {/* Phase 88 Plan 01 — slimToolbar gates the entire left
                    cluster (attachments + skill / agent / section / resume
                    menus). Toolbar height (44px) is preserved by the
                    surrounding container; the empty space is intentional. */}
                {!slimToolbar && (
                  <AttachmentButton
                    onAddFile={addFile}
                    disabled={isDisabled || isStreaming}
                    driveConnected={driveStatus?.connected}
                    onConnectDrive={handleConnectDrive}
                    onOpenDrivePicker={() => setDrivePickerOpen(true)}
                  />
                )}
                {tokenBudgetPercent != null && tokenBudgetPercent > 0 && (
                  <TokenBudgetRing
                    percentage={tokenBudgetPercent}
                    tokensUsed={tokensUsed}
                    tokenBudget={tokenBudget}
                  />
                )}
                {!slimToolbar && (
                  <>
                <SkillMenu
                  open={skillMenuOpen}
                  onOpenChange={(open) => {
                    setSkillMenuOpen(open);
                    if (!open) {
                      setSlashQuery(null);
                      slashQueryStartOffsetRef.current = null;
                      if (skipFocusOnSkillCloseRef.current) {
                        skipFocusOnSkillCloseRef.current = false;
                      } else {
                        setTimeout(() => editableRef.current?.focus(), 0);
                      }
                    }
                  }}
                  onSelect={handleSkillSelect}
                  onCancel={handleSkillCancel}
                  skills={dynamicSkills}
                  popoverWidth={inputWidth ?? undefined}
                  // Phase 87 Plan 02 — '/' typing now opens SlashMenu, not
                  // SkillMenu. Sparkles button is the only entry point for
                  // SkillMenu, which renders without a pre-filled query.
                  searchQuery=""
                  commandRef={skillCommandRef}
                >
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-muted-foreground/60 hover:text-foreground"
                    onClick={() => setSkillMenuOpen(true)}
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    <span className="sr-only">Open skill menu</span>
                  </Button>
                </SkillMenu>

                <AgentMenu
                  open={agentMenuOpen}
                  onOpenChange={setAgentMenuOpen}
                  onSelect={handleAgentSelect}
                  popoverWidth={inputWidth ?? undefined}
                >
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-muted-foreground/60 hover:text-foreground"
                    onClick={() => setAgentMenuOpen(true)}
                  >
                    <AtSign className="h-3.5 w-3.5" />
                    <span className="sr-only">Open agent menu</span>
                  </Button>
                </AgentMenu>

                {noteHeadings && noteHeadings.length > 0 && (
                  <SectionMenu
                    open={sectionMenuOpen}
                    onOpenChange={setSectionMenuOpen}
                    onSelect={handleSectionSelect}
                    onCancel={handleSectionCancel}
                    headings={noteHeadings}
                    popoverWidth={inputWidth ?? undefined}
                  >
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 text-muted-foreground/60 hover:text-foreground"
                      onClick={() => setSectionMenuOpen(true)}
                    >
                      <Hash className="h-3.5 w-3.5" />
                      <span className="sr-only">Reference note section</span>
                    </Button>
                  </SectionMenu>
                )}

                <SessionResumeMenu
                  open={resumeMenuOpen}
                  onOpenChange={setResumeMenuOpen}
                  sessions={sessions}
                  isLoading={sessionsLoading}
                  onSelect={handleSessionSelect}
                  onSearch={onSearchSessions}
                  popoverWidth={inputWidth ?? undefined}
                >
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-muted-foreground/60 hover:text-foreground"
                    onClick={() => setResumeMenuOpen(true)}
                  >
                    <History className="h-3.5 w-3.5" />
                    <span className="sr-only">Resume session</span>
                  </Button>
                </SessionResumeMenu>
                  </>
                )}
              </div>
            </div>

            {/* Phase 87 Plan 01 — right-aligned mode selector cluster.
              * Sits below the editor/inline-toolbar. Renders only when the
              * parent provides currentMode + onModeChange (i.e. ChatView
              * has wired the per-session mode store). */}
            {currentMode !== undefined && onModeChange && (
              <div className="ml-auto flex items-center gap-3">
                <ModeSelector
                  value={currentMode}
                  onChange={onModeChange}
                  disabled={isStreaming || isDisabled}
                />
              </div>
            )}

            {/* Working indicator when AI is processing */}
            <WorkingIndicator isVisible={isStreaming} />
          </div>
        </div>

        {/* Phase 87 Plan 02 — SlashMenu portal anchored above the composer.
            Mounts only when slashMenuOpen and we have an anchor rect. */}
        {slashMenuOpen &&
          slashAnchorRect &&
          typeof document !== 'undefined' &&
          createPortal(
            <div
              style={{
                position: 'fixed',
                left: slashAnchorRect.left,
                top: slashAnchorRect.top - 8,
                transform: 'translateY(-100%)',
                zIndex: 60,
              }}
            >
              <SlashMenu
                query={slashQuery ?? ''}
                onSelect={handleSlashSelect}
                onClose={handleSlashClose}
              />
            </div>,
            document.body,
          )}

        {drivePickerOpen && workspaceId && (
          <DriveFilePicker
            open={drivePickerOpen}
            onClose={() => setDrivePickerOpen(false)}
            workspaceId={workspaceId}
            sessionId={sessionId}
            onImported={(response) => {
              addFromDrive(response);
              setDrivePickerOpen(false);
            }}
          />
        )}
      </>
    );
  }
);

ChatInput.displayName = 'ChatInput';
