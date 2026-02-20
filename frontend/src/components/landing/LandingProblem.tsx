'use client';

import { ClipboardList, Compass, X, Check, ArrowRight } from 'lucide-react';
import { FadeIn } from './FadeIn';

const traditionalItems = [
  'Start with empty forms and templates',
  'Brainstorm in Slack, then transcribe to tickets',
  'AI bolted on as an afterthought',
  'Context lost between tools',
];

const pilotSpaceItems = [
  'Start with a blank canvas',
  'Think freely, AI assists inline',
  'Issues emerge from refined thinking',
  'Context preserved end-to-end',
];

export function LandingProblem() {
  return (
    <section id="problem" className="py-20 lg:py-24">
      <div className="mx-auto max-w-5xl px-4">
        <FadeIn className="mb-12 text-center">
          <h2 className="font-display text-3xl font-semibold tracking-tight text-foreground">
            A better way to plan
          </h2>
          <p className="mt-3 text-muted-foreground">
            Traditional tools force structure before thinking. We flip the script.
          </p>
        </FadeIn>

        <div className="grid gap-6 md:grid-cols-2 lg:gap-8">
          {/* Traditional PM */}
          <FadeIn className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 lg:p-8">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-lg bg-destructive/10">
                <ClipboardList className="size-5 text-destructive" />
              </div>
              <h3 className="text-lg font-semibold text-foreground">Traditional PM</h3>
            </div>
            <ul className="space-y-3">
              {traditionalItems.map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <X className="mt-0.5 size-4 shrink-0 text-destructive/60" />
                  <span className="text-sm text-muted-foreground">{item}</span>
                </li>
              ))}
            </ul>
          </FadeIn>

          {/* Pilot Space */}
          <FadeIn className="rounded-xl border border-primary/20 bg-primary/5 p-6 lg:p-8">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10">
                <Compass className="size-5 text-primary" />
              </div>
              <h3 className="text-lg font-semibold text-foreground">Pilot Space</h3>
            </div>
            <ul className="space-y-3">
              {pilotSpaceItems.map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <Check className="mt-0.5 size-4 shrink-0 text-primary" />
                  <span className="text-sm text-foreground/80">{item}</span>
                </li>
              ))}
            </ul>
          </FadeIn>
        </div>

        {/* Arrow connector (desktop) */}
        <div className="mt-4 hidden justify-center md:flex">
          <div className="flex items-center gap-2 text-muted-foreground">
            <span className="text-sm">Traditional approach</span>
            <ArrowRight className="size-4" />
            <span className="text-sm font-medium text-primary">Note-first workflow</span>
          </div>
        </div>
      </div>
    </section>
  );
}
