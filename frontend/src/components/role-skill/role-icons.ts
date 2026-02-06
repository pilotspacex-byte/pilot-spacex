/**
 * Icon mapping for SDLC role templates.
 *
 * Maps backend `icon` field values to Lucide React icon components.
 * T019: RoleCard icon support
 * Source: data-model.md seed data
 */

import {
  FileSearch,
  Target,
  Code,
  TestTube,
  Layers,
  GitBranch,
  BarChart3,
  Container,
  Pencil,
  type LucideIcon,
} from 'lucide-react';

/**
 * Map from backend role_template.icon field to Lucide component.
 *
 * Backend seed values (from data-model.md):
 *   FileSearch, Target, Code, TestTube, Layers,
 *   GitBranch, GanttChart, Container
 *
 * Note: Lucide does not export "GanttChart" — we use BarChart3 instead.
 */
export const ROLE_ICON_MAP: Record<string, LucideIcon> = {
  FileSearch,
  Target,
  Code,
  TestTube,
  Layers,
  GitBranch,
  GanttChart: BarChart3,
  BarChart3,
  Container,
  Pencil,
};

/**
 * Resolve a backend icon name to a Lucide component.
 * Falls back to Code icon for unknown values.
 */
export function getRoleIcon(iconName: string): LucideIcon {
  return ROLE_ICON_MAP[iconName] ?? Code;
}
