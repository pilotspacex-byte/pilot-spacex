/**
 * mime-type-router.ts
 *
 * Pure utility for determining which renderer component to use for a given file.
 *
 * ROUTING RULES:
 * - HTML files (text/html or .html/.htm extension) route to 'html-preview' renderer.
 *   Preview uses a sandboxed iframe with DOMPurify sanitization; source mode shows
 *   syntax-highlighted code. No JavaScript execution is permitted in preview mode.
 * - CSV files route to 'csv' (dedicated table renderer with papaparse).
 * - All other non-text types fall through to 'download' fallback.
 *
 * This module has zero React dependencies — it is a pure function module
 * safe to import in any context (tests, server components, hooks, etc.).
 */

export type RendererType =
  | 'image'
  | 'markdown'
  | 'text'
  | 'json'
  | 'code'
  | 'csv'
  | 'download'
  | 'html-preview';

/**
 * Extension to lowlight language name mapping.
 * Mirrors SUPPORTED_LANGUAGES in CodeBlockExtension.ts — keep in sync.
 */
const EXT_TO_LANG: Record<string, string> = {
  py: 'python',
  js: 'javascript',
  ts: 'typescript',
  tsx: 'typescript',
  jsx: 'javascript',
  rb: 'ruby',
  go: 'go',
  rs: 'rust',
  java: 'java',
  cs: 'csharp',
  php: 'php',
  swift: 'swift',
  kt: 'kotlin',
  html: 'html',
  css: 'css',
  scss: 'scss',
  json: 'json',
  yaml: 'yaml',
  yml: 'yaml',
  md: 'markdown',
  sh: 'bash',
  bash: 'bash',
  sql: 'sql',
  graphql: 'graphql',
  gql: 'graphql',
  c: 'c',
  cpp: 'cpp',
  h: 'c',
  hpp: 'cpp',
  dockerfile: 'dockerfile',
};

/**
 * File extensions that render as syntax-highlighted code (not plain text).
 * HTML/HTM are NOT here — they route to 'html-preview' renderer instead.
 */
const CODE_EXTENSIONS = new Set([
  'js',
  'ts',
  'jsx',
  'tsx',
  'py',
  'rb',
  'go',
  'rs',
  'java',
  'c',
  'cpp',
  'h',
  'hpp',
  'cs',
  'php',
  'swift',
  'kt',
  'sh',
  'bash',
  'yaml',
  'yml',
  'toml',
  'sql',
  'graphql',
  'gql',
  'dockerfile',
  'css',
  'scss',
]);

/**
 * Extract the lowercased file extension from a filename.
 * Returns empty string if no extension is found.
 */
function getExtension(filename: string): string {
  const parts = filename.split('.');
  if (parts.length < 2) return '';
  const last = parts[parts.length - 1];
  return last !== undefined ? last.toLowerCase() : '';
}

/**
 * Maps a filename's extension to a lowlight language identifier.
 * Returns 'plaintext' for unknown extensions.
 *
 * @example
 * getLanguageForFile('main.py') → 'python'
 * getLanguageForFile('app.tsx') → 'typescript'
 * getLanguageForFile('unknown.xyz') → 'plaintext'
 */
export function getLanguageForFile(filename: string): string {
  const ext = getExtension(filename);
  return EXT_TO_LANG[ext] ?? 'plaintext';
}

/**
 * Resolve to 'code' or 'text' based on file extension.
 * Code extensions show syntax-highlighted source; others show plain text.
 */
function resolveCodeOrText(filename: string): RendererType {
  const ext = getExtension(filename);
  return CODE_EXTENSIONS.has(ext) ? 'code' : 'text';
}

/**
 * Determine which renderer component to use for a file.
 *
 * Priority order:
 * 1. Image MIME types → 'image'
 * 2. CSV (MIME or extension) → 'csv'
 * 3. Markdown (MIME or .md extension) → 'markdown'
 * 4. JSON (MIME or .json extension) → 'json'
 * 5. HTML (MIME or .html/.htm extension) → 'html-preview' (sandboxed iframe + source toggle)
 * 6. text/* MIME → resolve by extension (code or text)
 * 7. Everything else → 'download'
 *
 * @param mimeType - The file's MIME type (case-insensitive)
 * @param filename - The file's name (used for extension-based overrides)
 * @returns The renderer type to use
 */
export function resolveRenderer(mimeType: string, filename: string): RendererType {
  const lowerMime = mimeType.toLowerCase();
  const ext = getExtension(filename);

  // 1. Image types
  if (lowerMime.startsWith('image/')) return 'image';

  // 2. CSV — check both MIME and extension (some servers send text/plain for CSV)
  if (lowerMime === 'text/csv' || lowerMime === 'application/csv' || ext === 'csv') return 'csv';

  // 3. Markdown — filename extension wins over generic text/plain
  if (lowerMime === 'text/markdown' || ext === 'md') return 'markdown';

  // 4. JSON — extension wins for ambiguous text/* MIME
  if (lowerMime === 'application/json' || ext === 'json') return 'json';

  // 5. HTML — route to html-preview renderer (sandboxed iframe + source toggle)
  //    DOMPurify sanitization + sandbox="allow-same-origin" prevents XSS.
  if (lowerMime === 'text/html' || ext === 'html' || ext === 'htm') return 'html-preview';

  // 6. text/* types — resolve to code or plain text by extension
  if (lowerMime.startsWith('text/')) return resolveCodeOrText(filename);

  // 7. application/octet-stream with code/text extension — servers often send
  //    octet-stream for .py, .go, .rs, .toml, .yaml, etc. Route by extension.
  if (lowerMime === 'application/octet-stream') {
    const resolved = resolveCodeOrText(filename);
    if (resolved === 'code') return 'code';
    // .txt files sent as octet-stream should render as text
    if (ext === 'txt') return 'text';
  }

  // 8. Everything else — download fallback (PDF, binary, video, audio, etc.)
  return 'download';
}
