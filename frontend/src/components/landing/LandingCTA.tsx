'use client';

import Link from 'next/link';
import { ArrowRight, Github } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FadeIn } from './FadeIn';
import { GITHUB_URL } from './constants';

export function LandingCTA() {
  return (
    <section className="relative py-24 lg:py-32">
      {/* Subtle radial gradient */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute top-1/2 left-1/2 h-[400px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/5 blur-3xl" />
      </div>

      <div className="mx-auto max-w-2xl px-4 text-center">
        <FadeIn
          as="h2"
          className="font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl lg:text-5xl"
        >
          Ready to think first?
        </FadeIn>

        <FadeIn as="p" className="mt-4 text-lg text-muted-foreground" delay={0.1}>
          Join teams who ship faster by letting ideas flow before structure follows.
        </FadeIn>

        <FadeIn className="mt-8 flex flex-col justify-center gap-3 sm:flex-row" delay={0.2}>
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
        </FadeIn>
      </div>
    </section>
  );
}
