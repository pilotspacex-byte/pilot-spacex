/**
 * Unit tests for the /link-note slash command.
 *
 * Verifies the command is registered with correct metadata.
 *
 * @module features/notes/editor/extensions/__tests__/slash-command-link-note.test
 */
import { describe, it, expect, vi } from 'vitest';
import { getDefaultCommands, filterCommands } from '../slash-command-items';

describe('/link-note slash command', () => {
  const commands = getDefaultCommands();

  it('is registered in default commands', () => {
    const linkNote = commands.find((c) => c.name === 'link-note');
    expect(linkNote).toBeDefined();
  });

  it('has correct metadata', () => {
    const linkNote = commands.find((c) => c.name === 'link-note')!;
    expect(linkNote.label).toBe('Link Note');
    expect(linkNote.description).toBe('Insert a linked note reference');
    expect(linkNote.icon).toBe('FileSymlink');
    expect(linkNote.group).toBe('blocks');
  });

  it('has searchable keywords', () => {
    const linkNote = commands.find((c) => c.name === 'link-note')!;
    expect(linkNote.keywords).toContain('note');
    expect(linkNote.keywords).toContain('link');
    expect(linkNote.keywords).toContain('wiki');
  });

  it('is found when filtering by "note"', () => {
    const results = filterCommands(commands, 'note');
    const linkNote = results.find((c) => c.name === 'link-note');
    expect(linkNote).toBeDefined();
  });

  it('is found when filtering by "wiki"', () => {
    const results = filterCommands(commands, 'wiki');
    const linkNote = results.find((c) => c.name === 'link-note');
    expect(linkNote).toBeDefined();
  });

  it('execute inserts [[ to trigger autocomplete', () => {
    const linkNote = commands.find((c) => c.name === 'link-note')!;
    const mockChain = {
      focus: vi.fn().mockReturnThis(),
      insertContent: vi.fn().mockReturnThis(),
      run: vi.fn(),
    };
    const mockEditor = { chain: () => mockChain } as never;

    linkNote.execute(mockEditor);

    expect(mockChain.insertContent).toHaveBeenCalledWith('[[');
    expect(mockChain.run).toHaveBeenCalled();
  });
});
