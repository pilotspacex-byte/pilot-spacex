'use client';

import { type ReactNode } from 'react';
import { motion, useReducedMotion } from 'motion/react';

interface FadeInProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  as?: 'div' | 'h2' | 'p';
}

export function FadeIn({ children, className, delay = 0, as = 'div' }: FadeInProps) {
  const shouldReduce = useReducedMotion();
  const Component = motion[as];

  return (
    <Component
      initial={shouldReduce ? undefined : { opacity: 0, y: 24 }}
      whileInView={shouldReduce ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={shouldReduce ? undefined : { duration: 0.5, ease: [0, 0, 0.2, 1], delay }}
      className={className}
    >
      {children}
    </Component>
  );
}
