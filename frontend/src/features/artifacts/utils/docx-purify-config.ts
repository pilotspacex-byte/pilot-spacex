/**
 * docx-purify-config.ts
 *
 * Dedicated DOMPurify configuration for DOCX-to-HTML output (mammoth fallback).
 *
 * CRITICAL SECURITY NOTES:
 * - This config MUST NOT be reused from HtmlRenderer's PURIFY_CONFIG.
 *   HtmlRenderer forbids 'style' attributes — mammoth uses inline styles for
 *   bold, italic, font sizes, colors, and indentation. Reusing it would strip
 *   all DOCX formatting and produce unstyled plain text.
 * - mammoth.js performs NO sanitization of the source DOCX. A malicious DOCX
 *   can contain hyperlinks with `javascript:alert(1)` as the href. This config
 *   uses ALLOWED_URI_REGEXP to block javascript: and other dangerous URI schemes.
 * - Pin mammoth >= 1.11.0 to avoid CVE-2025-11849 (directory traversal via
 *   external r:link image references).
 *
 * Key differences from HtmlRenderer's PURIFY_CONFIG:
 * - ALLOWED_URI_REGEXP added → blocks javascript: hrefs (critical XSS vector)
 * - FORBID_TAGS does NOT include 'style' → docx-preview outputs <style> blocks
 * - FORBID_ATTR does NOT include 'style' → mammoth uses inline styles for formatting
 * - Event handler attributes explicitly forbidden via FORBID_ATTR
 */
/**
 * DOMPurify configuration for sanitizing mammoth.js DOCX-to-HTML output.
 *
 * Blocks:
 * - javascript: URI scheme in href/src/action attributes (primary XSS vector)
 * - data: URI scheme (prevents data URI XSS; base64-encoded script injection)
 * - Event handler attributes (onerror, onload, onclick, etc.)
 * - Dangerous executable tags (script, object, embed, form, etc.)
 *
 * Allows:
 * - https:, http:, mailto: URI schemes (safe for document links)
 * - style attributes (mammoth uses these for font sizes, colors, indentation)
 * - <style> tags (docx-preview uses these for DOCX formatting)
 *
 * Type: Record<string, unknown> to avoid depending on DOMPurify's internal Config type.
 * DOMPurify.sanitize() accepts this shape at runtime.
 */
export const DOCX_PURIFY_CONFIG: Record<string, unknown> = {
  USE_PROFILES: { html: true },

  /**
   * Block javascript: and data: URI schemes in href, src, action, and other
   * URI-accepting attributes. Only allows https:, http:, mailto:, and data:image/
   * for safe raster image types (NOT svg+xml which can contain scripts).
   * This is the primary defense against javascript: href XSS from crafted DOCX files.
   */
  ALLOWED_URI_REGEXP:
    /^(?:https?:|mailto:|data:image\/(?:png|jpe?g|gif|webp|bmp|tiff?|x-icon|vnd\.microsoft\.icon);)/i,

  /**
   * Forbidden tags — executable or metadata injection vectors.
   * NOTE: 'style' is intentionally NOT included here.
   * docx-preview outputs <style> blocks for DOCX formatting — forbidding them
   * would destroy the rendered appearance.
   */
  FORBID_TAGS: ['script', 'object', 'embed', 'link', 'base', 'meta', 'form'] as string[],

  /**
   * Forbidden attributes — event handler injection vectors.
   * NOTE: 'style' is intentionally NOT included here.
   * mammoth.js uses inline styles for font sizes, colors, and indentation.
   * Forbidding 'style' would strip all DOCX formatting.
   */
  FORBID_ATTR: [
    'onerror',
    'onload',
    'onclick',
    'onmouseover',
    'onmouseout',
    'onfocus',
    'onblur',
    'onchange',
    'onsubmit',
    'onkeydown',
    'onkeyup',
    'onkeypress',
    'oncontextmenu',
    'ondblclick',
    'ondrag',
    'ondrop',
    'formaction',
    'srcdoc',
  ] as string[],
};
