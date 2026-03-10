/**
 * AI Governance settings route — /[workspaceSlug]/settings/ai-governance
 *
 * AIGOV-02: Policy matrix for per-role AI action approval configuration.
 */

import { AIGovernanceSettingsPage } from '@/features/settings/pages/ai-governance-settings-page';

export default function AIGovernancePage() {
  return <AIGovernanceSettingsPage />;
}
