export type GraphNodeType =
  | 'issue'
  | 'note'
  | 'project'
  | 'cycle'
  | 'user'
  | 'pull_request'
  | 'code_reference'
  | 'decision'
  | 'skill_outcome'
  | 'conversation_summary'
  | 'learned_pattern'
  | 'constitution_rule'
  | 'work_intent'
  | 'user_preference';

export type GraphEdgeType =
  | 'relates_to'
  | 'caused_by'
  | 'led_to'
  | 'decided_in'
  | 'authored_by'
  | 'assigned_to'
  | 'belongs_to'
  | 'references'
  | 'learned_from'
  | 'summarizes'
  | 'blocks'
  | 'duplicates'
  | 'parent_of';

export interface GraphNodeDTO {
  id: string;
  nodeType: GraphNodeType;
  label: string;
  summary?: string;
  properties: Record<string, unknown>;
  createdAt: string;
  score?: number;
}

export interface GraphEdgeDTO {
  id: string;
  sourceId: string;
  targetId: string;
  edgeType: GraphEdgeType;
  label: string;
  weight: number;
  properties?: Record<string, unknown>;
}

export interface GraphResponse {
  nodes: GraphNodeDTO[];
  edges: GraphEdgeDTO[];
  centerNodeId: string;
}

export interface GraphQueryParams {
  depth?: number;
  nodeTypes?: GraphNodeType[];
  maxNodes?: number;
  includeGithub?: boolean;
}
