'use client';

import * as React from 'react';
import DOMPurify from 'dompurify';
import { CodeRenderer } from './CodeRenderer';

/**
 * Sandbox attributes for the HTML preview iframe.
 * Empty sandbox = maximum isolation. No allow-same-origin prevents XSS
 * escalation if DOMPurify is bypassed.
 */
const SANDBOX_ATTRS = '';

/**
 * DOMPurify config for HTML preview sanitization.
 * Forbids executable tags. Use html profile only (no SVG extras needed here).
 */
const PURIFY_CONFIG = {
  USE_PROFILES: { html: true },
  FORBID_TAGS: ['script', 'object', 'embed', 'style', 'link', 'base', 'meta'] as string[],
  FORBID_ATTR: ['style'] as string[],
};

interface HtmlRendererProps {
  content: string;
  filename: string;
}

/**
 * HtmlRenderer — sandboxed iframe preview + source code toggle.
 *
 * Defaults to 'source' mode (safe-by-default posture).
 * Preview mode renders HTML in a sandboxed iframe with DOMPurify sanitization.
 * No JavaScript execution is possible in preview mode (sandbox lacks allow-scripts).
 */
export function HtmlRenderer({ content, filename }: HtmlRendererProps) {
  const [viewMode, setViewMode] = React.useState<'preview' | 'source'>('preview');

  const sanitizedHtml = React.useMemo(() => {
    if (viewMode !== 'preview') return '';
    if (typeof window === 'undefined') return '';
    return DOMPurify.sanitize(content, PURIFY_CONFIG) as string;
  }, [content, viewMode]);

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div
        role="tablist"
        aria-label="HTML view mode"
        className="flex items-center gap-1 px-3 py-2 border-b border-border shrink-0"
      >
        <button
          type="button"
          role="tab"
          id="html-tab-preview"
          aria-selected={viewMode === 'preview'}
          aria-controls="html-panel-preview"
          tabIndex={viewMode === 'preview' ? 0 : -1}
          onClick={() => setViewMode('preview')}
          className={
            'px-3 py-1.5 text-xs rounded-md transition-colors ' +
            (viewMode === 'preview'
              ? 'bg-muted text-foreground font-medium'
              : 'text-muted-foreground hover:text-foreground')
          }
        >
          Preview
        </button>
        <button
          type="button"
          role="tab"
          id="html-tab-source"
          aria-selected={viewMode === 'source'}
          aria-controls="html-panel-source"
          tabIndex={viewMode === 'source' ? 0 : -1}
          onClick={() => setViewMode('source')}
          className={
            'px-3 py-1.5 text-xs rounded-md transition-colors ' +
            (viewMode === 'source'
              ? 'bg-muted text-foreground font-medium'
              : 'text-muted-foreground hover:text-foreground')
          }
        >
          Source
        </button>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-auto min-h-0">
        {viewMode === 'preview' ? (
          <div role="tabpanel" id="html-panel-preview" aria-labelledby="html-tab-preview">
            <iframe
              srcDoc={sanitizedHtml}
              sandbox={SANDBOX_ATTRS}
              title={`HTML preview: ${filename}`}
              className="w-full h-full border-0 min-h-[400px]"
            />
          </div>
        ) : (
          <div role="tabpanel" id="html-panel-source" aria-labelledby="html-tab-source">
            <CodeRenderer content={content} language="html" />
          </div>
        )}
      </div>
    </div>
  );
}
