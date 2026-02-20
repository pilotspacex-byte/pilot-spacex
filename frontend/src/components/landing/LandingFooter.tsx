import { Compass, Github } from 'lucide-react';
import { GITHUB_URL } from './constants';

const footerLinks = {
  Product: [
    { label: 'Features', href: '#features' },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Open Source', href: '#open-source' },
    { label: 'Documentation', href: '#', disabled: true },
  ],
  Developers: [
    { label: 'GitHub', href: GITHUB_URL, external: true },
    { label: 'API Docs', href: '#', disabled: true },
    { label: 'Contributing', href: GITHUB_URL, external: true },
    { label: 'Changelog', href: '#', disabled: true },
  ],
  Company: [
    { label: 'About', href: '#', disabled: true },
    { label: 'Blog', href: '#', disabled: true },
    { label: 'Contact', href: '#', disabled: true },
  ],
  Legal: [
    { label: 'Privacy Policy', href: '#', disabled: true },
    { label: 'Terms of Service', href: '#', disabled: true },
    { label: 'Security', href: '#', disabled: true },
  ],
};

export function LandingFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-background-subtle">
      <div className="mx-auto max-w-6xl px-4 py-12 lg:px-8">
        {/* Link columns */}
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h4 className="mb-3 text-sm font-semibold text-foreground">{category}</h4>
              <ul className="space-y-2">
                {links.map((link) => (
                  <li key={link.label}>
                    {'external' in link && link.external ? (
                      <a
                        href={link.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 rounded-sm"
                      >
                        {link.label}
                      </a>
                    ) : 'disabled' in link && link.disabled ? (
                      <span
                        aria-disabled="true"
                        className="text-sm text-muted-foreground opacity-50 cursor-default rounded-sm"
                      >
                        {link.label}
                      </span>
                    ) : (
                      <a
                        href={link.href}
                        className="text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 rounded-sm"
                      >
                        {link.label}
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom row */}
        <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-border pt-6 sm:flex-row">
          <div className="flex items-center gap-2">
            <Compass className="size-4 text-primary" strokeWidth={1.5} />
            <span className="text-sm text-muted-foreground">
              &copy; {currentYear} Pilot Space. All rights reserved.
            </span>
          </div>
          <div className="flex items-center gap-4">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground transition-colors hover:text-foreground"
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
