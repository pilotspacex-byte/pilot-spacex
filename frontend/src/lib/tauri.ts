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
 * Reset the projects directory to default ~/PilotSpace/projects/.
 * Deletes the persisted override — next getProjectsDir() returns the default.
 */
export async function resetProjectsDir(): Promise<void> {
  if (!isTauri()) return;
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('reset_projects_dir');
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

// --- Git result types (Phase 33) ---

export interface GitPullResult {
  updated: boolean;
  conflicts: string[];
}

export interface FileStatus {
  path: string;
  status: 'modified' | 'added' | 'deleted' | 'renamed' | 'untracked' | 'conflicted';
  staged: boolean;
}

export interface GitRepoStatus {
  files: FileStatus[];
  branch: string;
  ahead: number;
  behind: number;
}

export interface BranchInfo {
  name: string;
  is_current: boolean;
  is_remote: boolean;
  upstream: string | null;
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

/**
 * Pull from the remote for the repository at repoPath.
 * Uses Tauri v2 Channel API to stream progress updates.
 * Returns a GitPullResult indicating whether commits were merged and any conflicted paths.
 * @param repoPath - Absolute path to the local git repository
 * @param onProgress - Callback invoked on each progress update
 */
export async function gitPull(
  repoPath: string,
  onProgress: (progress: GitProgress) => void
): Promise<GitPullResult> {
  if (!isTauri()) throw new Error('Not in Tauri mode');
  const { invoke, Channel } = await import('@tauri-apps/api/core');
  const channel = new Channel<GitProgress>();
  channel.onmessage = onProgress;
  return invoke<GitPullResult>('git_pull', { repoPath, onProgress: channel });
}

/**
 * Push the current branch to origin for the repository at repoPath.
 * Uses Tauri v2 Channel API to stream progress updates.
 * @param repoPath - Absolute path to the local git repository
 * @param onProgress - Callback invoked on each progress update
 */
export async function gitPush(
  repoPath: string,
  onProgress: (progress: GitProgress) => void
): Promise<void> {
  if (!isTauri()) throw new Error('Not in Tauri mode');
  const { invoke, Channel } = await import('@tauri-apps/api/core');
  const channel = new Channel<GitProgress>();
  channel.onmessage = onProgress;
  await invoke('git_push', { repoPath, onProgress: channel });
}

/**
 * Get the working tree and index status for the repository at repoPath.
 * Returns an empty status object if not in Tauri mode.
 * @param repoPath - Absolute path to the local git repository
 */
export async function gitStatus(repoPath: string): Promise<GitRepoStatus> {
  if (!isTauri()) return { files: [], branch: '', ahead: 0, behind: 0 };
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<GitRepoStatus>('git_status', { repoPath });
}

/**
 * List all local and remote branches for the repository at repoPath.
 * Returns an empty array if not in Tauri mode.
 * @param repoPath - Absolute path to the local git repository
 */
export async function gitBranchList(repoPath: string): Promise<BranchInfo[]> {
  if (!isTauri()) return [];
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<BranchInfo[]>('git_branch_list', { repoPath });
}

/**
 * Create a new branch named `name` from the current HEAD commit.
 * @param repoPath - Absolute path to the local git repository
 * @param name - New branch name
 */
export async function gitBranchCreate(repoPath: string, name: string): Promise<void> {
  if (!isTauri()) throw new Error('Not in Tauri mode');
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('git_branch_create', { repoPath, name });
}

/**
 * Switch to the branch named `name` using a safe checkout.
 * Safe checkout refuses to overwrite uncommitted changes.
 * @param repoPath - Absolute path to the local git repository
 * @param name - Branch name to switch to
 */
export async function gitBranchSwitch(repoPath: string, name: string): Promise<void> {
  if (!isTauri()) throw new Error('Not in Tauri mode');
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('git_branch_switch', { repoPath, name });
}

/**
 * Delete the local branch named `name`.
 * Refuses to delete the currently checked-out branch.
 * @param repoPath - Absolute path to the local git repository
 * @param name - Branch name to delete
 */
export async function gitBranchDelete(repoPath: string, name: string): Promise<void> {
  if (!isTauri()) throw new Error('Not in Tauri mode');
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('git_branch_delete', { repoPath, name });
}

// --- Git diff/stage/commit types and commands (Phase 36) ---

export interface FileDiff {
  path: string;
  /** Unified diff text (--- +++ @@ lines). Empty string if binary. */
  diff: string;
  /** true if the file is binary (no text diff available) */
  is_binary: boolean;
}

/**
 * Get unified diff text for changed files in the repository at repoPath.
 * If filePath is provided, returns diff for that single file only.
 * If filePath is omitted, returns diffs for all changed files (staged + unstaged).
 * Returns an empty array if not in Tauri mode.
 * @param repoPath - Absolute path to the local git repository
 * @param filePath - Optional: restrict diff to this specific file path
 */
export async function gitDiff(repoPath: string, filePath?: string): Promise<FileDiff[]> {
  if (!isTauri()) return [];
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<FileDiff[]>('git_diff', { repoPath, filePath: filePath ?? null });
}

/**
 * Stage the specified files in the git index.
 * After staging, call gitStatus to get the updated file list.
 * @param repoPath - Absolute path to the local git repository
 * @param paths - Repo-relative paths of files to stage
 */
export async function gitStage(repoPath: string, paths: string[]): Promise<void> {
  if (!isTauri()) throw new Error('Not in Tauri mode');
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('git_stage', { repoPath, paths });
}

/**
 * Unstage the specified files, resetting their index entries to HEAD.
 * Does not touch the working tree — local file changes are preserved.
 * @param repoPath - Absolute path to the local git repository
 * @param paths - Repo-relative paths of files to unstage
 */
export async function gitUnstage(repoPath: string, paths: string[]): Promise<void> {
  if (!isTauri()) throw new Error('Not in Tauri mode');
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('git_unstage', { repoPath, paths });
}

/**
 * Create a commit from the currently staged files with the given message.
 * Returns the new commit OID as a hex string.
 * Handles initial commit (unborn HEAD) automatically.
 * @param repoPath - Absolute path to the local git repository
 * @param message - Commit message
 */
export async function gitCommit(repoPath: string, message: string): Promise<string> {
  if (!isTauri()) throw new Error('Not in Tauri mode');
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<string>('git_commit', { repoPath, message });
}

// --- Terminal commands (Phase 34) ---

export interface TerminalOutput {
  session_id: string;
  data: string;
}

export interface TerminalSessionInfo {
  session_id: string;
}

/**
 * Create a new PTY terminal session.
 * Returns session info with a unique session_id.
 * Output is streamed via the onOutput callback (batched at 16ms by Rust).
 * @param rows - Initial terminal height in rows
 * @param cols - Initial terminal width in columns
 * @param onOutput - Callback invoked with batched terminal output chunks
 */
export async function createTerminal(
  rows: number,
  cols: number,
  onOutput: (output: TerminalOutput) => void
): Promise<TerminalSessionInfo> {
  if (!isTauri()) throw new Error('Not in Tauri mode');
  const { invoke, Channel } = await import('@tauri-apps/api/core');
  const channel = new Channel<TerminalOutput>();
  channel.onmessage = onOutput;
  return invoke<TerminalSessionInfo>('create_terminal', {
    rows,
    cols,
    onOutput: channel,
  });
}

/**
 * Write data (keystrokes) to a terminal session's stdin.
 * @param sessionId - The session ID returned by createTerminal
 * @param data - Raw character data to write to the PTY
 */
export async function writeTerminal(sessionId: string, data: string): Promise<void> {
  if (!isTauri()) return;
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('write_terminal', { sessionId, data });
}

/**
 * Resize a terminal session's PTY dimensions.
 * Sends SIGWINCH to the child process so programs like vim/htop re-render.
 * @param sessionId - The session ID returned by createTerminal
 * @param rows - New height in rows
 * @param cols - New width in columns
 */
export async function resizeTerminal(sessionId: string, rows: number, cols: number): Promise<void> {
  if (!isTauri()) return;
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('resize_terminal', { sessionId, rows, cols });
}

/**
 * Close a terminal session, killing the child process and freeing resources.
 * Idempotent — safe to call even if the session is already closed.
 * @param sessionId - The session ID returned by createTerminal
 */
export async function closeTerminal(sessionId: string): Promise<void> {
  if (!isTauri()) return;
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('close_terminal', { sessionId });
}

// --- Sidecar commands (Phase 35) ---

export interface SidecarOutput {
  id: string;
  /** "stdout" or "stderr" */
  stream: string;
  data: string;
}

export interface SidecarResult {
  id: string;
  exit_code: number;
}

/**
 * Spawn the pilot-cli sidecar binary with the given arguments.
 * Streams stdout and stderr via the onOutput callback.
 * Returns a SidecarResult with the process exit code when the sidecar exits.
 *
 * @param args - CLI arguments (e.g., ["implement", "PS-42", "--oneshot"])
 * @param cwd - Optional working directory for the sidecar process
 * @param onOutput - Callback invoked with each stdout/stderr line
 */
export async function runSidecar(
  args: string[],
  cwd: string | undefined,
  onOutput: (output: SidecarOutput) => void
): Promise<SidecarResult> {
  if (!isTauri()) throw new Error('Not in Tauri mode');
  const { invoke, Channel } = await import('@tauri-apps/api/core');
  const channel = new Channel<SidecarOutput>();
  channel.onmessage = onOutput;
  return invoke<SidecarResult>('run_sidecar', {
    args,
    cwd: cwd ?? null,
    on_output: channel,
  });
}

/**
 * Cancel a running sidecar process by its ID.
 * Idempotent — safe to call even if the process has already exited.
 * @param id - The process ID from SidecarResult or SidecarOutput
 */
export async function cancelSidecar(id: string): Promise<void> {
  if (!isTauri()) return;
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('cancel_sidecar', { id });
}

/**
 * Convenience wrapper: run `pilot implement <issueId> --oneshot` via the sidecar.
 * Streams stdout and stderr via the onOutput callback.
 * Returns a SidecarResult with the process exit code when the sidecar exits.
 *
 * @param issueId - The issue identifier (e.g., "PS-42")
 * @param cwd - Absolute path to the repository working directory
 * @param onOutput - Callback invoked with each stdout/stderr line
 */
export async function runPilotImplement(
  issueId: string,
  cwd: string,
  onOutput: (output: SidecarOutput) => void
): Promise<SidecarResult> {
  return runSidecar(['implement', issueId, '--oneshot'], cwd, onOutput);
}

// --- Notification commands (Phase 37) ---

/**
 * Send a native OS notification via the system tray.
 * No-op if not in Tauri mode.
 * @param title - Notification title
 * @param body - Notification body text
 */
export async function sendNotification(title: string, body: string): Promise<void> {
  if (!isTauri()) return;
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('send_notification', { title, body });
}
