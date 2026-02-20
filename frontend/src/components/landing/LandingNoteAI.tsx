'use client';

import { useRef, useState, useCallback, useEffect } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import {
  Sparkles,
  MessageSquare,
  Layers,
  Wand2,
  Eye,
  Shield,
  Slash,
  PenTool,
  ChevronLeft,
  ChevronRight,
  type LucideIcon,
} from 'lucide-react';
import { FadeIn } from './FadeIn';

// ── Feature data ────────────────────────────────────────

interface NoteFeature {
  icon: LucideIcon;
  name: string;
  tagline: string;
  description: string;
  model: string;
  modelColor: string;
  badge: string;
  badgeColor: string;
  preview: React.ReactNode;
}

const features: NoteFeature[] = [
  {
    icon: Sparkles,
    name: 'Ghost Text',
    tagline: 'AI completes your thoughts as you type',
    description:
      'After 500ms pause, Gemini Flash suggests the next sentence inline at 40% opacity. Press Tab to accept, Escape to dismiss. Under 2.5s latency SLA.',
    model: 'Gemini Flash',
    modelColor: 'text-blue-600 bg-blue-50',
    badge: '500ms trigger',
    badgeColor: 'text-amber-600 bg-amber-50',
    preview: <GhostTextPreview />,
  },
  {
    icon: Eye,
    name: 'Margin Annotations',
    tagline: 'AI reads along and adds margin notes',
    description:
      'After 2s pause on 50+ character blocks, Claude analyzes context and adds colored margin indicators — suggestions, warnings, or issue candidates.',
    model: 'Claude',
    modelColor: 'text-purple-600 bg-purple-50',
    badge: 'Auto-trigger',
    badgeColor: 'text-primary bg-primary/10',
    preview: <AnnotationPreview />,
  },
  {
    icon: Layers,
    name: 'Issue Extraction',
    tagline: 'Actionable items become tickets automatically',
    description:
      'AI detects explicit tasks, implicit requirements, and related items in your notes. Issues are pre-filled with titles, descriptions, labels, and priority.',
    model: 'Claude',
    modelColor: 'text-purple-600 bg-purple-50',
    badge: 'Slash command',
    badgeColor: 'text-primary bg-primary/10',
    preview: <ExtractionPreview />,
  },
  {
    icon: Slash,
    name: 'AI Slash Commands',
    tagline: 'Type / to access AI actions instantly',
    description:
      'Inline commands for AI-powered writing: /improve for clarity, /summarize for concise overviews, /extract-issues to detect actionable items, and more.',
    model: 'Claude',
    modelColor: 'text-purple-600 bg-purple-50',
    badge: '8 commands',
    badgeColor: 'text-sky-600 bg-sky-50',
    preview: <SlashCommandPreview />,
  },
  {
    icon: Shield,
    name: 'Block Ownership',
    tagline: 'Know who wrote what — human or AI',
    description:
      'Every block tracks authorship: human, AI (with skill name), or shared. Prevents accidental edits to AI content with approve/reject controls.',
    model: 'Built-in',
    modelColor: 'text-foreground bg-muted',
    badge: 'Human-in-loop',
    badgeColor: 'text-primary bg-primary/10',
    preview: <OwnershipPreview />,
  },
  {
    icon: MessageSquare,
    name: 'AI Conversations',
    tagline: 'Threaded AI discussions per note',
    description:
      'Start a conversation thread scoped to your note context. Ask follow-up questions, refine ideas, and get architecture advice without leaving the editor.',
    model: 'Claude',
    modelColor: 'text-purple-600 bg-purple-50',
    badge: 'Multi-turn',
    badgeColor: 'text-ai bg-ai/10',
    preview: <ConversationPreview />,
  },
  {
    icon: PenTool,
    name: 'Selection AI Actions',
    tagline: 'Select text, get AI options',
    description:
      'Highlight any text to access "Ask Pilot", "Enhance", or "Extract Issues". AI gets your selected text plus surrounding block context for precise results.',
    model: 'Claude',
    modelColor: 'text-purple-600 bg-purple-50',
    badge: 'Context-aware',
    badgeColor: 'text-emerald-600 bg-emerald-50',
    preview: <SelectionPreview />,
  },
  {
    icon: Wand2,
    name: 'Focus Mode',
    tagline: 'Hide AI blocks for distraction-free writing',
    description:
      'Toggle Focus Mode to collapse all AI-generated blocks. Read and write without distraction, then expand to see AI suggestions when ready.',
    model: 'Built-in',
    modelColor: 'text-foreground bg-muted',
    badge: 'Toggle',
    badgeColor: 'text-muted-foreground bg-muted',
    preview: <FocusModePreview />,
  },
];

