/**
 * useExtractionResult - Wave 0 failing test scaffold
 * Covers TanStack Query hook for extraction API
 */
import { describe, it } from 'vitest';

// Will be created in Plan 02
// import { useExtractionResult } from '../useExtractionResult';

describe('useExtractionResult', () => {
  it.todo('does not fetch when open is false');
  it.todo('does not fetch when artifactId is empty string');
  it.todo('fetches when open=true and artifactId is set');
  it.todo('polls every 5s while extractionSource is "none"');
  it.todo('stops polling when extractionSource is not "none"');
});
