/**
 * XlsxRenderer tests — XLSX-RENDER
 *
 * Tests SheetJS integration, frozen headers, search, sheet tabs, column resize,
 * truncation, and error fallback.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock xlsx module
const mockRead = vi.fn();
const mockSheetToJson = vi.fn();
const mockDecodeRange = vi.fn();

vi.mock('xlsx', () => ({
  read: (...args: unknown[]) => mockRead(...args),
  utils: {
    sheet_to_json: (...args: unknown[]) => mockSheetToJson(...args),
    decode_range: (...args: unknown[]) => mockDecodeRange(...args),
  },
}));

import { XlsxRenderer } from '../renderers/XlsxRenderer';

// Helper: create a minimal workbook mock
function makeWorkbook(sheets: Record<string, unknown[][]>) {
  const sheetNames = Object.keys(sheets);
  const Sheets: Record<string, { '!ref': string }> = {};
  for (const name of sheetNames) {
    const sheetRows = sheets[name] ?? [];
    Sheets[name] = {
      '!ref': `A1:${String.fromCharCode(64 + ((sheetRows[0] as unknown[])?.length ?? 1))}${sheetRows.length}`,
    };
  }
  return { SheetNames: sheetNames, Sheets };
}

function setupMocks(sheets: Record<string, unknown[][]>) {
  const wb = makeWorkbook(sheets);
  mockRead.mockReturnValue(wb);

  // For each sheet, configure sheet_to_json to return the raw data
  mockSheetToJson.mockImplementation((ws: { '!ref': string }) => {
    // Find which sheet this is by matching the ref
    for (const [name, data] of Object.entries(sheets)) {
      if (wb.Sheets[name] === ws) return data;
    }
    return [];
  });

  // Configure decode_range to return proper range objects
  mockDecodeRange.mockImplementation((ref: string) => {
    // Parse "A1:C5" style refs
    const match = ref.match(/([A-Z]+)(\d+):([A-Z]+)(\d+)/);
    if (!match) return { s: { r: 0, c: 0 }, e: { r: 0, c: 0 } };
    const endCol = match[3]!.charCodeAt(0) - 65;
    const endRow = parseInt(match[4]!, 10) - 1;
    return { s: { r: 0, c: 0 }, e: { r: endRow, c: endCol } };
  });

  return wb;
}

const dummyBuffer = new ArrayBuffer(8);

describe('XlsxRenderer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders table headers from first row of parsed workbook data', async () => {
    setupMocks({
      Sheet1: [
        ['Name', 'Age', 'City'],
        ['Alice', '30', 'NYC'],
      ],
    });

    render(<XlsxRenderer content={dummyBuffer} filename="test.xlsx" signedUrl="" />);

    // Advance the setTimeout(0) used for async parsing
    await act(async () => {
      vi.runAllTimers();
    });

    await waitFor(() => {
      expect(screen.getByText('Name')).toBeDefined();
      expect(screen.getByText('Age')).toBeDefined();
      expect(screen.getByText('City')).toBeDefined();
    });
  });

  it('renders data rows in table body', async () => {
    setupMocks({
      Sheet1: [
        ['Name', 'Age'],
        ['Alice', '30'],
        ['Bob', '25'],
      ],
    });

    render(<XlsxRenderer content={dummyBuffer} filename="test.xlsx" signedUrl="" />);
    await act(async () => {
      vi.runAllTimers();
    });

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeDefined();
      expect(screen.getByText('Bob')).toBeDefined();
    });
  });

  it('shows truncation warning banner when data exceeds 500 rows', async () => {
    // Create data with 502 rows total (1 header + 501 data rows)
    const rows: string[][] = [['Col1']];
    for (let i = 0; i < 501; i++) {
      rows.push([`row${i}`]);
    }
    // Override decode_range to return a large range
    setupMocks({ Sheet1: rows });
    mockDecodeRange.mockReturnValue({ s: { r: 0, c: 0 }, e: { r: 501, c: 0 } });

    render(<XlsxRenderer content={dummyBuffer} filename="test.xlsx" signedUrl="" />);
    await act(async () => {
      vi.runAllTimers();
    });

    await waitFor(() => {
      expect(screen.getByText(/Showing 500 of/)).toBeDefined();
    });
  });

  it('renders sheet tabs for multi-sheet workbooks', async () => {
    setupMocks({
      Sales: [['Revenue'], ['100']],
      Expenses: [['Cost'], ['50']],
    });

    render(<XlsxRenderer content={dummyBuffer} filename="test.xlsx" signedUrl="" />);
    await act(async () => {
      vi.runAllTimers();
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Sales' })).toBeDefined();
      expect(screen.getByRole('button', { name: 'Expenses' })).toBeDefined();
    });
  });

  it('switches displayed data when clicking a different sheet tab', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    setupMocks({
      Sheet1: [['Header1'], ['Data1']],
      Sheet2: [['Header2'], ['Data2']],
    });

    render(<XlsxRenderer content={dummyBuffer} filename="test.xlsx" signedUrl="" />);
    await act(async () => {
      vi.runAllTimers();
    });

    // Verify Sheet1 data is shown initially
    await waitFor(() => {
      expect(screen.getByText('Header1')).toBeDefined();
    });

    // Click Sheet2 tab
    await user.click(screen.getByRole('button', { name: 'Sheet2' }));
    await act(async () => {
      vi.runAllTimers();
    });

    await waitFor(() => {
      expect(screen.getByText('Header2')).toBeDefined();
    });
  });

  it('has search input with correct aria-label', async () => {
    setupMocks({ Sheet1: [['A'], ['1']] });

    render(<XlsxRenderer content={dummyBuffer} filename="test.xlsx" signedUrl="" />);
    await act(async () => {
      vi.runAllTimers();
    });

    await waitFor(() => {
      expect(screen.getByLabelText('Search in sheet')).toBeDefined();
    });
  });

  it('renders DownloadFallback on parse error', async () => {
    mockRead.mockImplementation(() => {
      throw new Error('Corrupt file');
    });

    render(<XlsxRenderer content={dummyBuffer} filename="bad.xlsx" signedUrl="/download" />);
    await act(async () => {
      vi.runAllTimers();
    });

    await waitFor(() => {
      // DownloadFallback renders a download link with the filename
      expect(screen.getByText(/bad\.xlsx/)).toBeDefined();
    });
  });

  it('renders column resize handles with separator role', async () => {
    setupMocks({
      Sheet1: [
        ['Col1', 'Col2'],
        ['a', 'b'],
      ],
    });

    render(<XlsxRenderer content={dummyBuffer} filename="test.xlsx" signedUrl="" />);
    await act(async () => {
      vi.runAllTimers();
    });

    await waitFor(() => {
      const separators = screen.getAllByRole('separator');
      expect(separators.length).toBeGreaterThanOrEqual(2);
    });
  });

  it('applies alternating row background to odd rows', async () => {
    setupMocks({
      Sheet1: [['H'], ['r1'], ['r2'], ['r3']],
    });

    const { container } = render(
      <XlsxRenderer content={dummyBuffer} filename="test.xlsx" signedUrl="" />
    );
    await act(async () => {
      vi.runAllTimers();
    });

    await waitFor(() => {
      const tbody = container.querySelector('tbody');
      expect(tbody).not.toBeNull();
      const rows = tbody!.querySelectorAll('tr');
      // Row index 1 (second data row, 0-indexed) should have bg-muted/30
      expect(rows[1]?.className).toContain('bg-muted/30');
    });
  });
});
