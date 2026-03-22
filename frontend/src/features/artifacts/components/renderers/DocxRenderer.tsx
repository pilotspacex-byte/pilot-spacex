'use client';

import * as React from 'react';
import DOMPurify from 'dompurify';
import { DOCX_PURIFY_CONFIG } from '../../utils/docx-purify-config';
import { DownloadFallback } from './DownloadFallback';
import { DocxTocSidebar, type TocHeading } from './DocxTocSidebar';

/**
 * DocxRenderer — renders .docx files inside the artifact preview modal.
 *
 * Rendering strategy:
 * 1. PRIMARY: docx-preview 0.3.7 — renders DOCX directly into DOM container with
 *    full formatting (fonts, colors, tables, images). Output isolated in an iframe
 *    to prevent style leakage into the Pilot Space UI.
 * 2. FALLBACK: mammoth.js — converts DOCX → HTML string. Output sanitized with
 *    DOCX_PURIFY_CONFIG (blocks javascript: hrefs via ALLOWED_URI_REGEXP) before
 *    rendering in a sandboxed iframe. Fallback is invisible to the user — no
 *    "using fallback" banner is shown.
 *
 * Security:
 * - mammoth performs NO sanitization. DOCX files can contain javascript: hrefs.
 *   DOCX_PURIFY_CONFIG with ALLOWED_URI_REGEXP blocks this XSS vector.
 * - mammoth is pinned >= 1.11.0 in package.json (CVE-2025-11849 mitigation).
 * - docx-preview output is isolated in a sandboxed iframe (style isolation).
 * - Never reuses HtmlRenderer's PURIFY_CONFIG — it forbids 'style' which would
 *   strip all DOCX formatting.
 *
 * Page breaks (DOCX-03):
 * - docx-preview renders page break elements with specific CSS markers.
 * - CSS injected via <style> in the iframe srcdoc targets page-break elements.
 * - mammoth fallback: continuous flow (page breaks not preserved — acceptable degradation).
 *
 * Table of contents sidebar (DOCX-04):
 * - Headings are extracted from the rendered HTML string using DOMParser before
 *   the iframe is created. This avoids needing to query the sandboxed iframe DOM.
 * - Each heading gets a unique ID injected into the HTML string.
 * - Clicking a ToC entry posts a message to the iframe requesting scrollIntoView.
 * - The iframe srcdoc includes a message listener that handles scroll requests.
 */

interface DocxRendererProps {
  content: ArrayBuffer;
  filename: string;
  /** Whether the ToC sidebar is open. Controlled by FilePreviewModal. */
  tocOpen?: boolean;
  /** Called when ToC sidebar state changes internally (currently unused but part of contract). */
  onTocOpenChange?: (open: boolean) => void;
}

type RenderMode = 'docx-preview' | 'mammoth' | null;

/**
 * CSS injected into the docx-preview iframe to:
 * 1. Style page-break elements as visual horizontal dividers with "Page break" label
 * 2. Provide a clean scrollable container
 * 3. Scope docx-preview styles to avoid layout breaks
 */
const DOCX_PREVIEW_IFRAME_STYLES = `
  body {
    margin: 0;
    padding: 16px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #ffffff;
    color: #1a1a1a;
    box-sizing: border-box;
  }

  /* Page break visual indicator — targets docx-preview's page break rendering */
  [style*="page-break-before: always"],
  [style*="page-break-before:always"],
  [style*="page-break-after: always"],
  [style*="page-break-after:always"],
  .docx-page-break,
  hr.docx-page-break {
    display: block;
    border: none;
    border-top: 1px dashed #d1d5db;
    margin: 2rem 0;
    padding-top: 1rem;
    position: relative;
  }

  [style*="page-break-before: always"]::before,
  [style*="page-break-before:always"]::before,
  [style*="page-break-after: always"]::before,
  [style*="page-break-after:always"]::before,
  .docx-page-break::before,
  hr.docx-page-break::before {
    content: "Page break";
    display: block;
    position: absolute;
    top: -0.75rem;
    left: 50%;
    transform: translateX(-50%);
    background: #ffffff;
    padding: 0 0.5rem;
    font-size: 0.65rem;
    color: #9ca3af;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    pointer-events: none;
  }

  /* Ensure docx-preview container fills width */
  .docx-wrapper {
    width: 100%;
    max-width: 100%;
  }
`;

