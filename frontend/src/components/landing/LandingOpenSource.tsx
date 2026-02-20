'use client';

import { Github, Server, Key, Scale, Code2, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FadeIn } from './FadeIn';
import { GITHUB_URL } from './constants';

const highlights = [
  { icon: Key, label: 'BYOK \u2014 No AI cost pass-through' },
  { icon: Server, label: 'Self-hosted \u2014 Your data stays yours' },
  { icon: Scale, label: 'MIT License \u2014 Fork, modify, deploy' },
];

const credibilityPills = [
  { icon: Github, label: 'Open Source' },
  { icon: Scale, label: 'MIT Licensed' },
  { icon: Code2, label: 'TypeScript' },
  { icon: Users, label: 'Built for Teams of 5-100' },
];

export function LandingOpenSource() {
  return (
    <section id="open-source" className="relative overflow-hidden py-20 lg:py-24">
      {/* Background gradient */}
      <div className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-br from-primary/5 via-primary/10 to-ai/5" />
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute top-1/2 left-1/2 h-[500px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/5 blur-3xl" />
      </div>

      <div className="mx-auto max-w-4xl px-4 text-center">
        <FadeIn>
          <h2 className="font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl lg:text-5xl">
            Free. Open Source. Self-Hosted.
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            All features included. No artificial limits. Paid tiers only for enterprise support
            SLAs.
          </p>
        </FadeIn>

        <FadeIn className="mt-10 flex flex-wrap justify-center gap-3" delay={0.1}>
          {highlights.map((item) => (
            <div
              key={item.label}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2 text-sm text-foreground shadow-warm-sm"
            >
              <item.icon className="size-4 text-primary" />
              {item.label}
            </div>
          ))}
        </FadeIn>

        <FadeIn className="mt-8" delay={0.2}>
          <Button asChild variant="outline" size="lg" className="gap-2">
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
              <Github className="size-4" />
              Star on GitHub
            </a>
          </Button>
        </FadeIn>

        <FadeIn className="mt-8 flex flex-wrap justify-center gap-2" delay={0.3}>
          {credibilityPills.map((pill) => (
            <div
              key={pill.label}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground"
            >
              <pill.icon className="size-3.5 text-primary" />
              {pill.label}
            </div>
          ))}
        </FadeIn>

        <FadeIn className="mt-8" delay={0.4}>
          <p className="text-sm font-medium text-foreground">Built by engineers who ship</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Created by developers who were tired of form-filling before thinking was complete.
          </p>
        </FadeIn>
      </div>
    </section>
  );
}
