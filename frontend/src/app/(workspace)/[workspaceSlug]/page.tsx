'use client';

import { motion } from 'motion/react';
import {
  Compass,
  FileText,
  Sparkles,
  ArrowRight,
  Lightbulb,
  Zap,
  MessageSquare,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

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

export default function WorkspaceHomePage(_props: WorkspaceHomePageProps) {
  // params will be used in Phase 3 (US1) for workspace-specific data loading
  // void _props.params;
  return (
    <div className="flex h-full flex-col items-center justify-center px-8 py-16">
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

        {/* Main CTA */}
        <motion.div variants={fadeUp} className="mb-12 w-full max-w-lg">
          <div className="group relative">
            <div className="absolute -inset-1 rounded-xl bg-gradient-to-r from-primary/20 via-ai/20 to-primary/20 opacity-0 blur-lg transition-opacity group-hover:opacity-100" />
            <div
              className={cn(
                'relative flex items-center gap-3 rounded-xl border border-input bg-card px-5 py-4',
                'shadow-warm transition-all duration-300',
                'hover:border-primary/30 hover:shadow-warm-md',
                'focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20'
              )}
            >
              <Sparkles className="h-5 w-5 text-ai" />
              <input
                type="text"
                placeholder="Describe your idea, problem, or topic..."
                className="flex-1 bg-transparent text-base text-foreground placeholder:text-muted-foreground focus:outline-none"
              />
              <Button size="sm" className="gap-1.5 shadow-warm-sm">
                <span>Start</span>
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </motion.div>

        {/* Templates */}
        <motion.div variants={fadeUp}>
          <p className="mb-4 text-sm font-medium text-muted-foreground">Or start with a template</p>
          <div className="grid gap-3 sm:grid-cols-3">
            {templates.map((template, index) => (
              <motion.div
                key={template.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + index * 0.1 }}
              >
                <Card
                  className={cn(
                    'group cursor-pointer border-border/50 bg-card/50',
                    'transition-all duration-200',
                    'hover:border-border hover:bg-card hover:shadow-warm-md hover:-translate-y-0.5'
                  )}
                >
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

        {/* Recent Notes */}
        <motion.div variants={fadeUp} className="mt-12 w-full max-w-lg">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground">Recent notes</p>
            <Button variant="ghost" size="sm" className="text-primary">
              View all
            </Button>
          </div>
          <div className="mt-3 space-y-2">
            {[
              { title: 'Auth Refactor Planning', time: '2 hours ago' },
              { title: 'API Design Discussion', time: 'Yesterday' },
              { title: 'Sprint 12 Retrospective', time: '3 days ago' },
            ].map((note, index) => (
              <motion.div
                key={note.title}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 + index * 0.1 }}
              >
                <div
                  className={cn(
                    'group flex items-center gap-3 rounded-lg border border-transparent px-4 py-3',
                    'cursor-pointer transition-all duration-200',
                    'hover:border-border/50 hover:bg-accent/50'
                  )}
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-md bg-muted">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground transition-colors group-hover:text-primary">
                      {note.title}
                    </p>
                    <p className="text-xs text-muted-foreground">{note.time}</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Blank Note Link */}
        <motion.div variants={fadeUp} className="mt-8">
          <Button variant="ghost" className="text-muted-foreground hover:text-foreground">
            <FileText className="mr-2 h-4 w-4" />
            Start with a blank note
          </Button>
        </motion.div>
      </motion.div>
    </div>
  );
}
