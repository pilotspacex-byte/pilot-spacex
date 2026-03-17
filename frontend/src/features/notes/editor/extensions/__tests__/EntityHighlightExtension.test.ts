/**
 * Unit tests for EntityHighlightExtension — findEntityMatches + pointermove guard.
 *
 * Validates project name detection: case-insensitive matching,
 * word boundary respect, correct from/to positions, empty input,
 * and special regex character safety.
 *
 * Also covers the C-2 global pointermove guard (showCard / hideCard):
 *   1. document listener is attached when a card show is scheduled
 *   2. a pointermove off a highlight hides / cancels the pending card and
 *      detaches the listener
 *   3. the listener is detached when hideCard() runs (including destroy)
 *
 * @module features/notes/editor/extensions/__tests__/EntityHighlightExtension.test
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  findEntityMatches,
  _showCard,
  _hideCard,
  _isDocumentListenerAttached,
} from '../EntityHighlightExtension';

/**
 * Minimal ProseMirror doc mock for testing text traversal.
 */
function createMockDoc(texts: string[]) {
  const textNodes = texts.map((text) => ({
    isText: true,
    text,
  }));

  return {
    descendants(callback: (node: { isText: boolean; text?: string }, pos: number) => boolean) {
      let pos = 0;
      for (const node of textNodes) {
        callback(node, pos);
        pos += node.text?.length ?? 0;
      }
    },
  } as unknown as Parameters<typeof findEntityMatches>[0];
}

const entities = [
  { name: 'Frontend', projectId: 'proj-1' },
  { name: 'Backend API', projectId: 'proj-2' },
  { name: 'Pilot Space', projectId: 'proj-3' },
];

describe('findEntityMatches', () => {
  it('test_finds_exact_project_name_in_text', () => {
    const doc = createMockDoc(['Working on Frontend today']);
    const matches = findEntityMatches(doc, entities);

    expect(matches).toHaveLength(1);
    expect(matches[0]).toMatchObject({
      name: 'Frontend',
      projectId: 'proj-1',
      from: 11,
      to: 19,
    });
  });

  it('test_case_insensitive_matching', () => {
    const doc = createMockDoc(['The frontend team is great']);
    const matches = findEntityMatches(doc, entities);

    expect(matches).toHaveLength(1);
    expect(matches[0]).toMatchObject({
      name: 'frontend',
      projectId: 'proj-1',
    });
  });

  it('test_matches_multi_word_project_names', () => {
    const doc = createMockDoc(['Check the Backend API docs and Pilot Space repo']);
    const matches = findEntityMatches(doc, entities);

    expect(matches).toHaveLength(2);
    expect(matches[0]).toMatchObject({ name: 'Backend API', projectId: 'proj-2' });
    expect(matches[1]).toMatchObject({ name: 'Pilot Space', projectId: 'proj-3' });
  });

  it('test_respects_word_boundaries — no partial matches', () => {
    const doc = createMockDoc(['FrontendX is not Frontend']);
    const matches = findEntityMatches(doc, entities);

    // Only "Frontend" at the end should match, not "FrontendX"
    expect(matches).toHaveLength(1);
    expect(matches[0]).toMatchObject({ name: 'Frontend' });
    // Verify "FrontendX" was NOT matched
    expect(matches.some((m) => m.name === 'FrontendX')).toBe(false);
  });

  it('test_returns_correct_positions_for_multiple_matches', () => {
    const doc = createMockDoc(['Frontend and Frontend again']);
    const matches = findEntityMatches(doc, entities);

    expect(matches).toHaveLength(2);
    expect(matches[0]).toMatchObject({ from: 0, to: 8 });
    expect(matches[1]).toMatchObject({ from: 13, to: 21 });
  });

  it('test_empty_entities_returns_no_matches', () => {
    const doc = createMockDoc(['Frontend Backend']);
    const matches = findEntityMatches(doc, []);
    expect(matches).toHaveLength(0);
  });

  it('test_empty_document_returns_no_matches', () => {
    const doc = createMockDoc([]);
    const matches = findEntityMatches(doc, entities);
    expect(matches).toHaveLength(0);
  });

  it('test_handles_special_regex_characters_in_project_names', () => {
    const specialEntities = [
      { name: 'C++ Engine', projectId: 'proj-cpp' },
      { name: 'My (Project)', projectId: 'proj-parens' },
    ];
    const doc = createMockDoc(['Working on C++ Engine and My (Project)']);
    const matches = findEntityMatches(doc, specialEntities);

    expect(matches).toHaveLength(2);
    expect(matches[0]).toMatchObject({ name: 'C++ Engine', projectId: 'proj-cpp' });
    expect(matches[1]).toMatchObject({ name: 'My (Project)', projectId: 'proj-parens' });
  });

  it('test_ignores_short_names_under_2_chars', () => {
    const shortEntities = [
      { name: 'X', projectId: 'proj-x' },
      { name: 'OK', projectId: 'proj-ok' },
    ];
    const doc = createMockDoc(['X is short but OK is fine']);
    const matches = findEntityMatches(doc, shortEntities);

    // Only "OK" should match (>= 2 chars)
    expect(matches).toHaveLength(1);
    expect(matches[0]).toMatchObject({ name: 'OK', projectId: 'proj-ok' });
  });
});

