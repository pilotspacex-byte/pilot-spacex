import { describe, it, expect } from 'vitest';
import { hashString } from '../debounce';

describe('hashString', () => {
  it('generates consistent hash for same input', () => {
    const title = 'Fix login button';
    const hash1 = hashString(title);
    const hash2 = hashString(title);

    expect(hash1).toBe(hash2);
  });

  it('generates same hash for titles with different whitespace', () => {
    const title1 = 'Fix login button';
    const title2 = 'Fix  login   button';
    const title3 = ' Fix login button ';

    const hash1 = hashString(title1);
    const hash2 = hashString(title2);
    const hash3 = hashString(title3);

    expect(hash1).toBe(hash2);
    expect(hash2).toBe(hash3);
  });

  it('generates same hash for titles with different casing', () => {
    const title1 = 'Fix Login Button';
    const title2 = 'fix login button';
    const title3 = 'FIX LOGIN BUTTON';

    const hash1 = hashString(title1);
    const hash2 = hashString(title2);
    const hash3 = hashString(title3);

    expect(hash1).toBe(hash2);
    expect(hash2).toBe(hash3);
  });

  it('generates different hashes for different titles', () => {
    const title1 = 'Fix login button';
    const title2 = 'Fix logout button';

    const hash1 = hashString(title1);
    const hash2 = hashString(title2);

    expect(hash1).not.toBe(hash2);
  });

  it('returns hex string', () => {
    const title = 'Fix login button';
    const hash = hashString(title);

    expect(hash).toMatch(/^[0-9a-f]+$/);
  });
});
