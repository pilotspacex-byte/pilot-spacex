'use client';

/**
 * CommandPalette v3 (Plan 90-03)
 *
 * Center modal (680px @ ~120px from top, 20px radius) with:
 *   - Scope tabs:    All · Chats · Topics · Tasks · Specs · People
 *   - Prefix modes:  '#' tasks · '@' people · '/' pages · '>' commands
 *   - Mode chip rendered inside input row when a prefix is consumed
 *   - Ghost completion overlay (text-only, opacity 20%, no raw HTML injection)
 *   - AI fallback row when query has zero matches → /chat?prompt=…
 *   - URL state sync via usePaletteQueryStringSync (?palette=1, ?scope, ?q)
 *
 * Cmd+P stays as an alias for Cmd+K (handled in useEffect below).
 *
 * Threat-model mitigations (Plan 90-03 §threat_model):
 *   T-90-06 — encodeURIComponent on /chat?prompt= construction
 *   T-90-07 — render user query / titles via React text nodes only
 */

import { createElement, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { FileText, Ticket, Sparkles, MessageSquare, Users } from 'lucide-react';

import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandGroup,
  CommandItem,
} from '@/components/ui/command';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { observer } from 'mobx-react-lite';
import { useUIStore, useWorkspaceStore } from '@/stores';
import { notesApi } from '@/services/api/notes';
import { issuesApi } from '@/services/api/issues';
import type { Note } from '@/types/note';
import type { Issue } from '@/types/issue';
import type { PaletteScope } from '@/stores/UIStore';
// Phase 91 Plan 05 — palette SKILLS group rendering.
import { useSkillCatalog } from '@/features/skills/hooks';
import { resolveLucideIcon } from '@/features/skills/lib/skill-icon';
import type { Skill } from '@/types/skill';
// Plan 93-05 — Move-to picker body, rendered when paletteMode === 'move'.
import { MoveToPickerContent } from '@/features/topics/components';

import {
  detectPrefixMode,
  consumePrefix,
  scopeForPrefix,
  ghostCompletion,
  placeholderForPrefix,
} from './palette/prefix';
import { usePaletteQueryStringSync } from '@/hooks/usePaletteQueryStringSync';

const MAX_RESULTS_PER_GROUP = 5;
const DEBOUNCE_MS = 250;

interface SearchResults {
  notes: Note[];
  issues: Issue[];
}

const SCOPES: { id: PaletteScope; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'chats', label: 'Chats' },
  { id: 'topics', label: 'Topics' },
  { id: 'tasks', label: 'Tasks' },
  { id: 'specs', label: 'Specs' },
  // Phase 91 Plan 05 — Skills tab between Specs and People (UI-SPEC §Surface 3).
  { id: 'skills', label: 'Skills' },
  { id: 'people', label: 'People' },
];

const GROUP_HEADING_CLS =
  '[&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[10px] ' +
  '[&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:tracking-[0.04em] ' +
  '[&_[cmdk-group-heading]]:text-[var(--text-muted)] [&_[cmdk-group-heading]]:uppercase';

// ─── Result row sub-components ─────────────────────────────────────────────

function NoteResultItem({ note }: { note: Note }) {
  return (
    <div className="flex items-center gap-2 min-w-0 w-full">
      <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="truncate text-[13px] font-medium">{note.title || 'Untitled'}</span>
    </div>
  );
}

function IssueResultItem({ issue }: { issue: Issue }) {
  const stateName = issue.state?.name ?? '';
  const stateColor = issue.state?.color;

  return (
    <div className="flex items-center gap-2 min-w-0 w-full">
      <Ticket className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="font-mono text-xs text-muted-foreground shrink-0">{issue.identifier}</span>
      <span className="truncate text-[13px] font-medium flex-1">{issue.name ?? issue.title}</span>
      {stateName && (
        <Badge
          variant="secondary"
          className="text-xs shrink-0 font-normal"
          style={stateColor ? { borderColor: stateColor, color: stateColor } : undefined}
        >
          {stateName}
        </Badge>
      )}
    </div>
  );
}