// ── Mock previews ───────────────────────────────────────

function GhostTextPreview() {
  return (
    <div className="space-y-2 text-sm">
      <p className="text-foreground/80">
        The token refresh strategy should use sliding window expiry
      </p>
      <p className="italic text-foreground/30">
        with a 15-minute access token lifetime and 7-day refresh token, rotating
        on each use to prevent replay attacks...
      </p>
      <span className="inline-flex rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
        Tab ↵
      </span>
    </div>
  );
}

function AnnotationPreview() {
  return (
    <div className="flex gap-3">
      <div className="flex-1 space-y-1 text-sm">
        <p className="text-foreground/80">
          Users can reset their password via email link without verification...
        </p>
      </div>
      <div className="w-32 shrink-0 space-y-1.5">
        <div className="rounded border border-amber-200 bg-amber-50 p-1.5">
          <div className="flex items-center gap-1 text-[10px] font-medium text-amber-600">
            <Eye className="size-2.5" /> Warning
          </div>
          <p className="text-[9px] leading-tight text-amber-700/70">
            Security: no email verification
          </p>
        </div>
        <div className="rounded border border-ai/20 bg-ai/5 p-1.5">
          <div className="flex items-center gap-1 text-[10px] font-medium text-ai">
            <Sparkles className="size-2.5" /> Suggestion
          </div>
          <p className="text-[9px] leading-tight text-ai/70">
            Add rate limiting
          </p>
        </div>
      </div>
    </div>
  );
}

function ExtractionPreview() {
  return (
    <div className="space-y-1.5">
      {[
        { id: 'PS-101', title: 'JWT token service', type: 'Feature' },
        { id: 'PS-102', title: 'Token refresh flow', type: 'Feature' },
        { id: 'PS-103', title: 'Session migration', type: 'Task' },
      ].map((issue) => (
        <div
          key={issue.id}
          className="flex items-center gap-2 rounded border border-border bg-background p-2"
        >
          <span className="text-[10px] font-bold text-primary">{issue.id}</span>
          <span className="flex-1 truncate text-xs text-foreground/80">
            {issue.title}
          </span>
          <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[9px] font-medium text-primary">
            {issue.type}
          </span>
        </div>
      ))}
    </div>
  );
}

function SlashCommandPreview() {
  return (
    <div className="space-y-1">
      {[
        { cmd: '/improve', desc: 'Enhance clarity' },
        { cmd: '/summarize', desc: 'Concise overview' },
        { cmd: '/extract-issues', desc: 'Detect items' },
        { cmd: '/decompose', desc: 'Break into tasks' },
      ].map((item) => (
        <div
          key={item.cmd}
          className="flex items-center gap-2 rounded bg-muted/50 px-2 py-1.5"
        >
          <code className="text-[11px] font-semibold text-primary">
            {item.cmd}
          </code>
          <span className="text-[10px] text-muted-foreground">{item.desc}</span>
        </div>
      ))}
    </div>
  );
}

