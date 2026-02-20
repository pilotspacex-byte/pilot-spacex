'use client';

import { motion, useReducedMotion } from 'motion/react';
import {
  Lightbulb,
  FileText,
  Code2,
  GitPullRequest,
  Rocket,
  BarChart3,
  Sparkles,
  ArrowDown,
  ArrowRight,
  Clock,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { FadeIn } from './FadeIn';

interface AIStage {
  icon: LucideIcon;
  phase: string;
  color: string;
  bgColor: string;
  borderColor: string;
  glowColor: string;
  traditional: string;
  withAI: string;
  aiTools: string[];
  highlight: string;
  legacyTime: string;
  aiTime: string;
  savings: number;
}

// glowColor uses inline rgba() in Tailwind arbitrary shadow values because
// Tailwind does not support animated drop-shadows natively. These are applied
// as static hover/focus glows via the shadow utility, not as motion keyframes.
const aiStages: AIStage[] = [
  {
    icon: Lightbulb,
    phase: 'Plan & Capture',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    glowColor: 'shadow-[0_0_20px_rgba(234,179,8,0.15)]',
    traditional:
      'Brainstorm in Slack/Notion, then manually transcribe into Jira tickets',
    withAI:
      'Write freely in Note Canvas — AI ghost text completes your thoughts, extracts issues automatically',
    aiTools: ['Ghost Text', 'Issue Extraction', 'Note-First Workflow'],
    highlight: 'Ideas become tickets without form-filling',
    legacyTime: '2–3 days',
    aiTime: '~1 day',
    savings: 60,
  },
  {
    icon: FileText,
    phase: 'Design & Architect',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    glowColor: 'shadow-[0_0_20px_rgba(59,130,246,0.15)]',
    traditional:
      'Manual architecture docs, searching codebase for patterns and precedents',
    withAI:
      'AI Context surfaces relevant code, docs, and patterns. Architecture analysis catches issues early',
    aiTools: ['AI Context', 'Architecture Analysis', 'Multi-Turn Chat'],
    highlight: 'Full context at your fingertips before writing code',
    legacyTime: '1–2 days',
    aiTime: 'half day',
    savings: 50,
  },
  {
    icon: Code2,
    phase: 'Develop & Build',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    glowColor: 'shadow-[0_0_20px_rgba(16,185,129,0.15)]',
    traditional:
      'Copy-paste from Stack Overflow, context-switch between docs and IDE',
    withAI:
      'Ghost text assists coding. Per-issue Claude Code prompts with full project context are ready to use',
    aiTools: ['Ghost Text', 'Claude Code Prompts', 'Task Decomposition'],
    highlight: 'AI pair programming with project context',
    legacyTime: '5–8 days',
    aiTime: '3–5 days',
    savings: 40,
  },
  {
    icon: GitPullRequest,
    phase: 'Review & QA',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    glowColor: 'shadow-[0_0_20px_rgba(147,51,234,0.15)]',
    traditional:
      'Manual PR review — reviewer has limited context, misses cross-cutting concerns',
    withAI:
      'AI does the first review pass: security, performance, architecture patterns. Human reviewer focuses on business logic',
    aiTools: ['AI PR Review', 'Security Analysis', 'Severity Tags'],
    highlight: 'Every PR reviewed for security and architecture',
    legacyTime: '1–2 days',
    aiTime: '2–4 hours',
    savings: 75,
  },
  {
    icon: Rocket,
    phase: 'Release & Deploy',
    color: 'text-rose-600',
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-200',
    glowColor: 'shadow-[0_0_20px_rgba(244,63,94,0.15)]',
    traditional:
      'Manual release notes, hope nothing was missed in review',
    withAI:
      'Quality gates validated, task completion tracked, release notes generated from merged PRs',
    aiTools: ['Quality Gates', 'Task Tracking', 'Doc Generation'],
    highlight: 'Confidence in every release',
    legacyTime: '1 day',
    aiTime: 'half day',
    savings: 50,
  },
  {
    icon: BarChart3,
    phase: 'Measure & Learn',
    color: 'text-sky-600',
    bgColor: 'bg-sky-50',
    borderColor: 'border-sky-200',
    glowColor: 'shadow-[0_0_20px_rgba(14,165,233,0.15)]',
    traditional:
      'Manual velocity spreadsheets, retrospective meetings with incomplete data',
    withAI:
      'Real-time velocity tracking, AI cost insights per feature, cycle analytics with burndown charts',
    aiTools: ['Velocity Tracking', 'Cost Insights', 'Cycle Analytics'],
    highlight: 'Data-driven decisions, not guesses',
    legacyTime: '4 hours',
    aiTime: 'Real-time',
    savings: 80,
  },
];

// Animation timing constants
const CARD_STAGGER = 0.15;
const INNER_DELAY = 0.4;
const PILL_DELAY = 0.7;
const PILL_STAGGER = 0.06;

function AIStageCard({
  stage,
  index,
  isLast,
  shouldReduce,
}: {
  stage: AIStage;
  index: number;
  isLast: boolean;
  shouldReduce: boolean | null;
}) {
  const baseDelay = index * CARD_STAGGER;

  return (
    <>
      {/* Card entrance: staggered slide-up */}
      <motion.div
        initial={shouldReduce ? undefined : { opacity: 0, y: 32 }}
        whileInView={shouldReduce ? undefined : { opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-60px' }}
        transition={
          shouldReduce
            ? undefined
            : { duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: baseDelay }
        }
        className={`relative rounded-2xl border ${stage.borderColor} bg-card p-6 transition-shadow hover:shadow-warm-md`}
      >
        {/* Header */}
        <div className="mb-4 flex items-center gap-3">
          <motion.div
            initial={shouldReduce ? undefined : { scale: 0.5, opacity: 0 }}
            whileInView={shouldReduce ? undefined : { scale: 1, opacity: 1 }}
            viewport={{ once: true }}
            transition={
              shouldReduce
                ? undefined
                : {
                    duration: 0.4,
                    ease: [0.34, 1.56, 0.64, 1],
                    delay: baseDelay + 0.1,
                  }
            }
            className={`flex size-11 items-center justify-center rounded-xl ${stage.bgColor}`}
          >
            <stage.icon className={`size-5 ${stage.color}`} />
          </motion.div>
          <div>
            <h3 className="text-base font-semibold text-foreground">
              {stage.phase}
            </h3>
            <p className={`text-xs font-medium ${stage.color}`}>
              {stage.highlight}
            </p>
          </div>
        </div>

        {/* Before / After comparison with cross-fade + glow */}
        <div className="grid gap-3 sm:grid-cols-2">
          {/* Traditional — appears first */}
          <motion.div
            initial={shouldReduce ? undefined : { opacity: 0, x: -12 }}
            whileInView={shouldReduce ? undefined : { opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={
              shouldReduce
                ? undefined
                : { duration: 0.4, delay: baseDelay + INNER_DELAY }
            }
            className="rounded-lg bg-destructive/5 p-3"
          >
            <div className="mb-1.5 flex items-center gap-1.5">
              <div className="size-1.5 rounded-full bg-destructive/40" />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-destructive/70">
                Without AI
              </span>
            </div>
            <p className="text-xs leading-relaxed text-muted-foreground">
              {stage.traditional}
            </p>
          </motion.div>

          {/* With Pilot Space — cross-fades in with glow */}
          <motion.div
            initial={
              shouldReduce
                ? undefined
                : { opacity: 0, x: 12, boxShadow: '0 0 0px transparent' }
            }
            whileInView={
              shouldReduce
                ? undefined
                : {
                    opacity: 1,
                    x: 0,
                    boxShadow: [
                      '0 0 0px transparent',
                      '0 0 24px rgba(41,163,134,0.25)',
                      '0 0 0px transparent',
                    ],
                  }
            }
            viewport={{ once: true }}
            transition={
              shouldReduce
                ? undefined
                : {
                    duration: 0.8,
                    delay: baseDelay + INNER_DELAY + 0.3,
                    ease: [0.16, 1, 0.3, 1],
                    boxShadow: { duration: 1.2, delay: baseDelay + INNER_DELAY + 0.3 },
                  }
            }
            className="rounded-lg bg-primary/5 p-3"
          >
            <div className="mb-1.5 flex items-center gap-1.5">
              <Sparkles className="size-3 text-primary" />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">
                With Pilot Space
              </span>
            </div>
            <p className="text-xs leading-relaxed text-foreground/80">
              {stage.withAI}
            </p>
          </motion.div>
        </div>

        {/* AI Tools pills — pop-in stagger with bounce */}
        <div className="mt-3 flex flex-wrap gap-1.5">
          {stage.aiTools.map((tool, toolIndex) => (
            <motion.span
              key={tool}
              initial={shouldReduce ? undefined : { scale: 0, opacity: 0 }}
              whileInView={shouldReduce ? undefined : { scale: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={
                shouldReduce
                  ? undefined
                  : {
                      duration: 0.35,
                      ease: [0.34, 1.56, 0.64, 1],
                      delay:
                        baseDelay + PILL_DELAY + toolIndex * PILL_STAGGER,
                    }
              }
              className="inline-flex items-center gap-1 rounded-full border border-border bg-background px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
            >
              <Sparkles className="size-2.5 text-ai" />
              {tool}
            </motion.span>
          ))}
        </div>

        {/* Time savings bar */}
        <div className="mt-3 flex items-center gap-3 rounded-lg bg-muted/50 px-3 py-2">
          <Clock className="size-3.5 text-muted-foreground" />
          <div className="flex-1">
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground line-through">{stage.legacyTime}</span>
              <ArrowRight className="size-3 text-muted-foreground/40" />
              <span className="font-semibold text-primary">{stage.aiTime}</span>
            </div>
          </div>
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary">-{stage.savings}%</span>
        </div>
      </motion.div>

      {/* Arrow connector — fade in + pulse glow downward */}
      {!isLast && (
        <div className="flex justify-center py-1.5">
          <motion.div
            initial={shouldReduce ? undefined : { opacity: 0, y: -4 }}
            whileInView={
              shouldReduce
                ? undefined
                : {
                    opacity: 1,
                    y: 0,
                    filter: [
                      'drop-shadow(0 0px 0px transparent)',
                      'drop-shadow(0 2px 6px rgba(41,163,134,0.4))',
                      'drop-shadow(0 0px 0px transparent)',
                    ],
                  }
            }
            viewport={{ once: true }}
            transition={
              shouldReduce
                ? undefined
                : {
                    duration: 0.8,
                    delay: baseDelay + 0.9,
                    ease: 'easeOut',
                    filter: {
                      duration: 0.8,
                      delay: baseDelay + 1.0,
                      ease: 'easeInOut',
                    },
                  }
            }
          >
            <ArrowDown className="size-5 text-primary/50" />
          </motion.div>
        </div>
      )}
    </>
  );
}

export function LandingAIFlow() {
  const shouldReduce = useReducedMotion();

  return (
    <section id="ai-flow" className="bg-background-subtle py-24 lg:py-32">
      <div className="mx-auto max-w-3xl px-4">
        <FadeIn className="mb-14 text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-ai/10 px-3 py-1 text-xs font-medium text-ai">
            <Sparkles className="size-3" />
            AI-Augmented Workflow
          </span>
          <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            How AI transforms every SDLC stage
          </h2>
          <p className="mt-3 text-lg text-muted-foreground">
            See exactly where AI assists your team — from the first idea to
            production metrics
          </p>
        </FadeIn>

        <div className="flex flex-col">
          {aiStages.map((stage, i) => (
            <AIStageCard
              key={stage.phase}
              stage={stage}
              index={i}
              isLast={i === aiStages.length - 1}
              shouldReduce={shouldReduce}
            />
          ))}
        </div>

        <FadeIn className="mt-6 flex flex-col items-center gap-3 rounded-2xl border border-primary/20 bg-primary/5 p-5 sm:flex-row sm:justify-between" delay={0.3}>
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-full bg-primary/10">
              <Zap className="size-5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">Full sprint cycle</p>
              <p className="text-xs text-muted-foreground">
                <span className="line-through">10–16 days</span>
                <ArrowRight className="mx-1.5 inline size-3" />
                <span className="font-semibold text-primary">5–9 days</span>
              </p>
            </div>
          </div>
          <div className="text-center sm:text-right">
            <span className="text-2xl font-bold text-primary">up to 50%</span>
            <p className="text-xs text-muted-foreground">faster to production</p>
          </div>
        </FadeIn>
        <p className="mt-2 text-center text-[11px] text-muted-foreground/70">
          * Estimates based on typical 5–15 person engineering teams. Individual results vary.
        </p>
      </div>
    </section>
  );
}
