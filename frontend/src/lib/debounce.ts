/**
 * Simple debounce utility for delaying function execution until after
 * a specified wait time has elapsed since the last invocation.
 *
 * @param fn - Function to debounce
 * @param ms - Milliseconds to delay
 * @returns Debounced function
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  ms: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout | null = null;

  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(() => {
      fn(...args);
      timeoutId = null;
    }, ms);
  };
}

/**
 * Simple string hash function for deduplication.
 * Returns a deterministic hash for the same input.
 *
 * @param str - String to hash
 * @returns Hash string
 */
export function hashString(str: string): string {
  // Normalize: lowercase + trim + collapse whitespace
  const normalized = str.toLowerCase().trim().replace(/\s+/g, ' ');

  // Simple DJB2 hash algorithm
  let hash = 5381;
  for (let i = 0; i < normalized.length; i++) {
    hash = (hash * 33) ^ normalized.charCodeAt(i);
  }

  // Convert to unsigned 32-bit integer and format as hex
  return (hash >>> 0).toString(16);
}
