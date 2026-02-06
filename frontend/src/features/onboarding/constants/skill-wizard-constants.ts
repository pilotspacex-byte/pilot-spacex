/**
 * Skill wizard constants - role-specific sample descriptions and before/after examples.
 *
 * Extracted from hardcoded SkillGenerationWizard content to support
 * the two-panel form layout with role-specific pre-fills and examples.
 *
 * Source: FR-001, FR-002, FR-003, FR-004
 */

import type { SDLCRoleType } from '@/services/api/role-skills';

/**
 * Pre-fill text for the "Describe Your Expertise" textarea per role.
 * Users see this as a starting point they can edit.
 */
export const ROLE_SAMPLE_DESCRIPTIONS: Record<SDLCRoleType, string> = {
  developer:
    "I'm a full-stack TypeScript developer with 5 years of experience. I focus on React, Next.js, and Node.js backends with PostgreSQL. I care about clean architecture, comprehensive testing, and code review quality.",
  tester:
    "I'm a QA engineer specializing in automated testing with 4 years of experience. I use Playwright for E2E, Vitest for unit tests, and focus on test strategy, coverage analysis, and CI/CD pipeline integration.",
  architect:
    "I'm a solutions architect with 8 years of experience designing distributed systems. I focus on microservices, event-driven architecture, cloud-native patterns (AWS/GCP), and technical decision documentation.",
  tech_lead:
    "I'm a tech lead managing a team of 6 developers. I focus on sprint planning, code review standards, technical debt management, and mentoring junior engineers while still contributing to architecture decisions.",
  product_owner:
    "I'm a product owner with 5 years of experience in B2B SaaS. I focus on user story writing, backlog prioritization, stakeholder management, and translating business requirements into actionable development tasks.",
  business_analyst:
    "I'm a business analyst with experience in requirements gathering and process modeling. I focus on stakeholder interviews, use case documentation, data flow analysis, and bridging the gap between business and technical teams.",
  project_manager:
    "I'm a project manager certified in PMP and Agile methodologies. I manage cross-functional teams, track milestones, handle risk assessment, and ensure on-time delivery with clear communication to stakeholders.",
  devops:
    "I'm a DevOps engineer with 5 years of experience in CI/CD pipelines, Docker, Kubernetes, and infrastructure as code (Terraform). I focus on deployment automation, monitoring, and site reliability.",
  custom: '',
};

/** A single before/after example showing how a skill changes AI behavior. */
export interface SkillExample {
  /** Short scenario title. */
  title: string;
  /** What the user asks or does. */
  prompt: string;
  /** Generic AI response without the skill. */
  without: string[];
  /** Specific AI response with the skill active. */
  with: string[];
}

/**
 * Role-specific before/after examples (1-2 per role).
 * Shown in the right panel of the skill form view.
 */
