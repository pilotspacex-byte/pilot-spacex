/**
 * ApprovalOverlay - Manages multiple approval requests
 * Shows badge indicator and opens dialog for active approvals
 */

import { useCallback, useState, useEffect, useRef } from 'react';
import { observer } from 'mobx-react-lite';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ApprovalRequest } from '../types';
import { ApprovalDialog } from './ApprovalDialog';

interface ApprovalOverlayProps {
  approvals: ApprovalRequest[];
  onApprove: (id: string, modifications?: Record<string, unknown>) => Promise<void>;
  onReject: (id: string, reason: string) => Promise<void>;
  className?: string;
}

export const ApprovalOverlay = observer<ApprovalOverlayProps>(
  ({ approvals, onApprove, onReject, className }) => {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    // Track last seen approval count to detect genuinely new arrivals
    const lastSeenCountRef = useRef(0);

    const currentApproval = approvals[currentIndex] || null;
    const hasApprovals = approvals.length > 0;

    // Auto-open dialog only when new approvals arrive (not on dismiss)
    useEffect(() => {
      if (hasApprovals && approvals.length > lastSeenCountRef.current) {
        setIsDialogOpen(true);
        setCurrentIndex(0);
      }
      lastSeenCountRef.current = approvals.length;
    }, [hasApprovals, approvals.length]);

    const handleNext = useCallback(() => {
      if (currentIndex < approvals.length - 1) {
        setCurrentIndex((prev) => prev + 1);
      } else {
        setIsDialogOpen(false);
        setCurrentIndex(0);
      }
    }, [currentIndex, approvals.length]);

    const handleClose = useCallback(() => {
      setIsDialogOpen(false);
    }, []);

    const handleApprove = useCallback(
      async (id: string, modifications?: Record<string, unknown>) => {
        await onApprove(id, modifications);
        handleNext();
      },
      [onApprove, handleNext]
    );

    const handleReject = useCallback(
      async (id: string, reason: string) => {
        await onReject(id, reason);
        handleNext();
      },
      [onReject, handleNext]
    );

    if (!hasApprovals) return null;

    return (
      <>
        {/* Floating indicator */}
        <div className={cn('fixed bottom-4 left-4 z-50', className)} data-testid="approval-overlay">
          <Button
            variant="default"
            size="lg"
            onClick={() => setIsDialogOpen(true)}
            className="gap-2 shadow-lg animate-pulse hover:animate-none"
          >
            <AlertTriangle className="h-5 w-5" />
            <span>Approval Required</span>
            <Badge variant="secondary" className="bg-background text-foreground ml-2">
              {approvals.length}
            </Badge>
          </Button>
        </div>

        {/* Dialog */}
        <ApprovalDialog
          approval={currentApproval}
          isOpen={isDialogOpen}
          onClose={handleClose}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      </>
    );
  }
);

ApprovalOverlay.displayName = 'ApprovalOverlay';
