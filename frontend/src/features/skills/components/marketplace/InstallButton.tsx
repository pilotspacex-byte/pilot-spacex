'use client';

/**
 * InstallButton - Smart button with Install/Installed/Update states.
 *
 * State determination:
 * - Checks marketplace updates for an entry matching listing.id
 * - If update available: "Update to vX.Y.Z" with changelog confirmation
 * - If installed: "Installed" badge (disabled)
 * - If not installed: "Install" button
 *
 * Source: Phase 055, P55-03
 */

import { useCallback, useState } from 'react';
import { Check, Download, Loader2, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { MarketplaceListingResponse } from '@/services/api/marketplace';
import {
  useInstallListing,
  useMarketplaceUpdates,
  useApplyUpdate,
  useMarketplaceVersions,
} from '@/features/skills/hooks/use-marketplace';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface InstallButtonProps {
  listing: MarketplaceListingResponse;
  workspaceId: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function InstallButton({ listing, workspaceId }: InstallButtonProps) {
  const [localInstalled, setLocalInstalled] = useState(false);
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false);

  const { data: updates } = useMarketplaceUpdates(workspaceId);
  const { data: versions } = useMarketplaceVersions(workspaceId, listing.id);
  const installMutation = useInstallListing(workspaceId);
  const updateMutation = useApplyUpdate(workspaceId);

  // Determine state
  const updateEntry = updates?.find((u) => u.listingId === listing.id);
  const hasUpdate = !!updateEntry;
  const isInstalled = localInstalled || (!hasUpdate && !!updateEntry);

  // Latest version changelog
  const latestVersion = versions?.[0];

  const handleInstall = useCallback(async () => {
    try {
      const result = await installMutation.mutateAsync(listing.id);
      if (result.alreadyInstalled) {
        setLocalInstalled(true);
        toast.info('Already installed');
      } else {
        setLocalInstalled(true);
        toast.success('Installed!', {
          description: `${listing.name} has been added to your workspace.`,
        });
      }
    } catch {
      toast.error('Installation failed', {
        description: 'Please try again.',
      });
    }
  }, [installMutation, listing.id, listing.name]);

  const handleUpdateConfirm = useCallback(async () => {
    if (!updateEntry) return;
    try {
      const result = await updateMutation.mutateAsync(updateEntry.templateId);
      setUpdateDialogOpen(false);
      toast.success(`Updated to v${result.newVersion}!`, {
        description: `${listing.name} has been updated.`,
      });
    } catch {
      toast.error('Update failed', {
        description: 'Please try again.',
      });
    }
  }, [updateMutation, updateEntry, listing.name]);

  const handleUpdateClick = useCallback(() => {
    setUpdateDialogOpen(true);
  }, []);

  // Render: Update available
  if (hasUpdate) {
    return (
      <>
        <Button onClick={handleUpdateClick} disabled={updateMutation.isPending}>
          {updateMutation.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Update to v{updateEntry.availableVersion}
        </Button>

        <Dialog open={updateDialogOpen} onOpenChange={setUpdateDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Update {listing.name}</DialogTitle>
              <DialogDescription>
                v{updateEntry.installedVersion} → v{updateEntry.availableVersion}
              </DialogDescription>
            </DialogHeader>

            {latestVersion?.changelog && (
              <div className="rounded-lg border bg-muted/50 p-4">
                <p className="mb-1 text-sm font-medium">Changelog</p>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {latestVersion.changelog}
                </p>
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={() => setUpdateDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleUpdateConfirm} disabled={updateMutation.isPending}>
                {updateMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Apply Update
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </>
    );
  }

  // Render: Already installed
  if (isInstalled) {
    return (
      <Button variant="outline" disabled className="pointer-events-none">
        <Check className="mr-2 h-4 w-4" />
        Installed
      </Button>
    );
  }

  // Render: Not installed
  return (
    <Button onClick={handleInstall} disabled={installMutation.isPending}>
      {installMutation.isPending ? (
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      ) : (
        <Download className="mr-2 h-4 w-4" />
      )}
      Install
    </Button>
  );
}
