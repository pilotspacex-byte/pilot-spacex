/**
 * Version History UI Tests — T-221
 * Unit tests for VersionStore, VersionTimeline, VersionDiffViewer,
 * VersionRestoreConfirm, and VersionPanel.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { runInAction } from 'mobx';

import { VersionStore } from '../../stores/VersionStore';
import { VersionTimeline } from '../VersionTimeline';
import { VersionDiffViewer } from '../VersionDiffViewer';
import { VersionRestoreConfirm } from '../VersionRestoreConfirm';
import { VersionPanel } from '../VersionPanel';
import { versionApi } from '../../services/versionApi';
import type {
  NoteVersionResponse,
  NoteVersionListResponse,
  DiffResponse,
  DigestResponse,
  RestoreResponse,
} from '../../services/versionApi';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('../../services/versionApi', () => ({
  versionApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    diff: vi.fn(),
    restore: vi.fn(),
    digest: vi.fn(),
    pin: vi.fn(),
    undoAI: vi.fn(),
  },
}));

// Mock SidebarPanel so VersionPanel renders children directly
vi.mock('@/components/editor/sidebar', () => ({
  SidebarPanel: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useSidebarPanel: () => ({
    isOpen: false,
    activePanel: null,
    width: 320,
    openSidebar: vi.fn(),
    closeSidebar: vi.fn(),
    setWidth: vi.fn(),
  }),
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeVersion(overrides: Partial<NoteVersionResponse> = {}): NoteVersionResponse {
  return {
    id: 'v1',
    noteId: 'note-1',
    workspaceId: 'ws-1',
    trigger: 'manual',
    label: null,
    pinned: false,
    digest: null,
    digestCachedAt: null,
    createdBy: 'user-1',
    versionNumber: 1,
    createdAt: new Date('2026-02-19T10:00:00Z').toISOString(),
    aiBeforeVersionId: null,
    ...overrides,
  };
}

function makeListResponse(versions: NoteVersionResponse[]): NoteVersionListResponse {
  return { versions, total: versions.length, noteId: 'note-1' };
}

function makeQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={makeQueryClient()}>{children}</QueryClientProvider>;
}

// ---------------------------------------------------------------------------
// VersionStore unit tests
// ---------------------------------------------------------------------------

describe('VersionStore', () => {
  let store: VersionStore;

  beforeEach(() => {
    store = new VersionStore();
  });

  it('initialises with correct defaults', () => {
    expect(store.isOpen).toBe(false);
    expect(store.view).toBe('timeline');
    expect(store.selectedVersionId).toBeNull();
    expect(store.diffVersionIds).toBeNull();
    expect(store.pendingRestoreVersionId).toBeNull();
    expect(store.isSaving).toBe(false);
    expect(store.isUndoingAI).toBe(false);
    expect(store.conflictVersionNumber).toBeNull();
  });

  it('open/close/toggle change isOpen', () => {
    store.open();
    expect(store.isOpen).toBe(true);
    store.close();
    expect(store.isOpen).toBe(false);
    store.toggle();
    expect(store.isOpen).toBe(true);
    store.toggle();
    expect(store.isOpen).toBe(false);
  });

  it('close resets all selection state', () => {
    store.open();
    store.selectVersion('v-abc');
    store.openDiff('v1', 'v2');
    store.close();
    expect(store.selectedVersionId).toBeNull();
    expect(store.diffVersionIds).toBeNull();
    expect(store.view).toBe('timeline');
  });

  it('selectVersion updates selectedVersionId', () => {
    store.selectVersion('v-xyz');
    expect(store.selectedVersionId).toBe('v-xyz');
  });

  it('openDiff sets diffVersionIds and switches to diff view', () => {
    store.openDiff('v1', 'v2');
    expect(store.diffVersionIds).toEqual(['v1', 'v2']);
    expect(store.view).toBe('diff');
  });

  it('closeDiff resets diff state and returns to timeline', () => {
    store.openDiff('v1', 'v2');
    store.closeDiff();
    expect(store.diffVersionIds).toBeNull();
    expect(store.view).toBe('timeline');
  });

  it('openRestore sets pendingRestoreVersionId and switches to restore view', () => {
    store.openRestore('v-restore');
    expect(store.pendingRestoreVersionId).toBe('v-restore');
    expect(store.view).toBe('restore');
  });

  it('cancelRestore clears conflict and returns to timeline', () => {
    store.openRestore('v-restore');
    store.setConflict(42);
    store.cancelRestore();
    expect(store.pendingRestoreVersionId).toBeNull();
    expect(store.conflictVersionNumber).toBeNull();
    expect(store.view).toBe('timeline');
  });

  it('setSaving updates isSaving via runInAction', () => {
    store.setSaving(true);
    expect(store.isSaving).toBe(true);
    store.setSaving(false);
    expect(store.isSaving).toBe(false);
  });

  it('setUndoingAI updates isUndoingAI', () => {
    store.setUndoingAI(true);
    expect(store.isUndoingAI).toBe(true);
  });

  it('setConflict updates conflictVersionNumber', () => {
    store.setConflict(99);
    expect(store.conflictVersionNumber).toBe(99);
  });

  it('reset clears all state', () => {
    store.open();
    store.selectVersion('v1');
    store.setSaving(true);
    store.setUndoingAI(true);
    store.reset();
    expect(store.isOpen).toBe(false);
    expect(store.selectedVersionId).toBeNull();
    expect(store.isSaving).toBe(false);
    expect(store.isUndoingAI).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// VersionTimeline component tests
// ---------------------------------------------------------------------------

describe('VersionTimeline', () => {
  let store: VersionStore;

  beforeEach(() => {
    store = new VersionStore();
    vi.clearAllMocks();
  });

  it('shows loading skeletons while fetching', () => {
    vi.mocked(versionApi.list).mockReturnValue(new Promise(() => {}));
    render(<VersionTimeline workspaceId="ws-1" noteId="note-1" store={store} />, { wrapper });
    // Skeleton elements should appear
    expect(
      document.querySelectorAll('.animate-pulse, [data-slot="skeleton"]').length
    ).toBeGreaterThan(0);
  });

  it('shows empty state when no versions', async () => {
    vi.mocked(versionApi.list).mockResolvedValue(makeListResponse([]));
    render(<VersionTimeline workspaceId="ws-1" noteId="note-1" store={store} />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText(/no versions yet/i)).toBeTruthy();
    });
  });

  it('renders version entries with trigger labels', async () => {
    const versions = [
      makeVersion({ id: 'v1', trigger: 'manual', versionNumber: 1 }),
      makeVersion({ id: 'v2', trigger: 'auto', versionNumber: 2 }),
      makeVersion({ id: 'v3', trigger: 'ai_before', versionNumber: 3 }),
      makeVersion({ id: 'v4', trigger: 'ai_after', versionNumber: 4 }),
    ];
    vi.mocked(versionApi.list).mockResolvedValue(makeListResponse(versions));
    render(<VersionTimeline workspaceId="ws-1" noteId="note-1" store={store} />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Manual save')).toBeTruthy();
      expect(screen.getByText('Auto-save')).toBeTruthy();
      expect(screen.getByText('Before AI edit')).toBeTruthy();
      expect(screen.getByText('After AI edit')).toBeTruthy();
    });
  });

  it('shows "Save Version" button', async () => {
    vi.mocked(versionApi.list).mockResolvedValue(makeListResponse([]));
    render(<VersionTimeline workspaceId="ws-1" noteId="note-1" store={store} />, { wrapper });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /save manual version snapshot/i })).toBeTruthy();
    });
  });

  it('shows "Undo AI Changes" button only when ai_after version exists', async () => {
    const onUndoAI = vi.fn();

    // Without ai_after versions — no button
    vi.mocked(versionApi.list).mockResolvedValue(
      makeListResponse([makeVersion({ trigger: 'manual' })])
    );
    const { rerender } = render(
      <VersionTimeline workspaceId="ws-1" noteId="note-1" store={store} onUndoAI={onUndoAI} />,
      { wrapper }
    );
    await waitFor(() => {
      expect(screen.queryByText(/undo ai changes/i)).toBeNull();
    });

    // With ai_after version — button appears
    vi.mocked(versionApi.list).mockResolvedValue(
      makeListResponse([makeVersion({ trigger: 'ai_after' })])
    );
    rerender(
      <QueryClientProvider client={makeQueryClient()}>
        <VersionTimeline workspaceId="ws-1" noteId="note-1" store={store} onUndoAI={onUndoAI} />
      </QueryClientProvider>
    );
    await waitFor(() => {
      expect(screen.getByText(/undo ai changes/i)).toBeTruthy();
    });
  });

  it('selecting an entry shows Compare and Restore action buttons', async () => {
    const v = makeVersion({ id: 'v1', versionNumber: 1 });
    vi.mocked(versionApi.list).mockResolvedValue(makeListResponse([v]));
    render(<VersionTimeline workspaceId="ws-1" noteId="note-1" store={store} />, { wrapper });
    await waitFor(() => screen.getByText('Manual save'));

    // Select the entry
    runInAction(() => {
      store.selectedVersionId = 'v1';
    });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /compare/i })).toBeTruthy();
      expect(screen.getByRole('button', { name: /restore/i })).toBeTruthy();
    });
  });

  it('pin button has aria-pressed reflecting pinned state', async () => {
    const v = makeVersion({ id: 'v1', pinned: true });
    vi.mocked(versionApi.list).mockResolvedValue(makeListResponse([v]));
    render(<VersionTimeline workspaceId="ws-1" noteId="note-1" store={store} />, { wrapper });
    await waitFor(() => {
      const pinBtn = screen.getByRole('button', { name: /unpin version/i });
      expect(pinBtn.getAttribute('aria-pressed')).toBe('true');
    });
  });

  it('shows error message when list fails', async () => {
    vi.mocked(versionApi.list).mockRejectedValue(new Error('Network error'));
    render(<VersionTimeline workspaceId="ws-1" noteId="note-1" store={store} />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText(/failed to load versions/i)).toBeTruthy();
    });
  });
});

// ---------------------------------------------------------------------------
// VersionDiffViewer component tests
// ---------------------------------------------------------------------------

describe('VersionDiffViewer', () => {
  let store: VersionStore;
  const v1 = makeVersion({ id: 'v1', versionNumber: 1, trigger: 'ai_before' });
  const v2 = makeVersion({ id: 'v2', versionNumber: 2, trigger: 'ai_after' });

  beforeEach(() => {
    store = new VersionStore();
    vi.clearAllMocks();
  });

  const diffResponse: DiffResponse = {
    version1Id: 'v1',
    version2Id: 'v2',
    blocks: [
      {
        blockId: 'b1',
        diffType: 'unchanged',
        oldContent: { type: 'paragraph', content: [{ type: 'text', text: 'Same text' }] },
        newContent: { type: 'paragraph', content: [{ type: 'text', text: 'Same text' }] },
      },
      {
        blockId: 'b2',
        diffType: 'added',
        oldContent: null,
        newContent: { type: 'paragraph', content: [{ type: 'text', text: 'New block' }] },
      },
      {
        blockId: 'b3',
        diffType: 'removed',
        oldContent: { type: 'paragraph', content: [{ type: 'text', text: 'Old block' }] },
        newContent: null,
      },
    ],
    addedCount: 1,
    removedCount: 1,
    modifiedCount: 0,
    hasChanges: true,
  };

  const digestResponse: DigestResponse = {
    versionId: 'v2',
    digest: 'Added one paragraph, removed one paragraph.',
    fromCache: false,
  };

  it('renders Back button', async () => {
    vi.mocked(versionApi.diff).mockResolvedValue(diffResponse);
    vi.mocked(versionApi.digest).mockResolvedValue(digestResponse);
    const onBack = vi.fn();
    render(
      <VersionDiffViewer
        workspaceId="ws-1"
        noteId="note-1"
        store={store}
        v1={v1}
        v2={v2}
        onRestore={vi.fn()}
        onBack={onBack}
      />,
      { wrapper }
    );
    const backBtn = screen.getByRole('button', { name: /back to timeline/i });
    fireEvent.click(backBtn);
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('shows add/remove stats after diff loads', async () => {
    vi.mocked(versionApi.diff).mockResolvedValue(diffResponse);
    vi.mocked(versionApi.digest).mockResolvedValue(digestResponse);
    render(
      <VersionDiffViewer
        workspaceId="ws-1"
        noteId="note-1"
        store={store}
        v1={v1}
        v2={v2}
        onRestore={vi.fn()}
        onBack={vi.fn()}
      />,
      { wrapper }
    );
    await waitFor(() => {
      expect(screen.getByText(/\+1 added/i)).toBeTruthy();
      expect(screen.getByText(/−1 removed/i)).toBeTruthy();
    });
  });

  it('shows AI digest when loaded', async () => {
    vi.mocked(versionApi.diff).mockResolvedValue(diffResponse);
    vi.mocked(versionApi.digest).mockResolvedValue(digestResponse);
    render(
      <VersionDiffViewer
        workspaceId="ws-1"
        noteId="note-1"
        store={store}
        v1={v1}
        v2={v2}
        onRestore={vi.fn()}
        onBack={vi.fn()}
      />,
      { wrapper }
    );
    await waitFor(() => {
      expect(screen.getByText('Added one paragraph, removed one paragraph.')).toBeTruthy();
    });
  });

  it('shows no-differences message when diff is empty', async () => {
    vi.mocked(versionApi.diff).mockResolvedValue({
      ...diffResponse,
      blocks: [],
      hasChanges: false,
      addedCount: 0,
      removedCount: 0,
    });
    vi.mocked(versionApi.digest).mockResolvedValue(digestResponse);
    render(
      <VersionDiffViewer
        workspaceId="ws-1"
        noteId="note-1"
        store={store}
        v1={v1}
        v2={v2}
        onRestore={vi.fn()}
        onBack={vi.fn()}
      />,
      { wrapper }
    );
    await waitFor(() => {
      expect(screen.getByText(/no differences found/i)).toBeTruthy();
    });
  });

  it('calls onRestore when Restore v1 is clicked', async () => {
    vi.mocked(versionApi.diff).mockResolvedValue(diffResponse);
    vi.mocked(versionApi.digest).mockResolvedValue(digestResponse);
    const onRestore = vi.fn();
    render(
      <VersionDiffViewer
        workspaceId="ws-1"
        noteId="note-1"
        store={store}
        v1={v1}
        v2={v2}
        onRestore={onRestore}
        onBack={vi.fn()}
      />,
      { wrapper }
    );
    await waitFor(() => screen.getByText(/restore v1/i));
    fireEvent.click(screen.getByText(/restore v1/i));
    expect(onRestore).toHaveBeenCalledWith('v1');
  });
});

// ---------------------------------------------------------------------------
// VersionRestoreConfirm component tests
// ---------------------------------------------------------------------------

describe('VersionRestoreConfirm', () => {
  let store: VersionStore;
  const version = makeVersion({ id: 'v1', versionNumber: 1, label: 'Sprint 12 snapshot' });

  beforeEach(() => {
    store = new VersionStore();
    vi.clearAllMocks();
  });

  it('renders version info and CRDT warning', () => {
    render(
      <VersionRestoreConfirm
        workspaceId="ws-1"
        noteId="note-1"
        store={store}
        version={version}
        currentVersionNumber={5}
        onRestored={vi.fn()}
        onCancel={vi.fn()}
      />,
      { wrapper }
    );
    expect(screen.getByText(/restore version/i)).toBeTruthy();
    expect(screen.getByText(/sprint 12 snapshot/i)).toBeTruthy();
    expect(screen.getByText(/creates a new version/i)).toBeTruthy();
  });

  it('calls onCancel when Cancel is clicked', () => {
    const onCancel = vi.fn();
    render(
      <VersionRestoreConfirm
        workspaceId="ws-1"
        noteId="note-1"
        store={store}
        version={version}
        currentVersionNumber={5}
        onRestored={vi.fn()}
        onCancel={onCancel}
      />,
      { wrapper }
    );
    const cancelBtns = screen.getAllByRole('button', { name: /cancel/i });
    expect(cancelBtns.length).toBeGreaterThan(0);
    fireEvent.click(cancelBtns[0]!);
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('calls versionApi.restore and onRestored on success', async () => {
    const restoreResult: RestoreResponse = {
      newVersion: makeVersion({ id: 'v-new', versionNumber: 6 }),
      restoredFromVersionId: 'v1',
    };
    vi.mocked(versionApi.restore).mockResolvedValue(restoreResult);
    const onRestored = vi.fn();
    render(
      <VersionRestoreConfirm
        workspaceId="ws-1"
        noteId="note-1"
        store={store}
        version={version}
        currentVersionNumber={5}
        onRestored={onRestored}
        onCancel={vi.fn()}
      />,
      { wrapper }
    );
    fireEvent.click(screen.getByRole('button', { name: /restore note to version/i }));
    await waitFor(() => {
      expect(versionApi.restore).toHaveBeenCalledWith('ws-1', 'note-1', 'v1', 5);
      expect(onRestored).toHaveBeenCalledWith('v-new');
    });
  });

  it('shows conflict state when restore returns 409', async () => {
    const conflictError = Object.assign(new Error('Conflict'), {
      status: 409,
      body: { detail: { currentVersionNumber: 7 } },
    });
    vi.mocked(versionApi.restore).mockRejectedValue(conflictError);
    render(
      <VersionRestoreConfirm
        workspaceId="ws-1"
        noteId="note-1"
        store={store}
        version={version}
        currentVersionNumber={5}
        onRestored={vi.fn()}
        onCancel={vi.fn()}
      />,
      { wrapper }
    );
    fireEvent.click(screen.getByRole('button', { name: /restore note to version/i }));
    await waitFor(() => {
      expect(screen.getByText(/version conflict detected/i)).toBeTruthy();
      expect(screen.getByText(/now at v7/i)).toBeTruthy();
    });
  });

  it('shows generic error when restore fails with non-409', async () => {
    vi.mocked(versionApi.restore).mockRejectedValue(
      Object.assign(new Error('Server error'), { status: 500 })
    );
    render(
      <VersionRestoreConfirm
        workspaceId="ws-1"
        noteId="note-1"
        store={store}
        version={version}
        currentVersionNumber={5}
        onRestored={vi.fn()}
        onCancel={vi.fn()}
      />,
      { wrapper }
    );
    fireEvent.click(screen.getByRole('button', { name: /restore note to version/i }));
    await waitFor(() => {
      expect(screen.getByText(/restore failed/i)).toBeTruthy();
    });
  });
});

// ---------------------------------------------------------------------------
// VersionPanel routing tests
// ---------------------------------------------------------------------------

describe('VersionPanel', () => {
  let store: VersionStore;
  const v1 = makeVersion({ id: 'v1', versionNumber: 1 });
  const v2 = makeVersion({ id: 'v2', versionNumber: 2 });

  beforeEach(() => {
    store = new VersionStore();
    vi.clearAllMocks();
  });

  it('renders timeline view by default', async () => {
    vi.mocked(versionApi.list).mockResolvedValue(makeListResponse([v1]));
    render(<VersionPanel workspaceId="ws-1" noteId="note-1" store={store} />, { wrapper });
    // "Save Version" button is specific to timeline view
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /save manual version snapshot/i })).toBeTruthy();
    });
  });

  it('renders diff view when store.view === "diff"', async () => {
    vi.mocked(versionApi.diff).mockResolvedValue({
      version1Id: 'v1',
      version2Id: 'v2',
      blocks: [],
      addedCount: 0,
      removedCount: 0,
      modifiedCount: 0,
      hasChanges: false,
    });
    vi.mocked(versionApi.digest).mockResolvedValue({
      versionId: 'v2',
      digest: 'No changes.',
      fromCache: false,
    });
    vi.mocked(versionApi.get).mockResolvedValueOnce(v1).mockResolvedValueOnce(v2);

    runInAction(() => {
      store.openDiff('v1', 'v2');
    });

    render(<VersionPanel workspaceId="ws-1" noteId="note-1" store={store} />, { wrapper });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /back to timeline/i })).toBeTruthy();
    });
  });

  it('renders restore view when store.view === "restore"', async () => {
    vi.mocked(versionApi.get).mockResolvedValue(v1);
    runInAction(() => {
      store.openRestore('v1');
    });
    render(
      <VersionPanel workspaceId="ws-1" noteId="note-1" store={store} currentVersionNumber={3} />,
      { wrapper }
    );
    await waitFor(() => {
      expect(screen.getByText(/restore version/i)).toBeTruthy();
    });
  });
});
