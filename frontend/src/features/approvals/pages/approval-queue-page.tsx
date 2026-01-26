'use client';

/**
 * Approval Queue Page - List and manage AI approval requests.
 *
 * T189: Shows pending approvals for workspace with filtering and status tabs.
 * Implements DD-003 human-in-the-loop approval flow.
 *
 * @example
 * ```tsx
 * <ApprovalQueuePage />
 * ```
 */

import { useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { AlertCircle, CheckCircle, XCircle, Clock } from 'lucide-react';
import { useAIStore } from '@/stores';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ApprovalCard } from '../components/approval-card';
import { ApprovalDetailModal } from '../components/approval-detail-modal';
import type { ApprovalRequest } from '@/services/api/ai';

// ============================================================================
// Types
// ============================================================================

type ApprovalFilter = 'pending' | 'approved' | 'rejected' | 'expired' | 'all';

// ============================================================================
// Empty State Component
// ============================================================================

interface EmptyStateProps {
  filter: ApprovalFilter;
}

function EmptyState({ filter }: EmptyStateProps) {
  const messages = {
    pending: {
      icon: CheckCircle,
      title: 'No Pending Approvals',
      description: 'All AI actions have been reviewed. New requests will appear here.',
    },
    approved: {
      icon: CheckCircle,
      title: 'No Approved Actions',
      description: 'Approved AI actions will appear here.',
    },
    rejected: {
      icon: XCircle,
      title: 'No Rejected Actions',
      description: 'Rejected AI actions will appear here.',
    },
    expired: {
      icon: Clock,
      title: 'No Expired Requests',
      description: 'Expired approval requests will appear here.',
    },
    all: {
      icon: AlertCircle,
      title: 'No Approval Requests',
      description: 'Approval requests from AI agents will appear here.',
    },
  };

  const config = messages[filter];
  const Icon = config.icon;

  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Icon className="size-12 mb-4 text-muted-foreground opacity-50" />
      <h3 className="text-lg font-semibold mb-2">{config.title}</h3>
      <p className="text-sm text-muted-foreground max-w-md">{config.description}</p>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export const ApprovalQueuePage = observer(function ApprovalQueuePage() {
  const aiStore = useAIStore();
  const { approval } = aiStore;

  const [selectedRequest, setSelectedRequest] = useState<ApprovalRequest | null>(null);
  const [activeTab, setActiveTab] = useState<ApprovalFilter>('pending');

  // Load approvals on mount and when filter changes
  useEffect(() => {
    if (activeTab === 'all') {
      approval.loadAll();
    } else {
      approval.loadAll(activeTab);
    }
  }, [activeTab, approval]);

  // Subscribe to real-time updates
  useEffect(() => {
    // Real-time subscription will be added in T194
    // For now, just poll every 30 seconds for pending tab
    if (activeTab === 'pending') {
      const interval = setInterval(() => {
        approval.loadAll('pending');
      }, 30000);
      return () => clearInterval(interval);
    }
  }, [activeTab, approval]);

  const handleSelectRequest = (request: ApprovalRequest) => {
    setSelectedRequest(request);
  };

  const handleCloseModal = () => {
    setSelectedRequest(null);
  };

  const getPendingBadge = () => {
    if (approval.pendingCount === 0) return null;
    return (
      <Badge variant="destructive" className="ml-2">
        {approval.pendingCount}
      </Badge>
    );
  };

  return (
    <div className="container max-w-6xl mx-auto p-6 space-y-6" data-testid="approval-queue">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Approval Queue</h1>
          <p className="text-muted-foreground mt-1">
            Review AI-suggested actions requiring human approval
          </p>
        </div>
        {getPendingBadge()}
      </div>

      {/* Error Alert */}
      {approval.error && (
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertDescription>{approval.error}</AlertDescription>
        </Alert>
      )}

      {/* Tabs for filtering */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as ApprovalFilter)}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="pending">
            Pending
            {approval.pendingCount > 0 && (
              <Badge variant="secondary" className="ml-2 px-1.5 py-0 text-xs">
                {approval.pendingCount}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="approved">Approved</TabsTrigger>
          <TabsTrigger value="rejected">Rejected</TabsTrigger>
          <TabsTrigger value="expired">Expired</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
        </TabsList>

        {/* Tab Content */}
        {(['pending', 'approved', 'rejected', 'expired', 'all'] as const).map((filter) => (
          <TabsContent key={filter} value={filter} className="space-y-4">
            {approval.isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              </div>
            ) : approval.requests.length === 0 ? (
              <EmptyState filter={filter} />
            ) : (
              <div className="grid gap-4">
                {approval.requests.map((request) => (
                  <ApprovalCard key={request.id} request={request} onSelect={handleSelectRequest} />
                ))}
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>

      {/* Detail Modal */}
      {selectedRequest && (
        <ApprovalDetailModal
          request={selectedRequest}
          open={!!selectedRequest}
          onOpenChange={(open) => !open && handleCloseModal()}
          onApprove={async (note) => {
            await approval.approve(selectedRequest.id, note);
            handleCloseModal();
          }}
          onReject={async (note) => {
            await approval.reject(selectedRequest.id, note);
            handleCloseModal();
          }}
        />
      )}
    </div>
  );
});

export default ApprovalQueuePage;
