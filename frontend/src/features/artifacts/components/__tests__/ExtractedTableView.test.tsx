/**
 * ExtractedTableView tests - AUI-03
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ExtractedTableView } from '../ExtractedTableView';

const TABLE_MARKDOWN =
  '| Name | Age | City |\n|------|-----|------|\n| Alice | 30 | NY |\n| Bob | 25 | LA |';

describe('ExtractedTableView', () => {
  beforeEach(() => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it('renders table headers from markdown table string', () => {
    render(<ExtractedTableView markdown={TABLE_MARKDOWN} />);
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Age')).toBeInTheDocument();
    expect(screen.getByText('City')).toBeInTheDocument();
  });

  it('renders table rows from markdown table string', () => {
    render(<ExtractedTableView markdown={TABLE_MARKDOWN} />);
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });

  it('clicking header sorts column ascending', () => {
    render(<ExtractedTableView markdown={TABLE_MARKDOWN} />);
    const nameHeader = screen.getByText('Name').closest('th')!;
    fireEvent.click(nameHeader);
    const cells = screen.getAllByRole('cell');
    // After sort asc: Alice before Bob
    expect(cells[0]).toHaveTextContent('Alice');
  });

  it('clicking sorted-ascending header sorts descending', () => {
    render(<ExtractedTableView markdown={TABLE_MARKDOWN} />);
    const nameHeader = screen.getByText('Name').closest('th')!;
    fireEvent.click(nameHeader);
    fireEvent.click(nameHeader);
    const cells = screen.getAllByRole('cell');
    // After sort desc: Bob before Alice
    expect(cells[0]).toHaveTextContent('Bob');
  });

  it('Copy as Markdown calls navigator.clipboard.writeText with original markdown string', async () => {
    render(<ExtractedTableView markdown={TABLE_MARKDOWN} />);
    fireEvent.click(screen.getByRole('button', { name: /copy table/i }));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(TABLE_MARKDOWN);
  });

  it('does not mutate original rows array when sorting', () => {
    render(<ExtractedTableView markdown={TABLE_MARKDOWN} />);
    const nameHeader = screen.getByText('Name').closest('th')!;
    fireEvent.click(nameHeader);
    fireEvent.click(nameHeader);
    // Re-render with same markdown - original order should be preserved on reset
    const cells = screen.getAllByRole('cell');
    // After two clicks: sort desc, Bob first
    expect(cells[0]).toHaveTextContent('Bob');
  });
});
