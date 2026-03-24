export interface BreadcrumbSegment {
  /** Display label for this segment (file or folder name). */
  label: string;
  /** Full path up to and including this segment. */
  path: string;
  /** True if this is the last (current file) segment. */
  isLast: boolean;
  /** True if this is the first segment. */
  isFirst: boolean;
  /** Sibling files/folders at this level in the tree. */
  siblings: { id: string; name: string; path: string }[];
}
