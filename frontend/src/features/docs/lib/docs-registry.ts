/**
 * Docs Registry — metadata and navigation structure for documentation pages.
 *
 * Each doc entry maps a URL slug to a markdown file in content/.
 * Sidebar groups organize docs into collapsible sections.
 */

export interface DocEntry {
  slug: string;
  title: string;
  description: string;
  /** Filename in features/docs/content/ (without .md extension) */
  file: string;
}

export interface DocGroup {
  label: string;
  items: DocEntry[];
}

export const docsNavigation: DocGroup[] = [
  {
    label: 'Getting Started',
    items: [
      {
        slug: 'overview',
        title: 'Overview',
        description: 'PilotSpace platform overview and key concepts',
        file: 'overview',
      },
      {
        slug: 'getting-started',
        title: 'Developer Setup',
        description: 'Local development environment setup',
        file: 'getting-started',
      },
    ],
  },
  {
    label: 'Architecture',
    items: [
      {
        slug: 'architecture',
        title: 'System Architecture',
        description: 'Clean architecture layers and patterns',
        file: 'architecture',
      },
      {
        slug: 'ai-agent',
        title: 'AI Agent System',
        description: 'PilotSpaceAgent orchestrator, MCP tools, provider routing',
        file: 'ai-agent',
      },
      {
        slug: 'note-first',
        title: 'Note-First Paradigm',
        description: 'Note editor, ghost text, annotations, issue extraction',
        file: 'note-first',
      },
    ],
  },
  {
    label: 'Reference',
    items: [
      {
        slug: 'api-reference',
        title: 'API Reference',
        description: 'Key endpoints, error handling, and authentication',
        file: 'api-reference',
      },
    ],
  },
];

/** Flat lookup: slug → DocEntry */
export const docsBySlug = new Map<string, DocEntry>(
  docsNavigation.flatMap((g) => g.items).map((d) => [d.slug, d])
);

/** Default doc shown when navigating to /docs */
export const defaultDocSlug = 'overview';
