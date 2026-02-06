'use client';

/**
 * OnboardingCelebration - Celebration animation when onboarding completes
 *
 * T023: Create OnboardingCelebration component
 * Source: FR-013, US1
 */
import { useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { cn } from '@/lib/utils';
import { PartyPopper, Rocket, Star } from 'lucide-react';
import { useOnboardingStore } from '@/stores/RootStore';

const CONFETTI_COLORS = ['#29A386', '#6B8FAD', '#D9853F', '#8B7EC8'];

/**
 * Confetti particle component.
 * Uses the global `animate-confetti-fall` class from globals.css
 * so that prefers-reduced-motion disables it via the global rule.
 */
function ConfettiParticle({
  delay,
  left,
  colorIndex,
}: {
  delay: number;
  left: number;
  colorIndex: number;
}) {
  return (
    <div
      className={cn(
        'absolute w-2 h-2 rounded-full',
        'animate-confetti-fall'
      )}
      style={{
        animationDelay: `${delay}ms`,
        left: `${left}%`,
        top: '-10px',
        backgroundColor: CONFETTI_COLORS[colorIndex % CONFETTI_COLORS.length],
      }}
    />
  );
}

/**
 * OnboardingCelebration - displays celebration animation inside modal
 *
 * FR-013: Celebration trigger when all steps complete.
 * Auto-dismisses after 3 seconds (modal closes).
 */
export const OnboardingCelebration = observer(function OnboardingCelebration() {
  const onboardingStore = useOnboardingStore();
  const [particles, setParticles] = useState<
    { id: number; delay: number; left: number; colorIndex: number }[]
  >([]);

  // Generate confetti particles only when celebration is showing
  useEffect(() => {
    if (!onboardingStore.showingCelebration) return;

    const newParticles = Array.from({ length: 30 }, (_, i) => ({
      id: i,
      delay: Math.random() * 500,
      left: Math.random() * 100,
      colorIndex: Math.floor(Math.random() * CONFETTI_COLORS.length),
    }));
    setParticles(newParticles);
  }, [onboardingStore.showingCelebration]);

  if (!onboardingStore.showingCelebration) {
    return null;
  }

  return (
    <div
      className={cn(
        'relative overflow-hidden',
        'animate-in fade-in-0 zoom-in-95 duration-500',
        'motion-reduce:animate-none'
      )}
    >
      {/* Confetti container */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none motion-reduce:hidden">
        {particles.map((p) => (
          <ConfettiParticle key={p.id} delay={p.delay} left={p.left} colorIndex={p.colorIndex} />
        ))}
      </div>

      <div className="flex flex-col items-center justify-center py-8 text-center relative z-10">
        {/* Animated icons */}
        <div className="flex items-center gap-4 mb-4">
          <Star
            className={cn(
              'h-6 w-6 text-yellow-500',
              'animate-in spin-in-180 duration-700 delay-100',
              'motion-reduce:animate-none'
            )}
          />
          <PartyPopper
            className={cn(
              'h-10 w-10 text-primary',
              'animate-in zoom-in-50 duration-500',
              'motion-reduce:animate-none'
            )}
          />
          <Star
            className={cn(
              'h-6 w-6 text-yellow-500',
              'animate-in spin-in-180 duration-700 delay-200',
              'motion-reduce:animate-none'
            )}
          />
        </div>

        {/* Message */}
        <h3
          className={cn(
            'text-xl font-semibold text-foreground mb-2',
            'animate-in fade-in-0 slide-in-from-bottom-2 duration-500 delay-300',
            'motion-reduce:animate-none'
          )}
        >
          You&apos;re all set!
        </h3>
        <p
          className={cn(
            'text-sm text-muted-foreground mb-4',
            'animate-in fade-in-0 slide-in-from-bottom-2 duration-500 delay-400',
            'motion-reduce:animate-none'
          )}
        >
          Your workspace is ready. Start creating amazing things!
        </p>

        {/* Rocket animation */}
        <div
          className={cn(
            'flex items-center gap-2 text-primary',
            'animate-in fade-in-0 slide-in-from-bottom-4 duration-700 delay-500',
            'motion-reduce:animate-none'
          )}
        >
          <Rocket className="h-5 w-5" />
          <span className="text-sm font-medium">Ready to launch</span>
        </div>
      </div>
    </div>
  );
});
