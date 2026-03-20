/**
 * Tauri platform detection and typed IPC wrappers.
 *
 * ALL @tauri-apps/api imports MUST be lazy (dynamic import) or gated
 * by isTauri() to prevent SSG build errors. NEVER import @tauri-apps/api
 * at the top level of any file.
 *
 * Components and stores must NEVER call invoke() directly — always use
 * the typed wrappers exported from this module.
 */

// --- Types matching Rust structs ---

export interface ProjectEntry {
  name: string;
  path: string;
  remote_url: string;
  linked: boolean;
  added_at: string;
}

export interface GitProgress {
  pct: number;
  message: string;
}

export interface GitCredentialInfo {
  username: string;
  has_pat: boolean;
}

/**
 * Detect if running inside a Tauri desktop shell.
 * Returns false during SSG/SSR (no window) and in browser context.
 */
export function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

/**
 * Read the cached Supabase access token from Tauri Store (pilot-auth.json).
 * Returns null if not in Tauri mode or no token is stored.
 */
export async function getAuthToken(): Promise<string | null> {
  if (!isTauri()) return null;
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<string | null>('get_auth_token');
}

/**
 * Write auth tokens to both OS keychain and Tauri Store via Rust IPC command.
 * Keychain is the secure source of truth for Rust-side access.
 * Tauri Store is kept in sync as a fallback for WebView reads.
 */
export async function setAuthToken(
  accessToken: string | null,
  refreshToken: string | null
): Promise<void> {
  if (!isTauri()) return;
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('set_auth_token', {
    accessToken,
    refreshToken,
  });
}

/**
 * Migrate tokens from Tauri Store to OS keychain (one-time, on app startup).
 *
 * Handles the upgrade path from Plan 31-01 (Store-only) to Plan 31-02
 * (keychain as primary secure storage). Safe to call on every startup —
 * it is a no-op if tokens are already in the keychain.
 *
 * Returns true if migration was performed, false if already migrated or
 * no tokens exist.
 */
export async function migrateTokensToKeychain(): Promise<boolean> {
  if (!isTauri()) return false;
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<boolean>('migrate_tokens_to_keychain');
}

// --- Workspace commands ---

/**
 * Get the configured projects base directory.
 * Returns empty string if not in Tauri mode.
 */
export async function getProjectsDir(): Promise<string> {
  if (!isTauri()) return '';
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<string>('get_projects_dir');
}

/**
 * Set the base directory where projects are stored.
 */
export async function setProjectsDir(path: string): Promise<void> {
  if (!isTauri()) return;
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('set_projects_dir', { path });
}

/**
 * Open a native folder picker dialog. Returns the selected path or null.
 */
export async function openFolderDialog(): Promise<string | null> {
  if (!isTauri()) return null;
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<string | null>('open_folder_dialog');
}

/**
 * Link an existing local git repository by path.
 * Validates that the path contains a .git directory.
 */
export async function linkRepo(path: string): Promise<ProjectEntry> {
  if (!isTauri()) throw new Error('Not in Tauri mode');
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<ProjectEntry>('link_repo', { path });
}

/**
 * List all managed projects from workspace-config.json.
 * Returns empty array if not in Tauri mode.
 */
export async function listProjects(): Promise<ProjectEntry[]> {
  if (!isTauri()) return [];
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<ProjectEntry[]>('list_projects');
}

// --- Git commands ---

/**
 * Clone a repository from a URL into a target directory.
 * Uses Tauri v2 Channel API to stream progress updates.
 * @param url - Repository URL (HTTPS or SSH)
 * @param targetDir - Absolute path for the clone destination
 * @param onProgress - Callback invoked on each progress update
 */
export async function gitClone(
  url: string,
  targetDir: string,
  onProgress: (progress: GitProgress) => void
): Promise<void> {
  if (!isTauri()) throw new Error('Not in Tauri mode');
  const { invoke, Channel } = await import('@tauri-apps/api/core');
  const channel = new Channel<GitProgress>();
  channel.onmessage = onProgress;
  await invoke('git_clone', { url, targetDir, onProgress: channel });
}

/**
 * Cancel an in-progress clone operation.
 * Sets the AtomicBool cancel flag — git2 aborts on next progress tick.
 */
export async function cancelClone(): Promise<void> {
  if (!isTauri()) return;
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('cancel_clone');
}

/**
 * Store git credentials (username + PAT) in the OS keychain.
 * PAT is stored securely and never returned to the frontend.
 */
export async function setGitCredentials(username: string, pat: string): Promise<void> {
  if (!isTauri()) return;
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('set_git_credentials', { username, pat });
}

/**
 * Get stored git credential info.
 * Returns username + has_pat flag. PAT is never exposed to the frontend.
 */
export async function getGitCredentials(): Promise<GitCredentialInfo | null> {
  if (!isTauri()) return null;
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<GitCredentialInfo | null>('get_git_credentials');
}
