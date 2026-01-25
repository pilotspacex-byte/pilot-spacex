/**
 * Settings Views
 *
 * Workspace and project configuration screens.
 * Follows Web Interface Guidelines:
 * - Proper form structure with labels
 * - Password/secret fields with reveal toggle
 * - Confirmation for destructive actions
 * - Accessible tab navigation
 */

import * as React from 'react';
import {
  IconSettings,
  IconUsers,
  IconKey,
  IconBrandGithub,
  IconBrandSlack,
  IconWebhook,
  IconPalette,
  IconBell,
  IconShield,
  IconEye,
  IconEyeOff,
  IconPlus,
  IconTrash,
  IconCheck,
  IconExternalLink,
  IconRefresh,
} from '@tabler/icons-react';
import { cn } from '@/lib/utils';
import { Button } from '../components/button';
import { Input, FormField } from '../components/input';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../components/card';
import { Badge } from '../components/badge';
import { UserAvatar } from '../components/avatar';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '../components/select';
import { ConfirmDialog } from '../components/dialog';

// =============================================================================
// TYPES
// =============================================================================

export interface AIProvider {
  id: string;
  name: string;
  isConfigured: boolean;
  models: string[];
}

export interface Integration {
  id: string;
  type: 'github' | 'slack';
  name: string;
  isConnected: boolean;
  connectedAt?: Date;
  details?: Record<string, string>;
}

export interface WorkspaceMember {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
  role: 'owner' | 'admin' | 'member' | 'guest';
  joinedAt: Date;
}

// =============================================================================
// SETTINGS TABS
// =============================================================================

interface SettingsTabProps {
  icon: typeof IconSettings;
  label: string;
  isActive: boolean;
  onClick: () => void;
}

function SettingsTab({ icon: Icon, label, isActive, onClick }: SettingsTabProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        isActive
          ? 'bg-accent text-accent-foreground'
          : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
      )}
      role="tab"
      aria-selected={isActive}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}

// =============================================================================
// AI CONFIGURATION
// =============================================================================

interface AIConfigurationProps {
  providers: AIProvider[];
  onSaveKey: (providerId: string, apiKey: string) => Promise<void>;
  onRemoveKey: (providerId: string) => Promise<void>;
  onTestConnection: (providerId: string) => Promise<boolean>;
}

