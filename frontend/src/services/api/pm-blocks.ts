/**
 * PM Blocks API client.
 *
 * T-231: Sprint board data
 * T-237: Dependency graph
 * T-242: Capacity plan
 * T-244: Release notes
 * T-249: PM block insights (list / dismiss)
 *
 * Feature 017: Note Versioning / PM Block Engine — Phase 2b-2e
 */

import { apiClient } from './client';

// ── Types ─────────────────────────────────────────────────────────────────

export interface SprintBoardIssueCard {
  id: string;
  identifier: string;
  name: string;
  priority: string;
  stateName: string;
  stateId: string;
  assigneeId?: string;
  assigneeName?: string;
  labels: string[];
  estimateHours?: number;
}

export interface SprintBoardLane {
  stateId: string;
  stateName: string;
  stateGroup: string;
  count: number;
  issues: SprintBoardIssueCard[];
}

export interface SprintBoardData {
  cycleId: string;
  cycleName: string;
  lanes: SprintBoardLane[];
  totalIssues: number;
  isReadOnly: boolean;
}

export interface DepMapNode {
  id: string;
  identifier: string;
  name: string;
  state: string;
  stateGroup: string;
}

export interface DepMapEdge {
  sourceId: string;
  targetId: string;
  isCritical: boolean;
}

export interface DependencyMapData {
  nodes: DepMapNode[];
  edges: DepMapEdge[];
  criticalPath: string[];
  circularDeps: string[][];
  hasCircular: boolean;
}

export interface CapacityMember {
  userId: string;
  displayName: string;
  avatarUrl?: string;
  availableHours: number;
  committedHours: number;
  utilizationPct: number;
  isOverAllocated: boolean;
}

export interface CapacityPlanData {
  cycleId: string;
  cycleName: string;
  members: CapacityMember[];
  teamAvailable: number;
  teamCommitted: number;
  teamUtilizationPct: number;
  hasData: boolean;
}

export interface ReleaseEntry {
  issueId: string;
  identifier: string;
  name: string;
  category: string;
  confidence: number;
  humanEdited: boolean;
}

export interface ReleaseNotesData {
  cycleId: string;
  versionLabel: string;
  entries: ReleaseEntry[];
  generatedAt: string;
}

export type InsightSeverity = 'green' | 'yellow' | 'red';

export interface PMBlockInsight {
  id: string;
  workspaceId: string;
  blockId: string;
  blockType: string;
  insightType: string;
  severity: InsightSeverity;
  title: string;
  analysis: string;
  references: string[];
  suggestedActions: string[];
  confidence: number;
  dismissed: boolean;
}

// ── API Client ──────────────────────────────────────────────────────────────

export const pmBlocksApi = {
  /** Sprint board data grouped by state lane (T-231). */
  getSprintBoard(workspaceId: string, cycleId: string): Promise<SprintBoardData> {
    return apiClient.get<SprintBoardData>(`/pm-blocks/workspaces/${workspaceId}/sprint-board`, {
      params: { cycle_id: cycleId },
    });
  },

  /** Dependency graph with critical path + circular detection (T-237). */
  getDependencyMap(workspaceId: string, cycleId: string): Promise<DependencyMapData> {
    return apiClient.get<DependencyMapData>(`/pm-blocks/workspaces/${workspaceId}/dependency-map`, {
      params: { cycle_id: cycleId },
    });
  },

  /** Capacity plan (available vs committed hours) (T-242). */
  getCapacityPlan(workspaceId: string, cycleId: string): Promise<CapacityPlanData> {
    return apiClient.get<CapacityPlanData>(`/pm-blocks/workspaces/${workspaceId}/capacity-plan`, {
      params: { cycle_id: cycleId },
    });
  },

  /** Release notes classified from completed issues (T-244). */
  getReleaseNotes(workspaceId: string, cycleId: string): Promise<ReleaseNotesData> {
    return apiClient.get<ReleaseNotesData>(`/pm-blocks/workspaces/${workspaceId}/release-notes`, {
      params: { cycle_id: cycleId },
    });
  },

  /** List AI insights for a PM block (T-249). */
  listInsights(
    workspaceId: string,
    blockId: string,
    includeDismissed = false
  ): Promise<PMBlockInsight[]> {
    return apiClient.get<PMBlockInsight[]>(
      `/pm-blocks/workspaces/${workspaceId}/pm-block-insights`,
      { params: { block_id: blockId, include_dismissed: includeDismissed } }
    );
  },

  /** Dismiss a single insight (T-249, FR-059). */
  dismissInsight(workspaceId: string, insightId: string): Promise<void> {
    return apiClient.post<void>(
      `/pm-blocks/workspaces/${workspaceId}/pm-block-insights/${insightId}/dismiss`
    );
  },

  /** Dismiss all insights for a block (T-249, FR-059). */
  dismissAllInsights(workspaceId: string, blockId: string): Promise<void> {
    return apiClient.post<void>(
      `/pm-blocks/workspaces/${workspaceId}/pm-block-insights/dismiss-all`,
      undefined,
      { params: { block_id: blockId } }
    );
  },
};
