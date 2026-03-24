/**
 * PptxRenderer tests -- PPTX-RENDER
 *
 * Tests PptxViewJS integration, canvas rendering, ResizeObserver responsive sizing,
 * slide count callback, error fallback, and loading state.
 *
 * NOTE: Navigation (keyboard + buttons), fullscreen, and thumbnail strip integration
 * live in FilePreviewModal (controlled component pattern). Those are tested in
 * FilePreviewModal.test.tsx. PptxRenderer is a pure canvas renderer.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

// --- Mock pptxviewjs ---
const mockLoadFile = vi.fn().mockResolvedValue(undefined);
const mockRenderSlide = vi.fn().mockResolvedValue(undefined);
const mockGetSlideCount = vi.fn().mockReturnValue(5);
const mockDestroy = vi.fn();

vi.mock('pptxviewjs', () => ({
  PPTXViewer: vi.fn().mockImplementation(() => ({
    loadFile: mockLoadFile,
    renderSlide: mockRenderSlide,
    getSlideCount: mockGetSlideCount,
    destroy: mockDestroy,
  })),
}));

import { PptxRenderer } from '../renderers/PptxRenderer';

const dummyBuffer = new ArrayBuffer(8);

describe('PptxRenderer', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock ResizeObserver
    const mockObserve = vi.fn();
    const mockDisconnect = vi.fn();
    vi.stubGlobal(
      'ResizeObserver',
      vi.fn().mockImplementation((callback: ResizeObserverCallback) => {
        // Simulate an immediate resize entry with width 800
        setTimeout(() => {
          callback(
            [{ contentRect: { width: 800 } } as unknown as ResizeObserverEntry],
            {} as ResizeObserver
          );
        }, 0);
        return { observe: mockObserve, disconnect: mockDisconnect, unobserve: vi.fn() };
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders a canvas element with slide aria-label', async () => {
    render(
      <PptxRenderer
        content={dummyBuffer}
        currentSlide={0}
        onSlideCountKnown={vi.fn()}
        onNavigate={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByLabelText('Presentation slide 1')).toBeDefined();
    });
  });

  it('calls onSlideCountKnown after loading the PPTX file', async () => {
    const onSlideCountKnown = vi.fn();

    render(
      <PptxRenderer
        content={dummyBuffer}
        currentSlide={0}
        onSlideCountKnown={onSlideCountKnown}
        onNavigate={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(onSlideCountKnown).toHaveBeenCalledWith(5);
    });
  });

  it('renders the current slide via PPTXViewer.renderSlide', async () => {
    render(
      <PptxRenderer
        content={dummyBuffer}
        currentSlide={2}
        onSlideCountKnown={vi.fn()}
        onNavigate={vi.fn()}
      />
    );

    await waitFor(() => {
      // renderSlide is called with the initial slide index during load
      expect(mockRenderSlide).toHaveBeenCalledWith(2, expect.anything());
    });
  });

  it('displays error message when PPTXViewer.loadFile throws', async () => {
    mockLoadFile.mockRejectedValueOnce(new Error('Corrupt PPTX'));

    render(
      <PptxRenderer
        content={dummyBuffer}
        currentSlide={0}
        onSlideCountKnown={vi.fn()}
        onNavigate={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to load presentation/)).toBeDefined();
    });
  });

  it('shows loading spinner while PPTX is being parsed', () => {
    // Make loadFile hang (never resolves)
    mockLoadFile.mockReturnValue(new Promise(() => {}));

    render(
      <PptxRenderer
        content={dummyBuffer}
        currentSlide={0}
        onSlideCountKnown={vi.fn()}
        onNavigate={vi.fn()}
      />
    );

    expect(screen.getByLabelText('Loading presentation')).toBeDefined();
  });

  it('renders canvas with shadow-md ring styling for professional appearance', async () => {
    const { container } = render(
      <PptxRenderer
        content={dummyBuffer}
        currentSlide={0}
        onSlideCountKnown={vi.fn()}
        onNavigate={vi.fn()}
      />
    );

    await waitFor(() => {
      const canvasWrapper = container.querySelector('.shadow-md.ring-1');
      expect(canvasWrapper).not.toBeNull();
    });
  });

  it('destroys viewer instance on unmount', async () => {
    const { unmount } = render(
      <PptxRenderer
        content={dummyBuffer}
        currentSlide={0}
        onSlideCountKnown={vi.fn()}
        onNavigate={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(mockLoadFile).toHaveBeenCalled();
    });

    unmount();

    expect(mockDestroy).toHaveBeenCalled();
  });
});
