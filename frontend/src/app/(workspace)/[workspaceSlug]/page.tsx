'use client';

import { use } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import {
  Compass,
  FileText,
  Sparkles,
  Lightbulb,
  Zap,
  MessageSquare,
  ChevronRight,
} from 'lucide-react';
import { observer } from 'mobx-react-lite';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { useWorkspaceStore, useOnboardingStore } from '@/stores/RootStore';
import { OnboardingChecklist } from '@/features/onboarding';
import {
  useOnboardingState,
  selectCompletionPercentage,
} from '@/features/onboarding/hooks/useOnboardingState';

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

const templates = [
  {
    id: 'sprint',
    icon: Zap,
    title: 'Sprint Planning',
    description: 'Plan your next sprint with AI-powered task breakdown',
    color: 'text-amber-500',
    bgColor: 'bg-amber-500/10',
  },
  {
    id: 'feature',
    icon: Lightbulb,
    title: 'Feature Spec',
    description: 'Define new features with structured requirements',
    color: 'text-primary',
    bgColor: 'bg-primary/10',
  },
  {
    id: 'brainstorm',
    icon: MessageSquare,
    title: 'Brainstorm',
    description: 'Free-form thinking with AI collaboration',
    color: 'text-ai',
    bgColor: 'bg-ai/10',
  },
];

interface WorkspaceHomePageProps {
  params: Promise<{ workspaceSlug: string }>;
}

/**
 * Progress trigger shown when onboarding modal is closed but not dismissed.
 * Clicking re-opens the onboarding modal.
 */
const OnboardingTrigger = observer(function OnboardingTrigger({
  workspaceId,
}: {
  workspaceId: string;
}) {
  const onboardingStore = useOnboardingStore();
  const { data } = useOnboardingState({ workspaceId });

  if (!data || data.dismissedAt || data.completedAt) return null;
  if (onboardingStore.isModalOpen) return null;

  const percentage = selectCompletionPercentage(data);

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto mb-6"
    >
      <button
        onClick={() => onboardingStore.openModal()}
        className={cn(
          'flex items-center gap-2.5 px-4 py-2.5 rounded-lg',
          'border border-primary/20 bg-primary/5',
          'text-sm font-medium text-foreground',
          'transition-all duration-200',
          'hover:border-primary/40 hover:bg-primary/10 hover:shadow-sm'
        )}
      >
        <Sparkles className="h-4 w-4 text-primary" />
        <span>Setup: {percentage}%</span>
        <Progress value={percentage} className="h-1.5 w-16" />
        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
      </button>
    </motion.div>
  );
});

const WorkspaceHomePage = observer(function WorkspaceHomePage({ params }: WorkspaceHomePageProps) {
  const { workspaceSlug } = use(params);
  const router = useRouter();
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? workspaceSlug;

  return (
    <div className="flex h-full flex-col px-8 py-8 overflow-auto">
      {/* Onboarding Modal (renders as Dialog, no layout space) */}
      <OnboardingChecklist workspaceId={workspaceId} workspaceSlug={workspaceSlug} />

      {/* Progress trigger when modal is closed but onboarding active */}
      <OnboardingTrigger workspaceId={workspaceId} />

      <div className="flex flex-1 flex-col items-center justify-center">
        <motion.div
          variants={stagger}
          initial="initial"
          animate="animate"
          className="flex max-w-2xl flex-col items-center text-center"
        >
          {/* Hero Icon */}
          <motion.div variants={fadeUp} className="mb-8">
            <motion.div
              className="relative"
              animate={{ rotate: [0, 5, -5, 0] }}
              transition={{ repeat: Infinity, duration: 6, ease: 'easeInOut' }}
            >
              <div className="absolute inset-0 blur-2xl">
                <div className="h-24 w-24 rounded-full bg-primary/20" />
              </div>
              <div className="relative flex h-24 w-24 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-ai/20 shadow-warm-lg">
                <Compass className="h-12 w-12 text-primary" strokeWidth={1.5} />
              </div>
            </motion.div>
          </motion.div>

          {/* Greeting */}
          <motion.h1
            variants={fadeUp}
            className="mb-4 text-4xl font-semibold tracking-tight text-foreground"
          >
            What would you like to work on?
          </motion.h1>

          <motion.p variants={fadeUp} className="mb-10 max-w-md text-lg text-muted-foreground">
            Start with your thoughts. AI will help you refine them into actionable items.
          </motion.p>

          {/* Main CTA — navigates to create a new note */}
          <motion.div variants={fadeUp} className="mb-12">
            <Button
              size="lg"
              className="gap-2 shadow-warm-sm"
              onClick={() => router.push(`/${workspaceSlug}/notes`)}
            >
              <FileText className="h-5 w-5" />
              <span>Create a note</span>
            </Button>
          </motion.div>

          {/* Templates (display-only — not yet wired) */}
          <motion.div variants={fadeUp}>
            <p className="mb-4 text-sm font-medium text-muted-foreground">
              Or start with a template
            </p>
            <div className="grid gap-3 sm:grid-cols-3">
              {templates.map((template, index) => (
                <motion.div
                  key={template.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + index * 0.1 }}
                >
                  <Card className="border-border/50 bg-card/50">
                    <CardContent className="flex flex-col items-center p-5 text-center">
                      <div
                        className={cn(
                          'mb-3 flex h-10 w-10 items-center justify-center rounded-lg',
                          template.bgColor
                        )}
                      >
                        <template.icon className={cn('h-5 w-5', template.color)} />
                      </div>
                      <h3 className="mb-1 font-medium text-foreground">{template.title}</h3>
                      <p className="text-xs text-muted-foreground">{template.description}</p>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
});

export default WorkspaceHomePage;
