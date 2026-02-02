'use client';

import { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { motion, AnimatePresence } from 'motion/react';
import { useUIStore } from '@/stores';
import { Sidebar } from './sidebar';
import { Header } from './header';
import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

interface AppShellProps {
  children: ReactNode;
}

export const AppShell = observer(function AppShell({ children }: AppShellProps) {
  const uiStore = useUIStore();

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

      {/* Sidebar */}
      <AnimatePresence mode="wait">
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
      </AnimatePresence>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <Header />

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
