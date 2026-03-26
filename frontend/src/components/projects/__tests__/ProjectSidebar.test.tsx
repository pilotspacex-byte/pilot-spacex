/**
 * Unit tests for ProjectSidebar navigation feature gating.
 *
 * Tests that NAV_ITEMS are hidden based on workspace feature toggles,
 * and that the Recent notes section is hidden when the notes feature is disabled.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProjectSidebar } from '../ProjectSidebar';
import type { Project } from '@/types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    ...props
  }: {
    href: string;
    children: React.ReactNode;
    [k: string]: unknown;
  }) => <a href={href} {...props}>{children}</a>,
}));

vi.mock('next/navigation', () => ({
  usePathname: () => '/test-ws/projects/proj-1/overview',
}));

const mockProject: Project = {
  id: 'proj-1',
  name: 'Test Project',
  identifier: 'TP',
  workspaceId: 'ws-1',
  issueCount: 0,
  openIssueCount: 0,
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

const defaultFeatureToggles = {
  notes: true,
  issues: true,
  projects: true,
  members: true,
  knowledge: true,
  docs: true,
  skills: true,
  costs: true,
  approvals: true,
};
const mockFeatureToggles = { ...defaultFeatureToggles };

vi.mock('@/stores', () => ({
  useWorkspaceStore: () => ({
    isFeatureEnabled: (key: keyof typeof mockFeatureToggles) =>
      !!mockFeatureToggles[key as keyof typeof mockFeatureToggles],
    featureToggles: mockFeatureToggles,
  }),
}));

vi.mock('../ProjectNotesPanel', () => ({
  ProjectNotesPanel: () => <div data-testid="project-notes-panel">ProjectNotesPanel</div>,
}));

function renderSidebar() {
  return render(
    <ProjectSidebar project={mockProject} workspaceSlug="test-ws" />
  );
}

function getNavItem(text: string) {
  return screen.getAllByText(text)[0];
}

function queryNavItem(text: string) {
  return screen.queryAllByText(text)[0] ?? null;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ProjectSidebar feature gating', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(mockFeatureToggles, defaultFeatureToggles);
  });

  describe('NAV_ITEMS visibility', () => {
    it('shows Overview, Issues, Cycles, Knowledge, Artifacts, Chat, Settings by default', () => {
      renderSidebar();

      expect(getNavItem('Overview')).toBeInTheDocument();
      expect(getNavItem('Issues')).toBeInTheDocument();
      expect(getNavItem('Cycles')).toBeInTheDocument();
      expect(getNavItem('Knowledge')).toBeInTheDocument();
      expect(getNavItem('Artifacts')).toBeInTheDocument();
      expect(getNavItem('Chat')).toBeInTheDocument();
      expect(getNavItem('Settings')).toBeInTheDocument();
    });

    it('hides Issues and Cycles when issues feature is disabled', () => {
      mockFeatureToggles.issues = false;
      renderSidebar();

      expect(queryNavItem('Issues')).not.toBeInTheDocument();
      expect(queryNavItem('Cycles')).not.toBeInTheDocument();
      expect(getNavItem('Overview')).toBeInTheDocument();
      expect(getNavItem('Artifacts')).toBeInTheDocument();
      expect(getNavItem('Settings')).toBeInTheDocument();
    });

    it('hides Knowledge when knowledge feature is disabled', () => {
      mockFeatureToggles.knowledge = false;
      renderSidebar();

      expect(queryNavItem('Knowledge')).not.toBeInTheDocument();
      expect(getNavItem('Issues')).toBeInTheDocument();
    });

    it('hides Chat when skills feature is disabled', () => {
      mockFeatureToggles.skills = false;
      renderSidebar();

      expect(queryNavItem('Chat')).not.toBeInTheDocument();
      expect(getNavItem('Artifacts')).toBeInTheDocument();
    });

    it('always shows Overview regardless of feature toggles', () => {
      mockFeatureToggles.issues = false;
      mockFeatureToggles.knowledge = false;
      mockFeatureToggles.skills = false;
      renderSidebar();

      expect(getNavItem('Overview')).toBeInTheDocument();
      expect(getNavItem('Artifacts')).toBeInTheDocument();
      expect(getNavItem('Settings')).toBeInTheDocument();
    });

    it('always shows Artifacts and Settings regardless of feature toggles', () => {
      mockFeatureToggles.issues = false;
      mockFeatureToggles.knowledge = false;
      mockFeatureToggles.skills = false;
      renderSidebar();

      expect(getNavItem('Artifacts')).toBeInTheDocument();
      expect(getNavItem('Settings')).toBeInTheDocument();
    });
  });

  describe('Recent notes section (ProjectNotesPanel)', () => {
    it('shows ProjectNotesPanel when notes feature is enabled', () => {
      mockFeatureToggles.notes = true;
      renderSidebar();

      expect(screen.getByTestId('project-notes-panel')).toBeInTheDocument();
    });

    it('hides ProjectNotesPanel when notes feature is disabled', () => {
      mockFeatureToggles.notes = false;
      renderSidebar();

      expect(screen.queryByTestId('project-notes-panel')).not.toBeInTheDocument();
    });
  });
});
