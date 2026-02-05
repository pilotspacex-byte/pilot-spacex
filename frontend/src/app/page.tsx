'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import { Compass, Loader2 } from 'lucide-react';
import { WorkspaceSelector, addRecentWorkspace } from '@/components/workspace-selector';

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

  // Check for stored workspace on mount
  React.useEffect(() => {
    const storedWorkspace = localStorage.getItem(WORKSPACE_STORAGE_KEY);
    if (storedWorkspace) {
      // Redirect to stored workspace
      router.replace(`/${storedWorkspace}`);
    } else {
      setIsLoading(false);
    }
  }, [router]);

  const handleWorkspaceSelect = (slug: string) => {
    addRecentWorkspace(slug);
    router.push(`/${slug}`);
  };

  // Show loading while checking for stored workspace
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

  // Show workspace selector if no stored workspace
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

        <motion.p
          variants={fadeUp}
          className="mb-8 text-center text-muted-foreground"
        >
          Select a workspace to get started
        </motion.p>

        {/* Workspace Selector */}
        <motion.div variants={fadeUp} className="w-full">
          <WorkspaceSelector onSelect={handleWorkspaceSelect} />
        </motion.div>
      </motion.div>
    </div>
  );
}
