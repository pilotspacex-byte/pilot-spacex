/**
 * Dashboard types for the Implementation Dashboard.
 *
 * Matches the backend DashboardResponse schema from:
 * GET /workspaces/{workspace_id}/batch-runs/{batch_run_id}/dashboard
 *
 * Phase 77 Plan 01 — dashboard data layer.
 */

import type { ImplementationStatus } from '@/features/issues/components/implementation-status-badge';

export interface DashboardIssueStatus {
  id: string;
  issueId: string;
  issueIdentifier: string | null;
  issueTitle: string | null;
  status: ImplementationStatus;
  executionOrder: number;
  currentStage: string | null;
  prUrl: string | null;
  errorMessage: string | null;
  costCents: number;
  startedAt: string | null;
  completedAt: string | null;
}

export interface AttentionItem {
  type: 'pr_ready' | 'blocked' | 'pending_approval';
  issueId: string;
  issueIdentifier: string | null;
  issueTitle: string | null;
  prUrl: string | null;
}

export interface DashboardData {
  batchRunId: string;
  cycleId: string;
  status: string;
  totalIssues: number;
  completedIssues: number;
  failedIssues: number;
  queuedIssues: number;
  runningIssues: number;
  completionPercent: number;
  startedAt: string | null;
  completedAt: string | null;
  issues: DashboardIssueStatus[];
  attentionItems: AttentionItem[];
  attentionCount: number;
  sprintCostCents: number;
  monthlyCostCents: number;
}

export interface IssueCostEntry {
  issueIdentifier: string | null;
  issueTitle: string | null;
  costCents: number;
}
