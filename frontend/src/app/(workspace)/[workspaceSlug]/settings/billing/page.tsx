/**
 * Billing settings page — placeholder for future billing integration.
 * Shows usage summary and plan information (US-11).
 */

import { CreditCard } from 'lucide-react';

export default function BillingSettingsPage() {
  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-foreground">Billing</h2>
        <p className="text-sm text-muted-foreground">Manage your workspace plan and usage.</p>
      </div>

      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border p-12 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <CreditCard className="h-6 w-6 text-muted-foreground" />
        </div>
        <h3 className="mt-4 text-sm font-medium text-foreground">Billing coming soon</h3>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          Pilot Space is free and open source. Paid tiers for support SLAs will be available in a
          future release.
        </p>
      </div>
    </div>
  );
}
