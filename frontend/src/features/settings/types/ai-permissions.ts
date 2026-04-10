/**
 * AI permission types — Phase 69 Wave 4.
 *
 * Backend source of truth: backend/src/pilot_space/api/v1/routers/ai_permissions.py
 * The single permissions list endpoint also serves as the tool inventory (39 tools).
 */

export type ToolPermissionMode = 'auto' | 'ask' | 'deny';
export type ToolPermissionSource = 'db' | 'override' | 'default';
export type PolicyTemplate = 'conservative' | 'standard' | 'trusted';

export interface ToolPermission {
  tool_name: string;
  mode: ToolPermissionMode;
  source: ToolPermissionSource;
  /** DD-003: when false, the "auto" mode is forbidden — UI must hide (not disable) the option. */
  can_set_auto: boolean;
}

export interface PermissionAuditEntry {
  id: string;
  tool_name: string;
  old_mode: ToolPermissionMode | null;
  new_mode: ToolPermissionMode;
  actor_user_id: string | null;
  created_at: string;
}

/** Parse mcp__server__tool into server name + short tool name. */
export function parseToolName(toolName: string): { server: string; shortName: string } {
  const match = /^mcp__([^_]+(?:_[^_]+)*?)__(.+)$/.exec(toolName);
  if (match) return { server: match[1]!, shortName: match[2]! };
  return { server: 'builtin', shortName: toolName };
}
