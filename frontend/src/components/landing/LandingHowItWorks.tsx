'use client';

import { motion, useReducedMotion } from 'motion/react';
import { PenTool, Wand2, Rocket } from 'lucide-react';
import { FadeIn } from './FadeIn';

const steps = [
  {
    number: '1',
    icon: PenTool,
    title: 'Write',
    subtitle: 'Start with a blank canvas',
    description:
      'Open the Note Canvas and write freely. No templates, no forms. Just your ideas flowing naturally.',
  },
  {
    number: '2',
    icon: Wand2,
    title: 'AI Assists',
    subtitle: 'AI suggests and refines',
    description:
      'Ghost text completes your thoughts. Margin annotations catch ambiguities. Threaded discussions dive deeper.',
  },
  {
    number: '3',
    icon: Rocket,
    title: 'Ship',
    subtitle: 'Issues emerge naturally',
    description:
      'AI extracts structured issues from your refined thinking. Approve, edit, and track \u2014 all linked back to the source.',
  },
];

export function LandingHowItWorks() {
  const shouldReduce = useReducedMotion();

  return (
    <section id="how-it-works" className="bg-background-subtle py-20 lg:py-24">
      <div className="mx-auto max-w-5xl px-4">
        <FadeIn className="mb-14 text-center">
          <h2 className="font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            From thought to action in three steps
          </h2>
          <p className="mt-3 text-lg text-muted-foreground">
            No learning curve. Just open a note and start writing.
          </p>
        </FadeIn>

        <div className="relative grid gap-8 md:grid-cols-3 md:gap-12">
          {/* Connecting line (desktop only) */}
          <div className="pointer-events-none absolute top-16 right-[16.67%] left-[16.67%] hidden h-px border-t-2 border-dashed border-border md:block" />

          {steps.map((step, i) => (
            <motion.div
              key={step.number}
              initial={shouldReduce ? undefined : { opacity: 0, y: 24 }}
              whileInView={shouldReduce ? undefined : { opacity: 1, y: 0 }}
              viewport={shouldReduce ? undefined : { once: true, margin: '-60px' }}
              transition={shouldReduce ? undefined : {
                duration: 0.5,
                ease: [0, 0, 0.2, 1],
                delay: i * 0.15,
              }}
              className="relative flex flex-col items-center text-center"
            >
              {/* Step number badge */}
              <div className="relative z-10 mb-4 flex size-12 items-center justify-center rounded-full bg-primary text-lg font-semibold text-primary-foreground shadow-warm">
                {step.number}
              </div>

              {/* Icon */}
              <div className="mb-4 flex size-12 items-center justify-center rounded-xl bg-card shadow-warm-sm">
                <step.icon className="size-5 text-primary" />
              </div>

              {/* Content */}
              <h3 className="mb-1 text-lg font-semibold text-foreground">{step.title}</h3>
              <p className="mb-2 text-sm font-medium text-primary">{step.subtitle}</p>
              <p className="text-sm leading-relaxed text-muted-foreground">{step.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
