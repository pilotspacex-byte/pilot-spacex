'use client';

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { observer } from 'mobx-react-lite';
import { motion } from 'motion/react';
import { Loader2, AlertCircle, LogIn, Building2 } from 'lucide-react';
import { useAuthStore, useWorkspaceStore } from '@/stores';
import { workspacesApi } from '@/services/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import type { Workspace } from '@/types';

interface WorkspaceContextValue {
  workspace: Workspace;
  workspaceSlug: string;
}

const WorkspaceContext = React.createContext<WorkspaceContextValue | null>(null);

/**
 * Hook to access current workspace context.
 * Must be used within WorkspaceGuard.
 */
export function useWorkspace(): WorkspaceContextValue {
  const context = React.useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within WorkspaceGuard');
  }
  return context;
}

interface WorkspaceGuardProps {
  children: React.ReactNode;
}

type GuardState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'not-found'; slug: string }
  | { status: 'error'; message: string }
  | { status: 'ready'; workspace: Workspace };

/**
 * Guard component that validates workspace access.
 *
 * - Checks if user is authenticated
 * - Validates workspace exists and user has access
 * - Provides workspace context to children
 */
export const WorkspaceGuard = observer(function WorkspaceGuard({
  children,
}: WorkspaceGuardProps) {
  const params = useParams();
  const router = useRouter();
  const authStore = useAuthStore();
  const workspaceStore = useWorkspaceStore();

  const workspaceSlug = params.workspaceSlug as string;

  const [state, setState] = React.useState<GuardState>({ status: 'loading' });

  // Validate workspace access when auth or slug changes
  React.useEffect(() => {
    let cancelled = false;

    async function validateWorkspace() {
      // Wait for auth to initialize
      if (authStore.isLoading) {
        return;
      }

      // Check authentication
      if (!authStore.isAuthenticated) {
        setState({ status: 'unauthenticated' });
        return;
      }

      // Validate workspace
      if (!workspaceSlug) {
        setState({ status: 'error', message: 'No workspace specified' });
        return;
      }

      setState({ status: 'loading' });

      try {
        const workspace = await workspacesApi.get(workspaceSlug);
        if (!cancelled) {
          setState({ status: 'ready', workspace });
          // Sync to MobX store for components that use workspaceStore
          workspaceStore.setCurrentWorkspace(workspace);
        }
      } catch (error) {
        if (cancelled) return;

        // Check for specific error types
        if (error instanceof Error) {
          if (error.message.includes('401') || error.message.includes('Unauthorized')) {
            setState({ status: 'unauthenticated' });
          } else if (error.message.includes('404') || error.message.includes('not found')) {
            setState({ status: 'not-found', slug: workspaceSlug });
          } else {
            setState({ status: 'error', message: error.message });
          }
        } else {
          setState({ status: 'error', message: 'Failed to load workspace' });
        }
      }
    }

    validateWorkspace();

    return () => {
      cancelled = true;
    };
  }, [authStore.isLoading, authStore.isAuthenticated, workspaceSlug]);

  // Loading state
  if (state.status === 'loading') {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center gap-4"
        >
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading workspace...</p>
        </motion.div>
      </div>
    );
  }

  // Unauthenticated state
  if (state.status === 'unauthenticated') {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <Card className="border-border/50 shadow-warm">
            <CardContent className="flex flex-col items-center p-8 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
                <LogIn className="h-7 w-7 text-primary" />
              </div>
              <h2 className="mb-2 text-xl font-semibold text-foreground">
                Sign in required
              </h2>
              <p className="mb-6 text-muted-foreground">
                Please sign in to access this workspace.
              </p>
              <Button
                onClick={() => router.push('/login')}
                className="w-full gap-2"
              >
                <LogIn className="h-4 w-4" />
                Sign in
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }

  // Workspace not found state
  if (state.status === 'not-found') {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <Card className="border-border/50 shadow-warm">
            <CardContent className="flex flex-col items-center p-8 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
                <Building2 className="h-7 w-7 text-destructive" />
              </div>
              <h2 className="mb-2 text-xl font-semibold text-foreground">
                Workspace not found
              </h2>
              <p className="mb-6 text-muted-foreground">
                The workspace <span className="font-medium">&ldquo;{state.slug}&rdquo;</span> doesn&apos;t exist
                or you don&apos;t have access.
              </p>
              <div className="flex w-full flex-col gap-2">
                <Button onClick={() => router.push('/')} className="w-full">
                  Go to workspace selector
                </Button>
                <Button
                  variant="outline"
                  onClick={() => router.back()}
                  className="w-full"
                >
                  Go back
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }

  // Error state
  if (state.status === 'error') {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <Card className="border-border/50 shadow-warm">
            <CardContent className="flex flex-col items-center p-8 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
                <AlertCircle className="h-7 w-7 text-destructive" />
              </div>
              <h2 className="mb-2 text-xl font-semibold text-foreground">
                Something went wrong
              </h2>
              <p className="mb-6 text-muted-foreground">{state.message}</p>
              <div className="flex w-full flex-col gap-2">
                <Button
                  onClick={() => window.location.reload()}
                  className="w-full"
                >
                  Try again
                </Button>
                <Button
                  variant="outline"
                  onClick={() => router.push('/')}
                  className="w-full"
                >
                  Go to workspace selector
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }

  // Ready state - render children with workspace context
  return (
    <WorkspaceContext.Provider
      value={{ workspace: state.workspace, workspaceSlug }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
});
