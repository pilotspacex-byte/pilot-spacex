'use client';

/**
 * MermaidPreview - Renders mermaid diagram source as interactive SVG.
 *
 * FR-001: Render text-based diagram definitions as vector graphics.
 * FR-002: 10 diagram types (flowchart, sequence, Gantt, class, ER, state, C4, pie, mindmap, git graph).
 * FR-003: Interactive diagrams — click nodes for tooltips + "Link to Issue" action.
 * FR-004: Live preview alongside diagram source editor.
 * FR-005: Inline syntax validation with error messages.
 * FR-006: Preserve last valid render when syntax errors are introduced.
 * FR-012: Export as PNG (SVG -> Canvas -> PNG).
 * FR-052: Theme sync (light/dark).
 * SC-003: Render < 500ms for diagrams with < 100 nodes.
 *
 * Size Limits: Max 500 lines / 200 nodes. Exceeding shows "Diagram too complex" fallback.
 * Security: mermaid `securityLevel: 'strict'` + DOMPurify sanitization on SVG output.
 */
import { useState, useEffect, useRef, useCallback, useId } from 'react';
import DOMPurify from 'dompurify';
import { AlertTriangle, Code2, Download, Eye, Link2 } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { mermaidPreviewStyles } from './mermaid-preview-styles';

export interface MermaidPreviewProps {
  code: string;
  theme?: 'light' | 'dark';
  className?: string;
  /** Callback when user clicks "Link to Issue" on a diagram node (FR-003). */
  onLinkToIssue?: (nodeLabel: string) => void;
  /** Callback when view mode toggles between code/preview (used by CodeBlockExtension). */
  onViewModeChange?: (mode: 'preview' | 'code') => void;
}

/** Debounce delay for re-rendering on source edits (ms) */
const RENDER_DEBOUNCE_MS = 300;

/** Maximum lines of mermaid source before complexity fallback */
const MAX_SOURCE_LINES = 500;

/** Maximum SVG nodes before complexity fallback */
const MAX_SVG_NODES = 200;

/** Mermaid themes mapped from our theme names */
const THEME_MAP: Record<string, string> = {
  light: 'default',
  dark: 'dark',
};

/**
 * DOMPurify config for SVG: allow SVG + HTML elements (mermaid v11+ uses
 * foreignObject with HTML divs for text rendering in flowcharts).
 */
// Safety: foreignObject is required by Mermaid v11+ for HTML text rendering inside
// flowcharts/sequence diagrams. FORBID_TAGS blocks executable content; foreignObject
// only contains styled <div>/<span> text which DOMPurify sanitizes via USE_PROFILES.
const PURIFY_CONFIG = {
  USE_PROFILES: { svg: true, svgFilters: true, html: true },
  FORBID_TAGS: ['script', 'iframe', 'object', 'embed'],
  ADD_TAGS: ['foreignObject'],
  ADD_ATTR: [
    'dominant-baseline',
    'marker-end',
    'marker-start',
    'xmlns',
    'requiredExtensions',
    'style',
    'class',
    'transform',
    'data-id',
    'data-node',
  ],
  RETURN_TRUSTED_TYPE: false,
};

/** SVG element selectors that represent clickable diagram nodes */
const NODE_SELECTOR = [
  '.node',
  '.actor',
  '.task',
  '.entityBox',
  '.statediagram-state',
  '.mindmap-node',
  '.piearc',
  '.nodeLabel',
].join(',');

function formatMermaidError(err: unknown): string {
  if (err instanceof Error) {
    const msg = err.message || String(err);
    const firstLine = msg.split('\n')[0] ?? msg;
    return firstLine.replace(/^Error:\s*/, '').trim() || 'Syntax error in diagram';
  }
  return 'Syntax error in diagram';
}

function sanitizeSvg(svgHtml: string): string {
  return DOMPurify.sanitize(svgHtml, PURIFY_CONFIG) as string;
}

/**
 * Check if source exceeds complexity limits.
 * Returns a reason string if too complex, or null if within limits.
 */
function checkComplexityLimits(source: string): string | null {
  const lineCount = source.split('\n').length;
  if (lineCount > MAX_SOURCE_LINES) {
    return `Source exceeds ${MAX_SOURCE_LINES} lines (${lineCount} lines)`;
  }
  return null;
}

/**
 * Extract a human-readable label from a clicked SVG node element.
 */
function extractNodeLabel(target: Element): string | null {
  // Try text content within the node or its closest node group
  const nodeGroup = target.closest(NODE_SELECTOR);
  if (!nodeGroup) return null;

  const textEl = nodeGroup.querySelector('.nodeLabel, text, .label, span');
  const label = textEl?.textContent?.trim() ?? nodeGroup.textContent?.trim();
  return label || null;
}

/**
 * Export the SVG inside the container as a PNG file download.
 * Renders SVG onto a Canvas, then triggers a download.
 */
