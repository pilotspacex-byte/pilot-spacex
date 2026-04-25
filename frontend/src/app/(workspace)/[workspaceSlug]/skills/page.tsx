/**
 * Skills gallery route — Phase 91 Plan 03.
 *
 * Replaces the legacy SkillsSettingsPage mount with the new gallery surface.
 * The role-skills settings page is preserved at `/{slug}/settings/skills`
 * and `/{slug}/roles` (both routes untouched by this plan).
 */
import { SkillsGalleryPage } from '@/features/skills';

export default function SkillsPage() {
  return <SkillsGalleryPage />;
}
