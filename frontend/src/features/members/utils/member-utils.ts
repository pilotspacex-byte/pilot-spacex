/**
 * Shared member display utilities.
 *
 * Used by MemberRow (settings) and MemberCard (members page).
 */

export const ROLE_HIERARCHY: Record<string, number> = {
  owner: 0,
  admin: 1,
  member: 2,
  guest: 3,
};

export const ROLE_BADGE_VARIANT: Record<string, 'default' | 'secondary' | 'outline'> = {
  owner: 'default',
  admin: 'secondary',
  member: 'outline',
  guest: 'outline',
};

export function getInitials(name: string | null, email: string): string {
  if (name) {
    const parts = name
      .trim()
      .split(/\s+/)
      .filter((p) => p.length > 0);
    if (parts.length >= 2) {
      return ((parts[0]?.[0] ?? '') + (parts[parts.length - 1]?.[0] ?? '')).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }
  return email.slice(0, 2).toUpperCase();
}

export function formatJoinDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}