function AIConfiguration({
  providers,
  onSaveKey,
  onRemoveKey,
  onTestConnection,
}: AIConfigurationProps) {
  const [editingProvider, setEditingProvider] = React.useState<string | null>(null);
  const [apiKey, setApiKey] = React.useState('');
  const [showKey, setShowKey] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const [testResult, setTestResult] = React.useState<Record<string, boolean | null>>({});

  const handleSave = async (providerId: string) => {
    setIsSaving(true);
    try {
      await onSaveKey(providerId, apiKey);
      setEditingProvider(null);
      setApiKey('');
    } finally {
      setIsSaving(false);
    }
  };

  const handleTest = async (providerId: string) => {
    setTestResult((prev) => ({ ...prev, [providerId]: null }));
    const result = await onTestConnection(providerId);
    setTestResult((prev) => ({ ...prev, [providerId]: result }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">AI Provider Configuration</h3>
        <p className="text-sm text-muted-foreground">
          Configure API keys for AI features. Keys are encrypted and stored securely.
        </p>
      </div>

      <div className="grid gap-4">
        {providers.map((provider) => (
          <Card key={provider.id}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                    <IconKey className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-medium">{provider.name}</h4>
                    <p className="text-sm text-muted-foreground">
                      {provider.models.join(', ')}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {provider.isConfigured ? (
                    <>
                      <Badge variant="done">Configured</Badge>
                      {testResult[provider.id] !== undefined && (
                        <Badge
                          variant={testResult[provider.id] ? 'done' : 'destructive'}
                        >
                          {testResult[provider.id] === null
                            ? 'Testing...'
                            : testResult[provider.id]
                              ? 'Connected'
                              : 'Failed'}
                        </Badge>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTest(provider.id)}
                      >
                        Test
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setEditingProvider(provider.id)}
                      >
                        Update
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => onRemoveKey(provider.id)}
                        aria-label="Remove API key"
                      >
                        <IconTrash className="h-4 w-4 text-destructive" />
                      </Button>
                    </>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setEditingProvider(provider.id)}
                    >
                      Configure
                    </Button>
                  )}
                </div>
              </div>

              {editingProvider === provider.id && (
                <div className="mt-4 space-y-3 border-t pt-4">
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Input
                        type={showKey ? 'text' : 'password'}
                        placeholder="Enter API key"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        autoComplete="off"
                        spellCheck={false}
                      />
                      <button
                        type="button"
                        onClick={() => setShowKey(!showKey)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
                        aria-label={showKey ? 'Hide API key' : 'Show API key'}
                      >
                        {showKey ? (
                          <IconEyeOff className="h-4 w-4" />
                        ) : (
                          <IconEye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                    <Button
                      onClick={() => handleSave(provider.id)}
                      loading={isSaving}
                      disabled={!apiKey.trim()}
                    >
                      Save
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setEditingProvider(null);
                        setApiKey('');
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Your API key will be encrypted before storage. Never share your API keys.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// INTEGRATIONS
// =============================================================================

interface IntegrationsProps {
  integrations: Integration[];
  onConnect: (type: 'github' | 'slack') => void;
  onDisconnect: (id: string) => void;
  onRefresh: (id: string) => void;
}

function Integrations({
  integrations,
  onConnect,
  onDisconnect,
  onRefresh,
}: IntegrationsProps) {
  const [showDisconnectConfirm, setShowDisconnectConfirm] = React.useState<string | null>(null);

  const integrationTypes = [
    {
      type: 'github' as const,
      name: 'GitHub',
      icon: IconBrandGithub,
      description: 'Link repositories for PR reviews and commit tracking',
    },
    {
      type: 'slack' as const,
      name: 'Slack',
      icon: IconBrandSlack,
      description: 'Receive notifications and create issues from Slack',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">Integrations</h3>
        <p className="text-sm text-muted-foreground">
          Connect external services to enhance your workflow.
        </p>
      </div>

      <div className="grid gap-4">
        {integrationTypes.map((intType) => {
          const integration = integrations.find((i) => i.type === intType.type);
          const Icon = intType.icon;

          return (
            <Card key={intType.type}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <h4 className="font-medium">{intType.name}</h4>
                      <p className="text-sm text-muted-foreground">
                        {intType.description}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {integration?.isConnected ? (
                      <>
                        <Badge variant="done">Connected</Badge>
                        <span className="text-xs text-muted-foreground">
                          {integration.connectedAt &&
                            new Intl.DateTimeFormat('en-US', {
                              dateStyle: 'medium',
                            }).format(integration.connectedAt)}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => onRefresh(integration.id)}
                          aria-label="Refresh connection"
                        >
                          <IconRefresh className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setShowDisconnectConfirm(integration.id)}
                        >
                          Disconnect
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onConnect(intType.type)}
                      >
                        <IconPlus className="mr-1 h-4 w-4" />
                        Connect
                      </Button>
                    )}
                  </div>
                </div>

                {integration?.details && Object.keys(integration.details).length > 0 && (
                  <div className="mt-4 rounded-md bg-muted p-3">
                    <dl className="space-y-1 text-sm">
                      {Object.entries(integration.details).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <dt className="text-muted-foreground">{key}</dt>
                          <dd className="font-medium">{value}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <ConfirmDialog
        open={!!showDisconnectConfirm}
        onOpenChange={() => setShowDisconnectConfirm(null)}
        title="Disconnect Integration"
        description="Are you sure you want to disconnect this integration? Any related data will be preserved but syncing will stop."
        variant="destructive"
        confirmLabel="Disconnect"
        onConfirm={() => {
          if (showDisconnectConfirm) {
            onDisconnect(showDisconnectConfirm);
          }
          setShowDisconnectConfirm(null);
        }}
      />
    </div>
  );
}

// =============================================================================
// MEMBERS MANAGEMENT
// =============================================================================

interface MembersManagementProps {
  members: WorkspaceMember[];
  currentUserId: string;
  onInvite: (email: string, role: string) => Promise<void>;
  onUpdateRole: (memberId: string, role: string) => Promise<void>;
  onRemove: (memberId: string) => Promise<void>;
}

function MembersManagement({
  members,
  currentUserId,
  onInvite,
  onUpdateRole,
  onRemove,
}: MembersManagementProps) {
  const [inviteEmail, setInviteEmail] = React.useState('');
  const [inviteRole, setInviteRole] = React.useState('member');
  const [isInviting, setIsInviting] = React.useState(false);
  const [showRemoveConfirm, setShowRemoveConfirm] = React.useState<string | null>(null);

  const handleInvite = async () => {
    setIsInviting(true);
    try {
      await onInvite(inviteEmail, inviteRole);
      setInviteEmail('');
    } finally {
      setIsInviting(false);
    }
  };

  const roleLabels: Record<string, string> = {
    owner: 'Owner',
    admin: 'Admin',
    member: 'Member',
    guest: 'Guest',
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">Team Members</h3>
        <p className="text-sm text-muted-foreground">
          Manage workspace members and their permissions.
        </p>
      </div>

      {/* Invite form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Invite New Member</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Input
              type="email"
              placeholder="Email address"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              className="flex-1"
              autoComplete="email"
            />
            <Select value={inviteRole} onValueChange={setInviteRole}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="member">Member</SelectItem>
                <SelectItem value="guest">Guest</SelectItem>
              </SelectContent>
            </Select>
            <Button
              onClick={handleInvite}
              loading={isInviting}
              disabled={!inviteEmail.trim()}
            >
              Send Invite
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Members list */}
      <div className="space-y-2">
        {members.map((member) => (
          <div
            key={member.id}
            className="flex items-center justify-between rounded-md border bg-card p-3"
          >
            <div className="flex items-center gap-3">
              <UserAvatar user={member} size="sm" />
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">{member.name}</span>
                  {member.id === currentUserId && (
                    <Badge variant="outline">You</Badge>
                  )}
                </div>
                <span className="text-sm text-muted-foreground">{member.email}</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {member.role === 'owner' ? (
                <Badge>Owner</Badge>
              ) : member.id !== currentUserId ? (
                <>
                  <Select
                    value={member.role}
                    onValueChange={(role) => onUpdateRole(member.id, role)}
                  >
                    <SelectTrigger className="w-28">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="admin">Admin</SelectItem>
                      <SelectItem value="member">Member</SelectItem>
                      <SelectItem value="guest">Guest</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => setShowRemoveConfirm(member.id)}
                    aria-label={`Remove ${member.name}`}
                  >
                    <IconTrash className="h-4 w-4 text-destructive" />
                  </Button>
                </>
              ) : (
                <Badge variant="outline">{roleLabels[member.role]}</Badge>
              )}
            </div>
          </div>
        ))}
      </div>

      <ConfirmDialog
        open={!!showRemoveConfirm}
        onOpenChange={() => setShowRemoveConfirm(null)}
        title="Remove Member"
        description="Are you sure you want to remove this member from the workspace? They will lose access to all projects."
        variant="destructive"
        confirmLabel="Remove"
        onConfirm={() => {
          if (showRemoveConfirm) {
            onRemove(showRemoveConfirm);
          }
          setShowRemoveConfirm(null);
        }}
      />
    </div>
  );
}

// =============================================================================
// MAIN SETTINGS PAGE
// =============================================================================

export interface SettingsPageProps {
  workspaceName: string;
  providers: AIProvider[];
  integrations: Integration[];
  members: WorkspaceMember[];
  currentUserId: string;
  // AI Config handlers
  onSaveApiKey: (providerId: string, apiKey: string) => Promise<void>;
  onRemoveApiKey: (providerId: string) => Promise<void>;
  onTestConnection: (providerId: string) => Promise<boolean>;
  // Integration handlers
  onConnectIntegration: (type: 'github' | 'slack') => void;
  onDisconnectIntegration: (id: string) => void;
  onRefreshIntegration: (id: string) => void;
  // Member handlers
  onInviteMember: (email: string, role: string) => Promise<void>;
  onUpdateMemberRole: (memberId: string, role: string) => Promise<void>;
  onRemoveMember: (memberId: string) => Promise<void>;
}

export function SettingsPage({
  workspaceName,
  providers,
  integrations,
  members,
  currentUserId,
  onSaveApiKey,
  onRemoveApiKey,
  onTestConnection,
  onConnectIntegration,
  onDisconnectIntegration,
  onRefreshIntegration,
  onInviteMember,
  onUpdateMemberRole,
  onRemoveMember,
}: SettingsPageProps) {
  const [activeTab, setActiveTab] = React.useState('ai');

  const tabs = [
    { id: 'ai', icon: IconKey, label: 'AI Configuration' },
    { id: 'integrations', icon: IconWebhook, label: 'Integrations' },
    { id: 'members', icon: IconUsers, label: 'Members' },
    { id: 'general', icon: IconSettings, label: 'General' },
  ];

  return (
    <div className="flex gap-8">
      {/* Sidebar */}
      <nav className="w-56 flex-shrink-0" role="tablist" aria-label="Settings sections">
        <h2 className="mb-4 text-lg font-semibold">{workspaceName} Settings</h2>
        <div className="space-y-1">
          {tabs.map((tab) => (
            <SettingsTab
              key={tab.id}
              icon={tab.icon}
              label={tab.label}
              isActive={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
            />
          ))}
        </div>
      </nav>

      {/* Content */}
      <div className="flex-1" role="tabpanel">
        {activeTab === 'ai' && (
          <AIConfiguration
            providers={providers}
            onSaveKey={onSaveApiKey}
            onRemoveKey={onRemoveApiKey}
            onTestConnection={onTestConnection}
          />
        )}

        {activeTab === 'integrations' && (
          <Integrations
            integrations={integrations}
            onConnect={onConnectIntegration}
            onDisconnect={onDisconnectIntegration}
            onRefresh={onRefreshIntegration}
          />
        )}

        {activeTab === 'members' && (
          <MembersManagement
            members={members}
            currentUserId={currentUserId}
            onInvite={onInviteMember}
            onUpdateRole={onUpdateMemberRole}
            onRemove={onRemoveMember}
          />
        )}

        {activeTab === 'general' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold">General Settings</h3>
              <p className="text-sm text-muted-foreground">
                Configure workspace preferences and defaults.
              </p>
            </div>
            <Card>
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground">
                  General settings content would go here...
                </p>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
