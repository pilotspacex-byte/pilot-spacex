/**
 * Role-Based Skills API client.
 *
 * Typed functions for all role-skills endpoints per contracts/rest-api.md.
 * T017: Create role-skills API client
 * Source: FR-001 through FR-020, US1-US6
 */

import { apiClient } from './client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Predefined SDLC role types matching backend enum + custom.
 */
export type SDLCRoleType =
  | 'business_analyst'
  | 'product_owner'
  | 'developer'
  | 'tester'
  | 'architect'
  | 'tech_lead'
  | 'project_manager'
  | 'devops'
  | 'custom';

/**
 * Predefined role template from seed data.
 * GET /api/v1/role-templates
 */
export interface RoleTemplate {
  id: string;
  roleType: SDLCRoleType;
  displayName: string;
  description: string;
  icon: string;
  sortOrder: number;
  version: number;
  defaultSkillContent: string;
}

/**
 * Response wrapper for templates list.
 */
export interface RoleTemplatesResponse {
  templates: RoleTemplate[];
}

/**
 * User's role skill for a workspace.
 * GET /api/v1/workspaces/{id}/role-skills
 */
export interface RoleSkill {
  id: string;
  roleType: SDLCRoleType;
  roleName: string;
  skillContent: string;
  experienceDescription: string | null;
  isPrimary: boolean;
  templateVersion: number | null;
  templateUpdateAvailable: boolean;
  wordCount: number;
  createdAt: string;
  updatedAt: string;
}

/**
 * Response wrapper for role skills list.
 */
export interface RoleSkillsResponse {
  skills: RoleSkill[];
}

/**
 * Payload for creating a new role skill.
 * POST /api/v1/workspaces/{id}/role-skills
 */
export interface CreateRoleSkillPayload {
  roleType: SDLCRoleType;
  roleName: string;
  skillContent: string;
  experienceDescription?: string;
  isPrimary?: boolean;
}

/**
 * Payload for updating an existing role skill.
 * PUT /api/v1/workspaces/{id}/role-skills/{skillId}
 */
export interface UpdateRoleSkillPayload {
  roleName?: string;
  skillContent?: string;
  isPrimary?: boolean;
}

/**
 * Payload for AI skill generation.
 * POST /api/v1/workspaces/{id}/role-skills/generate
 */
export interface GenerateSkillPayload {
  roleType: SDLCRoleType;
  roleName?: string;
  experienceDescription: string;
}

/**
 * AI-generated skill response.
 */
export interface GenerateSkillResponse {
  skillContent: string;
  suggestedRoleName: string;
  wordCount: number;
  generationModel: string;
  generationTimeMs: number;
}

/**
 * Regeneration response extends generation with previous values.
 * POST /api/v1/workspaces/{id}/role-skills/{skillId}/regenerate
 */
export interface RegenerateSkillResponse extends GenerateSkillResponse {
  previousSkillContent: string;
  previousRoleName: string;
}

/**
 * Payload for skill regeneration.
 */
export interface RegenerateSkillPayload {
  experienceDescription: string;
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

export const roleSkillsApi = {
  /**
   * List all predefined SDLC role templates.
   * FR-001, US1
   */
  getTemplates(): Promise<RoleTemplatesResponse> {
    return apiClient.get<RoleTemplatesResponse>('/role-templates');
  },

  /**
   * Get current user's role skills for a workspace.
   * FR-009, US6
   */
  getRoleSkills(workspaceId: string): Promise<RoleSkillsResponse> {
    return apiClient.get<RoleSkillsResponse>(`/workspaces/${workspaceId}/role-skills`);
  },

  /**
   * Create a new role skill in a workspace.
   * FR-002, FR-018, FR-020, US1, US6
   */
  createRoleSkill(workspaceId: string, payload: CreateRoleSkillPayload): Promise<RoleSkill> {
    return apiClient.post<RoleSkill>(`/workspaces/${workspaceId}/role-skills`, payload);
  },

  /**
   * Update an existing role skill.
   * FR-009, FR-010, US6
   */
  updateRoleSkill(
    workspaceId: string,
    skillId: string,
    payload: UpdateRoleSkillPayload
  ): Promise<RoleSkill> {
    return apiClient.put<RoleSkill>(`/workspaces/${workspaceId}/role-skills/${skillId}`, payload);
  },

  /**
   * Delete a role skill.
   * FR-009, US6
   */
  deleteRoleSkill(workspaceId: string, skillId: string): Promise<void> {
    return apiClient.delete(`/workspaces/${workspaceId}/role-skills/${skillId}`);
  },

  /**
   * Generate a role skill using AI. Returns preview (does NOT save).
   * FR-003, FR-004, US2
   */
  generateSkill(
    workspaceId: string,
    payload: GenerateSkillPayload
  ): Promise<GenerateSkillResponse> {
    return apiClient.post<GenerateSkillResponse>(
      `/workspaces/${workspaceId}/role-skills/generate`,
      payload
    );
  },

  /**
   * Regenerate an existing skill with updated experience. Returns preview.
   * FR-003, FR-015, US6
   */
  regenerateSkill(
    workspaceId: string,
    skillId: string,
    payload: RegenerateSkillPayload
  ): Promise<RegenerateSkillResponse> {
    return apiClient.post<RegenerateSkillResponse>(
      `/workspaces/${workspaceId}/role-skills/${skillId}/regenerate`,
      payload
    );
  },

  /**
   * Update user's default SDLC role in profile.
   * FR-011, US4
   *
   * Extends existing PATCH /auth/me endpoint.
   */
  updateDefaultRole(defaultSdlcRole: SDLCRoleType | null): Promise<void> {
    return apiClient.patch('/auth/me', { defaultSdlcRole });
  },
};
