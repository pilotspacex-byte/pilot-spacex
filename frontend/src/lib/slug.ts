/**
 * Convert an arbitrary string to a valid workspace slug.
 * Rules: lowercase, letters/numbers/hyphens only, max 48 chars,
 * no leading/trailing hyphens, no consecutive hyphens.
 */
export function toSlug(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-{2,}/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48);
}