function OwnershipPreview() {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2 rounded border-l-2 border-primary bg-primary/5 p-2">
        <div className="size-4 rounded-full bg-primary/20 text-center text-[8px] font-bold leading-4 text-primary">
          H
        </div>
        <span className="text-xs text-foreground/80">Human-written block</span>
      </div>
      <div className="flex items-center gap-2 rounded border-l-2 border-ai bg-ai/5 p-2">
        <div className="size-4 rounded-full bg-ai/20 text-center text-[8px] font-bold leading-4 text-ai">
          AI
        </div>
        <span className="text-xs text-foreground/80">
          AI block{' '}
          <span className="text-[10px] text-muted-foreground">
            (ghost-text)
          </span>
        </span>
        <div className="ml-auto flex gap-1">
          <span className="rounded bg-primary/10 px-1 py-0.5 text-[8px] font-medium text-primary">
            ✓
          </span>
          <span className="rounded bg-destructive/10 px-1 py-0.5 text-[8px] font-medium text-destructive">
            ✕
          </span>
        </div>
      </div>
    </div>
  );
}

function ConversationPreview() {
  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <div className="size-5 shrink-0 rounded-full bg-muted text-center text-[8px] font-bold leading-5">
          U
        </div>
        <div className="rounded-lg bg-muted px-2.5 py-1.5 text-[10px] text-foreground/80">
          How should I handle token rotation?
        </div>
      </div>
      <div className="flex gap-2">
        <div className="size-5 shrink-0 rounded-full bg-ai/20 text-center text-[8px] font-bold leading-5 text-ai">
          AI
        </div>
        <div className="rounded-lg bg-ai/5 px-2.5 py-1.5 text-[10px] text-foreground/80">
          Issue a new refresh token on each use. Store a token family ID
          to detect reuse...
        </div>
      </div>
    </div>
  );
}

function SelectionPreview() {
  return (
    <div className="space-y-2">
      <p className="text-xs text-foreground/80">
        <span className="rounded bg-primary/10 px-0.5">
          Token refresh strategy should use sliding window
        </span>{' '}
        with fixed expiry fallback.
      </p>
      <div className="inline-flex items-center gap-1 rounded-lg border border-border bg-background px-1 shadow-warm-sm">
        <button className="rounded px-2 py-1 text-[10px] font-medium text-primary hover:bg-primary/5">
          Ask Pilot
        </button>
        <div className="h-3 w-px bg-border" />
        <button className="rounded px-2 py-1 text-[10px] font-medium text-ai hover:bg-ai/5">
          Enhance
        </button>
        <div className="h-3 w-px bg-border" />
        <button className="rounded px-2 py-1 text-[10px] font-medium text-foreground/70 hover:bg-muted">
          Extract
        </button>
      </div>
    </div>
  );
}

function FocusModePreview() {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2 rounded bg-muted/50 p-2">
        <div className="size-3 rounded-sm bg-primary" />
        <span className="text-xs text-foreground/80">Your note content</span>
      </div>
      <div className="flex items-center gap-2 rounded bg-ai/5 p-2 opacity-40">
        <div className="size-3 rounded-sm bg-ai/30" />
        <span className="text-xs text-foreground/50 line-through">
          AI suggestion block (hidden)
        </span>
      </div>
      <div className="flex items-center gap-2 rounded bg-muted/50 p-2">
        <div className="size-3 rounded-sm bg-primary" />
        <span className="text-xs text-foreground/80">More of your writing</span>
      </div>
    </div>
  );
}

// ── Carousel card ───────────────────────────────────────

function FeatureCard({
  feature,
}: {
  feature: NoteFeature;
}) {
  return (
    <div className="flex h-full w-[320px] shrink-0 snap-center flex-col rounded-2xl border border-border bg-card shadow-warm-sm sm:w-[380px]">
      {/* Header */}
      <div className="border-b border-border-subtle p-5">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10">
              <feature.icon className="size-4.5 text-primary" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">
                {feature.name}
              </h3>
              <p className="text-[11px] text-muted-foreground">
                {feature.tagline}
              </p>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${feature.modelColor}`}
          >
            {feature.model}
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${feature.badgeColor}`}
          >
            {feature.badge}
          </span>
        </div>
      </div>

      {/* Preview mockup */}
      <div className="flex-1 p-5">
        <div className="mb-3 rounded-lg border border-border-subtle bg-background p-3">
          {feature.preview}
        </div>
        <p className="text-xs leading-relaxed text-muted-foreground">
          {feature.description}
        </p>
      </div>
    </div>
  );
}

