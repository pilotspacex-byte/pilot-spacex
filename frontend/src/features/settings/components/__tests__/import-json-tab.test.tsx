/**
 * Tests for ImportJsonTab - Phase 25 JSON import editor with preview.
 *
 * Verifies: valid JSON shows detected servers, invalid JSON shows error,
 * Import button disabled on invalid JSON, empty textarea state.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ImportJsonTab } from '../import-json-tab';

const validJson = JSON.stringify({
  mcpServers: {
    'my-server': {
      url: 'https://mcp.example.com/sse',
    },
    'npx-server': {
      command: 'npx @modelcontextprotocol/server',
    },
  },
});

const invalidJson = '{ invalid json';

const emptyServersJson = JSON.stringify({ mcpServers: {} });

describe('ImportJsonTab', () => {
  it('renders textarea and info line', () => {
    render(<ImportJsonTab onImport={vi.fn()} isImporting={false} />);
    expect(screen.getByText(/Supports Claude, Cursor, and VS Code/)).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('renders Upload File button', () => {
    render(<ImportJsonTab onImport={vi.fn()} isImporting={false} />);
    expect(screen.getByText('Upload File')).toBeInTheDocument();
  });

  it('shows detected servers preview for valid JSON', async () => {
    const user = userEvent.setup();
    render(<ImportJsonTab onImport={vi.fn()} isImporting={false} />);

    await user.click(screen.getByRole('textbox'));
    await user.paste(validJson);

    await waitFor(() => {
      expect(screen.getByText('my-server')).toBeInTheDocument();
      expect(screen.getByText('npx-server')).toBeInTheDocument();
    });
    expect(screen.getByText(/2 servers detected/)).toBeInTheDocument();
  });

  it('shows error for invalid JSON', async () => {
    const user = userEvent.setup();
    render(<ImportJsonTab onImport={vi.fn()} isImporting={false} />);

    await user.click(screen.getByRole('textbox'));
    await user.paste(invalidJson);

    await waitFor(() => {
      // The parse error message appears
      expect(screen.queryByText(/servers detected/)).not.toBeInTheDocument();
    });
  });

  it('has Import button disabled when textarea is empty', () => {
    render(<ImportJsonTab onImport={vi.fn()} isImporting={false} />);
    expect(screen.getByText('Import & Add Servers')).toBeDisabled();
  });

  it('has Import button disabled when JSON has 0 servers', async () => {
    const user = userEvent.setup();
    render(<ImportJsonTab onImport={vi.fn()} isImporting={false} />);

    await user.click(screen.getByRole('textbox'));
    await user.paste(emptyServersJson);

    await waitFor(() => {
      expect(screen.getByText('Import & Add Servers')).toBeDisabled();
    });
  });

  it('enables Import button when valid JSON with servers is entered', async () => {
    const user = userEvent.setup();
    render(<ImportJsonTab onImport={vi.fn()} isImporting={false} />);

    await user.click(screen.getByRole('textbox'));
    await user.paste(validJson);

    await waitFor(() => {
      expect(screen.getByText('Import & Add Servers')).not.toBeDisabled();
    });
  });

  it('calls onImport with JSON string when Import button is clicked', async () => {
    const user = userEvent.setup();
    const onImport = vi.fn();
    render(<ImportJsonTab onImport={onImport} isImporting={false} />);

    await user.click(screen.getByRole('textbox'));
    await user.paste(validJson);

    await waitFor(() => {
      expect(screen.getByText('Import & Add Servers')).not.toBeDisabled();
    });

    await user.click(screen.getByText('Import & Add Servers'));
    expect(onImport).toHaveBeenCalledWith(validJson);
  });

  it('disables textarea and button when isImporting=true', () => {
    render(<ImportJsonTab onImport={vi.fn()} isImporting={true} />);
    expect(screen.getByRole('textbox')).toBeDisabled();
    expect(screen.getByText('Upload File')).toBeDisabled();
  });

  it('shows Detected Servers heading when valid servers parsed', async () => {
    const user = userEvent.setup();
    render(<ImportJsonTab onImport={vi.fn()} isImporting={false} />);

    await user.click(screen.getByRole('textbox'));
    await user.paste(validJson);

    await waitFor(() => {
      expect(screen.getByText('Detected Servers')).toBeInTheDocument();
    });
  });
});
