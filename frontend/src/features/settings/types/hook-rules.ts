/**
 * Hook rule types -- Phase 83 Workspace Hooks API.
 *
 * Backend source of truth: backend/src/pilot_space/api/v1/schemas/hook_rule.py
 * Response uses camelCase via BaseSchema (DD convention).
 */

export type HookAction = 'allow' | 'deny' | 'require_approval';
export type HookEventType = 'PreToolUse' | 'PostToolUse' | 'Stop';

export interface HookRule {
  id: string;
  name: string;
  toolPattern: string;
  action: HookAction;
  eventType: HookEventType;
  priority: number;
  isEnabled: boolean;
  description: string | null;
  createdBy: string;
  updatedBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface HookRuleListResponse {
  rules: HookRule[];
  count: number;
}

export interface CreateHookRuleInput {
  name: string;
  toolPattern: string;
  action: HookAction;
  eventType?: HookEventType;
  priority?: number;
  description?: string;
}

export interface UpdateHookRuleInput {
  name?: string;
  toolPattern?: string;
  action?: HookAction;
  eventType?: HookEventType;
  priority?: number;
  description?: string;
  isEnabled?: boolean;
}