// ---------------------------------------------------------------------------
// C-2: Global pointermove guard tests
// ---------------------------------------------------------------------------

/**
 * A stub DOMRect returned by getBoundingClientRect() in the hover handlers.
 * Positioned well within a 1024×768 viewport so the card never flips above.
 */
const STUB_RECT: DOMRect = {
  left: 100,
  right: 200,
  top: 100,
  bottom: 120,
  width: 100,
  height: 20,
  x: 100,
  y: 100,
  toJSON() {
    return this;
  },
};

const STUB_ENTITY = { name: 'Frontend', projectId: 'proj-1', from: 0, to: 8 };

/**
 * Dispatch a synthetic pointermove event on document, optionally targeting a
 * specific element (defaults to document.body which is outside any
 * .entity-highlight).
 *
 * jsdom does not ship PointerEvent, so we create a plain Event whose `target`
 * property is overridden before dispatch. The module's onDocumentPointerMove
 * handler only inspects `event.target`, so this is sufficient.
 */
function firePointerMove(target: EventTarget = document.body): void {
  const event = new Event('pointermove', { bubbles: true, cancelable: true });
  // Override the read-only `target` property so onDocumentPointerMove sees it
  Object.defineProperty(event, 'target', { value: target, configurable: true });
  document.dispatchEvent(event);
}

