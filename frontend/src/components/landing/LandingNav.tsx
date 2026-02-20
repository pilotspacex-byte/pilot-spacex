'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence, useReducedMotion } from 'motion/react';
import { Compass, Menu, X, Github } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GITHUB_URL } from './constants';

const navLinks = [
  { label: 'Features', href: '#features' },
  { label: 'AI in SDLC', href: '#ai-flow' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Claude Code', href: '#claude-code' },
  { label: 'Open Source', href: '#open-source' },
];

export function LandingNav() {
  const shouldReduce = useReducedMotion();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 10);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 right-0 left-0 z-50 transition-all duration-200 ${
        isScrolled ? 'border-b border-border bg-background/80 backdrop-blur-xl' : 'bg-transparent'
      }`}
    >
      <nav className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 lg:px-8">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 transition-opacity hover:opacity-80"
          aria-label="Pilot Space Home"
        >
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10">
            <Compass className="size-4 text-primary" strokeWidth={1.5} />
          </div>
          <span className="font-display text-lg font-semibold tracking-tight text-foreground">
            Pilot Space
          </span>
        </Link>

        {/* Desktop Links */}
        <div className="hidden items-center gap-1 md:flex">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2"
            >
              {link.label}
            </a>
          ))}
        </div>

        {/* Desktop CTAs */}
        <div className="hidden items-center gap-3 md:flex">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground transition-colors hover:text-foreground"
            aria-label="View on GitHub"
          >
            <Github className="size-5" />
          </a>
          <Button asChild size="sm">
            <Link href="/login">Get Started</Link>
          </Button>
        </div>

        {/* Mobile Menu Toggle */}
        <button
          type="button"
          className="flex size-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:text-foreground md:hidden"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={isMobileMenuOpen}
          aria-controls="mobile-nav-menu"
        >
          {isMobileMenuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </nav>

      {/* Mobile Menu */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            id="mobile-nav-menu"
            role="navigation"
            aria-label="Mobile navigation"
            initial={shouldReduce ? undefined : { opacity: 0, height: 0 }}
            animate={shouldReduce ? undefined : { opacity: 1, height: 'auto' }}
            exit={shouldReduce ? undefined : { opacity: 0, height: 0 }}
            className="overflow-hidden border-b border-border bg-background/95 backdrop-blur-xl md:hidden"
          >
            <div className="flex flex-col gap-1 px-4 py-3">
              {navLinks.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className="rounded-md px-3 py-3 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2"
                  onClick={(e) => {
                    e.preventDefault();
                    setIsMobileMenuOpen(false);
                    setTimeout(() => {
                      const id = link.href.startsWith('#') ? link.href.slice(1) : null;
                      if (id) document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
                    }, 300);
                  }}
                >
                  {link.label}
                </a>
              ))}
              <div className="mt-2 flex items-center gap-3 border-t border-border pt-3">
                <a
                  href={GITHUB_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-muted-foreground transition-colors hover:text-foreground"
                  aria-label="View on GitHub"
                >
                  <Github className="size-5" />
                </a>
                <Button asChild size="sm" className="flex-1">
                  <Link href="/login">Get Started</Link>
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
