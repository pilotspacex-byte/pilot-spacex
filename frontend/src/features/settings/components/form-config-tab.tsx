/**
 * FormConfigTab - Guided form for adding/editing an MCP server.
 *
 * Phase 25: Controlled form with server type selection, transport auto-default,
 * dynamic key-value editors for headers/env vars, and secret masking on edit.
 *
 * Phase 25.15: Headers are plaintext (visible on edit). Env var keys are
 * visible with masked values on edit.
 */

'use client';

import * as React from 'react';
import { Plus, Trash2, HelpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type {
  McpCommandRunner,
  McpServerType,
  McpTransport,
  MCPServer,
  MCPServerRegisterRequest,
  MCPServerUpdateRequest,
} from '@/stores/ai/MCPServersStore';

// ── Types ───────────────────────────────────────────────────

interface KVPair {
  key: string;
  value: string;
}

export interface FormConfigData {
  displayName: string;
  serverType: McpServerType;
  commandRunner: McpCommandRunner;
  urlOrCommand: string;
  transport: McpTransport;
  authType: 'none' | 'bearer' | 'oauth2';
  authToken: string;
  headers: KVPair[];
  envVars: KVPair[];
  commandArgs: string;
  oauthClientId: string;
  oauthAuthUrl: string;
  oauthTokenUrl: string;
  oauthScopes: string;
}

interface FormConfigTabProps {
  initialData?: MCPServer;
  onSave: (data: MCPServerRegisterRequest | MCPServerUpdateRequest) => void;
  isSaving: boolean;
  formId?: string;
}

// ── Helpers ─────────────────────────────────────────────────

function getDefaultTransport(serverType: McpServerType): McpTransport {
  return serverType === 'remote' ? 'sse' : 'stdio';
}

function isValidUrl(s: string): boolean {
  try {
    new URL(s);
    return true;
  } catch {
    return false;
  }
}

const SECRET_MASK = '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022';

function buildInitialState(server?: MCPServer): FormConfigData {
  if (!server) {
    return {
      displayName: '',
      serverType: 'remote',
      commandRunner: 'npx',
      urlOrCommand: '',
      transport: 'sse',
      authType: 'none',
      authToken: '',
      headers: [],
      envVars: [],
      commandArgs: '',
      oauthClientId: '',
      oauthAuthUrl: '',
      oauthTokenUrl: '',
      oauthScopes: '',
    };
  }

  // Populate headers from server response (headers are plaintext)
  const headers: KVPair[] = server.headers
    ? Object.entries(server.headers).map(([key, value]) => ({ key, value }))
    : [];

  // Populate env var keys with masked values (values are secret)
  const envVars: KVPair[] = server.env_var_keys
    ? server.env_var_keys.map((key) => ({ key, value: '' }))
    : [];

  const isCommand = server.server_type !== 'remote';

  return {
    displayName: server.display_name,
    serverType: server.server_type,
    commandRunner: server.command_runner ?? 'npx',
    // For command servers, url_or_command stores the package/args — populate commandArgs from it.
    // For remote servers, urlOrCommand holds the URL; commandArgs holds extra CLI args (unused currently).
    urlOrCommand: isCommand ? '' : (server.url_or_command || server.url || ''),
    transport: server.transport,
    authType: server.auth_type,
    authToken: '',
    headers,
    envVars,
    commandArgs: isCommand ? (server.url_or_command || '') : (server.command_args || ''),
    oauthClientId: '',
    oauthAuthUrl: '',
    oauthTokenUrl: '',
    oauthScopes: '',
  };
}

// ── KV Editor ───────────────────────────────────────────────

function KVEditor({
  label,
  pairs,
  onUpdate,
  addLabel,
  maskValues,
}: {
  label: string;
  pairs: KVPair[];
  onUpdate: (pairs: KVPair[]) => void;
  addLabel: string;
  /** When true, value inputs use type="password" (for env var values) */
  maskValues?: boolean;
}) {
  const addPair = () => onUpdate([...pairs, { key: '', value: '' }]);
  const removePair = (idx: number) => onUpdate(pairs.filter((_, i) => i !== idx));
  const updatePair = (idx: number, field: 'key' | 'value', val: string) =>
    onUpdate(pairs.map((p, i) => (i === idx ? { ...p, [field]: val } : p)));
  const ariaPrefix = label
    || (addLabel.toLowerCase().includes('header')
      ? 'Headers'
      : addLabel.toLowerCase().includes('variable')
        ? 'Environment Variables'
        : 'Key-value');

  return (
    <div className="space-y-2">
      {label && <Label>{label}</Label>}
      {pairs.map((pair, idx) => (
        <div key={idx} className="flex items-center gap-2">
          <Input
            placeholder="Key"
            value={pair.key}
            onChange={(e) => updatePair(idx, 'key', e.target.value)}
            className="flex-1"
            aria-label={`${ariaPrefix} key ${idx + 1}`}
          />
          <Input
            placeholder={maskValues && pair.key && !pair.value ? SECRET_MASK : 'Value'}
            type={maskValues ? 'password' : 'text'}
            value={pair.value}
            onChange={(e) => updatePair(idx, 'value', e.target.value)}
            className="flex-1"
            aria-label={`${ariaPrefix} value ${idx + 1}`}
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={() => removePair(idx)}
            aria-label={`Remove ${label ? label.toLowerCase() : 'key-value'} entry`}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ))}
      <Button type="button" variant="outline" size="sm" onClick={addPair} className="gap-1">
        <Plus className="h-3 w-3" />
        {addLabel}
      </Button>
    </div>
  );
}

// ── Component ───────────────────────────────────────────────

export function FormConfigTab({ initialData, onSave, isSaving, formId }: FormConfigTabProps) {
  const [form, setForm] = React.useState<FormConfigData>(() => buildInitialState(initialData));
  const isEdit = !!initialData;

  const setField = <K extends keyof FormConfigData>(key: K, value: FormConfigData[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleServerTypeChange = (type: McpServerType) => {
    setForm((prev) => ({
      ...prev,
      serverType: type,
      transport: getDefaultTransport(type),
      urlOrCommand: '',
      commandArgs: '',
      commandRunner: 'npx',
      // Clear remote-only auth/header fields so secrets don't persist hidden
      ...(type !== 'remote' && {
        authType: 'none' as const,
        authToken: '',
        headers: [],
        oauthClientId: '',
        oauthAuthUrl: '',
        oauthTokenUrl: '',
        oauthScopes: '',
      }),
    }));
  };

  const hasRequiredValue =
    form.serverType === 'remote'
      ? form.urlOrCommand.trim().length > 0 && isValidUrl(form.urlOrCommand.trim())
      : form.commandArgs.trim().length > 0;

  const isOAuthValid =
    form.authType !== 'oauth2' ||
    (form.oauthClientId.trim().length > 0 &&
      form.oauthAuthUrl.trim().length > 0 &&
      form.oauthTokenUrl.trim().length > 0);

  const canSubmit =
    form.displayName.trim().length > 0 &&
    form.displayName.trim().length <= 128 &&
    hasRequiredValue &&
    isOAuthValid;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit || isSaving) return;

    const isRemote = form.serverType === 'remote';

    // Remote-only: headers; for command types, always omit.
    const headersMap =
      isRemote && form.headers.length > 0
        ? Object.fromEntries(form.headers.filter((p) => p.key.trim()).map((p) => [p.key, p.value]))
        : undefined;

    // For env vars, only send entries where the user provided a value.
    // Entries with empty values (from pre-populated keys) are skipped
    // to preserve existing encrypted values on the backend.
    const envVarEntries = form.envVars.filter((p) => p.key.trim() && p.value.trim());
    const envVarsMap = envVarEntries.length > 0
      ? Object.fromEntries(envVarEntries.map((p) => [p.key, p.value]))
      : undefined;

    // Auth fields are remote-only — force 'none' for command types to
    // prevent stale secrets from leaking into the request payload.
    const authType = isRemote ? form.authType : 'none';
    const authToken = isRemote && form.authToken ? form.authToken : undefined;

    // For command servers, commandArgs owns the full package+args string → url_or_command.
    // For remote servers, urlOrCommand is the URL → url_or_command; commandArgs is unused.
    const urlOrCommandValue = isRemote
      ? form.urlOrCommand.trim()
      : form.commandArgs.trim();

    if (isEdit) {
      const data: MCPServerUpdateRequest = {
        display_name: form.displayName.trim(),
        server_type: form.serverType,
        command_runner: isRemote ? null : form.commandRunner,
        transport: form.transport,
        url_or_command: urlOrCommandValue,
        // command_args is a remote-only field; not sent for command servers.
        command_args: isRemote ? (form.commandArgs.trim() || null) : null,
        auth_type: authType,
        ...(authToken ? { auth_token: authToken } : {}),
        ...(headersMap ? { headers: headersMap } : {}),
        ...(envVarsMap ? { env_vars: envVarsMap } : {}),
        ...(authType === 'oauth2'
          ? {
              oauth_client_id: form.oauthClientId.trim() || undefined,
              oauth_auth_url: form.oauthAuthUrl.trim() || undefined,
              oauth_token_url: form.oauthTokenUrl.trim() || undefined,
              oauth_scopes: form.oauthScopes.trim() || undefined,
            }
          : {}),
      };
      onSave(data);
    } else {
      const data: MCPServerRegisterRequest = {
        display_name: form.displayName.trim(),
        server_type: form.serverType,
        command_runner: isRemote ? undefined : form.commandRunner,
        transport: form.transport,
        url_or_command: urlOrCommandValue,
        // command_args is a remote-only field; not sent for command servers.
        command_args: isRemote ? (form.commandArgs.trim() || undefined) : undefined,
        auth_type: authType,
        ...(authToken ? { auth_token: authToken } : {}),
        ...(headersMap ? { headers: headersMap } : {}),
        ...(envVarsMap ? { env_vars: envVarsMap } : {}),
        ...(authType === 'oauth2'
          ? {
              oauth_client_id: form.oauthClientId.trim(),
              oauth_auth_url: form.oauthAuthUrl.trim(),
              oauth_token_url: form.oauthTokenUrl.trim(),
              oauth_scopes: form.oauthScopes.trim() || undefined,
            }
          : {}),
      };
      onSave(data);
    }
  };

  return (
    <form id={formId} onSubmit={handleSubmit} className="space-y-5">
      {/* Row 1: Name + Type */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="fc-name">Server Name</Label>
          <Input
            id="fc-name"
            value={form.displayName}
            onChange={(e) => setField('displayName', e.target.value)}
            placeholder="my-remote-server"
            maxLength={128}
            disabled={isSaving}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="fc-type">Server Type</Label>
          <Select
            value={form.serverType}
            onValueChange={(v) => handleServerTypeChange(v as McpServerType)}
            disabled={isSaving}
          >
            <SelectTrigger id="fc-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="remote">Remote Server</SelectItem>
              <SelectItem value="command">Command</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Row 1b: Command Runner + Transport (Command type only) */}
      {form.serverType === 'command' && (
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="fc-runner">Command Runner</Label>
            <Select
              value={form.commandRunner}
              onValueChange={(v) => setField('commandRunner', v as McpCommandRunner)}
              disabled={isSaving}
            >
              <SelectTrigger id="fc-runner">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="npx">npx</SelectItem>
                <SelectItem value="uvx">uvx</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="fc-transport">Transport</Label>
            <Select
              value={form.transport}
              onValueChange={(v) => setField('transport', v as McpTransport)}
              disabled={isSaving}
            >
              <SelectTrigger id="fc-transport">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sse">SSE</SelectItem>
                <SelectItem value="stdio">stdio</SelectItem>
                <SelectItem value="streamable_http">StreamableHTTP</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {/* Row 2: Command Arguments (Command type) or Server URL + Transport (Remote) */}
      {form.serverType === 'command' ? (
        <div className="space-y-2">
          <Label htmlFor="fc-args">Command Arguments</Label>
          <Input
            id="fc-args"
            value={form.commandArgs}
            onChange={(e) => setField('commandArgs', e.target.value)}
            placeholder="@modelcontextprotocol/server-github --api-key $API_KEY"
            disabled={isSaving}
            required
          />
          <p className="text-xs text-muted-foreground">
            Full command:{' '}
            <code className="font-mono">
              {form.commandRunner} {form.commandArgs || '<package or args>'}
            </code>
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="fc-url">Server URL</Label>
            <Input
              id="fc-url"
              value={form.urlOrCommand}
              onChange={(e) => setField('urlOrCommand', e.target.value)}
              placeholder="https://mcp.example.com/sse"
              disabled={isSaving}
              required
            />
            {form.urlOrCommand.trim().length > 0 && !isValidUrl(form.urlOrCommand.trim()) && (
              <p className="text-xs text-destructive">
                Please enter a valid URL (must include https://)
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="fc-transport">Transport</Label>
            <Select
              value={form.transport}
              onValueChange={(v) => setField('transport', v as McpTransport)}
              disabled={isSaving}
            >
              <SelectTrigger id="fc-transport">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sse">SSE</SelectItem>
                <SelectItem value="stdio">stdio</SelectItem>
                <SelectItem value="streamable_http">StreamableHTTP</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {/* Auth Type (Remote only) */}
      {form.serverType === 'remote' && (
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            Authentication
          </legend>
          <div className="flex gap-4">
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                name="fc-auth-type"
                value="none"
                checked={form.authType === 'none'}
                onChange={() => setField('authType', 'none')}
                disabled={isSaving}
                className="accent-primary"
              />
              <span className="text-sm">None</span>
            </label>
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                name="fc-auth-type"
                value="bearer"
                checked={form.authType === 'bearer'}
                onChange={() => setField('authType', 'bearer')}
                disabled={isSaving}
                className="accent-primary"
              />
              <span className="text-sm">Bearer Token</span>
            </label>
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                name="fc-auth-type"
                value="oauth2"
                checked={form.authType === 'oauth2'}
                onChange={() => setField('authType', 'oauth2')}
                disabled={isSaving}
                className="accent-primary"
              />
              <span className="text-sm">OAuth 2.0</span>
            </label>
          </div>
        </fieldset>
      )}

      {/* Bearer token */}
      {form.serverType === 'remote' && form.authType === 'bearer' && (
        <div className="space-y-2">
          <Label htmlFor="fc-token">Bearer Token</Label>
          <Input
            id="fc-token"
            type="password"
            value={form.authToken}
            onChange={(e) => setField('authToken', e.target.value)}
            placeholder={isEdit && initialData?.has_auth_secret ? SECRET_MASK : 'Token (encrypted server-side)'}
            disabled={isSaving}
          />
          {isEdit && initialData?.has_auth_secret && (
            <p className="text-xs text-muted-foreground">
              Leave blank to keep existing token. Enter a new value to replace it.
            </p>
          )}
        </div>
      )}

      {/* OAuth2 fields */}
      {form.serverType === 'remote' && form.authType === 'oauth2' && (
        <div className="space-y-3 rounded-md border border-border p-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            OAuth 2.0 Configuration
          </p>
          <div className="space-y-2">
            <Label htmlFor="fc-oauth-client">Client ID</Label>
            <Input
              id="fc-oauth-client"
              value={form.oauthClientId}
              onChange={(e) => setField('oauthClientId', e.target.value)}
              placeholder="your-client-id"
              disabled={isSaving}
              required
            />
            {form.oauthClientId.trim().length === 0 && (
              <p className="text-xs text-destructive">Client ID is required</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="fc-oauth-auth">Authorization URL</Label>
            <Input
              id="fc-oauth-auth"
              type="url"
              value={form.oauthAuthUrl}
              onChange={(e) => setField('oauthAuthUrl', e.target.value)}
              placeholder="https://provider.com/oauth/authorize"
              disabled={isSaving}
              required
            />
            {form.oauthAuthUrl.trim().length === 0 && (
              <p className="text-xs text-destructive">Authorization URL is required</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="fc-oauth-token">Token URL</Label>
            <Input
              id="fc-oauth-token"
              type="url"
              value={form.oauthTokenUrl}
              onChange={(e) => setField('oauthTokenUrl', e.target.value)}
              placeholder="https://provider.com/oauth/token"
              disabled={isSaving}
              required
            />
            {form.oauthTokenUrl.trim().length === 0 && (
              <p className="text-xs text-destructive">Token URL is required</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="fc-oauth-scopes">Scopes (optional)</Label>
            <Input
              id="fc-oauth-scopes"
              value={form.oauthScopes}
              onChange={(e) => setField('oauthScopes', e.target.value)}
              placeholder="read write"
              disabled={isSaving}
            />
          </div>
        </div>
      )}

      {/* Headers (Remote only) */}
      {form.serverType === 'remote' && (
        <div className="space-y-2">
          <div className="flex items-center gap-1.5">
            <Label>Headers</Label>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  tabIndex={0}
                  className="inline-flex cursor-help focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-label="Headers help"
                >
                  <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right" className="max-w-[280px]">
                Custom HTTP headers sent with every request to the remote MCP server. Headers are stored in plaintext — do not put secrets here. Use the Bearer Token field or Environment Variables for sensitive values.
              </TooltipContent>
            </Tooltip>
          </div>
          <KVEditor
            label=""
            pairs={form.headers}
            onUpdate={(pairs) => setField('headers', pairs)}
            addLabel="Add Header"
          />
        </div>
      )}

      {/* Env Vars */}
      <div className="space-y-2">
        <div className="flex items-center gap-1.5">
          <Label>Environment Variables</Label>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                tabIndex={0}
                className="inline-flex cursor-help focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label="Environment variables help"
              >
                <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-[280px]">
              Define environment variables passed to the command process. Use $VAR_NAME in command arguments to reference them (e.g. --api-key $API_KEY).
            </TooltipContent>
          </Tooltip>
        </div>
        <KVEditor
          label=""
          pairs={form.envVars}
          onUpdate={(pairs) => setField('envVars', pairs)}
          addLabel="Add Variable"
          maskValues
        />
        {isEdit && initialData?.has_env_secret && form.envVars.some((p) => p.key && !p.value) && (
          <p className="text-xs text-muted-foreground">
            Existing variables shown with hidden values. Enter a new value to replace, or leave blank to keep unchanged.
          </p>
        )}
      </div>

    </form>
  );
}