// Phase 91 Plan 05 — SKILLS row, mirrors NoteResultItem composition with
// the violet 12% icon-box from UI-SPEC §Surface 3. The icon is rendered
// via React.createElement (mirrors SkillCard) so the
// react-hooks/static-components lint rule doesn't flag the
// resolve-then-uppercase-JSX pattern.
function SkillResultItem({ skill }: { skill: Skill }) {
  const iconComponent = resolveLucideIcon(skill.icon);
  return (
    <div className="flex items-center gap-2 min-w-0 w-full">
      <span
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px]"
        style={{ background: 'rgba(124,92,255,0.12)' }}
      >
        {createElement(iconComponent, {
          className: 'h-4 w-4',
          style: { color: '#7c5cff' },
          'aria-hidden': true,
        })}
      </span>
      <span className="truncate text-[13px] font-medium">{skill.name}</span>
      <span className="truncate text-[13px] font-medium text-muted-foreground">
        {skill.description}
      </span>
    </div>
  );
}

function ResultSkeleton() {
  return (
    <div className="px-2 py-1.5 space-y-2">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="flex items-center gap-2">
          <Skeleton className="h-4 w-4 rounded shrink-0" />
          <Skeleton className="h-4 flex-1 rounded" />
        </div>
      ))}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────

export const CommandPalette = observer(function CommandPalette() {
  const uiStore = useUIStore();
  const workspaceStore = useWorkspaceStore();
  const router = useRouter();
  const params = useParams<{ workspaceSlug: string }>();
  const searchParams = useSearchParams();

  // Mount the URL ↔ store sync (palette + scope; q is local).
  usePaletteQueryStringSync();

  const open = uiStore.commandPaletteOpen;

  // Initial query hydrated from ?q= once (lazy initializer).
  const [query, setQuery] = useState<string>(() => searchParams?.get('q') ?? '');
  const [results, setResults] = useState<SearchResults>({ notes: [], issues: [] });
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Tracks whether the user manually clicked a scope tab AFTER typing a
  // prefix; prevents the prefix-driven scope auto-switch from clobbering
  // the user's choice.
  const manualScopeOverrideRef = useRef(false);

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) {
        uiStore.closeCommandPalette();
        setQuery('');
        setResults({ notes: [], issues: [] });
        setFetchError(null);
        manualScopeOverrideRef.current = false;
      }
    },
    [uiStore]
  );

  const workspaceSlug = params?.workspaceSlug;
  const workspaceId =
    workspaceStore.currentWorkspace?.id ??
    (workspaceSlug ? workspaceStore.getWorkspaceBySlug(workspaceSlug)?.id : undefined) ??
    workspaceStore.currentWorkspaceId;

  // ─── Phase 91 Plan 05 — skills catalog ───────────────────────────────────
  // TanStack staleTime is 30min so opening the palette repeatedly does NOT
  // refetch. The catalog is workspace-agnostic and small (~25 entries).
  const { data: allSkills } = useSkillCatalog();

  // ─── Prefix detection effect ─────────────────────────────────────────────
  // Only writes to the scope when a prefix transition actually happens —
  // never unconditionally on every query keystroke — so the user's manual
  // scope-tab click survives.
  const prevPrefixModeRef = useRef(uiStore.palettePrefixMode);
  useEffect(() => {
    const nextMode = detectPrefixMode(query);
    const prevMode = prevPrefixModeRef.current;

    if (nextMode !== uiStore.palettePrefixMode) {
      uiStore.setPalettePrefixMode(nextMode);
    }

    if (nextMode === prevMode) {
      // No transition — leave scope alone.
      return;
    }

    // Mode just appeared (null → tasks/people/pages/commands).
    if (nextMode !== null && !manualScopeOverrideRef.current) {
      const next = scopeForPrefix(nextMode);
      if (uiStore.paletteScope !== next) {
        uiStore.setPaletteScope(next);
      }
    }

    // Mode just disappeared (tasks → null via backspace, etc.). Restore
    // 'all' UNLESS the user explicitly clicked a different scope tab.
    if (nextMode === null) {
      manualScopeOverrideRef.current = false;
      if (uiStore.paletteScope !== 'all') {
        uiStore.setPaletteScope('all');
      }
    }

    prevPrefixModeRef.current = nextMode;
  }, [query, uiStore]);

  // ─── Debounced workspace search (notes + issues) ─────────────────────────
  const effectiveQuery = consumePrefix(query);

  useEffect(() => {
    if (!open) return;
    if (!workspaceId) return;

    if (!effectiveQuery.trim()) {
      setResults({ notes: [], issues: [] });
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setFetchError(null);

    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const [notesRes, issuesRes] = await Promise.all([
          notesApi.list(workspaceId, { search: effectiveQuery }, 1, MAX_RESULTS_PER_GROUP),
          issuesApi.list(workspaceId, { search: effectiveQuery }, 1, MAX_RESULTS_PER_GROUP),
        ]);
        if (cancelled) return;
        setResults({
          notes: notesRes.items.slice(0, MAX_RESULTS_PER_GROUP),
          issues: issuesRes.items.slice(0, MAX_RESULTS_PER_GROUP),
        });
      } catch {
        if (cancelled) return;
        setFetchError("Couldn't reach search. Retry?");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [effectiveQuery, open, workspaceId]);

  // ─── Cmd+P alias for Cmd+K ───────────────────────────────────────────────
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const platform =
        (navigator as Navigator & { userAgentData?: { platform?: string } }).userAgentData
          ?.platform ?? navigator.platform;
      const isMac = /mac/i.test(platform);
      const modifier = isMac ? event.metaKey : event.ctrlKey;

      if (modifier && event.key === 'p') {
        const activeTag = document.activeElement?.tagName.toLowerCase();
        const isEditorFocused =
          document.activeElement?.closest('.ProseMirror') !== null ||
          activeTag === 'input' ||
          activeTag === 'textarea';
        if (isEditorFocused) return;

        event.preventDefault();
        uiStore.openCommandPalette();
      }
    }
    window.addEventListener('keydown', handleKeyDown, { capture: true });
    return () => window.removeEventListener('keydown', handleKeyDown, { capture: true });
  }, [uiStore]);

  // ─── Selection handlers ──────────────────────────────────────────────────
  // ⌘↵ split-pane (?focus=) is recorded via metaSelectRef; cmdk Items don't
  // expose the originating event, so we capture modifier state on keydown
  // and read it inside onSelect.
  const metaSelectRef = useRef(false);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        metaSelectRef.current = true;
      }
    }
    function onKeyUp(e: KeyboardEvent) {
      // Reset shortly after enter handling so a subsequent plain Enter
      // doesn't inherit split-pane intent.
      if (e.key === 'Enter') {
        // small async reset
        setTimeout(() => {
          metaSelectRef.current = false;
        }, 0);
      }
    }
    window.addEventListener('keydown', onKeyDown, { capture: true });
    window.addEventListener('keyup', onKeyUp, { capture: true });
    return () => {
      window.removeEventListener('keydown', onKeyDown, { capture: true });
      window.removeEventListener('keyup', onKeyUp, { capture: true });
    };
  }, [open]);

  const handleSelectNote = useCallback(
    (noteId: string) => {
      if (!workspaceSlug) return;
      const target = metaSelectRef.current
        ? `/${workspaceSlug}/notes/${noteId}?focus=${noteId}`
        : `/${workspaceSlug}/notes/${noteId}`;
      router.push(target);
      handleOpenChange(false);
    },
    [router, workspaceSlug, handleOpenChange]
  );

  const handleSelectIssue = useCallback(
    (issueId: string, identifier?: string) => {
      if (!workspaceSlug) return;
      const focus = identifier ?? issueId;
      const target = metaSelectRef.current
        ? `/${workspaceSlug}/issues/${issueId}?focus=${focus}`
        : `/${workspaceSlug}/issues/${issueId}`;
      router.push(target);
      handleOpenChange(false);
    },
    [router, workspaceSlug, handleOpenChange]
  );

  // ─── Input keydown: backspace-to-empty clears prefix mode ────────────────
  function handleInputKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key !== 'Backspace') return;
    if (query === '' && uiStore.palettePrefixMode !== null) {
      uiStore.setPalettePrefixMode(null);
      uiStore.setPaletteScope('all');
      manualScopeOverrideRef.current = false;
    }
  }

  // ─── Derived view-model ──────────────────────────────────────────────────
  const trimmed = effectiveQuery.trim();
  const hasQuery = trimmed.length > 0;

  const scope = uiStore.paletteScope;
  const showTopics = scope === 'all' || scope === 'topics';
  const showTasks = scope === 'all' || scope === 'tasks';
  const showChats = scope === 'all' || scope === 'chats';
  const showSpecs = scope === 'all' || scope === 'specs';
  const showSkills = scope === 'all' || scope === 'skills';
  const showPeople = scope === 'all' || scope === 'people';

  // Phase 91 Plan 05 — Skills filter. In 'skills' scope with empty query show
  // the full catalog; otherwise filter against name/description/slug. Group is
  // hidden in 'all' scope when query is empty (UI-SPEC: do not render empty
  // groups; only the prefix-hint empty state shows).
  const filteredSkills = useMemo<Skill[]>(() => {
    if (!allSkills) return [];
    const q = trimmed.toLowerCase();
    if (!q && scope !== 'skills') return [];
    const matches = q
      ? allSkills.filter(
          (s) =>
            s.name.toLowerCase().includes(q) ||
            s.description.toLowerCase().includes(q) ||
            s.slug.toLowerCase().includes(q),
        )
      : allSkills;
    return scope === 'skills' ? matches.slice(0, 50) : matches.slice(0, MAX_RESULTS_PER_GROUP);
  }, [allSkills, trimmed, scope]);

  const hasSkillResults = filteredSkills.length > 0;

  // Skills count toward "has results" so the AI fallback row is suppressed
  // when only skills match (Plan 91-05).
  const hasResults =
    results.notes.length > 0 ||
    results.issues.length > 0 ||
    (showSkills && hasSkillResults);

  const firstResultTitle =
    results.notes[0]?.title ?? results.issues[0]?.name ?? results.issues[0]?.title ?? undefined;
  const ghost = ghostCompletion(effectiveQuery, firstResultTitle);

  // Plan 93-05 — when paletteMode === 'move', the palette becomes a Move-to
  // picker. We branch the result body, the input placeholder, and the footer
  // legend; everything else (Dialog, sizing, dismiss handler) is reused from
  // the search render path so backwards-compat stays trivial.
  const isMoveMode =
    uiStore.paletteMode === 'move' && uiStore.paletteMoveSourceId !== null;

  const placeholder = isMoveMode
    ? 'Move topic to…'
    : placeholderForPrefix(uiStore.palettePrefixMode);
  const modeChipChar =
    uiStore.palettePrefixMode === 'tasks'
      ? '#'
      : uiStore.palettePrefixMode === 'people'
        ? '@'
        : uiStore.palettePrefixMode === 'pages'
          ? '/'
          : uiStore.palettePrefixMode === 'commands'
            ? '>'
            : null;

  return (
    <CommandDialog
      open={open}
      onOpenChange={handleOpenChange}
      title={isMoveMode ? 'Move to…' : 'Command Palette'}
      description={
        isMoveMode
          ? 'Pick a destination topic'
          : 'Search chats, topics, tasks, specs, and people'
      }
      className="max-w-none w-[680px] rounded-[20px] top-[120px] translate-y-0 p-0"
      showCloseButton={false}
    >
      {/* ── Scope tabs ── (hidden in 93-05 move mode — picker has no scope) */}
      {!isMoveMode && (
        <ul
          role="tablist"
          aria-label="Palette scope"
          className="flex gap-1 px-4 py-2 border-b border-[var(--border-card)]"
        >
          {SCOPES.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                role="tab"
                aria-selected={scope === s.id}
                data-scope={s.id}
                aria-label={`${s.label ?? s.id} scope`}
                className={cn(
                  'px-3 py-1.5 rounded-md text-[13px] font-medium motion-safe:transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-primary)] focus-visible:ring-offset-2',
                  scope === s.id
                    ? 'bg-[#29a38615] text-[var(--brand-primary)] font-semibold'
                    : 'text-[var(--text-muted)] hover:bg-[var(--surface-input)]'
                )}
                onClick={() => {
                  uiStore.setPaletteScope(s.id);
                  manualScopeOverrideRef.current = true;
                }}
              >
                {s.label}
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* ── Input row: mode chip + CommandInput + ghost overlay + ⌘K ── */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-card)]">
        {modeChipChar && (
          <span
            data-testid="palette-mode-chip"
            className="inline-flex items-center justify-center px-2 py-0.5 rounded-md bg-[#29a38615] text-[var(--brand-primary)] text-[13px] font-semibold font-mono"
          >
            {modeChipChar}
          </span>
        )}

        <div className="relative flex-1 min-w-0">
          <CommandInput
            value={query}
            onValueChange={setQuery}
            onKeyDown={handleInputKeyDown}
            placeholder={placeholder}
            autoFocus
            className="text-[15px] placeholder:text-[var(--text-muted)] font-medium border-0 px-0 h-auto py-0"
          />
          {ghost && hasQuery && (
            <span
              aria-hidden="true"
              className="pointer-events-none absolute left-0 top-0 text-[15px] font-medium text-[var(--text-muted)] opacity-20 select-none"
              style={{ whiteSpace: 'pre' }}
            >
              {/* Pad with the user's typed text length so suffix lines up.
                  Rendered as a React text node — no raw HTML injection. */}
              {effectiveQuery + ghost}
            </span>
          )}
        </div>

        <kbd className="font-mono text-[10px] text-[var(--text-muted)] bg-[var(--surface-input)] rounded-md px-1.5 py-0.5">
          ⌘K
        </kbd>
      </div>

      {/* ── Results list ── */}
      <CommandList className="max-h-[420px]">
        {/* Plan 93-05 move-mode branch — render the Move-to picker body
            instead of the search groups. */}
        {isMoveMode && workspaceId && uiStore.paletteMoveSourceId && (
          <MoveToPickerContent
            workspaceId={workspaceId}
            sourceId={uiStore.paletteMoveSourceId}
            parentBeforeId={uiStore.paletteMoveSourceParentId}
          />
        )}

        {/* Loading */}
        {!isMoveMode && isLoading && <ResultSkeleton />}

        {/* Error */}
        {!isMoveMode && fetchError && !isLoading && (
          <div role="alert" className="px-3 py-4 text-[13px] text-destructive text-center">
            {fetchError}
          </div>
        )}

        {/* No-query empty state — suppressed in 'skills' scope where the
            catalog is the empty-query view (Plan 91-05). */}
        {!isMoveMode && !isLoading && !hasQuery && scope !== 'skills' && (
          <div className="py-12 text-center">
            <div className="text-[13px] font-medium text-[var(--text-secondary)]">
              Search everything
            </div>
            <div className="text-[13px] font-medium text-[var(--text-muted)] mt-1">
              Try{' '}
              <kbd className="font-mono text-[10px] bg-[var(--surface-input)] rounded-md px-1.5 py-0.5">
                #tasks
              </kbd>
              ,{' '}
              <kbd className="font-mono text-[10px] bg-[var(--surface-input)] rounded-md px-1.5 py-0.5">
                @people
              </kbd>
              ,{' '}
              <kbd className="font-mono text-[10px] bg-[var(--surface-input)] rounded-md px-1.5 py-0.5">
                /pages
              </kbd>
              , or{' '}
              <kbd className="font-mono text-[10px] bg-[var(--surface-input)] rounded-md px-1.5 py-0.5">
                &gt; commands
              </kbd>
              .
            </div>
          </div>
        )}

        {/* Topics group */}
        {!isMoveMode && !isLoading && hasQuery && showTopics && results.notes.length > 0 && (
          <CommandGroup heading="TOPICS" className={GROUP_HEADING_CLS}>
            {results.notes.map((note) => (
              <CommandItem
                key={note.id}
                value={`note-${note.id}-${note.title}`}
                onSelect={() => handleSelectNote(note.id)}
              >
                <NoteResultItem note={note} />
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {/* Tasks group */}
        {!isMoveMode && !isLoading && hasQuery && showTasks && results.issues.length > 0 && (
          <CommandGroup heading="TASKS" className={GROUP_HEADING_CLS}>
            {results.issues.map((issue) => (
              <CommandItem
                key={issue.id}
                value={`issue-${issue.id}-${issue.identifier}-${issue.name ?? issue.title}`}
                onSelect={() => handleSelectIssue(issue.id, issue.identifier)}
              >
                <IssueResultItem issue={issue} />
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {/* Chats group — empty-state placeholder; data source lands in 91.
            Rendered OUTSIDE cmdk's CommandGroup because cmdk requires
            CommandItem children; using plain markup keeps the visual
            tab parity without breaking cmdk's filter index. */}
        {!isMoveMode && !isLoading && hasQuery && showChats && (
          <div data-palette-group="chats" className="px-2 py-1">
            <div className="px-2 py-1.5 font-mono text-[10px] font-semibold tracking-[0.04em] uppercase text-[var(--text-muted)]">
              CHATS
            </div>
            <div className="px-2 py-3 text-[13px] text-[var(--text-muted)] flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              <span>Chat search arrives in Phase 91.</span>
            </div>
          </div>
        )}

        {/* Skills group — Phase 91 Plan 05.
            Renders when scope is 'all' (with query) or 'skills' (always).
            Each row navigates to the detail page on select; ⌘K palette closes
            via handleOpenChange(false). Hidden in 'all' scope when filter
            yields zero matches (UI-SPEC: never render empty groups). */}
        {!isMoveMode && !isLoading && showSkills && hasSkillResults && (scope === 'skills' || hasQuery) && (
          <CommandGroup heading="SKILLS" className={GROUP_HEADING_CLS}>
            {filteredSkills.map((skill) => (
              <CommandItem
                key={skill.slug}
                value={`skill-${skill.slug}-${skill.name}-${skill.description}`}
                onSelect={() => {
                  if (!workspaceSlug) return;
                  router.push(`/${workspaceSlug}/skills/${skill.slug}`);
                  handleOpenChange(false);
                }}
              >
                <SkillResultItem skill={skill} />
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {/* Skills empty state — only when user is explicitly in 'skills' scope. */}
        {!isMoveMode && !isLoading && scope === 'skills' && !hasSkillResults && (
          <div data-palette-group="skills" className="px-2 py-1">
            <div className="px-2 py-1.5 font-mono text-[10px] font-semibold tracking-[0.04em] uppercase text-[var(--text-muted)]">
              SKILLS
            </div>
            <div className="px-2 py-3 text-[13px] text-[var(--text-muted)] flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              <span>No skills available.</span>
            </div>
          </div>
        )}

        {/* Specs group — empty-state placeholder until specs API wired */}
        {!isMoveMode && !isLoading && hasQuery && showSpecs && (
          <div data-palette-group="specs" className="px-2 py-1">
            <div className="px-2 py-1.5 font-mono text-[10px] font-semibold tracking-[0.04em] uppercase text-[var(--text-muted)]">
              SPECS
            </div>
            <div className="px-2 py-3 text-[13px] text-[var(--text-muted)] flex items-center gap-2">
              <FileText className="h-4 w-4" />
              <span>Spec search not wired yet.</span>
            </div>
          </div>
        )}

        {/* People group — empty-state placeholder until members API wired */}
        {!isMoveMode && !isLoading && hasQuery && showPeople && (
          <div data-palette-group="people" className="px-2 py-1">
            <div className="px-2 py-1.5 font-mono text-[10px] font-semibold tracking-[0.04em] uppercase text-[var(--text-muted)]">
              PEOPLE
            </div>
            <div className="px-2 py-3 text-[13px] text-[var(--text-muted)] flex items-center gap-2">
              <Users className="h-4 w-4" />
              <span>People search not wired yet.</span>
            </div>
          </div>
        )}

        {/* AI fallback — only when query has zero matches.
            UI-SPEC Copywriting Contract: no "No results" heading above.
            Wrapped in CommandGroup with an explicit heading prop to keep
            cmdk happy (empty-string heading renders nothing visible). */}
        {!isMoveMode && !isLoading && !fetchError && hasQuery && !hasResults && (
          <CommandGroup heading="" className={GROUP_HEADING_CLS}>
            <CommandItem
              value={`ai-fallback-${query}`}
              onSelect={() => {
                const target = `/chat?prompt=${encodeURIComponent(consumePrefix(query))}`;
                router.push(target);
                handleOpenChange(false);
              }}
              className="bg-[var(--surface-snow)]"
            >
              <Sparkles className="h-[15px] w-[15px] text-[var(--ai-partner)]" />
              <span className="flex-1 text-[13px] text-[var(--text-heading)]">
                Ask AI: &ldquo;
                <span className="font-medium">{consumePrefix(query)}</span>
                &rdquo;
              </span>
              <kbd className="font-mono text-[10px] text-[var(--text-muted)]">⌘↵</kbd>
            </CommandItem>
          </CommandGroup>
        )}
      </CommandList>

      {/* ── Footer legend ── (Plan 93-05: 'open' → 'move' when in move mode) */}
      <div className="flex items-center gap-3 px-5 py-3 border-t border-[var(--border-card)] font-mono text-[10px] text-[var(--text-muted)]">
        <span>↑↓ navigate</span>
        <span>·</span>
        <span>{isMoveMode ? '↵ move' : '↵ open'}</span>
        {!isMoveMode && (
          <>
            <span>·</span>
            <span>⌘↵ open in split</span>
          </>
        )}
        <span>·</span>
        <span>{isMoveMode ? 'esc cancel' : 'esc close'}</span>
      </div>
    </CommandDialog>
  );
});
