'use client';

import { motion, useReducedMotion } from 'motion/react';
import { Code2, Users, FileText, GraduationCap, type LucideIcon } from 'lucide-react';
import { FadeIn } from './FadeIn';

interface Persona {
  icon: LucideIcon;
  role: string;
  tagline: string;
  description: string;
  color: string;
  bgColor: string;
  borderColor: string;
  features: string[];
}

const personas: Persona[] = [
  {
    icon: Code2,
    role: 'Architect',
    tagline: 'AI-powered code review',
    description:
      'AI reviews PRs for architecture patterns, security issues, and performance bottlenecks before you even look.',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    features: ['AI PR Review', 'Architecture Analysis', 'Security Scanning'],
  },
  {
    icon: Users,
    role: 'Tech Lead',
    tagline: 'Unified team intelligence',
    description:
      'Unified task decomposition, velocity tracking, and PR reviews. Spend less time on process, more on direction.',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    features: ['Task Decomposition', 'Velocity Tracking', 'Cycle Analytics'],
  },
  {
    icon: FileText,
    role: 'PM',
    tagline: 'Note-first requirements',
    description:
      'Note-First workflow captures requirements naturally. AI extracts and enhances issues from your thinking.',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    features: ['Note-First Workflow', 'Issue Extraction', 'AI Enhancement'],
  },
  {
    icon: GraduationCap,
    role: 'Junior Dev',
    tagline: 'AI-assisted onboarding',
    description:
      'AI Context gives you code snippets, related docs, and Claude Code prompts. Ramp up in hours, not weeks.',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    features: ['AI Context', 'Claude Code Prompts', 'Code Snippets'],
  },
];

export function LandingPersonas() {
  const shouldReduce = useReducedMotion();

  return (
    <section id="personas" className="py-20 lg:py-24">
      <div className="mx-auto max-w-5xl px-4">
        <FadeIn className="mb-14 text-center">
          <h2 className="font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Built for every role on your team
          </h2>
          <p className="mt-3 text-lg text-muted-foreground">
            From architects to junior devs, AI adapts to how you work
          </p>
        </FadeIn>

        <div className="grid gap-5 sm:grid-cols-2">
          {personas.map((persona, i) => (
            <motion.div
              key={persona.role}
              initial={shouldReduce ? undefined : { opacity: 0, y: 24 }}
              whileInView={shouldReduce ? undefined : { opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={shouldReduce ? undefined : {
                duration: 0.5,
                ease: [0, 0, 0.2, 1],
                delay: i * 0.08,
              }}
              className={`rounded-xl border ${persona.borderColor} bg-card p-6 transition-shadow hover:shadow-warm-md lg:p-8`}
            >
              <div className="mb-4 flex items-center gap-3">
                <div className={`flex size-10 items-center justify-center rounded-lg ${persona.bgColor}`}>
                  <persona.icon className={`size-5 ${persona.color}`} />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-foreground">{persona.role}</h3>
                  <p className={`text-xs font-medium ${persona.color}`}>{persona.tagline}</p>
                </div>
              </div>
              <p className="text-sm leading-relaxed text-muted-foreground">{persona.description}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {persona.features.map((feature) => (
                  <span
                    key={feature}
                    className="rounded-full border border-border bg-background px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