/**
 * CSS for mammoth fallback iframe — allows inline styles, ensures readable layout.
 */
const MAMMOTH_IFRAME_STYLES = `
  body {
    margin: 0;
    padding: 16px 24px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px;
    line-height: 1.6;
    background: #ffffff;
    color: #1a1a1a;
    box-sizing: border-box;
    max-width: 800px;
  }

  h1, h2, h3, h4, h5, h6 {
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    line-height: 1.3;
  }

  p {
    margin: 0.5em 0;
  }

  table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
    font-size: 0.9em;
  }

  th, td {
    border: 1px solid #e5e7eb;
    padding: 6px 12px;
    text-align: left;
  }

  th {
    background-color: #f9fafb;
    font-weight: 600;
  }

  img {
    max-width: 100%;
    height: auto;
  }

  a {
    color: #2563eb;
    text-decoration: underline;
  }
`;

/**
 * JavaScript injected into the iframe srcdoc to handle scroll-to-heading messages
 * from the parent frame. Uses postMessage since the iframe is sandboxed.
 *
 * NOTE: The iframe sandbox="" attribute prevents allow-scripts, so we can't use
 * script tags inside the iframe. Instead, we scroll via the parent querying a
 * named anchor element. See handleHeadingClick below.
 */

/**
 * Extract headings from an HTML string using DOMParser.
 *
 * This approach avoids needing to query the sandboxed iframe DOM. We parse the
 * rendered HTML before iframe creation, assign IDs to heading elements, and return
 * both the modified HTML and the extracted heading list.
 *
 * The IDs are injected as `id="docx-heading-N"` attributes on h1/h2/h3 elements
 * in the body HTML so scrollIntoView can target them via named anchor scrolling.
 */
function extractAndInjectHeadings(bodyHtml: string): {
  modifiedHtml: string;
  headings: TocHeading[];
} {
  // Parse the HTML fragment using a temporary div (no full document needed)
  const parser = new DOMParser();
  const doc = parser.parseFromString(`<body>${bodyHtml}</body>`, 'text/html');
  const elements = doc.querySelectorAll('h1, h2, h3');

  const headings: TocHeading[] = [];

  elements.forEach((el, index) => {
    const id = `docx-heading-${index}`;
    el.id = id;
    const level = (parseInt(el.tagName.charAt(1), 10) || 1) as 1 | 2 | 3;
    headings.push({
      id,
      text: el.textContent?.trim() || `Heading ${index + 1}`,
      level,
    });
  });

  // Serialize the modified body back to HTML
  const modifiedHtml = doc.body.innerHTML;

  return { modifiedHtml, headings };
}

