import { describe, it, expect } from 'vitest';
// These imports will fail until Plan 04 adds the media group — intentional (RED)
import { getDefaultCommands } from '../slash-command-items';

describe('slash command media group', () => {
  it('includes a "media" group in the available groups', () => {
    const commands = getDefaultCommands();
    const groups = [...new Set(commands.map((c) => c.group))];
    expect(groups).toContain('media');
  });

  it('includes /image command in media group', () => {
    const commands = getDefaultCommands();
    const imageCmd = commands.find((c) => c.name === 'image');
    expect(imageCmd).toBeDefined();
    expect(imageCmd?.group).toBe('media');
  });

  it('includes /file command in media group', () => {
    const commands = getDefaultCommands();
    const fileCmd = commands.find((c) => c.name === 'file');
    expect(fileCmd).toBeDefined();
    expect(fileCmd?.group).toBe('media');
  });

  it('/image command has correct keywords for search', () => {
    const commands = getDefaultCommands();
    const imageCmd = commands.find((c) => c.name === 'image');
    expect(imageCmd?.keywords).toContain('upload');
  });

  it('/file command has correct keywords for search', () => {
    const commands = getDefaultCommands();
    const fileCmd = commands.find((c) => c.name === 'file');
    expect(fileCmd?.keywords).toContain('attach');
  });
});