// ── Main section ────────────────────────────────────────

export function LandingNoteAI() {
  const shouldReduce = useReducedMotion();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(true);

  const updateScrollState = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 10);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 10);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.addEventListener('scroll', updateScrollState, { passive: true });
    updateScrollState();
    return () => el.removeEventListener('scroll', updateScrollState);
  }, [updateScrollState]);

  const scroll = useCallback((direction: 'left' | 'right') => {
    const el = scrollRef.current;
    if (!el) return;
    const cardWidth = window.innerWidth < 640 ? 320 : 380;
    el.scrollBy({
      left: direction === 'left' ? -cardWidth - 16 : cardWidth + 16,
      behavior: 'smooth',
    });
  }, []);

  const handleCarouselKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        scroll('left');
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        scroll('right');
      }
    },
    [scroll],
  );

  return (
    <section id="note-ai" className="py-24 lg:py-28">
      <div className="mx-auto max-w-6xl px-4">
        <FadeIn className="mb-10 flex flex-col items-center text-center sm:flex-row sm:items-end sm:justify-between sm:text-left">
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-ai/10 px-3 py-1 text-xs font-medium text-ai">
              <Sparkles className="size-3" />
              Note Canvas AI
            </span>
            <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
              AI built into every keystroke
            </h2>
            <p className="mt-3 max-w-xl text-lg text-muted-foreground">
              8 AI features embedded in the Note Canvas — from ghost text
              to issue extraction, all powered by your own API keys
            </p>
          </div>
          {/* Desktop nav arrows */}
          <div className="mt-4 flex gap-2 sm:mt-0">
            <button
              onClick={() => scroll('left')}
              disabled={!canScrollLeft}
              className="flex size-9 items-center justify-center rounded-full border border-border bg-card text-foreground transition-all hover:shadow-warm-sm disabled:opacity-30 disabled:hover:shadow-none"
              aria-label="Scroll left"
            >
              <ChevronLeft className="size-4" />
            </button>
            <button
              onClick={() => scroll('right')}
              disabled={!canScrollRight}
              className="flex size-9 items-center justify-center rounded-full border border-border bg-card text-foreground transition-all hover:shadow-warm-sm disabled:opacity-30 disabled:hover:shadow-none"
              aria-label="Scroll right"
            >
              <ChevronRight className="size-4" />
            </button>
          </div>
        </FadeIn>

        {/* Carousel */}
        <div className="relative">
          {/* Fade edges */}
          {canScrollLeft && (
            <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-12 bg-gradient-to-r from-background to-transparent" />
          )}
          {canScrollRight && (
            <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-12 bg-gradient-to-l from-background to-transparent" />
          )}

          <div
            ref={scrollRef}
            tabIndex={0}
            role="region"
            aria-label="AI features carousel"
            onKeyDown={handleCarouselKeyDown}
            className="-mx-4 flex snap-x snap-mandatory gap-4 overflow-x-auto px-4 pb-4 scrollbar-none focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 focus-visible:rounded-xl"
          >
            {features.map((feature, i) => (
              <motion.div
                key={feature.name}
                initial={
                  shouldReduce ? undefined : { opacity: 0, x: 40 }
                }
                whileInView={
                  shouldReduce ? undefined : { opacity: 1, x: 0 }
                }
                viewport={{ once: true, margin: '-20px' }}
                transition={
                  shouldReduce
                    ? undefined
                    : { duration: 0.5, delay: i * 0.06 }
                }
              >
                <FeatureCard feature={feature} />
              </motion.div>
            ))}
          </div>
        </div>

        {/* Feature count */}
        <FadeIn className="mt-6 text-center" delay={0.3}>
          <p className="text-sm text-muted-foreground">
            <span className="font-semibold text-foreground">17 AI features</span>{' '}
            across 19 editor extensions • BYOK with Gemini Flash + Claude •{' '}
            <span className="font-medium text-primary">
              All respecting prefers-reduced-motion
            </span>
          </p>
        </FadeIn>
      </div>
    </section>
  );
}