describe('C-2 pointermove guard — showCard / hideCard', () => {
  let addListenerSpy: ReturnType<typeof vi.spyOn>;
  let removeListenerSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // Use fake timers so the 300 ms showCard delay is under test control
    vi.useFakeTimers();

    // Spy on document listener registration
    addListenerSpy = vi.spyOn(document, 'addEventListener');
    removeListenerSpy = vi.spyOn(document, 'removeEventListener');

    // Guarantee a clean slate before every test by hiding any lingering card
    _hideCard();
    addListenerSpy.mockClear();
    removeListenerSpy.mockClear();
  });

  afterEach(() => {
    // Always clean up so module-level state does not bleed between tests
    _hideCard();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // -------------------------------------------------------------------------
  // Assertion 1: listener is attached when a card show is scheduled
  // -------------------------------------------------------------------------
  it('test_document_listener_attached_when_card_show_is_scheduled', () => {
    // The listener should not be attached before showCard
    expect(_isDocumentListenerAttached()).toBe(false);

    _showCard(STUB_ENTITY, STUB_RECT);

    // attachDocumentListener() is called synchronously inside showCard()
    // (before the 300 ms timeout fires)
    expect(_isDocumentListenerAttached()).toBe(true);
    expect(addListenerSpy).toHaveBeenCalledWith('pointermove', expect.any(Function));
  });

  it('test_document_listener_not_added_twice_for_consecutive_showCard_calls', () => {
    _showCard(STUB_ENTITY, STUB_RECT);
    addListenerSpy.mockClear();

    // A second showCard (e.g. hovering another highlight) must not double-register
    _showCard(STUB_ENTITY, STUB_RECT);

    expect(addListenerSpy).not.toHaveBeenCalledWith('pointermove', expect.any(Function));
    expect(_isDocumentListenerAttached()).toBe(true);
  });

  // -------------------------------------------------------------------------
  // Assertion 2: pointermove outside a highlight hides the pending card and
  //              detaches the listener
  // -------------------------------------------------------------------------
  it('test_pointermove_off_highlight_cancels_pending_card_and_detaches_listener', () => {
    _showCard(STUB_ENTITY, STUB_RECT);
    expect(_isDocumentListenerAttached()).toBe(true);

    // Move pointer to an element that is NOT inside .entity-highlight
    // (document.body by default has no .entity-highlight ancestor)
    firePointerMove(document.body);

    // The guard should have called hideCard() synchronously
    expect(_isDocumentListenerAttached()).toBe(false);
    expect(removeListenerSpy).toHaveBeenCalledWith('pointermove', expect.any(Function));

    // Also confirm the scheduled timeout was cancelled (advancing time produces no card)
    vi.runAllTimers();
    expect(document.body.querySelector('.entity-preview-card')).toBeNull();
  });

  it('test_pointermove_inside_highlight_does_not_hide_card', () => {
    _showCard(STUB_ENTITY, STUB_RECT);

    // Create an element that IS inside .entity-highlight
    const highlight = document.createElement('span');
    highlight.className = 'entity-highlight';
    document.body.appendChild(highlight);

    firePointerMove(highlight);

    // Card should still be pending
    expect(_isDocumentListenerAttached()).toBe(true);

    // Advance time to verify the card actually renders
    vi.runAllTimers();
    const card = document.body.querySelector('.entity-preview-card');
    expect(card).not.toBeNull();

    // Clean up DOM
    highlight.remove();
  });

  it('test_pointermove_inside_child_of_highlight_does_not_hide_card', () => {
    // Validates the .closest() fix: the event target may be a child node
    // nested inside the .entity-highlight span (e.g. a <strong> inside it)
    _showCard(STUB_ENTITY, STUB_RECT);

    const highlight = document.createElement('span');
    highlight.className = 'entity-highlight';
    const inner = document.createElement('strong');
    highlight.appendChild(inner);
    document.body.appendChild(highlight);

    // Target is the inner <strong>, which is a descendant of .entity-highlight
    firePointerMove(inner);

    expect(_isDocumentListenerAttached()).toBe(true);

    // Clean up DOM
    highlight.remove();
  });

  // -------------------------------------------------------------------------
  // Assertion 3: listener is detached when hideCard() runs
  // -------------------------------------------------------------------------
  it('test_document_listener_detached_when_hideCard_is_called_directly', () => {
    _showCard(STUB_ENTITY, STUB_RECT);
    expect(_isDocumentListenerAttached()).toBe(true);

    _hideCard();

    expect(_isDocumentListenerAttached()).toBe(false);
    expect(removeListenerSpy).toHaveBeenCalledWith('pointermove', expect.any(Function));
  });

  it('test_document_listener_detached_on_plugin_destroy_via_hideCard', () => {
    // The plugin's destroy() hook calls hideCard() — simulate that path
    _showCard(STUB_ENTITY, STUB_RECT);

    // Advance timers so the card is in the DOM (tests a richer destroy scenario)
    vi.runAllTimers();
    expect(document.body.querySelector('.entity-preview-card')).not.toBeNull();

    // Simulate destroy()
    _hideCard();

    expect(_isDocumentListenerAttached()).toBe(false);
    expect(removeListenerSpy).toHaveBeenCalledWith('pointermove', expect.any(Function));
    // Card must also be removed from the DOM
    expect(document.body.querySelector('.entity-preview-card')).toBeNull();
  });

  it('test_hideCard_is_idempotent_when_no_card_is_active', () => {
    // Calling hideCard() when nothing is scheduled must not throw and must not
    // attempt to remove a listener that was never attached
    expect(() => _hideCard()).not.toThrow();
    expect(removeListenerSpy).not.toHaveBeenCalledWith('pointermove', expect.any(Function));
    expect(_isDocumentListenerAttached()).toBe(false);
  });
});
