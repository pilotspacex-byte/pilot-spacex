/**
 * Tests for RelatedIssuesPanel — Phase 15 (Related Issues).
 *
 * RELISS-01: semantic suggestion display
 * RELISS-02: manual linking UI
 * RELISS-03: reason badge enrichment
 * RELISS-04: dismissal flow
 *
 * Wave 0 stubs: all tests are it.todo() pending state.
 * The component does not exist yet — do NOT import it here.
 * Stubs will be promoted to real tests in phase 15 plan 04.
 */
import { describe, it } from 'vitest';

describe('RelatedIssuesPanel', () => {
  // RELISS-01
  it.todo('renders AI suggestions with similarity reason badge');
  it.todo('renders empty state when no suggestions available');

  // RELISS-04
  it.todo('dismiss button calls mutation and invalidates suggestions query');

  // RELISS-02
  it.todo('renders linked issues section with unlink button');
  it.todo('link issue search calls createRelation and refreshes list');
});
