/**
 * Phase 87.1 Plan 04 — Task 3 telemetry.
 *
 * Verifies that opening the Peek drawer for an MD or HTML artifact emits a
 * single `artifact_preview_opened` analytics event with
 * `{format, artifactId}`. NOTE/ISSUE etc. must NOT emit.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';

const trackMock = vi.fn();
vi.mock('@/lib/analytics', () => ({
  trackEvent: (name: string, props: Record<string, unknown>) =>
    trackMock(name, props),
}));

// Stubs for the heavy dependencies so we can mount the drawer in isolation.
vi.mock('@/hooks/use-artifact-peek-state', () => ({
  useArtifactPeekState: vi.fn(),
}));
vi.mock('@/hooks/use-artifact-query', () => ({
  useArtifactQuery: () => ({ data: undefined, isLoading: false, error: null, refetch: vi.fn() }),
}));
vi.mock('@/hooks/useViewport', () => ({
  useViewport: () => ({ peekMode: 'side-drawer' }),
}));
vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'ws' }),
}));
vi.mock('@/components/artifacts/ArtifactRendererSwitch', () => ({
  ArtifactRendererSwitch: () => null,
}));
vi.mock('@/features/skills/components/SkillFilePreview', () => ({
  SkillFilePreview: () => null,
}));

import { useArtifactPeekState } from '@/hooks/use-artifact-peek-state';
import { ArtifactPeekDrawer } from '../ArtifactPeekDrawer';

const useArtifactPeekStateMock = vi.mocked(useArtifactPeekState);

function setPeekState(args: {
  isPeekOpen: boolean;
  peekId?: string | null;
  peekType?: 'MD' | 'HTML' | 'NOTE' | 'ISSUE' | null;
}) {
  useArtifactPeekStateMock.mockReturnValue({
    peekId: args.peekId ?? null,
    peekType: (args.peekType ?? null) as never,
    isPeekOpen: args.isPeekOpen,
    isSkillFilePeek: false,
    skillFile: null,
    closePeek: vi.fn(),
    openPeek: vi.fn(),
    escalate: vi.fn(),
  } as never);
}

describe('ArtifactPeekDrawer telemetry — artifact_preview_opened', () => {
  beforeEach(() => {
    trackMock.mockReset();
    useArtifactPeekStateMock.mockReset();
  });

  it('emits artifact_preview_opened with format=md when MD opens', () => {
    setPeekState({ isPeekOpen: true, peekId: 'abc', peekType: 'MD' });
    render(<ArtifactPeekDrawer />);
    expect(trackMock).toHaveBeenCalledTimes(1);
    expect(trackMock).toHaveBeenCalledWith(
      'artifact_preview_opened',
      expect.objectContaining({ format: 'md', artifactId: 'abc' }),
    );
  });

  it('emits artifact_preview_opened with format=html when HTML opens', () => {
    setPeekState({ isPeekOpen: true, peekId: 'h1', peekType: 'HTML' });
    render(<ArtifactPeekDrawer />);
    expect(trackMock).toHaveBeenCalledTimes(1);
    expect(trackMock).toHaveBeenCalledWith(
      'artifact_preview_opened',
      expect.objectContaining({ format: 'html', artifactId: 'h1' }),
    );
  });

  it('does NOT emit for NOTE artifacts', () => {
    setPeekState({ isPeekOpen: true, peekId: 'n1', peekType: 'NOTE' });
    render(<ArtifactPeekDrawer />);
    expect(trackMock).not.toHaveBeenCalled();
  });

  it('does NOT emit for ISSUE artifacts', () => {
    setPeekState({ isPeekOpen: true, peekId: 'i1', peekType: 'ISSUE' });
    render(<ArtifactPeekDrawer />);
    expect(trackMock).not.toHaveBeenCalled();
  });

  it('does NOT emit when drawer is closed', () => {
    setPeekState({ isPeekOpen: false, peekId: null, peekType: null });
    render(<ArtifactPeekDrawer />);
    expect(trackMock).not.toHaveBeenCalled();
  });
});