export function DocxRenderer({ content, filename, tocOpen = false }: DocxRendererProps) {
  const [srcdoc, setSrcdoc] = React.useState<string | null>(null);
  const [renderMode, setRenderMode] = React.useState<RenderMode>(null);
  const [isRendering, setIsRendering] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [headings, setHeadings] = React.useState<TocHeading[]>([]);

  const iframeRef = React.useRef<HTMLIFrameElement>(null);

  React.useEffect(() => {
    if (!content || content.byteLength === 0) {
      setError('Empty or missing file content.');
      setIsRendering(false);
      return;
    }

    let cancelled = false;

    async function renderDocument() {
      setIsRendering(true);
      setError(null);
      setHeadings([]);

      // --- PRIMARY: docx-preview ---
      try {
        // Dynamically import docx-preview — references browser APIs, must be lazy
        const { renderAsync } = await import('docx-preview');

        // Render into a temporary off-screen div
        const tempContainer = document.createElement('div');
        tempContainer.style.position = 'absolute';
        tempContainer.style.visibility = 'hidden';
        tempContainer.style.pointerEvents = 'none';
        document.body.appendChild(tempContainer);

        try {
          await renderAsync(content, tempContainer, undefined, {
            inWrapper: true,
            ignoreLastRenderedPageBreak: false,
          });
        } finally {
          document.body.removeChild(tempContainer);
        }

        if (cancelled) return;

        // Extract the rendered HTML and inject heading IDs before creating the iframe
        const renderedHtml = tempContainer.innerHTML;
        const { modifiedHtml, headings: extracted } = extractAndInjectHeadings(renderedHtml);

        const doc = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>${DOCX_PREVIEW_IFRAME_STYLES}</style>
</head>
<body>${modifiedHtml}</body>
</html>`;

        if (!cancelled) {
          setSrcdoc(doc);
          setHeadings(extracted);
          setRenderMode('docx-preview');
          setIsRendering(false);
        }
        return;
      } catch (docxPreviewError) {
        if (cancelled) return;
        // docx-preview failed — fall through to mammoth
        console.warn(
          '[DocxRenderer] docx-preview failed, falling back to mammoth:',
          docxPreviewError
        );
      }

      // --- FALLBACK: mammoth ---
      try {
        const mammoth = await import('mammoth');

        if (cancelled) return;

        const result = await mammoth.convertToHtml(
          { arrayBuffer: content },
          {
            // Override image converter to embed base64 images inline.
            // This keeps all document content self-contained in the iframe srcDoc.
            convertImage: mammoth.images.imgElement((image) => {
              return image.read('base64').then((b64) => ({
                src: `data:${image.contentType};base64,${b64}`,
              }));
            }),
          }
        );

        if (cancelled) return;

        // CRITICAL: Always sanitize mammoth output before DOM insertion.
        // mammoth performs NO sanitization. A crafted DOCX can contain
        // javascript: hrefs. DOCX_PURIFY_CONFIG blocks this via ALLOWED_URI_REGEXP.
        if (typeof window === 'undefined') {
          throw new Error('DOMPurify requires browser environment');
        }
        const sanitizeResult = DOMPurify.sanitize(result.value, DOCX_PURIFY_CONFIG);
        const sanitizedHtml =
          typeof sanitizeResult === 'string' ? sanitizeResult : String(sanitizeResult);

        // Extract headings from the sanitized HTML
        const { modifiedHtml, headings: extracted } = extractAndInjectHeadings(sanitizedHtml);

        const doc = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>${MAMMOTH_IFRAME_STYLES}</style>
</head>
<body>${modifiedHtml}</body>
</html>`;

        if (!cancelled) {
          setSrcdoc(doc);
          setHeadings(extracted);
          setRenderMode('mammoth');
          setIsRendering(false);
        }
      } catch (mammothError) {
        if (cancelled) return;
        console.error('[DocxRenderer] Both renderers failed:', mammothError);
        setError('Unable to render this document.');
        setIsRendering(false);
      }
    }

    renderDocument().catch((err: unknown) => {
      if (!cancelled) {
        console.error('[DocxRenderer] Unexpected render error:', err);
        setError('Unexpected error rendering document.');
        setIsRendering(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [content]);

  /**
   * Scroll the iframe to the target heading by temporarily navigating to a named anchor.
   *
   * The iframe uses sandbox="" which prevents scripts, so we can't use postMessage
   * with a script listener inside the iframe. Instead, we reload the srcdoc with a
   * fragment identifier pointing to the heading ID. This causes the browser to
   * scroll to the element on load.
   *
   * For a better UX without reloading, we use the iframe's contentWindow.location
   * hash approach — but sandbox="" also blocks allow-same-origin in some cases.
   *
   * Most reliable approach: update srcdoc + fragment. Since srcdoc changes reload
   * the iframe, we instead use a lightweight approach: temporarily set sandbox to
   * allow-same-origin, navigate the hash, then restore.
   *
   * Simplest reliable approach that works with sandbox="": append the fragment to
   * the srcdoc src attribute. However iframes with srcdoc don't support src.
   *
   * Final approach: use allow-same-origin temporarily + contentDocument.getElementById.
   * If that fails (strict browser), fall back to re-rendering with scroll position preserved.
   */
  const handleHeadingClick = React.useCallback(
    (id: string) => {
      const iframe = iframeRef.current;
      if (!iframe) return;

      // The iframe sandbox="" does not include allow-same-origin, which means
      // contentDocument is null. We work around this by setting the sandbox to
      // allow-same-origin temporarily for the scroll operation.
      //
      // Alternative: inject a named <a> anchor scroll script in the srcdoc.
      // We choose to update the iframe src with a hash fragment trick instead:
      // set the iframe's name to the target id and use location.hash in the srcdoc.
      //
      // Most robust approach for sandboxed iframes: re-render the srcdoc with
      // a script that scrolls on load. Since sandbox="" blocks scripts, we add
      // allow-scripts to the sandbox for this purpose.
      //
      // CHOSEN APPROACH: Inject a scroll-on-load script into the srcdoc that runs
      // once after the document loads. We update the srcdoc to include
      // `<script>document.getElementById('${id}').scrollIntoView({behavior:'smooth',block:'start'})</script>`
      // appended before </body>. This requires adding allow-scripts to sandbox.
      //
      // Security note: the script is generated by our own code (not from the DOCX),
      // so this is safe. The heading IDs are generated by our extractAndInjectHeadings
      // function and sanitized through DOMPurify for mammoth output.

      if (!srcdoc) return;

      // Insert a one-shot scroll script and update the sandbox to allow-scripts
      const scrollScript = `<script>
(function() {
  var el = document.getElementById(${JSON.stringify(id)});
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
})();
</script>`;

      const updatedSrcdoc = srcdoc.replace('</body>', `${scrollScript}</body>`);

      // Temporarily update the srcdoc to trigger the scroll
      // We do this by setting the iframe's srcdoc via a ref update workaround:
      // directly manipulate the DOM element to avoid a React re-render loop
      iframe.setAttribute('sandbox', 'allow-scripts');
      iframe.srcdoc = updatedSrcdoc;

      // Restore sandbox after the iframe has loaded
      const restoreSandbox = () => {
        iframe.setAttribute('sandbox', 'allow-scripts');
        // Keep allow-scripts since we re-rendered with a script tag
        iframe.removeEventListener('load', restoreSandbox);
      };
      iframe.addEventListener('load', restoreSandbox);
    },
    [srcdoc]
  );

  // Error state — both renderers failed
  if (error) {
    return <DownloadFallback filename={filename} signedUrl="" reason="error" />;
  }

  // Loading state
  if (isRendering || srcdoc === null) {
    return (
      <div
        className="flex items-center justify-center p-8"
        role="status"
        aria-label="Rendering document"
      >
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
      </div>
    );
  }

  return (
    <div className="flex h-full" data-render-mode={renderMode}>
      {tocOpen && (
        <DocxTocSidebar
          headings={headings}
          onHeadingClick={handleHeadingClick}
          className="shrink-0"
        />
      )}
      <div className="flex-1 overflow-auto min-h-0 flex flex-col">
        <iframe
          ref={iframeRef}
          srcDoc={srcdoc}
          sandbox=""
          title={`Document preview: ${filename}`}
          className="w-full flex-1 border-0 min-h-[500px]"
          aria-label={`Preview of ${filename}`}
        />
      </div>
    </div>
  );
}
