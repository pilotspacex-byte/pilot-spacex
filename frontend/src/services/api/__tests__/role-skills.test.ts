/**
 * Unit tests for role-skills API client.
 *
 * T017: Tests for role-skills API typed functions.
 * Source: contracts/rest-api.md endpoints 1-9
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { roleSkillsApi } from '../role-skills';
import { apiClient } from '../client';

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('roleSkillsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getTemplates', () => {
    it('should GET /role-templates', async () => {
      const mockResponse = {
        templates: [
          {
            id: 'tmpl-1',
            roleType: 'developer',
            displayName: 'Developer',
            description: 'Code & architecture',
            icon: 'Code',
            sortOrder: 3,
            version: 1,
            defaultSkillContent: '# Developer\n...',
          },
        ],
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await roleSkillsApi.getTemplates();

      expect(apiClient.get).toHaveBeenCalledWith('/role-templates');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getRoleSkills', () => {
    it('should GET /workspaces/{id}/role-skills', async () => {
      const mockResponse = {
        skills: [
          {
            id: 'skill-1',
            roleType: 'developer',
            roleName: 'Senior Developer',
            skillContent: '# Developer\n...',
            experienceDescription: null,
            isPrimary: true,
            templateVersion: 1,
            templateUpdateAvailable: false,
            wordCount: 200,
            createdAt: '2026-02-06T10:00:00Z',
            updatedAt: '2026-02-06T10:00:00Z',
          },
        ],
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await roleSkillsApi.getRoleSkills('ws-123');

      expect(apiClient.get).toHaveBeenCalledWith('/workspaces/ws-123/role-skills');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('createRoleSkill', () => {
    it('should POST /workspaces/{id}/role-skills with payload', async () => {
      const payload = {
        roleType: 'developer' as const,
        roleName: 'Senior Developer',
        skillContent: '# Developer\nFocus areas...',
        experienceDescription: 'Full-stack engineer',
        isPrimary: true,
      };

      const mockResponse = {
        id: 'skill-1',
        ...payload,
        templateVersion: 1,
        wordCount: 50,
        createdAt: '2026-02-06T10:00:00Z',
      };

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await roleSkillsApi.createRoleSkill('ws-123', payload);

      expect(apiClient.post).toHaveBeenCalledWith('/workspaces/ws-123/role-skills', payload);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('updateRoleSkill', () => {
    it('should PUT /workspaces/{id}/role-skills/{skillId} with payload', async () => {
      const payload = {
        roleName: 'Lead Developer',
        skillContent: '# Updated skill',
      };

      const mockResponse = {
        id: 'skill-1',
        roleType: 'developer',
        roleName: 'Lead Developer',
        skillContent: '# Updated skill',
        experienceDescription: null,
        isPrimary: true,
        templateVersion: 1,
        wordCount: 30,
        createdAt: '2026-02-06T10:00:00Z',
        updatedAt: '2026-02-06T11:00:00Z',
      };

      vi.mocked(apiClient.put).mockResolvedValue(mockResponse);

      const result = await roleSkillsApi.updateRoleSkill('ws-123', 'skill-1', payload);

      expect(apiClient.put).toHaveBeenCalledWith('/workspaces/ws-123/role-skills/skill-1', payload);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('deleteRoleSkill', () => {
    it('should DELETE /workspaces/{id}/role-skills/{skillId}', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue(undefined);

      await roleSkillsApi.deleteRoleSkill('ws-123', 'skill-1');

      expect(apiClient.delete).toHaveBeenCalledWith('/workspaces/ws-123/role-skills/skill-1');
    });
  });

  describe('generateSkill', () => {
    it('should POST /workspaces/{id}/role-skills/generate with payload', async () => {
      const payload = {
        roleType: 'developer' as const,
        roleName: 'Developer',
        experienceDescription: 'Full-stack engineer with 5 years experience',
      };

      const mockResponse = {
        skillContent: '# Senior Full-Stack Developer\n...',
        suggestedRoleName: 'Senior Full-Stack TypeScript Developer',
        wordCount: 400,
        generationModel: 'claude-sonnet',
        generationTimeMs: 8500,
      };

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await roleSkillsApi.generateSkill('ws-123', payload);

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/ws-123/role-skills/generate',
        payload
      );
      expect(result).toEqual(mockResponse);
    });

    it('should send without roleName when not provided', async () => {
      const payload = {
        roleType: 'custom' as const,
        experienceDescription: 'Security specialist focusing on threat modeling',
      };

      vi.mocked(apiClient.post).mockResolvedValue({
        skillContent: '# Security Engineer\n...',
        suggestedRoleName: 'Application Security Engineer',
        wordCount: 350,
        generationModel: 'claude-sonnet',
        generationTimeMs: 9200,
      });

      await roleSkillsApi.generateSkill('ws-123', payload);

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/ws-123/role-skills/generate',
        payload
      );
    });
  });

  describe('regenerateSkill', () => {
    it('should POST /workspaces/{id}/role-skills/{skillId}/regenerate', async () => {
      const payload = {
        experienceDescription: 'Now also doing infrastructure and Terraform',
      };

      const mockResponse = {
        skillContent: '# Updated Developer\n...',
        suggestedRoleName: 'Senior Full-Stack & DevOps Engineer',
        wordCount: 500,
        generationModel: 'claude-sonnet',
        generationTimeMs: 10000,
        previousSkillContent: '# Developer\nOld content',
        previousRoleName: 'Senior Full-Stack Developer',
      };

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await roleSkillsApi.regenerateSkill('ws-123', 'skill-1', payload);

      expect(apiClient.post).toHaveBeenCalledWith(
        '/workspaces/ws-123/role-skills/skill-1/regenerate',
        payload
      );
      expect(result).toEqual(mockResponse);
      expect(result.previousSkillContent).toBe('# Developer\nOld content');
      expect(result.previousRoleName).toBe('Senior Full-Stack Developer');
    });
  });

  describe('updateDefaultRole', () => {
    it('should PATCH /auth/me with defaultSdlcRole', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue(undefined);

      await roleSkillsApi.updateDefaultRole('developer');

      expect(apiClient.patch).toHaveBeenCalledWith('/auth/me', {
        defaultSdlcRole: 'developer',
      });
    });

    it('should clear default role with null', async () => {
      vi.mocked(apiClient.patch).mockResolvedValue(undefined);

      await roleSkillsApi.updateDefaultRole(null);

      expect(apiClient.patch).toHaveBeenCalledWith('/auth/me', {
        defaultSdlcRole: null,
      });
    });
  });
});
