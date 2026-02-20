import type { ReactNode } from 'react';
import type { Metadata } from 'next';
import { LandingNav } from '@/components/landing/LandingNav';
import { LandingFooter } from '@/components/landing/LandingFooter';

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'https://pilotspace.dev'),
  title: 'Pilot Space — Think first, structure later',
  description:
    'AI-augmented SDLC platform with Note-First workflow. Ghost text, PR review, issue extraction, and AI context — all embedded in your development process.',
  openGraph: {
    title: 'Pilot Space — Think first, structure later',
    description:
      'The note-first platform where AI helps your ideas become structured issues naturally.',
    type: 'website',
    url: '/welcome',
    siteName: 'Pilot Space',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'Pilot Space — AI-Augmented SDLC Platform',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Pilot Space — Think first, structure later',
    description:
      'The note-first platform where AI helps your ideas become structured issues naturally.',
  },
};

interface WelcomeLayoutProps {
  children: ReactNode;
}

export default function WelcomeLayout({ children }: WelcomeLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <a
        href="#landing-main"
        className="sr-only rounded bg-background px-3 py-2 text-sm text-foreground focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus-visible:outline-2 focus-visible:outline-primary"
      >
        Skip to content
      </a>
      <LandingNav />
      <main id="landing-main">{children}</main>
      <LandingFooter />
    </div>
  );
}
