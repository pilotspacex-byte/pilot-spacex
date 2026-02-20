import { LandingHero } from '@/components/landing/LandingHero';
import { LandingDemo } from '@/components/landing/LandingDemo';
import { LandingProblem } from '@/components/landing/LandingProblem';
import { LandingFeatures } from '@/components/landing/LandingFeatures';
import { LandingMidCTA } from '@/components/landing/LandingMidCTA';
import { LandingNoteAI } from '@/components/landing/LandingNoteAI';
import { LandingAIFlow } from '@/components/landing/LandingAIFlow';
import { LandingHowItWorks } from '@/components/landing/LandingHowItWorks';
import { LandingPersonas } from '@/components/landing/LandingPersonas';
import { LandingClaudeCode } from '@/components/landing/LandingClaudeCode';
import { LandingOpenSource } from '@/components/landing/LandingOpenSource';
import { LandingCTA } from '@/components/landing/LandingCTA';

export default function LandingPage() {
  return (
    <>
      <LandingHero />
      <LandingDemo />
      <LandingProblem />
      <LandingFeatures />
      <LandingMidCTA />
      <LandingNoteAI />
      <LandingAIFlow />
      <LandingHowItWorks />
      <LandingClaudeCode />
      <LandingPersonas />
      <LandingOpenSource />
      <LandingCTA />
    </>
  );
}
