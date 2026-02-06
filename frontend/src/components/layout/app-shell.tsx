'use client';

import { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { motion, AnimatePresence } from 'motion/react';
import { Menu } from 'lucide-react';
import { useUIStore } from '@/stores';
import { useResponsive } from '@/hooks/useMediaQuery';
import { Sidebar } from './sidebar';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

interface AppShellProps {
  children: ReactNode;
}

export const AppShell = observer(function AppShell({ children }: AppShellProps) {
  const uiStore = useUIStore();
  const { isSmallScreen } = useResponsive();
  const sidebarOpen = !uiStore.sidebarCollapsed;

  useEffect(() => {
    uiStore.hydrate();
  }, [uiStore]);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Skip to main content - accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:m-4 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        Skip to main content
      </a>

      {/* Mobile backdrop overlay */}
      <AnimatePresence>
        {isSmallScreen && sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-background/60 backdrop-blur-sm"
            onClick={() => uiStore.setSidebarCollapsed(true)}
            aria-hidden="true"
          />
        )}
      </AnimatePresence>

      {/* Sidebar — overlay on mobile, inline on desktop */}
      {isSmallScreen ? (
        <AnimatePresence>
          {sidebarOpen && (
            <motion.aside
              initial={{ x: -260 }}
              animate={{ x: 0 }}
              exit={{ x: -260 }}
              transition={{ duration: 0.2, ease: [0, 0, 0.2, 1] }}
              className="fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col border-r border-sidebar-border bg-sidebar"
            >
              <Sidebar />
            </motion.aside>
          )}
        </AnimatePresence>
      ) : (
        <motion.aside
          initial={false}
          animate={{
            width: uiStore.sidebarCollapsed ? 60 : uiStore.sidebarWidth,
          }}
          transition={{ duration: 0.2, ease: [0, 0, 0.2, 1] }}
          className="relative flex h-full flex-col border-r border-sidebar-border bg-sidebar"
        >
          <Sidebar />
        </motion.aside>
      )}

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile hamburger toggle */}
        {isSmallScreen && !sidebarOpen && (
          <div className="flex h-10 items-center border-b border-border px-2">
            <Button
              variant="ghost"
              size="icon"
              aria-label="Open sidebar"
              className="h-8 w-8 text-muted-foreground hover:text-foreground"
              onClick={() => uiStore.setSidebarCollapsed(false)}
            >
              <Menu className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* Main content */}
        <main id="main-content" className={cn('flex-1 overflow-auto', 'scrollbar-thin')}>
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0, 0, 0.2, 1] }}
            className="h-full"
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  );
});
