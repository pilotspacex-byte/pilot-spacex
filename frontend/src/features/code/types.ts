/**
 * types.ts — Core type definitions for the Monaco IDE code editor.
 *
 * Provides FileTab, OpenFile, EditorMode, and utility functions for
 * mapping file extensions to Monaco language IDs and editor modes.
 */

// ─── Editor Mode ─────────────────────────────────────────────────────────────

export type EditorMode = 'code' | 'markdown' | 'json' | 'yaml' | 'config' | 'unknown';

// ─── File Types ───────────────────────────────────────────────────────────────

/**
 * A file tab in the editor, representing a file's metadata and current state.
 * `content` is null until the file has been loaded from storage.
 */
export interface FileTab {
  id: string;
  name: string;
  path: string;
  language: string;
  isDirty: boolean;
  content: string | null;
  lastAccessed: number; // Unix epoch ms — used for LRU eviction
}

/**
 * An open file with both current and original content for dirty-state comparison.
 */
export type OpenFile = FileTab & {
  originalContent: string | null;
};

// ─── Extension Mappings ────────────────────────────────────────────────────────

/**
 * Maps file extensions to Monaco language IDs.
 * These identifiers are used directly in Monaco's `language` prop.
 */
const EXT_TO_MONACO_LANGUAGE: Record<string, string> = {
  // TypeScript / JavaScript
  ts: 'typescript',
  tsx: 'typescript',
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  cjs: 'javascript',

  // Web
  html: 'html',
  htm: 'html',
  css: 'css',
  scss: 'scss',
  less: 'less',

  // Data / Config
  json: 'json',
  jsonc: 'json',
  yaml: 'yaml',
  yml: 'yaml',
  toml: 'ini',
  ini: 'ini',
  env: 'ini',

  // Systems languages
  py: 'python',
  rb: 'ruby',
  go: 'go',
  rs: 'rust',
  java: 'java',
  cs: 'csharp',
  cpp: 'cpp',
  c: 'c',
  h: 'c',
  hpp: 'cpp',
  swift: 'swift',
  kt: 'kotlin',
  php: 'php',

  // Shell / Scripts
  sh: 'shell',
  bash: 'shell',
  zsh: 'shell',
  fish: 'shell',
  ps1: 'powershell',

  // Database
  sql: 'sql',

  // Infrastructure
  dockerfile: 'dockerfile',
  tf: 'hcl',
  hcl: 'hcl',

  // Markup / Docs
  md: 'markdown',
  mdx: 'markdown',
  xml: 'xml',
  svg: 'xml',

  // Query / Graph
  graphql: 'graphql',
  gql: 'graphql',

  // Plain text
  txt: 'plaintext',
  log: 'plaintext',
};

/**
 * Maps file extensions to EditorMode values, controlling
 * how the IDE presents the file (preview toggles, folding behavior, etc).
 */
const EXT_TO_EDITOR_MODE: Record<string, EditorMode> = {
  md: 'markdown',
  mdx: 'markdown',
  json: 'json',
  jsonc: 'json',
  yaml: 'yaml',
  yml: 'yaml',
  toml: 'config',
  ini: 'config',
  env: 'config',
  tf: 'config',
  hcl: 'config',
  dockerfile: 'config',
};

// ─── Utility Functions ────────────────────────────────────────────────────────

/**
 * Extract the lowercased extension from a filename.
 * Handles extensionless filenames like "Dockerfile" by returning the lowercased basename.
 */
function getExtension(filename: string): string {
  const base = filename.split(/[\\/]/).pop() ?? '';
  const parts = base.split('.');
  if (parts.length < 2) return base.toLowerCase();
  const last = parts[parts.length - 1];
  return last !== undefined ? last.toLowerCase() : '';
}

/**
 * Get the EditorMode for a filename.
 * Defaults to 'code' for all recognized code extensions, 'unknown' for unrecognized types.
 *
 * @example
 * getEditorMode('README.md') // 'markdown'
 * getEditorMode('config.yaml') // 'yaml'
 * getEditorMode('main.ts') // 'code'
 * getEditorMode('unknown.xyz') // 'unknown'
 */
export function getEditorMode(filename: string): EditorMode {
  const ext = getExtension(filename);
  if (EXT_TO_EDITOR_MODE[ext]) return EXT_TO_EDITOR_MODE[ext]!;
  if (EXT_TO_MONACO_LANGUAGE[ext]) return 'code';
  return 'unknown';
}

/**
 * Get the Monaco language ID for a filename.
 * Returns 'plaintext' for unknown extensions.
 *
 * @example
 * getLanguageLabel('app.tsx') // 'typescript'
 * getLanguageLabel('server.py') // 'python'
 * getLanguageLabel('unknown.xyz') // 'plaintext'
 */
export function getLanguageLabel(filename: string): string {
  const ext = getExtension(filename);
  return EXT_TO_MONACO_LANGUAGE[ext] ?? 'plaintext';
}
