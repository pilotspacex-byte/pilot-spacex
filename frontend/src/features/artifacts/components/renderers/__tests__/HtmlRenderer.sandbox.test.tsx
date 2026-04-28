/**
 * Phase 87.1 Plan 04 — T-87.1-04-01 invariant test.
 *
 * Locks in the security posture of HtmlRenderer's iframe:
 *  - sandbox attribute is the empty string (maximum isolation)
 *  - sandbox does NOT contain 'allow-scripts'
 *
 * This is the foundational HTML preview safety contract. If this test fails,
 * AI-generated HTML could execute scripts in the user's session.
 */
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { HtmlRenderer } from '../HtmlRenderer';

describe('HtmlRenderer iframe sandbox invariant (T-87.1-04-01)', () => {
  it('iframe sandbox attribute equals empty string and does not contain allow-scripts', () => {
    const { container } = render(
      <HtmlRenderer content="<p>safe</p>" filename="a.html" />,
    );
    const iframe = container.querySelector('iframe');
    expect(iframe).not.toBeNull();
    const sandbox = iframe!.getAttribute('sandbox');
    expect(sandbox).toBe('');
    expect(sandbox).not.toContain('allow-scripts');
  });
});
