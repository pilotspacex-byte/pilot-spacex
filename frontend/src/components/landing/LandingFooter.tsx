import { Compass, Github } from 'lucide-react';
import { GITHUB_URL } from './constants';

interface FooterLink {
  label: string;
  href: string;
  external?: boolean;
}

const footerLinks: Record<string, FooterLink[]> = {
  Product: [
    { label: 'Features', href: '#features' },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Open Source', href: '#open-source' },
    { label: 'Documentation', href: '#features' },
  ],
  Developers: [
    { label: 'GitHub', href: GITHUB_URL, external: true },
    { label: 'Contributing', href: GITHUB_URL, external: true },
  ],
};

export function LandingFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-background-subtle">
      <div className="mx-auto max-w-6xl px-4 py-12 lg:px-8">
        {/* Link columns */}
        <div className="grid grid-cols-2 gap-8 md:grid-cols-3">
          {/* Brand column */}
          <div>
            <div className="mb-4 flex items-center gap-2">
              <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10">
                <Compass className="size-4 text-primary" strokeWidth={1.5} />
              </div>
              <span className="font-display text-lg font-semibold text-foreground">
                Pilot Space
              </span>
            </div>
            <p className="text-sm leading-relaxed text-muted-foreground">
              AI-augmented SDLC platform built on the Note-First paradigm. Think first, structure
              later.
            </p>
          </div>

          {/* Link columns */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h4 className="mb-3 text-sm font-semibold text-foreground">{category}</h4>
              <ul className="space-y-2">
                {links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      {...(link.external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                      className="rounded-sm text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom row */}
        <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-border pt-6 sm:flex-row">
          <span className="text-sm text-muted-foreground">
            &copy; {currentYear} Pilot Space. MIT Licensed.
          </span>
          <div className="flex items-center gap-4">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2"
              aria-label="GitHub"
            >
              <Github className="size-4" />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
