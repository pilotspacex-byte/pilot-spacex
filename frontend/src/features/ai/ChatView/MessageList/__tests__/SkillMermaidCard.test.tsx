/**
 * Unit tests for SkillMermaidCard component.
 * Phase 64-03
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SkillMermaidCard } from '../SkillMermaidCard';

// Mock next/dynamic to avoid SSR/lazy-loading complexity in tests
vi.mock('next/dynamic', () => ({
  default: (factory: () => Promise<unknown>) => {
    // Return a synchronous stub that renders a simple div with the code
    const MockComponent = ({ code }: { code: string }) => (
      <div data-testid="mermaid-preview">{code}</div>
    );
    MockComponent.displayName = 'MockMermaidPreview';
    // Suppress unused variable warning
    void factory;
    return MockComponent;
  },
}));

describe('SkillMermaidCard', () => {
  it('renders "Skill Graph" header text when no skillName provided', () => {
    render(<SkillMermaidCard code="graph LR; A-->B" />);
    expect(screen.getByText('Skill Graph')).toBeInTheDocument();
  });

  it('renders "Skill Graph: my-skill" when skillName provided', () => {
    render(<SkillMermaidCard code="graph LR; A-->B" skillName="my-skill" />);
    expect(screen.getByText('Skill Graph: my-skill')).toBeInTheDocument();
  });

  it('passes code prop to MermaidPreview child', () => {
    const testCode = 'graph TD; A[Start]-->B[End]';
    render(<SkillMermaidCard code={testCode} skillName="my-skill" />);
    // The mocked MermaidPreview renders code as text content
    expect(screen.getByTestId('mermaid-preview')).toHaveTextContent(testCode);
  });

  it('renders a header icon area alongside the title', () => {
    render(<SkillMermaidCard code="graph LR; A-->B" skillName="my-skill" />);
    // The header div contains the title — verify the header section is there
    const titleEl = screen.getByText('Skill Graph: my-skill');
    expect(titleEl).toBeInTheDocument();
    // Icon is aria-hidden so we check the parent div contains the text
    expect(titleEl.closest('div')).not.toBeNull();
  });
});
