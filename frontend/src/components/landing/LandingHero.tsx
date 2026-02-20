'use client';

import Link from 'next/link';
import { motion, useReducedMotion } from 'motion/react';
import { ArrowRight, Github, Sparkles, FileText, Layers, Brain, Wand2, Search, Hash } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GITHUB_URL } from './constants';

const fadeUp = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
};

const stagger = {
  animate: { transition: { staggerChildren: 0.12 } },
};

export function LandingHero() {
  const shouldReduce = useReducedMotion();

  return (
    <section className="relative overflow-hidden pt-28 pb-20 lg:pt-36 lg:pb-28">
      {/* Background decorative gradient */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute top-0 left-1/2 h-[600px] w-[800px] -translate-x-1/2 rounded-full bg-primary/5 blur-3xl" />
        <div className="absolute top-20 right-1/4 h-[400px] w-[400px] rounded-full bg-ai/5 blur-3xl" />
      </div>

      <motion.div
        variants={shouldReduce ? undefined : stagger}
        initial="initial"
        animate="animate"
        className="mx-auto flex max-w-4xl flex-col items-center px-4 text-center"
      >
        {/* Badge */}
        <motion.div variants={shouldReduce ? undefined : fadeUp} transition={shouldReduce ? undefined : { duration: 0.5, ease: [0, 0, 0.2, 1] }}>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-ai/10 px-3 py-1 text-xs font-medium text-ai">
            <Sparkles className="size-3" />
            AI-Augmented SDLC Platform
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          variants={shouldReduce ? undefined : fadeUp}
          transition={shouldReduce ? undefined : { duration: 0.5, ease: [0, 0, 0.2, 1] }}
          className="mt-6 font-display text-4xl font-semibold tracking-tight text-foreground sm:text-5xl lg:text-6xl"
        >
          Think first,
          <br />
          <span className="text-primary">structure later.</span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          variants={shouldReduce ? undefined : fadeUp}
          transition={shouldReduce ? undefined : { duration: 0.5, ease: [0, 0, 0.2, 1] }}
          className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground"
        >
          The note-first platform where AI helps your ideas become structured issues naturally. No
          more form-filling before thinking is complete.
        </motion.p>

        {/* CTAs */}
        <motion.div
          variants={shouldReduce ? undefined : fadeUp}
          transition={shouldReduce ? undefined : { duration: 0.5, ease: [0, 0, 0.2, 1] }}
          className="mt-8 flex flex-col gap-3 sm:flex-row"
        >
          <Button asChild size="lg" className="gap-2">
            <Link href="/login">
              Start for Free
              <ArrowRight className="size-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="gap-2">
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
              <Github className="size-4" />
              View on GitHub
            </a>
          </Button>
        </motion.div>

        {/* Decorative Canvas Mockup */}
        <motion.div
          variants={shouldReduce ? undefined : fadeUp}
          transition={shouldReduce ? undefined : { duration: 0.6, ease: [0, 0, 0.2, 1], delay: 0.1 }}
          className="mt-16 w-full max-w-3xl"
        >
          <div className="shadow-warm-xl rounded-xl border border-border bg-card">
            {/* Fake title bar */}
            <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-2.5">
              <div className="flex gap-1.5">
                <div className="size-2.5 rounded-full bg-destructive/40" />
                <div className="size-2.5 rounded-full bg-warning/40" />
                <div className="size-2.5 rounded-full bg-primary/40" />
              </div>
              <span className="ml-2 text-xs text-muted-foreground">Sprint Planning Notes</span>
              <div className="ml-auto flex items-center gap-2">
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">Auto-saved</span>
              </div>
            </div>

            {/* Note editor content with sidebar indicators */}
            <div className="relative flex">
              {/* Line gutter */}
              <div className="hidden w-8 shrink-0 border-r border-border-subtle bg-muted/30 pt-6 sm:block">
                {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
                  <div key={n} className="px-2 text-right text-[10px] leading-[22px] text-muted-foreground/40">
                    {n}
                  </div>
                ))}
              </div>

              {/* Main content */}
              <div className="min-w-0 flex-1 space-y-3 p-6 text-left">
                <div className="font-display text-xl font-semibold text-foreground">
                  Authentication Redesign
                </div>
                <div className="space-y-2 text-sm leading-relaxed text-foreground/80">
                  <p>We need to migrate from session-based auth to JWT tokens for the mobile app.</p>
                  <p>Key considerations:</p>
                  <ul className="ml-4 list-disc space-y-1 text-foreground/70">
                    <li>Token refresh strategy (sliding window vs fixed expiry)</li>
                    <li>Backward compatibility with existing sessions</li>
                    <li>Rate limiting per user for API endpoints</li>
                  </ul>
                </div>

                {/* Ghost text suggestion */}
                <div className="text-sm text-foreground/30 italic">
                  Consider implementing a token blacklist for immediate revocation on logout and
                  password change events...
                  <span className="ml-1 inline-flex items-center rounded bg-muted px-1 py-0.5 text-[10px] font-medium not-italic text-muted-foreground">Tab ↵</span>
                </div>

                {/* Slash command menu (inline mockup) */}
                <div className="mt-2">
                  <div className="mb-1 text-sm text-muted-foreground">/</div>
                  <div className="w-64 rounded-lg border border-border bg-background shadow-warm-lg">
                    <div className="border-b border-border-subtle px-3 py-2">
                      <div className="flex items-center gap-2 rounded bg-muted/50 px-2 py-1">
                        <Search className="size-3 text-muted-foreground" />
                        <span className="text-xs text-muted-foreground">Search commands...</span>
                      </div>
                    </div>
                    <div className="p-1">
                      <div className="flex items-center gap-2.5 rounded-md bg-primary/5 px-2.5 py-2">
                        <Layers className="size-4 text-primary" />
                        <div>
                          <div className="text-xs font-medium text-foreground">Extract Issues</div>
                          <div className="text-[10px] text-muted-foreground">AI detects actionable items</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2.5 px-2.5 py-2">
                        <Wand2 className="size-4 text-ai" />
                        <div>
                          <div className="text-xs font-medium text-foreground">Improve Writing</div>
                          <div className="text-[10px] text-muted-foreground">Enhance clarity &amp; structure</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2.5 px-2.5 py-2">
                        <Brain className="size-4 text-ai" />
                        <div>
                          <div className="text-xs font-medium text-foreground">AI Context</div>
                          <div className="text-[10px] text-muted-foreground">Get code &amp; docs context</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2.5 px-2.5 py-2">
                        <FileText className="size-4 text-primary" />
                        <div>
                          <div className="text-xs font-medium text-foreground">Summarize</div>
                          <div className="text-[10px] text-muted-foreground">Create concise summary</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* AI annotation sidebar indicator */}
              <div className="hidden w-48 shrink-0 border-l border-border-subtle bg-muted/20 p-3 lg:block">
                <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  AI Annotations
                </div>
                <div className="space-y-2">
                  <div className="rounded-lg border border-ai/20 bg-ai/5 p-2">
                    <div className="flex items-center gap-1 text-[10px] font-medium text-ai">
                      <Sparkles className="size-2.5" />
                      Issue detected
                    </div>
                    <p className="mt-0.5 text-[10px] leading-tight text-muted-foreground">
                      This could be split into 3 separate issues
                    </p>
                  </div>
                  <div className="rounded-lg border border-primary/20 bg-primary/5 p-2">
                    <div className="flex items-center gap-1 text-[10px] font-medium text-primary">
                      <Hash className="size-2.5" />
                      Related: PS-42
                    </div>
                    <p className="mt-0.5 text-[10px] leading-tight text-muted-foreground">
                      Similar auth work in prior sprint
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </section>
  );
}
