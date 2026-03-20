'use client';

import { motion, useReducedMotion } from 'motion/react';
import {
  Sparkles,
  GitPullRequest,
  Layers,
  Brain,
  MessageSquare,
  Key,
  type LucideIcon,
} from 'lucide-react';
import { FadeIn } from './FadeIn';

interface Feature {
  icon: LucideIcon;
  iconColor: string;
  iconBg: string;
  title: string;
  description: string;
  accent?: string;
}

const heroFeatures: Feature[] = [
  {
    icon: Sparkles,
    iconColor: 'text-primary',
    iconBg: 'bg-primary/10',
    title: 'Ghost Text',
    description:
      'Get intelligent AI suggestions as you type. Accept with Tab, dismiss with Escape. Real-time co-writing with under 2.5 seconds latency.',
    accent: 'border-l-primary',
  },
  {
    icon: GitPullRequest,
    iconColor: 'text-ai',
    iconBg: 'bg-ai/10',
    title: 'AI PR Review',
    description:
      'Every pull request gets architecture, security, and performance analysis. Comments posted directly to GitHub with severity tags.',
    accent: 'border-l-ai',
  },
];

const gridFeatures: Feature[] = [
  {
    icon: Layers,
    iconColor: 'text-primary',
    iconBg: 'bg-primary/10',
    title: 'Issue Extraction',
    description:
      'AI detects actionable items in your notes and extracts structured issues with titles, descriptions, labels, and priority.',
  },
  {
    icon: Brain,
    iconColor: 'text-ai',
    iconBg: 'bg-ai/10',
    title: 'AI Context',
    description:
      'Every issue gets relevant code snippets, related docs, and ready-to-use Claude Code prompts for faster implementation.',
  },
  {
    icon: MessageSquare,
    iconColor: 'text-primary',
    iconBg: 'bg-primary/10',
    title: 'Multi-Turn Chat',
    description:
      'Conversational AI that understands your project. Discuss architecture, decompose tasks, and get estimates in natural conversation.',
  },
  {
    icon: Key,
    iconColor: 'text-ai',
    iconBg: 'bg-ai/10',
    title: 'Bring Your Own Keys',
    description:
      'Use your own API keys for Claude and Gemini. No cost pass-through. Choose the right model for each task automatically.',
  },
];

export function LandingFeatures() {
  const shouldReduce = useReducedMotion();

  return (
    <section id="features" className="py-20 lg:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <FadeIn className="mb-14 text-center">
          <h2 className="font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl lg:text-5xl">
            Everything you need to ship faster
          </h2>
          <p className="mt-3 text-lg text-muted-foreground">
            AI-powered tools embedded in every step of your workflow
          </p>
        </FadeIn>

        {/* Hero row — two larger feature cards with accent border */}
        <div className="grid gap-5 md:grid-cols-2">
          {heroFeatures.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={shouldReduce ? undefined : { opacity: 0, y: 24 }}
              whileInView={shouldReduce ? undefined : { opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={
                shouldReduce
                  ? undefined
                  : {
                      duration: 0.5,
                      ease: [0, 0, 0.2, 1],
                      delay: i * 0.1,
                    }
              }
              className={`group rounded-xl border border-border border-l-4 ${feature.accent} bg-card p-8 transition-shadow duration-200 hover:shadow-warm-md`}
            >
              <div className="flex items-start gap-4">
                <div
                  className={`flex size-12 shrink-0 items-center justify-center rounded-xl ${feature.iconBg}`}
                >
                  <feature.icon className={`size-6 ${feature.iconColor}`} />
                </div>
                <div>
                  <h3 className="mb-2 text-lg font-semibold text-foreground">{feature.title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Secondary row — four compact feature cards */}
        <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {gridFeatures.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={shouldReduce ? undefined : { opacity: 0, y: 24 }}
              whileInView={shouldReduce ? undefined : { opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={
                shouldReduce
                  ? undefined
                  : {
                      duration: 0.5,
                      ease: [0, 0, 0.2, 1],
                      delay: 0.2 + i * 0.08,
                    }
              }
              className="group rounded-xl border border-border bg-card p-5 transition-shadow duration-200 hover:shadow-warm-md"
            >
              <div
                className={`mb-3 flex size-9 items-center justify-center rounded-lg ${feature.iconBg}`}
              >
                <feature.icon className={`size-4.5 ${feature.iconColor}`} />
              </div>
              <h3 className="mb-1.5 text-sm font-semibold text-foreground">{feature.title}</h3>
              <p className="text-xs leading-relaxed text-muted-foreground">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
