/**
 * Settings feature hooks exports.
 */

export {
  useWorkspaceSettings,
  useUpdateWorkspaceSettings,
  useDeleteWorkspace,
  type UpdateWorkspaceSettingsData,
} from './use-workspace-settings';

export {
  useSamlConfig,
  useUpdateSamlConfig,
  useOidcConfig,
  useUpdateOidcConfig,
  useSetSsoRequired,
  useRoleClaimMapping,
  useUpdateRoleClaimMapping,
  type SamlConfig,
  type UpdateSamlConfigInput,
  type OidcConfig,
  type UpdateOidcConfigInput,
  type RoleClaimMapping,
  type UpdateRoleClaimMappingInput,
} from './use-sso-settings';

export {
  useCustomRoles,
  useCustomRole,
  useCreateRole,
  useUpdateRole,
  useDeleteRole,
  useAssignRole,
  type CustomRole,
  type CreateRoleInput,
  type UpdateRoleInput,
  type AssignRoleInput,
} from './use-custom-roles';

export {
  useSessions,
  useTerminateSession,
  useTerminateAllUserSessions,
  type Session,
} from './use-sessions';

export { useGenerateScimToken, type ScimTokenResponse } from './use-scim';
