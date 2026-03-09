'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import { Compass, Loader2, Plus, Building2, ArrowLeft, Check, AlertCircle } from 'lucide-react';
import { WorkspaceSelector, addRecentWorkspace } from '@/components/workspace-selector';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { getAuthProvider } from '@/services/auth/providers';
import { workspacesApi } from '@/services/api/workspaces';
import { ApiError } from '@/services/api/client';
import { toSlug } from '@/lib/slug';
import { supabase } from '@/lib/supabase';

const WORKSPACE_STORAGE_KEY = 'pilot-space:last-workspace';

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

const stagger = {
  animate: {
    transition: {
      staggerChildren: 0.1,
    },
  },
};

export default function HomePage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = React.useState(true);
  const [hasWorkspaces, setHasWorkspaces] = React.useState(true);
  const [fetchError, setFetchError] = React.useState<string | null>(null);

  // Wizard state
  const [step, setStep] = React.useState<1 | 2>(1);
  const [newWorkspaceName, setNewWorkspaceName] = React.useState('');
  const [workspaceSlug, setWorkspaceSlug] = React.useState('');
  const [slugError, setSlugError] = React.useState<string | null>(null);
  const [isValidatingSlug, setIsValidatingSlug] = React.useState(false);
  const [createError, setCreateError] = React.useState<string | null>(null);
  const [isCreating, setIsCreating] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;

    async function resolveWorkspace() {
      // 1. Check if user is authenticated (works for both Supabase and AuthCore)
      const provider = await getAuthProvider();
      const token = await provider.getToken();

      if (cancelled) return;

      if (!token) {
        router.replace('/welcome');
        return;
      }

      // 2. Fetch user's workspaces to validate access
      try {
        const { items } = await workspacesApi.list();

        if (cancelled) return;

        if (items.length > 0) {
          const storedSlug = localStorage.getItem(WORKSPACE_STORAGE_KEY);
          // Use stored workspace if user still has access, otherwise use first
          const target = (storedSlug && items.find((w) => w.slug === storedSlug)) || items[0]!;
          addRecentWorkspace(target.slug);
          router.replace(`/${target.slug}`);
          return;
        }
      } catch (err) {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : '';
        // Auth errors → redirect to login
        if (
          msg.includes('401') ||
          msg.includes('403') ||
          msg.toLowerCase().includes('unauthorized') ||
          msg.toLowerCase().includes('forbidden')
        ) {
          router.replace('/login');
          return;
        }
        // Other errors (network, 5xx) → show error UI
        setFetchError('Failed to load workspaces. Please refresh the page.');
        setIsLoading(false);
        return;
      }

      // 3. No workspaces found → clear stale stored slug, auto-create from email
      localStorage.removeItem(WORKSPACE_STORAGE_KEY);
      if (!cancelled) {
        await autoCreateWorkspace();
      }

      async function autoCreateWorkspace(): Promise<void> {
        // Derive display name from auth metadata or email prefix
        const {
          data: { user },
        } = await supabase.auth.getUser();

        const email = user?.email ?? '';
        const displayName =
          (user?.user_metadata?.name as string | undefined) ||
          (user?.user_metadata?.full_name as string | undefined) ||
          email.split('@')[0] ||
          'my-workspace';

        const baseSlug = toSlug(displayName) || 'my-workspace';

        const tryCreate = async (suffix: string): Promise<void> => {
          const slug = `${baseSlug}-${suffix}`;
          try {
            const workspace = await workspacesApi.create({ name: displayName, slug });
            addRecentWorkspace(workspace.slug);
            if (!cancelled) router.replace(`/${workspace.slug}`);
          } catch (err) {
            if (err instanceof ApiError && err.status === 409) {
              // Retry exactly once with a new 4-char suffix
              const newSuffix = Math.random().toString(36).slice(2, 6);
              try {
                const workspace2 = await workspacesApi.create({
                  name: displayName,
                  slug: `${baseSlug}-${newSuffix}`,
                });
                addRecentWorkspace(workspace2.slug);
                if (!cancelled) router.replace(`/${workspace2.slug}`);
              } catch {
                // Both attempts failed — fall back to manual form
                if (!cancelled) {
                  setHasWorkspaces(false);
                  setIsLoading(false);
                }
              }
            } else {
              // Non-conflict error — fall back to manual form
              if (!cancelled) {
                setHasWorkspaces(false);
                setIsLoading(false);
              }
            }
          }
        };

        const initialSuffix = Math.random().toString(36).slice(2, 6);
        await tryCreate(initialSuffix);
      }
    }

    resolveWorkspace();

    return () => {
      cancelled = true;
    };
  }, [router]);

  const handleWorkspaceSelect = (slug: string) => {
    addRecentWorkspace(slug);
    router.push(`/${slug}`);
  };

  // Step 1: sync slug from name input
  const handleNameChange = (value: string) => {
    setNewWorkspaceName(value);
    setSlugError(null);
    const derived = toSlug(value);
    setWorkspaceSlug(derived);
  };

  // Step 1: manual slug edit — format as-you-type, clear error
  const handleSlugChange = (value: string) => {
    setSlugError(null);
    setWorkspaceSlug(toSlug(value));
  };

  // Step 1 → Step 2: validate slug uniqueness
  const handleNext = async () => {
    if (!newWorkspaceName.trim() || !workspaceSlug) return;

    setSlugError(null);
    setIsValidatingSlug(true);

    try {
      await workspacesApi.get(workspaceSlug);
      // Resolved → slug exists → taken
      setSlugError('Slug taken — try another');
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        // 404 = slug is free → proceed
        setStep(2);
      } else {
        // Network / 5xx — do not proceed, show error
        setSlugError('Unable to check availability. Please try again.');
      }
    } finally {
      setIsValidatingSlug(false);
    }
  };

  // Step 2: create workspace
  const handleCreateWorkspace = async () => {
    setCreateError(null);
    setIsCreating(true);

    try {
      const workspace = await workspacesApi.create({
        name: newWorkspaceName.trim(),
        slug: workspaceSlug,
      });
      addRecentWorkspace(workspace.slug);
      router.replace(`/${workspace.slug}`);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create workspace');
      setIsCreating(false);
    }
  };

  const isNextDisabled =
    !newWorkspaceName.trim() || !workspaceSlug || slugError !== null || isValidatingSlug;

  if (fetchError) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background px-4">
        <div className="flex flex-col items-center gap-4 text-center">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <p className="text-sm text-muted-foreground">{fetchError}</p>
          <Button variant="outline" onClick={() => window.location.reload()}>
            Refresh
          </Button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center gap-4"
        >
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-background px-4 py-12">
      <motion.div
        variants={stagger}
        initial="initial"
        animate="animate"
        className="flex w-full max-w-md flex-col items-center"
      >
        {/* Logo */}
        <motion.div variants={fadeUp} className="mb-8">
          <motion.div
            className="relative"
            animate={{ rotate: [0, 5, -5, 0] }}
            transition={{ repeat: Infinity, duration: 6, ease: 'easeInOut' }}
          >
            <div className="absolute inset-0 blur-2xl">
              <div className="h-20 w-20 rounded-full bg-primary/20" />
            </div>
            <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-ai/20 shadow-warm-lg">
              <Compass className="h-10 w-10 text-primary" strokeWidth={1.5} />
            </div>
          </motion.div>
        </motion.div>

        {/* Welcome Text */}
        <motion.h1
          variants={fadeUp}
          className="mb-2 text-center text-3xl font-semibold tracking-tight text-foreground"
        >
          Welcome to Pilot Space
        </motion.h1>

        <motion.p variants={fadeUp} className="mb-8 text-center text-muted-foreground">
          {hasWorkspaces ? 'Select a workspace to get started' : 'Create your first workspace'}
        </motion.p>

        {/* Workspace Selector or Creation Wizard */}
        <motion.div variants={fadeUp} className="w-full">
          {hasWorkspaces ? (
            <WorkspaceSelector onSelect={handleWorkspaceSelect} />
          ) : step === 1 ? (
            <Card className="border-border/50 shadow-warm">
              <CardContent className="p-6">
                {/* Step indicator */}
                <div className="mb-5 flex items-center gap-3">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    <Building2 className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                      Step 1 of 2
                    </p>
                    <p className="text-sm font-semibold text-foreground">Name your workspace</p>
                  </div>
                </div>

                <div className="space-y-4">
                  {/* Workspace name */}
                  <div className="space-y-2">
                    <Label htmlFor="workspace-name">Workspace name</Label>
                    <Input
                      id="workspace-name"
                      type="text"
                      placeholder="My team workspace"
                      value={newWorkspaceName}
                      onChange={(e) => handleNameChange(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !isNextDisabled) handleNext();
                      }}
                      disabled={isValidatingSlug}
                      className="h-11"
                      autoFocus
                    />
                  </div>

                  {/* Slug */}
                  <div className="space-y-2">
                    <Label htmlFor="workspace-slug">URL slug</Label>
                    <Input
                      id="workspace-slug"
                      type="text"
                      placeholder="my-team-workspace"
                      value={workspaceSlug}
                      onChange={(e) => handleSlugChange(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !isNextDisabled) handleNext();
                      }}
                      disabled={isValidatingSlug}
                      maxLength={48}
                      className={`h-11 font-mono text-sm ${slugError ? 'border-destructive focus-visible:ring-destructive' : ''}`}
                      aria-describedby={slugError ? 'slug-error' : 'slug-hint'}
                    />
                    {slugError ? (
                      <p
                        id="slug-error"
                        role="alert"
                        className="flex items-center gap-1.5 text-xs text-destructive"
                      >
                        <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                        {slugError}
                      </p>
                    ) : workspaceSlug ? (
                      <p id="slug-hint" className="text-xs text-muted-foreground">
                        pilotspace.io/
                        <span className="font-medium text-foreground">{workspaceSlug}</span>
                      </p>
                    ) : (
                      <p id="slug-hint" className="text-xs text-muted-foreground">
                        pilotspace.io/your-slug
                      </p>
                    )}
                  </div>

                  <Button onClick={handleNext} disabled={isNextDisabled} className="w-full gap-2">
                    {isValidatingSlug ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                        Checking availability...
                      </>
                    ) : (
                      'Next'
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-border/50 shadow-warm">
              <CardContent className="p-6">
                {/* Step indicator */}
                <div className="mb-5 flex items-center gap-3">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    <Check className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                      Step 2 of 2
                    </p>
                    <p className="text-sm font-semibold text-foreground">You&apos;re all set!</p>
                  </div>
                </div>

                {/* Summary block */}
                <div className="mb-5 rounded-lg border border-border/60 bg-muted/40 px-4 py-3 space-y-2">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-xs font-medium text-muted-foreground">Name</span>
                    <span className="text-sm font-semibold text-foreground truncate max-w-[220px]">
                      {newWorkspaceName.trim()}
                    </span>
                  </div>
                  <div className="h-px bg-border/50" />
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-xs font-medium text-muted-foreground">URL</span>
                    <span className="font-mono text-xs text-foreground truncate max-w-[220px]">
                      pilotspace.io/
                      <span className="font-semibold text-primary">{workspaceSlug}</span>
                    </span>
                  </div>
                </div>

                {createError && (
                  <p
                    role="alert"
                    className="mb-4 flex items-center gap-1.5 text-sm text-destructive"
                  >
                    <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
                    {createError}
                  </p>
                )}

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setStep(1);
                      setCreateError(null);
                    }}
                    disabled={isCreating}
                    className="gap-1.5"
                    aria-label="Back to step 1"
                  >
                    <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                    Back
                  </Button>

                  <Button
                    onClick={handleCreateWorkspace}
                    disabled={isCreating}
                    className="flex-1 gap-2"
                  >
                    {isCreating ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                        Creating...
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4" aria-hidden="true" />
                        Create Workspace
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </motion.div>
      </motion.div>
    </div>
  );
}