async function exportSvgAsPng(container: HTMLElement, filename = 'diagram.png'): Promise<void> {
  const svgEl = container.querySelector('svg');
  if (!svgEl) return;

  const svgData = new XMLSerializer().serializeToString(svgEl);
  const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(svgBlob);

  const img = new Image();
  img.crossOrigin = 'anonymous';

  await new Promise<void>((resolve, reject) => {
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const scale = 2; // 2x for retina
      canvas.width = img.naturalWidth * scale;
      canvas.height = img.naturalHeight * scale;

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Canvas context unavailable'));
        return;
      }

      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0);

      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error('PNG blob creation failed'));
          return;
        }

        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
        URL.revokeObjectURL(a.href);
        resolve();
      }, 'image/png');
    };
    img.onerror = () => reject(new Error('SVG image load failed'));
    img.src = url;
  });

  URL.revokeObjectURL(url);
}

export function MermaidPreview({
  code,
  theme = 'light',
  className,
  onLinkToIssue,
  onViewModeChange,
}: MermaidPreviewProps) {
  const uniqueId = useId();
  const renderIdRef = useRef(0);
  const svgContainerRef = useRef<HTMLDivElement>(null);

  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview');
  const [svgHtml, setSvgHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRendering, setIsRendering] = useState(false);
  const [complexityError, setComplexityError] = useState<string | null>(null);

  // FR-003: tooltip state for clicked node
  const [tooltip, setTooltip] = useState<{
    label: string;
    x: number;
    y: number;
  } | null>(null);

  // Cache last valid SVG so errors don't blank the diagram (FR-006)
  const lastValidSvgRef = useRef<string | null>(null);

  const mermaidTheme = THEME_MAP[theme] ?? 'default';

  const renderDiagram = useCallback(
    (diagramSource: string, mTheme: string, renderId: number) => {
      if (!diagramSource.trim()) {
        setSvgHtml(null);
        setError(null);
        setComplexityError(null);
        return;
      }

      // T014: Check source line limit before rendering
      const limitReason = checkComplexityLimits(diagramSource);
      if (limitReason) {
        setComplexityError(limitReason);
        setSvgHtml(null);
        setError(null);
        return;
      }
      setComplexityError(null);

      setIsRendering(true);

      import('mermaid')
        .then(({ default: mermaid }) => {
          mermaid.initialize({
            startOnLoad: false,
            theme: mTheme as 'default' | 'dark',
            securityLevel: 'strict',
            suppressErrorRendering: true,
          });

          const diagramId = `mermaid-${uniqueId.replace(/:/g, '')}-${renderId}`;
          return mermaid.render(diagramId, diagramSource);
        })
        .then(({ svg }) => {
          if (renderId === renderIdRef.current) {
            const sanitized = sanitizeSvg(svg);

            // Pre-render node count check (N-4: check before setSvgHtml)
            const parser = new DOMParser();
            const svgDoc = parser.parseFromString(sanitized, 'image/svg+xml');
            const nodeCount = svgDoc.querySelectorAll(NODE_SELECTOR).length;
            if (nodeCount > MAX_SVG_NODES) {
              setComplexityError(`Diagram has ${nodeCount} nodes (max ${MAX_SVG_NODES})`);
              setSvgHtml(null);
              return;
            }

            setSvgHtml(sanitized);
            lastValidSvgRef.current = sanitized;
            setError(null);
          }
        })
        .catch((err: unknown) => {
          if (renderId === renderIdRef.current) {
            setError(formatMermaidError(err));
          }
        })
        .finally(() => {
          if (renderId === renderIdRef.current) {
            setIsRendering(false);
          }
        });
    },
    [uniqueId]
  );

  // Debounced rendering on code or theme change
  useEffect(() => {
    renderIdRef.current += 1;
    const currentRenderId = renderIdRef.current;

    const timer = setTimeout(() => {
      renderDiagram(code, mermaidTheme, currentRenderId);
    }, RENDER_DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [code, mermaidTheme, renderDiagram]);

  // FR-003: SVG click handler for node tooltips
  const handleSvgClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const target = e.target as Element;
    const label = extractNodeLabel(target);

    if (label) {
      const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
      setTooltip({
        label,
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
    } else {
      setTooltip(null);
    }
  }, []);

  // Dismiss tooltip on outside click or escape
  useEffect(() => {
    if (!tooltip) return;

    const dismiss = () => setTooltip(null);
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') dismiss();
    };
    document.addEventListener('click', dismiss);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('click', dismiss);
      document.removeEventListener('keydown', handleKey);
    };
  }, [tooltip]);

  // FR-012: Export handler
  const handleExport = useCallback(() => {
    if (svgContainerRef.current) {
      exportSvgAsPng(svgContainerRef.current).catch((err: unknown) => {
        const message = err instanceof Error ? err.message : 'Unknown error';
        toast.error('Export failed', { description: message });
      });
    }
  }, []);

  const displaySvg = svgHtml ?? lastValidSvgRef.current;

  /** Toggle view mode and notify CodeBlockExtension to show/hide <pre>. */
  const handleSetViewMode = useCallback(
    (mode: 'preview' | 'code') => {
      setViewMode(mode);
      onViewModeChange?.(mode);
    },
    [onViewModeChange]
  );

  // T014: Complexity fallback
  if (complexityError) {
    return (
      <div className={cn(mermaidPreviewStyles.wrapper, className)} data-testid="mermaid-preview">
        <div
          className={cn(mermaidPreviewStyles.error, 'flex items-start gap-1.5')}
          role="alert"
          data-testid="mermaid-complexity-error"
        >
          <AlertTriangle className="mt-0.5 size-3 shrink-0" />
          <span>Diagram too complex — showing source only. {complexityError}.</span>
        </div>
      </div>
    );
  }

  // Code mode: compact toggle bar only (editable ProseMirror <pre> is above)
  if (viewMode === 'code') {
    return (
      <div
        className={cn(mermaidPreviewStyles.wrapper, 'py-1.5 px-2', className)}
        data-testid="mermaid-preview"
      >
        <div
          className="flex items-center"
          role="radiogroup"
          aria-label="Diagram view mode"
          data-testid="mermaid-view-toggle"
        >
          <button
            type="button"
            role="radio"
            aria-checked={false}
            aria-label="Preview diagram"
            className={cn(mermaidPreviewStyles.toggleButton)}
            onClick={() => handleSetViewMode('preview')}
            data-testid="mermaid-toggle-preview"
          >
            <Eye className="size-3" />
            Preview
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={true}
            aria-label="View source code"
            className={cn(
              mermaidPreviewStyles.toggleButton,
              mermaidPreviewStyles.toggleButtonActive
            )}
            onClick={() => handleSetViewMode('code')}
            data-testid="mermaid-toggle-code"
          >
            <Code2 className="size-3" />
            Code
          </button>
        </div>
      </div>
    );
  }

  // SVG output is sanitized by DOMPurify in sanitizeSvg() before setState
  const sanitizedSvgHtml = displaySvg;

  return (
    <div className={cn(mermaidPreviewStyles.wrapper, className)} data-testid="mermaid-preview">
      {sanitizedSvgHtml ? (
        <div className="relative">
          {/* View mode toggle */}
          <div
            className={mermaidPreviewStyles.toggleGroup}
            role="radiogroup"
            aria-label="Diagram view mode"
            data-testid="mermaid-view-toggle"
          >
            <button
              type="button"
              role="radio"
              aria-checked={true}
              aria-label="Preview diagram"
              className={cn(
                mermaidPreviewStyles.toggleButton,
                mermaidPreviewStyles.toggleButtonActive
              )}
              onClick={() => handleSetViewMode('preview')}
              data-testid="mermaid-toggle-preview"
            >
              <Eye className="size-3" />
              Preview
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={false}
              aria-label="View source code"
              className={cn(mermaidPreviewStyles.toggleButton)}
              onClick={() => handleSetViewMode('code')}
              data-testid="mermaid-toggle-code"
            >
              <Code2 className="size-3" />
              Code
            </button>
          </div>

          {/* FR-012: Export toolbar */}
          <div className={mermaidPreviewStyles.toolbar}>
            <button
              type="button"
              className={mermaidPreviewStyles.toolbarButton}
              onClick={handleExport}
              aria-label="Export diagram as PNG"
              data-testid="mermaid-export-button"
            >
              <Download className="size-3.5" />
            </button>
          </div>

          {/* SVG render area (FR-003) — sanitized via DOMPurify in sanitizeSvg() */}
          <div
            ref={svgContainerRef}
            className={cn(
              mermaidPreviewStyles.svg,
              isRendering && 'opacity-60 transition-opacity',
              '[&_text]:!font-[Geist,sans-serif] [&_.nodeLabel]:text-sm [&_.edgeLabel]:text-xs'
            )}
            aria-label="Diagram preview"
            role="img"
            data-testid="mermaid-svg-container"
            dangerouslySetInnerHTML={{ __html: sanitizedSvgHtml }}
            onClick={handleSvgClick}
          />

          {/* FR-003: Node tooltip */}
          {tooltip && (
            <div
              className="absolute z-20 rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-md"
              style={{ left: tooltip.x, top: tooltip.y - 40 }}
              data-testid="mermaid-node-tooltip"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-1 font-medium text-foreground">{tooltip.label}</div>
              {onLinkToIssue && (
                <button
                  type="button"
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                  onClick={() => {
                    onLinkToIssue(tooltip.label);
                    setTooltip(null);
                  }}
                  data-testid="mermaid-link-to-issue"
                >
                  <Link2 className="size-3" />
                  Link to Issue
                </button>
              )}
            </div>
          )}
        </div>
      ) : !error ? (
        <div className={mermaidPreviewStyles.loading}>
          <div className={mermaidPreviewStyles.loadingSkeleton}>
            <span className="flex h-full items-center justify-center text-xs text-muted-foreground">
              {isRendering ? 'Rendering diagram...' : 'Enter mermaid syntax to see preview'}
            </span>
          </div>
        </div>
      ) : null}

      {error && (
        <div
          className={cn(mermaidPreviewStyles.error, 'flex items-start gap-1.5')}
          role="alert"
          aria-live="polite"
          data-testid="mermaid-error"
        >
          <AlertTriangle className="mt-0.5 size-3 shrink-0" />
          <span className="break-words">{error}</span>
        </div>
      )}
    </div>
  );
}