export const ROLE_EXAMPLES: Record<SDLCRoleType, SkillExample[]> = {
  developer: [
    {
      title: 'Reviewing an Issue',
      prompt: 'Review this issue about adding caching',
      without: [
        'Consider what data to cache',
        'Think about cache invalidation',
        'Review performance requirements',
      ],
      with: [
        'Use Redis with read-through pattern',
        'Set TTL based on data volatility (30m hot, 7d cold)',
        'Add cache-aside for frequently queried endpoints',
        'Watch for N+1 in the repository layer',
      ],
    },
  ],
  tester: [
    {
      title: 'Writing Test Plan',
      prompt: 'Create a test plan for the login feature',
      without: [
        'Test valid and invalid credentials',
        'Check error messages',
        'Verify redirect after login',
      ],
      with: [
        'E2E: Happy path with Playwright + visual regression',
        'Unit: Auth service mock with edge cases (expired token, rate limit)',
        'Security: SQL injection, XSS on input fields, brute force lockout',
        'Performance: Login under 500ms at P99 with 100 concurrent users',
      ],
    },
  ],
  architect: [
    {
      title: 'Designing a Feature',
      prompt: 'Design the notification system architecture',
      without: [
        'Create a notification service',
        'Store notifications in database',
        'Send notifications to users',
      ],
      with: [
        'Event-driven: Domain events -> Message queue -> Fan-out',
        'Multi-channel: In-app (WebSocket), Email (SES), Push (FCM)',
        'Delivery guarantee: At-least-once with idempotency keys',
        'ADR: Document trade-offs vs polling approach',
      ],
    },
  ],
  tech_lead: [
    {
      title: 'Reviewing a PR',
      prompt: 'Review this pull request for the payment integration',
      without: [
        'Check code style and formatting',
        'Look for obvious bugs',
        'Verify tests are included',
      ],
      with: [
        'Architecture: Does this follow our hexagonal pattern?',
        'Security: PCI compliance for payment data handling',
        'Team impact: Will this block other PRs or need migration?',
        'Mentoring: Suggest patterns for junior dev who authored this',
      ],
    },
  ],
  product_owner: [
    {
      title: 'Refining a User Story',
      prompt: 'Help me refine this feature request for dark mode',
      without: [
        'Add acceptance criteria',
        'Define scope',
        'Estimate effort',
      ],
      with: [
        'User segments: Which personas benefit most? (night-shift devs, accessibility)',
        'Acceptance: Color contrast ratios per WCAG AA, system preference detection',
        'Metrics: Track adoption rate, session duration delta, support ticket reduction',
        'Dependencies: Design system tokens, third-party component audit',
      ],
    },
  ],
  business_analyst: [
    {
      title: 'Analyzing Requirements',
      prompt: 'Analyze requirements for the reporting dashboard',
      without: [
        'List the required reports',
        'Define data sources',
        'Create wireframes',
      ],
      with: [
        'Stakeholder map: Who consumes which report and how often?',
        'Data lineage: Source systems -> ETL -> Data warehouse -> API',
        'Gap analysis: Current manual process vs automated dashboard',
        'Acceptance: Export formats, filter combinations, refresh frequency SLA',
      ],
    },
  ],
  project_manager: [
    {
      title: 'Planning a Sprint',
      prompt: 'Help plan the next sprint for our team',
      without: [
        'Prioritize backlog items',
        'Assign tasks to team members',
        'Set sprint goals',
      ],
      with: [
        'Capacity: Account for PTO, on-call rotation, tech debt allocation (20%)',
        'Dependencies: Map cross-team blockers and external API timelines',
        'Risk: Identify top 3 risks with mitigation (new hire onboarding, API stability)',
        'Metrics: Target velocity based on 3-sprint rolling average',
      ],
    },
  ],
  devops: [
    {
      title: 'Setting Up CI/CD',
      prompt: 'Help me improve our deployment pipeline',
      without: [
        'Add automated tests to pipeline',
        'Set up staging environment',
        'Configure deployment scripts',
      ],
      with: [
        'Pipeline: Lint -> Unit -> Integration -> Build -> Deploy canary -> Promote',
        'Infrastructure: Terraform modules with remote state, drift detection',
        'Observability: Deploy markers in Datadog, automated rollback on error rate >1%',
        'Security: SAST/DAST scanning, dependency audit, secrets rotation',
      ],
    },
  ],
  custom: [],
};

/**
 * Generic examples shown in CustomRoleInput right panel.
 * Shows how different predefined roles change AI behavior.
 */
export const CUSTOM_ROLE_EXAMPLES: {
  roleName: string;
  description: string;
  example: string;
}[] = [
  {
    roleName: 'Developer',
    description: 'Code-focused suggestions',
    example: 'Recommends specific patterns, catches N+1 queries, suggests test strategies',
  },
  {
    roleName: 'Product Owner',
    description: 'Business-aligned guidance',
    example: 'Adds acceptance criteria, identifies user segments, suggests success metrics',
  },
  {
    roleName: 'Architect',
    description: 'System design perspective',
    example: 'Evaluates trade-offs, suggests ADRs, identifies cross-service impacts',
  },
];
