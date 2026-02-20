'use client';

import Link from 'next/link';
import { ArrowRight, Github } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FadeIn } from './FadeIn';
import { GITHUB_URL } from './constants';

export function LandingMidCTA() {
  return (
    <section className="border-y border-border bg-background-subtle py-12 lg:py-16">
      <div className="mx-auto max-w-3xl px-4 text-center">
        <FadeIn>
          <p className="text-lg font-semibold text-foreground">Ready to see it in action?</p>
          <p className="mt-2 text-sm text-muted-foreground">
            Open source · MIT Licensed · Bring your own API keys
          </p>
        </FadeIn>
        <FadeIn className="mt-6 flex flex-col justify-center gap-3 sm:flex-row" delay={0.1}>
          <Button asChild size="lg" className="gap-2">
            <Link href="/login">
              Start for Free
              <ArrowRight className="size-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="gap-2">
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
              <Github className="size-4" />
              Star on GitHub
            </a>
          </Button>
        </FadeIn>
      </div>
    </section>
  );
}
