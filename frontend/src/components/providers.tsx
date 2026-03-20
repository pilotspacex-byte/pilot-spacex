'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { ThemeProvider } from 'next-themes';
import { useEffect, type ReactNode } from 'react';
import { getQueryClient } from '@/lib/queryClient';
import { rootStore, StoreContext } from '@/stores';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Toaster } from '@/components/ui/sonner';
import { isTauri } from '@/lib/tauri';

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  // Use the singleton query client getter for proper SSR support
  const queryClient = getQueryClient();

  // Sync Supabase JWT tokens to Tauri Store on mount (Tauri mode only).
  // Dynamic import ensures this module never loads during SSG/web builds.
  useEffect(() => {
    if (isTauri()) {
      import('@/lib/tauri-auth').then(({ syncTokenToTauriStore }) => {
        syncTokenToTauriStore().catch(console.error);
      });
    }
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <StoreContext.Provider value={rootStore}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <TooltipProvider delayDuration={0}>
            {children}
            <Toaster
              position="top-right"
              toastOptions={{
                classNames: {
                  toast: 'bg-card border-border shadow-warm-md rounded-lg',
                  title: 'text-foreground font-medium',
                  description: 'text-muted-foreground',
                },
              }}
            />
          </TooltipProvider>
        </ThemeProvider>
      </StoreContext.Provider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
