'use client';

import { motion, useReducedMotion, useInView } from 'motion/react';
import { useRef } from 'react';
import {
  Sparkles,
  Layers,
  GitPullRequest,
  CheckCircle2,
  ShieldAlert,
  AlertTriangle,
  Hash,
  Pencil,
} from 'lucide-react';

// ── Step indicator ──────────────────────────────────────
const STEPS = [
  { label: 'Write', icon: Pencil },
  { label: 'AI Assists', icon: Sparkles },
  { label: 'Extract', icon: Layers },
  { label: 'Review', icon: GitPullRequest },
  { label: 'Ship', icon: CheckCircle2 },
] as const;

// ── Timing constants (seconds) ──────────────────────────
const T = {
  /** Typing starts after entering view */
  typeStart: 0.3,
  /** Total typing duration */
  typeDuration: 2.0,
  /** Ghost text appears after typing */
  ghostDelay: 2.8,
  /** Issues extract after ghost text */
  extractDelay: 4.5,
  /** Stagger between issues */
  issueStagger: 0.25,
  /** PR review appears after issues */
  reviewDelay: 6.5,
  /** Ship checkmarks after review */
  shipDelay: 8.0,
  /** Stagger between ship items */
  shipStagger: 0.2,
} as const;

// ── Fake typing text ────────────────────────────────────
const TYPED_LINES = [
  'We need to migrate from session-based auth',
  'to JWT tokens for the mobile app.',
  '',
  'Key considerations:',
  '• Token refresh strategy',
  '• Backward compatibility',
  '• Rate limiting per user',
];

const GHOST_TEXT =
  'Consider implementing a token blacklist for immediate revocation on logout and password change events...';

const EXTRACTED_ISSUES = [
  {
    id: 'PS-101',
    title: 'Implement JWT token service',
    type: 'Feature',
    typeColor: 'text-primary bg-primary/10',
    priority: 'High',
    priorityColor: 'text-amber-600 bg-amber-50',
  },
  {
    id: 'PS-102',
    title: 'Add token refresh with sliding window',
    type: 'Feature',
    typeColor: 'text-primary bg-primary/10',
    priority: 'High',
    priorityColor: 'text-amber-600 bg-amber-50',
  },
  {
    id: 'PS-103',
    title: 'Migrate existing sessions to JWT',
    type: 'Task',
    typeColor: 'text-blue-600 bg-blue-50',
    priority: 'Medium',
    priorityColor: 'text-sky-600 bg-sky-50',
  },
];

const PR_COMMENTS = [
  {
    icon: ShieldAlert,
    severity: 'Security',
    severityColor: 'text-destructive bg-destructive/10',
    message: 'Token blacklist should use Redis for O(1) lookup, not DB query',
    file: 'auth/jwt_service.py:42',
  },
  {
    icon: AlertTriangle,
    severity: 'Performance',
    severityColor: 'text-amber-600 bg-amber-50',
    message: 'Add index on token_hash column for revocation checks',
    file: 'migrations/024_jwt.py:18',
  },
];

// ── Subcomponents ───────────────────────────────────────

function TypingText({
  lines,
  startDelay,
  duration,
  shouldReduce,
}: {
  lines: string[];
  startDelay: number;
  duration: number;
  shouldReduce: boolean | null;
}) {
  const perLine = duration / lines.length;
  return (
    <div className="space-y-1 text-sm leading-relaxed text-foreground/80">
      {lines.map((line, i) => {
        if (line === '') return <div key={i} className="h-2" />;
        return (
          <motion.div
            key={i}
            initial={shouldReduce ? { opacity: 1 } : { opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: '100%' }}
            transition={
              shouldReduce
                ? undefined
                : { duration: perLine * 0.7, delay: startDelay + i * perLine }
            }
            className="overflow-hidden whitespace-nowrap"
          >
            {line}
          </motion.div>
        );
      })}
    </div>
  );
}

// ── Main Component ──────────────────────────────────────

