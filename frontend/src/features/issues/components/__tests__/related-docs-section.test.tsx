/**
 * RelatedDocsSection component tests.
 *
 * Tests for displaying related documentation with type badges and summaries.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RelatedDocsSection } from '../related-docs-section';
import type { ContextRelatedDoc } from '@/stores/ai/AIContextStore';

describe('RelatedDocsSection', () => {
  const mockItems: ContextRelatedDoc[] = [
    {
      docType: 'note',
      title: 'Authentication Implementation Notes',
      summary: 'Detailed notes on OAuth2 implementation with JWT tokens and refresh flow strategy',
    },
    {
      docType: 'adr',
      title: 'ADR-001: Database Selection',
      summary: 'Decision to use PostgreSQL with pgvector for semantic search capabilities',
    },
    {
      docType: 'spec',
      title: 'API Specification v2.0',
      summary: 'REST API endpoints with request/response schemas and authentication requirements',
    },
  ];

  it('renders nothing when items is empty', () => {
    const { container } = render(<RelatedDocsSection items={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders doc type badges (NOTE, ADR, SPEC)', () => {
    render(<RelatedDocsSection items={mockItems} />);

    expect(screen.getByText('NOTE')).toBeInTheDocument();
    expect(screen.getByText('ADR')).toBeInTheDocument();
    expect(screen.getByText('SPEC')).toBeInTheDocument();
  });

  it('renders title for each doc', () => {
    render(<RelatedDocsSection items={mockItems} />);

    expect(screen.getByText('Authentication Implementation Notes')).toBeInTheDocument();
    expect(screen.getByText('ADR-001: Database Selection')).toBeInTheDocument();
    expect(screen.getByText('API Specification v2.0')).toBeInTheDocument();
  });

  it('renders summary for each doc with line-clamp-2', () => {
    render(<RelatedDocsSection items={mockItems} />);

    expect(
      screen.getByText(
        'Detailed notes on OAuth2 implementation with JWT tokens and refresh flow strategy'
      )
    ).toBeInTheDocument();

    const summaries = document.querySelectorAll('.line-clamp-2');
    expect(summaries.length).toBe(3);
    summaries.forEach((summary) => {
      expect(summary).toHaveClass('line-clamp-2');
    });
  });

  it('handles items without summary gracefully', () => {
    const items: ContextRelatedDoc[] = [
      { docType: 'note', title: 'Meeting Notes 2024-01-15' },
      { docType: 'adr', title: 'ADR-002: Framework Selection' },
    ];

    render(<RelatedDocsSection items={items} />);

    expect(screen.getByText('Meeting Notes 2024-01-15')).toBeInTheDocument();
    expect(document.querySelectorAll('.line-clamp-2').length).toBe(0);
  });

  it('renders custom doc type with default styling', () => {
    const items: ContextRelatedDoc[] = [
      { docType: 'rfc', title: 'RFC-001: Custom Protocol', summary: 'Proposal' },
    ];

    render(<RelatedDocsSection items={items} />);

    expect(screen.getByText('RFC')).toBeInTheDocument();
  });
});
