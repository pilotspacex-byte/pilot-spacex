'use client';

/**
 * MonacoErrorBoundary — React error boundary wrapping Monaco Editor.
 *
 * Catches chunk load failures (dynamic import errors) and Monaco initialization
 * errors, rendering a user-friendly fallback with a refresh button.
 *
 * Common failure modes handled:
 * - ChunkLoadError: Webpack chunk failed to load (network issue, deploy)
 * - Dynamic import timeout
 * - Monaco WebWorker initialization failure
 */

import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional custom fallback. If not provided, uses default error UI. */
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  errorMessage: string | null;
}

export class MonacoErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, errorMessage: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Capture a user-facing message from the error
    const isChunkError =
      error.name === 'ChunkLoadError' ||
      error.message?.includes('Loading chunk') ||
      error.message?.includes('Failed to fetch dynamically imported module');

    return {
      hasError: true,
      errorMessage: isChunkError
        ? 'Editor failed to load (network error). Please refresh the page.'
        : 'Failed to load editor. Please refresh the page.',
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log to console for observability; structured logging can be added here
    console.error('[MonacoErrorBoundary] Editor load failure:', error, errorInfo);
  }

  private handleRefresh = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex h-full w-full flex-col items-center justify-center gap-4 bg-background p-8 text-center">
          <AlertTriangle className="h-10 w-10 text-destructive opacity-80" aria-hidden="true" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">
              {this.state.errorMessage ?? 'Failed to load editor. Please refresh the page.'}
            </p>
            <p className="text-xs text-muted-foreground">
              If the problem persists, try clearing your browser cache.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={this.handleRefresh}>
            Refresh Page
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