export function LandingDemo() {
  const shouldReduce = useReducedMotion();
  const sectionRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(sectionRef, { once: true, margin: '-100px' });

  return (
    <section ref={sectionRef} className="bg-background-subtle py-24 lg:py-32">
      <div className="mx-auto max-w-4xl px-4">
        {/* Section header */}
        <motion.div
          initial={shouldReduce ? undefined : { opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : undefined}
          transition={shouldReduce ? undefined : { duration: 0.5 }}
          className="mb-8 text-center"
        >
          <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
            <Sparkles className="size-3" />
            See it in action
          </span>
          <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            From idea to shipped — in one flow
          </h2>
          <p className="mt-3 text-muted-foreground">
            Watch how the &ldquo;Auth Redesign&rdquo; feature flows through
            Pilot Space
          </p>
        </motion.div>

        {/* Step indicator */}
        {isInView && (
          <StepTimeline shouldReduce={shouldReduce} />
        )}

        {/* Demo window */}
        <motion.div
          initial={shouldReduce ? undefined : { opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : undefined}
          transition={
            shouldReduce ? undefined : { duration: 0.5, delay: 0.2 }
          }
          className="rounded-2xl border border-border bg-card shadow-warm-xl"
        >
          {/* Title bar */}
          <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-2.5">
            <div className="flex gap-1.5">
              <div className="size-2.5 rounded-full bg-destructive/40" />
              <div className="size-2.5 rounded-full bg-warning/40" />
              <div className="size-2.5 rounded-full bg-primary/40" />
            </div>
            <span className="ml-2 text-xs text-muted-foreground">
              Pilot Space — Auth Redesign Demo
            </span>
          </div>

          {/* Content area */}
          <div className="p-6 lg:p-8">
            {isInView && (
              <DemoContent shouldReduce={shouldReduce} />
            )}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ── Step timeline with auto-advancing indicator ─────────

function StepTimeline({
  shouldReduce,
}: {
  shouldReduce: boolean | null;
}) {
  return (
    <div className="mb-6 flex items-center justify-center gap-1 sm:gap-2">
      {STEPS.map((step, i) => {
        const delay = [0, T.ghostDelay, T.extractDelay, T.reviewDelay, T.shipDelay][i];
        return (
          <div key={step.label} className="flex items-center gap-1 sm:gap-2">
            <motion.div
              initial={
                shouldReduce
                  ? { opacity: 1, scale: 1 }
                  : { opacity: 0.35, scale: 1 }
              }
              animate={{ opacity: 1, scale: [1, 1.1, 1] }}
              transition={
                shouldReduce
                  ? undefined
                  : {
                      opacity: { duration: 0.3, delay },
                      scale: { duration: 0.4, delay },
                    }
              }
              className="flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary"
            >
              <step.icon className="size-3" />
              <span className="hidden sm:inline">{step.label}</span>
            </motion.div>
            {i < STEPS.length - 1 && (
              <motion.div
                initial={shouldReduce ? undefined : { scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={
                  shouldReduce
                    ? undefined
                    : {
                        duration: 0.5,
                        delay: [T.ghostDelay, T.extractDelay, T.reviewDelay, T.shipDelay][i],
                      }
                }
                className="h-px w-3 origin-left bg-primary/40 sm:w-6"
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Demo content with sequenced animations ──────────────

function DemoContent({
  shouldReduce,
}: {
  shouldReduce: boolean | null;
}) {
  return (
    <div className="space-y-6">
      {/* ─── Step 1: Writing ─────────────────────────── */}
      <div>
        <div className="mb-3 font-display text-lg font-semibold text-foreground">
          Authentication Redesign
        </div>
        <TypingText
          lines={TYPED_LINES}
          startDelay={T.typeStart}
          duration={T.typeDuration}
          shouldReduce={shouldReduce}
        />
      </div>

      {/* ─── Step 2: Ghost Text ──────────────────────── */}
      <motion.div
        initial={shouldReduce ? { opacity: 1 } : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={
          shouldReduce
            ? undefined
            : { duration: 0.6, delay: T.ghostDelay }
        }
        className="flex items-start gap-2 rounded-lg border border-ai/20 bg-ai/5 p-3"
      >
        <Sparkles className="mt-0.5 size-4 shrink-0 text-ai" />
        <div>
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-ai">
            Ghost Text Suggestion
          </div>
          <p className="text-sm italic text-foreground/40">{GHOST_TEXT}</p>
          <span className="mt-1 inline-flex items-center rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
            Tab ↵ to accept
          </span>
        </div>
      </motion.div>

      {/* ─── Step 3: Issue Extraction ────────────────── */}
      <motion.div
        initial={shouldReduce ? { opacity: 1 } : { opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={
          shouldReduce
            ? undefined
            : { duration: 0.4, delay: T.extractDelay }
        }
      >
        <div className="mb-3 flex items-center gap-2">
          <Layers className="size-4 text-primary" />
          <span className="text-sm font-semibold text-foreground">
            AI extracted 3 issues
          </span>
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
            Auto-detected
          </span>
        </div>
        <div className="space-y-2">
          {EXTRACTED_ISSUES.map((issue, i) => (
            <motion.div
              key={issue.id}
              initial={
                shouldReduce ? { opacity: 1 } : { opacity: 0, x: -16, scale: 0.95 }
              }
              animate={{ opacity: 1, x: 0, scale: 1 }}
              transition={
                shouldReduce
                  ? undefined
                  : {
                      duration: 0.4,
                      delay: T.extractDelay + 0.3 + i * T.issueStagger,
                      ease: [0.34, 1.56, 0.64, 1],
                    }
              }
              className="flex items-center gap-3 rounded-lg border border-border bg-background p-3 transition-shadow hover:shadow-warm-sm"
            >
              <Hash className="size-4 shrink-0 text-primary" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-primary">
                    {issue.id}
                  </span>
                  <span className="truncate text-sm font-medium text-foreground">
                    {issue.title}
                  </span>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${issue.typeColor}`}
                >
                  {issue.type}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${issue.priorityColor}`}
                >
                  {issue.priority}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* ─── Step 4: PR Review ───────────────────────── */}
      <motion.div
        initial={shouldReduce ? { opacity: 1 } : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={
          shouldReduce
            ? undefined
            : { duration: 0.5, delay: T.reviewDelay }
        }
      >
        <div className="mb-3 flex items-center gap-2">
          <GitPullRequest className="size-4 text-purple-600" />
          <span className="text-sm font-semibold text-foreground">
            AI PR Review — PR #142
          </span>
          <span className="rounded-full bg-purple-50 px-2 py-0.5 text-[10px] font-medium text-purple-600">
            2 findings
          </span>
        </div>
        <div className="space-y-2">
          {PR_COMMENTS.map((comment, i) => (
            <motion.div
              key={comment.file}
              initial={
                shouldReduce
                  ? { opacity: 1 }
                  : { opacity: 0, x: -12 }
              }
              animate={
                shouldReduce
                  ? undefined
                  : {
                      opacity: 1,
                      x: 0,
                      boxShadow: [
                        '0 0 0px transparent',
                        '0 0 16px rgba(147,51,234,0.15)',
                        '0 0 0px transparent',
                      ],
                    }
              }
              transition={
                shouldReduce
                  ? undefined
                  : {
                      duration: 0.5,
                      delay: T.reviewDelay + 0.3 + i * 0.25,
                      boxShadow: {
                        duration: 1.0,
                        delay: T.reviewDelay + 0.5 + i * 0.25,
                      },
                    }
              }
              className="rounded-lg border border-border bg-background p-3"
            >
              <div className="mb-1.5 flex items-center gap-2">
                <comment.icon className="size-3.5 text-destructive" />
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${comment.severityColor}`}
                >
                  {comment.severity}
                </span>
                <span className="text-[10px] text-muted-foreground">
                  {comment.file}
                </span>
              </div>
              <p className="text-xs leading-relaxed text-foreground/80">
                {comment.message}
              </p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* ─── Step 5: Ship ────────────────────────────── */}
      <motion.div
        initial={shouldReduce ? { opacity: 1 } : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={
          shouldReduce
            ? undefined
            : { duration: 0.5, delay: T.shipDelay }
        }
        className="rounded-xl border border-primary/20 bg-primary/5 p-4"
      >
        <div className="mb-3 flex items-center gap-2">
          <CheckCircle2 className="size-5 text-primary" />
          <span className="text-sm font-semibold text-foreground">
            Sprint Complete — Auth Redesign
          </span>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          {[
            { label: '3 issues shipped', delay: 0 },
            { label: '2 security fixes applied', delay: 1 },
            { label: '0 post-deploy incidents', delay: 2 },
          ].map((item, i) => (
            <motion.div
              key={item.label}
              initial={
                shouldReduce ? { opacity: 1 } : { opacity: 0, scale: 0.8 }
              }
              animate={{ opacity: 1, scale: 1 }}
              transition={
                shouldReduce
                  ? undefined
                  : {
                      duration: 0.35,
                      delay: T.shipDelay + 0.3 + i * T.shipStagger,
                      ease: [0.34, 1.56, 0.64, 1],
                    }
              }
              className="flex items-center gap-2 rounded-lg bg-background/80 px-3 py-2"
            >
              <CheckCircle2 className="size-3.5 text-primary" />
              <span className="text-xs font-medium text-foreground">
                {item.label}
              </span>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
