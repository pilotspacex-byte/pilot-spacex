/**
 * DesktopSettingsPage — Desktop-only settings for project directory and git credentials.
 *
 * Only rendered when running inside the Tauri desktop shell. Provides:
 *   - Project base directory configuration with native folder picker
 *   - HTTPS git credentials (username + PAT) stored in OS keychain
 *
 * Security: The PAT is never pre-populated or displayed — only has_pat status
 * is returned from Rust. Users enter a new PAT to update credentials.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { Check, Eye, EyeOff, FolderOpen, KeyRound, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  getProjectsDir,
  setProjectsDir,
  openFolderDialog,
  getGitCredentials,
  setGitCredentials,
} from '@/lib/tauri';
import type { GitCredentialInfo } from '@/lib/tauri';

// ---------------------------------------------------------------------------
// Project Directory section
// ---------------------------------------------------------------------------

function ProjectDirectorySection() {
  const [currentPath, setCurrentPath] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPath = useCallback(async () => {
    try {
      const path = await getProjectsDir();
      setCurrentPath(path);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load project directory.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPath();
  }, [loadPath]);

  const handleChange = async () => {
    setError(null);
    setSaved(false);
    try {
      const selected = await openFolderDialog();
      if (selected === null) return; // user cancelled
      setIsSaving(true);
      await setProjectsDir(selected);
      setCurrentPath(selected);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update project directory.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    setError(null);
    setSaved(false);
    setIsSaving(true);
    try {
      // Empty string signals reset to default ~/PilotSpace/projects/
      await setProjectsDir('');
      // Reload the resolved default path
      await loadPath();
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to reset project directory.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section>
      <h2 className="text-sm font-semibold text-foreground">Project Directory</h2>
      <p className="mt-0.5 text-xs text-muted-foreground">
        Base directory where cloned repositories are stored.
      </p>

      <div className="mt-4 space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="projects-dir">Base Path</Label>
          <div className="flex items-center gap-2">
            <Input
              id="projects-dir"
              type="text"
              readOnly
              value={isLoading ? 'Loading...' : currentPath}
              className="flex-1 cursor-default font-mono text-sm opacity-80 sm:max-w-md"
              aria-label="Current project base directory"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleChange}
              disabled={isLoading || isSaving}
              aria-busy={isSaving}
            >
              <FolderOpen className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
              Change...
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            New repositories will be cloned into this directory.
          </p>
        </div>

        <div className="flex items-center gap-4">
          {saved && (
            <span className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400" role="status">
              <Check className="h-3.5 w-3.5" aria-hidden="true" />
              Saved
            </span>
          )}
          {error && (
            <p className="text-xs text-destructive" role="alert">
              {error}
            </p>
          )}
          <button
            type="button"
            onClick={handleReset}
            disabled={isLoading || isSaving}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:pointer-events-none disabled:opacity-50"
            aria-label="Reset project directory to default"
          >
            <RotateCcw className="h-3 w-3" aria-hidden="true" />
            Reset to default
          </button>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Git Credentials section
// ---------------------------------------------------------------------------

function GitCredentialsSection() {
  const [credentials, setCredentials] = useState<GitCredentialInfo | null>(null);
  const [isLoadingCreds, setIsLoadingCreds] = useState(true);

  const [username, setUsername] = useState('');
  const [pat, setPat] = useState('');
  const [showPat, setShowPat] = useState(false);

  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCredentials = useCallback(async () => {
    try {
      const creds = await getGitCredentials();
      setCredentials(creds);
      if (creds?.username) {
        setUsername(creds.username);
      }
    } catch (e) {
      // Non-fatal — credentials may not exist yet
      setCredentials(null);
    } finally {
      setIsLoadingCreds(false);
    }
  }, []);

  useEffect(() => {
    void loadCredentials();
  }, [loadCredentials]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !pat.trim()) return;

    setError(null);
    setSaved(false);
    setIsSaving(true);

    try {
      await setGitCredentials(username.trim(), pat.trim());
      // Clear the PAT input — it is never pre-populated
      setPat('');
      // Refresh credential status
      await loadCredentials();
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save credentials.');
    } finally {
      setIsSaving(false);
    }
  };

  const hasCredentials = credentials !== null;

  return (
    <section>
      <h2 className="text-sm font-semibold text-foreground">Git Credentials</h2>
      <p className="mt-0.5 text-xs text-muted-foreground">
        HTTPS credentials for git operations (clone, push, pull).
      </p>

      <div className="mt-4 space-y-4">
        {/* Current credential status */}
        <div className="rounded-lg border border-border bg-background-subtle p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <KeyRound className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
            <span className="text-xs font-semibold text-foreground">Credential Status</span>
          </div>
          {isLoadingCreds ? (
            <p className="text-xs text-muted-foreground">Loading...</p>
          ) : hasCredentials ? (
            <div className="space-y-1">
              <div className="flex items-center gap-1.5">
                <Check className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                <span className="text-xs text-foreground">
                  Username: <span className="font-mono">{credentials.username}</span>
                </span>
              </div>
              {credentials.has_pat && (
                <div className="flex items-center gap-1.5">
                  <Check className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                  <span className="text-xs text-foreground">PAT: Configured</span>
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No credentials configured.</p>
          )}
        </div>

        {/* Credential form */}
        <form onSubmit={handleSave} className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="git-username">Username</Label>
            <Input
              id="git-username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isSaving}
              placeholder="e.g. your-github-username"
              className="sm:max-w-md"
              aria-describedby="git-username-hint"
            />
            <p id="git-username-hint" className="text-xs text-muted-foreground">
              Your git hosting provider username.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="git-pat">Personal Access Token</Label>
            <div className="relative sm:max-w-md">
              <Input
                id="git-pat"
                type={showPat ? 'text' : 'password'}
                autoComplete="new-password"
                value={pat}
                onChange={(e) => setPat(e.target.value)}
                disabled={isSaving}
                placeholder={hasCredentials ? 'Enter new PAT to update' : 'Enter your Personal Access Token'}
                className="pr-10"
                aria-describedby="git-pat-hint"
              />
              <button
                type="button"
                onClick={() => setShowPat((v) => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                aria-label={showPat ? 'Hide token' : 'Show token'}
              >
                {showPat ? (
                  <EyeOff className="h-3.5 w-3.5" aria-hidden="true" />
                ) : (
                  <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                )}
              </button>
            </div>
            <p id="git-pat-hint" className="text-xs text-muted-foreground">
              Stored securely in your OS keychain. Never displayed after saving.
            </p>
          </div>

          <div className="flex items-center gap-3 pt-1">
            <Button
              type="submit"
              size="sm"
              disabled={!username.trim() || !pat.trim() || isSaving}
              aria-busy={isSaving}
            >
              {isSaving ? 'Saving...' : 'Save Credentials'}
            </Button>
            {saved && (
              <span
                className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400"
                role="status"
              >
                <Check className="h-3.5 w-3.5" aria-hidden="true" />
                Saved
              </span>
            )}
            {error && (
              <p className="text-xs text-destructive" role="alert">
                {error}
              </p>
            )}
          </div>
        </form>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function DesktopSettingsPage() {
  return (
    <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Desktop</h1>
          <p className="text-sm text-muted-foreground">
            Configure local project storage and git credentials for the desktop app.
          </p>
        </div>

        <ProjectDirectorySection />

        <Separator />

        <GitCredentialsSection />
      </div>
    </div>
  );
}
