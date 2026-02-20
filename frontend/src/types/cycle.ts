import type { User, ProjectBrief } from './workspace';
import type { IssueBrief } from './issue';

export type CycleStatus = 'draft' | 'planned' | 'active' | 'completed' | 'cancelled';

export interface Cycle {
  id: string;
  workspaceId: string;
  name: string;
  description?: string;
  status: CycleStatus;
  startDate?: string;
  endDate?: string;
  sequence: number;
  createdAt: string;
  updatedAt: string;
  project: ProjectBrief;
  ownedBy?: User;
  metrics?: CycleMetrics;
  issueCount: number;
}

export interface CycleMetrics {
  cycleId: string;
  totalIssues: number;
  completedIssues: number;
  inProgressIssues: number;
  notStartedIssues: number;
  totalPoints: number;
  completedPoints: number;
  completionPercentage: number;
  velocity: number;
}

export interface CreateCycleData {
  name: string;
  description?: string;
  projectId: string;
  startDate?: string;
  endDate?: string;
  ownedById?: string;
  status?: CycleStatus;
}

export interface UpdateCycleData {
  name?: string;
  description?: string;
  startDate?: string;
  endDate?: string;
  status?: CycleStatus;
  ownedById?: string;
  clearDescription?: boolean;
  clearStartDate?: boolean;
  clearEndDate?: boolean;
  clearOwner?: boolean;
}

export interface RolloverCycleData {
  targetCycleId: string;
  issueIds?: string[];
  includeInProgress?: boolean;
  completeSourceCycle?: boolean;
}

export interface RolloverCycleResult {
  sourceCycle: Cycle;
  targetCycle: Cycle;
  rolledOverIssues: IssueBrief[];
  skippedCount: number;
  totalRolledOver: number;
}

// Burndown Chart Types
export interface BurndownDataPoint {
  date: string;
  remainingPoints: number;
  remainingIssues: number;
  idealPoints: number;
  idealIssues: number;
}

export interface BurndownChartData {
  cycleId: string;
  startDate: string;
  endDate: string;
  totalPoints: number;
  totalIssues: number;
  dataPoints: BurndownDataPoint[];
}

// Velocity Chart Types
export interface VelocityDataPoint {
  cycleId: string;
  cycleName: string;
  completedPoints: number;
  committedPoints: number;
  velocity: number;
}

export interface VelocityChartData {
  projectId: string;
  dataPoints: VelocityDataPoint[];
  averageVelocity: number;
}
