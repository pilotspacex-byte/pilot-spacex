'use client';

import { useRef } from 'react';
import { motion, useReducedMotion, useInView } from 'motion/react';
import {
  Terminal,
  Sparkles,
  Copy,
  CheckCircle2,
  FileCode2,
  Brain,
  ArrowRight,
  Hash,
} from 'lucide-react';
import { FadeIn } from './FadeIn';

// ── Timing constants ────────────────────────────────────
const T = {
  issueAppear: 0.3,
  contextGenerate: 2.0,
  promptReveal: 3.8,
  promptTyping: 4.5,
  outputAppear: 7.0,
  outputStagger: 0.2,
} as const;

// ── Step 1: Issue card mockup ───────────────────────────
function IssueCardMockup({ shouldReduce }: { shouldReduce: boolean | null }) {
  return (
    <motion.div
      initial={shouldReduce ? undefined : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={shouldReduce ? undefined : { duration: 0.5, delay: T.issueAppear }}
      className="rounded-xl border border-border bg-card p-4 shadow-warm-sm"
    >
      <div className="mb-3 flex items-center gap-2">
        <Hash className="size-4 text-primary" />
        <span className="text-sm font-bold text-primary">PS-42</span>
        <span className="text-sm font-semibold text-foreground">
          Implement JWT token service
        </span>
      </div>
      <div className="mb-3 flex flex-wrap gap-1.5">
        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
          Feature
        </span>
        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-600">
          High Priority
        </span>
        <span className="rounded-full bg-purple-50 px-2 py-0.5 text-[10px] font-medium text-purple-600">
          In Progress
        </span>
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">
        Create JWT token service with sliding window refresh, token blacklist
        for revocation, and backward compatibility with existing sessions.
      </p>
    </motion.div>
  );
}

// ── Step 2: AI Context generation ───────────────────────
function AIContextMockup({ shouldReduce }: { shouldReduce: boolean | null }) {
  return (
    <motion.div
      initial={shouldReduce ? undefined : { opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={shouldReduce ? undefined : { duration: 0.5, delay: T.contextGenerate }}
      className="rounded-xl border border-ai/20 bg-ai/5 p-4"
    >
      <div className="mb-3 flex items-center gap-2">
        <Brain className="size-4 text-ai" />
        <span className="text-sm font-semibold text-foreground">
          AI Context Generated
        </span>
        <motion.span
          initial={shouldReduce ? undefined : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={shouldReduce ? undefined : { delay: T.contextGenerate + 0.3 }}
          className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary"
        >
          Auto-generated
        </motion.span>
      </div>
      <div className="space-y-2 text-xs">
        <div className="flex items-start gap-2">
          <FileCode2 className="mt-0.5 size-3 shrink-0 text-primary" />
          <div>
            <span className="font-medium text-foreground">3 related files</span>
            <p className="text-muted-foreground">
              auth/session.py, middleware/auth.py, models/user.py
            </p>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <Hash className="mt-0.5 size-3 shrink-0 text-primary" />
          <div>
            <span className="font-medium text-foreground">2 related issues</span>
            <p className="text-muted-foreground">PS-38 Rate limiting, PS-40 Auth middleware</p>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <Sparkles className="mt-0.5 size-3 shrink-0 text-ai" />
          <div>
            <span className="font-medium text-foreground">4 implementation tasks</span>
            <p className="text-muted-foreground">
              Token model, refresh endpoint, blacklist service, migration
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ── Step 3: Claude Code terminal ────────────────────────
const PROMPT_LINES = [
  { text: '## Issue: PS-42 — Implement JWT token service', style: 'text-blue-400' },
  { text: '', style: '' },
  { text: '## Context', style: 'text-blue-400' },
  { text: 'Migrate from session-based auth to JWT.', style: 'text-slate-300' },
  { text: 'Related: auth/session.py, middleware/auth.py', style: 'text-green-400' },
  { text: '', style: '' },
  { text: '## Implementation Tasks', style: 'text-blue-400' },
  { text: '1. Create JWTTokenService in auth/jwt_service.py', style: 'text-yellow-300' },
  { text: '2. Add /auth/refresh endpoint with sliding window', style: 'text-yellow-300' },
  { text: '3. Implement token blacklist with Redis O(1) lookup', style: 'text-yellow-300' },
  { text: '4. Add Alembic migration for token table', style: 'text-yellow-300' },
  { text: '', style: '' },
  { text: '## Instructions', style: 'text-blue-400' },
  { text: 'Follow existing patterns in auth/ directory.', style: 'text-slate-300' },
  { text: 'Use dependency-injector for DI. Add pytest tests.', style: 'text-slate-300' },
];

function TerminalMockup({ shouldReduce }: { shouldReduce: boolean | null }) {
  const lineDelay = 0.08;

  return (
    <motion.div
      initial={shouldReduce ? undefined : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={shouldReduce ? undefined : { duration: 0.5, delay: T.promptReveal }}
      className="overflow-hidden rounded-xl border border-slate-700 bg-slate-950 shadow-warm-lg"
    >
      {/* Terminal header */}
      <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-2.5">
        <div className="flex gap-1.5">
          <div className="size-2.5 rounded-full bg-red-500/60" />
          <div className="size-2.5 rounded-full bg-yellow-500/60" />
          <div className="size-2.5 rounded-full bg-green-500/60" />
        </div>
        <div className="flex items-center gap-1.5">
          <Terminal className="size-3 text-slate-400" />
          <span className="text-[11px] text-slate-400">Claude Code</span>
        </div>
        <motion.div
          initial={shouldReduce ? undefined : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={shouldReduce ? undefined : { delay: T.promptReveal + 0.5 }}
          className="ml-auto flex items-center gap-1.5"
        >
          <Copy className="size-3 text-green-400" />
          <span className="text-[10px] text-green-400">Pasted from Pilot Space</span>
        </motion.div>
      </div>

      {/* Terminal content */}
      <div className="p-4 font-mono text-[11px] leading-relaxed sm:text-xs">
        {/* Prompt command */}
        <motion.div
          initial={shouldReduce ? undefined : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={shouldReduce ? undefined : { delay: T.promptTyping }}
          className="mb-3"
        >
          <span className="text-green-400">❯ </span>
          <span className="text-slate-300">claude</span>
          <span className="text-slate-500"> &quot;Implement PS-42&quot;</span>
        </motion.div>

        {/* Prompt content lines */}
        <div className="space-y-0.5 border-l-2 border-slate-700 pl-3">
          {PROMPT_LINES.map((line, i) => (
            <motion.div
              key={i}
              initial={shouldReduce ? undefined : { opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={
                shouldReduce
                  ? undefined
                  : { duration: 0.2, delay: T.promptTyping + 0.3 + i * lineDelay }
              }
              className={line.style || 'h-3'}
            >
              {line.text}
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

// ── Step 4: Implementation output ───────────────────────
const OUTPUT_FILES = [
  { file: 'auth/jwt_service.py', action: 'Created', lines: '+142' },
  { file: 'api/v1/routers/auth.py', action: 'Modified', lines: '+38' },
  { file: 'auth/token_blacklist.py', action: 'Created', lines: '+67' },
  { file: 'migrations/025_jwt_tokens.py', action: 'Created', lines: '+24' },
  { file: 'tests/test_jwt_service.py', action: 'Created', lines: '+89' },
];

function OutputMockup({ shouldReduce }: { shouldReduce: boolean | null }) {
  return (
    <motion.div
      initial={shouldReduce ? undefined : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={shouldReduce ? undefined : { duration: 0.5, delay: T.outputAppear }}
      className="rounded-xl border border-primary/20 bg-primary/5 p-4"
    >
      <div className="mb-3 flex items-center gap-2">
        <CheckCircle2 className="size-4 text-primary" />
        <span className="text-sm font-semibold text-foreground">
          Implementation Complete
        </span>
      </div>
      <div className="space-y-1.5">
        {OUTPUT_FILES.map((f, i) => (
          <motion.div
            key={f.file}
            initial={shouldReduce ? undefined : { opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={
              shouldReduce
                ? undefined
                : {
                    duration: 0.3,
                    delay: T.outputAppear + 0.3 + i * T.outputStagger,
                    ease: [0.34, 1.56, 0.64, 1],
                  }
            }
            className="flex items-center gap-2 rounded-lg bg-background/80 px-3 py-2"
          >
            <FileCode2 className="size-3.5 text-primary" />
            <code className="flex-1 text-[11px] text-foreground/80">
              {f.file}
            </code>
            <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
              {f.action}
            </span>
            <span className="text-[10px] text-muted-foreground">{f.lines}</span>
          </motion.div>
        ))}
      </div>
      <motion.div
        initial={shouldReduce ? undefined : { opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={
          shouldReduce
            ? undefined
            : { delay: T.outputAppear + 1.5 }
        }
        className="mt-3 flex items-center justify-between rounded-lg bg-background/80 px-3 py-2"
      >
        <span className="text-xs font-medium text-foreground">
          5 files changed, 360 insertions
        </span>
        <span className="flex items-center gap-1 text-[10px] font-medium text-primary">
          <CheckCircle2 className="size-3" />
          All tests passing
        </span>
      </motion.div>
    </motion.div>
  );
}

// ── Step indicators ─────────────────────────────────────
const DEMO_STEPS = [
  { label: 'Pick Issue', icon: Hash, delay: T.issueAppear },
  { label: 'AI Context', icon: Brain, delay: T.contextGenerate },
  { label: 'Claude Code', icon: Terminal, delay: T.promptReveal },
  { label: 'Implemented', icon: CheckCircle2, delay: T.outputAppear },
] as const;

function StepTimeline({ shouldReduce }: { shouldReduce: boolean | null }) {
  return (
    <div className="mb-6 flex items-center justify-center gap-1 sm:gap-2">
      {DEMO_STEPS.map((step, i) => (
        <div key={step.label} className="flex items-center gap-1 sm:gap-2">
          <motion.div
            initial={shouldReduce ? { opacity: 1 } : { opacity: 0.35 }}
            animate={{ opacity: 1, scale: [1, 1.1, 1] }}
            transition={
              shouldReduce
                ? undefined
                : { opacity: { duration: 0.3, delay: step.delay }, scale: { duration: 0.4, delay: step.delay } }
            }
            className="flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary"
          >
            <step.icon className="size-3" />
            <span className="hidden sm:inline">{step.label}</span>
          </motion.div>
          {i < DEMO_STEPS.length - 1 && (
            <motion.div
              initial={shouldReduce ? undefined : { scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={
                shouldReduce
                  ? undefined
                  : { duration: 0.5, delay: DEMO_STEPS[i + 1]!.delay }
              }
              className="h-px w-3 origin-left bg-primary/40 sm:w-6"
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ── Main section ────────────────────────────────────────
export function LandingClaudeCode() {
  const shouldReduce = useReducedMotion();
  const sectionRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(sectionRef, { once: true, margin: '-100px' });

  return (
    <section ref={sectionRef} id="claude-code" className="py-20 lg:py-24">
      <div className="mx-auto max-w-4xl px-4">
        <FadeIn className="mb-8 text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
            <Terminal className="size-3" />
            Claude Code Integration
          </span>
          <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            From issue to implementation in one prompt
          </h2>
          <p className="mt-3 text-lg text-muted-foreground">
            Every issue gets a ready-to-use Claude Code prompt with full
            project context — paste and implement
          </p>
        </FadeIn>

        {isInView && (
          <>
            <StepTimeline shouldReduce={shouldReduce} />

            <div className="space-y-4">
              {/* Row 1: Issue + AI Context side by side */}
              <div className="grid gap-4 lg:grid-cols-2">
                <IssueCardMockup shouldReduce={shouldReduce} />
                <AIContextMockup shouldReduce={shouldReduce} />
              </div>

              {/* Row 2: Arrow */}
              <motion.div
                initial={shouldReduce ? undefined : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={shouldReduce ? undefined : { delay: T.promptReveal - 0.3 }}
                className="flex justify-center"
              >
                <ArrowRight className="size-5 rotate-90 text-primary/40" />
              </motion.div>

              {/* Row 3: Terminal */}
              <TerminalMockup shouldReduce={shouldReduce} />

              {/* Row 4: Arrow */}
              <motion.div
                initial={shouldReduce ? undefined : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={shouldReduce ? undefined : { delay: T.outputAppear - 0.3 }}
                className="flex justify-center"
              >
                <ArrowRight className="size-5 rotate-90 text-primary/40" />
              </motion.div>

              {/* Row 5: Output */}
              <OutputMockup shouldReduce={shouldReduce} />
            </div>

            {/* Bottom callout */}
            <FadeIn className="mt-8 text-center" delay={0.5}>
              <p className="text-sm text-muted-foreground">
                <span className="font-semibold text-foreground">Zero context-switching</span>{' '}
                — AI analyzes your issue, gathers related code and docs, builds a
                prompt with implementation tasks, and Claude Code executes it.{' '}
                <span className="font-medium text-primary">
                  BYOK — use your own API key
                </span>
              </p>
            </FadeIn>
          </>
        )}
      </div>
    </section>
  );
}
