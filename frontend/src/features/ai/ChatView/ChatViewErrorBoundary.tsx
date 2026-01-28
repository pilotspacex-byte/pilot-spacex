/**
 * ChatViewErrorBoundary - React Error Boundary for ChatView
 *
 * Provides graceful error handling with retry functionality.
 * Catches React component errors in the ChatView tree and displays
 * a user-friendly error UI with retry capability.
 *
 * @see https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary
 */

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface Props {
  children: React.ReactNode;
  onRetry?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ChatViewErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error details for debugging
    console.error('ChatView Error Boundary caught error:', error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
    this.props.onRetry?.();
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <div
          className="flex flex-col items-center justify-center h-full p-8 text-center"
          data-testid="chat-view-error-boundary"
        >
          <AlertCircle className="w-12 h-12 text-destructive mb-4" aria-hidden="true" />
          <h3 className="text-lg font-semibold mb-2">Something went wrong</h3>
          <p className="text-muted-foreground mb-4 max-w-md">
            {this.state.error?.message || 'An unexpected error occurred in the chat interface.'}
          </p>
          <Button onClick={this.handleRetry} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" aria-hidden="true" />
            Try Again
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
