/**
 * SsoSettingsPage - Admin SSO configuration.
 *
 * AUTH-01, AUTH-02: SAML 2.0 configuration, OIDC/OAuth config,
 * role claim mapping, and SSO enforcement toggle.
 */

'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { AlertCircle, Copy, Loader2, Plus, X } from 'lucide-react';
import { toast } from 'sonner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { useStore } from '@/stores';
import { ApiError } from '@/services/api';
import {
  useSamlConfig,
  useUpdateSamlConfig,
  useOidcConfig,
  useUpdateOidcConfig,
  useSetSsoRequired,
  useRoleClaimMapping,
  useUpdateRoleClaimMapping,
  type UpdateSamlConfigInput,
  type UpdateOidcConfigInput,
  type OidcConfig,
} from '../hooks/use-sso-settings';

type OidcProvider = OidcConfig['provider'];

interface ClaimMappingRow {
  id: string;
  claim_value: string;
  role_id: string;
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full sm:w-96" />
      </div>
      <Skeleton className="h-[300px] w-full" />
      <Skeleton className="h-[200px] w-full" />
    </div>
  );
}

function CopyButton({ value, label }: { value: string; label: string }) {
  const handleCopy = () => {
    navigator.clipboard.writeText(value).catch(() => undefined);
    toast.success('Copied to clipboard');
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className="h-7 w-7 p-0"
      onClick={handleCopy}
      aria-label={label}
    >
      <Copy className="h-3.5 w-3.5" />
    </Button>
  );
}

export function SsoSettingsPage() {
  const { workspaceStore } = useStore();
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const isAdmin = workspaceStore.isAdmin;

  const {
    data: samlConfig,
    isLoading: samlLoading,
    error: samlError,
  } = useSamlConfig(workspaceSlug);
  const updateSamlConfig = useUpdateSamlConfig(workspaceSlug);
  const { data: oidcConfig, isLoading: oidcLoading } = useOidcConfig(workspaceSlug);
  const updateOidcConfig = useUpdateOidcConfig(workspaceSlug);
  const ssoRequiredMutation = useSetSsoRequired(workspaceSlug);
  const { data: roleMapping } = useRoleClaimMapping(workspaceSlug);
  const updateRoleMapping = useUpdateRoleClaimMapping(workspaceSlug);

  // SAML form state
  const [entityId, setEntityId] = React.useState('');
  const [ssoUrl, setSsoUrl] = React.useState('');
  const [certificate, setCertificate] = React.useState('');
  const [samlError_, setSamlError] = React.useState<string | null>(null);

  // OIDC form state
  const [oidcProvider, setOidcProvider] = React.useState<OidcProvider>('google');
  const [clientId, setClientId] = React.useState('');
  const [clientSecret, setClientSecret] = React.useState('');
  const [issuerUrl, setIssuerUrl] = React.useState('');
  const [oidcError, setOidcError] = React.useState<string | null>(null);

  // SSO enforcement state
  const [ssoRequired, setSsoRequired] = React.useState(false);
  const [showSsoWarning, setShowSsoWarning] = React.useState(false);

  // Role claim mapping state
  const [claimKey, setClaimKey] = React.useState('');
  const [mappingRows, setMappingRows] = React.useState<ClaimMappingRow[]>([]);

  // Sync form state from query data
  React.useEffect(() => {
    if (samlConfig) {
      setEntityId(samlConfig.entity_id ?? '');
      setSsoUrl(samlConfig.sso_url ?? '');
      setSsoRequired(samlConfig.sso_required ?? false);
    }
  }, [samlConfig]);

  React.useEffect(() => {
    if (oidcConfig) {
      setOidcProvider(oidcConfig.provider);
      setClientId(oidcConfig.client_id ?? '');
      setIssuerUrl(oidcConfig.issuer_url ?? '');
    }
  }, [oidcConfig]);

  React.useEffect(() => {
    if (roleMapping) {
      setClaimKey(roleMapping.claim_key ?? '');
      setMappingRows(
        (roleMapping.mappings ?? []).map((m, i) => ({
          id: `row-${i}`,
          claim_value: m.claim_value,
          role_id: m.role_id,
        }))
      );
    }
  }, [roleMapping]);

  const handleSamlSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSamlError(null);

    const data: UpdateSamlConfigInput = {};
    if (entityId) data.entity_id = entityId;
    if (ssoUrl) data.sso_url = ssoUrl;
    if (certificate) data.certificate = certificate;

    try {
      await updateSamlConfig.mutateAsync(data);
      toast.success('SAML configuration saved');
    } catch (err) {
      const msg =
        err instanceof ApiError ? (err.detail ?? err.message) : 'Failed to save SAML config';
      setSamlError(msg);
      toast.error('Failed to save SAML configuration');
    }
  };

  const handleOidcSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setOidcError(null);

    const data: UpdateOidcConfigInput = {
      provider: oidcProvider,
      client_id: clientId,
    };
    if (clientSecret) data.client_secret = clientSecret;
    if (issuerUrl && (oidcProvider === 'azure' || oidcProvider === 'okta')) {
      data.issuer_url = issuerUrl;
    }

    try {
      await updateOidcConfig.mutateAsync(data);
      toast.success('OIDC configuration saved');
    } catch (err) {
      const msg =
        err instanceof ApiError ? (err.detail ?? err.message) : 'Failed to save OIDC config';
      setOidcError(msg);
      toast.error('Failed to save OIDC configuration');
    }
  };

  const handleSsoToggle = async (checked: boolean) => {
    setSsoRequired(checked);
    if (checked) {
      setShowSsoWarning(true);
    } else {
      setShowSsoWarning(false);
    }

    try {
      await ssoRequiredMutation.mutateAsync(checked);
      toast.success(checked ? 'SSO enforcement enabled' : 'SSO enforcement disabled');
    } catch {
      setSsoRequired(!checked);
      setShowSsoWarning(false);
      toast.error('Failed to update SSO enforcement');
    }
  };

  const handleMappingSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateRoleMapping.mutateAsync({
        claim_key: claimKey,
        mappings: mappingRows.map((r) => ({
          claim_value: r.claim_value,
          role_id: r.role_id,
        })),
      });
      toast.success('Role claim mapping saved');
    } catch {
      toast.error('Failed to save role claim mapping');
    }
  };

  const addMappingRow = () => {
    setMappingRows((prev) => [...prev, { id: `row-${Date.now()}`, claim_value: '', role_id: '' }]);
  };

  const removeMappingRow = (id: string) => {
    setMappingRows((prev) => prev.filter((r) => r.id !== id));
  };

  const updateMappingRow = (id: string, field: 'claim_value' | 'role_id', value: string) => {
    setMappingRows((prev) => prev.map((r) => (r.id === id ? { ...r, [field]: value } : r)));
  };

  // Admin-only guard
  if (!isAdmin) {
    return (
      <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="space-y-1 mb-6">
          <h1 className="text-2xl font-semibold tracking-tight">SSO Configuration</h1>
          <p className="text-sm text-muted-foreground">
            Configure SAML 2.0 and OIDC for enterprise single sign-on.
          </p>
        </div>
        <Alert className="border-amber-500/30 bg-amber-50 text-amber-800">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Access restricted</AlertTitle>
          <AlertDescription>
            Only workspace admins and owners can manage SSO settings. Contact your workspace admin
            to configure SSO.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (samlLoading || oidcLoading) {
    return (
      <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
        <LoadingSkeleton />
      </div>
    );
  }

  if (samlError) {
    return (
      <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load SSO configuration</AlertTitle>
          <AlertDescription>
            {samlError instanceof Error ? samlError.message : 'An error occurred.'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">SSO Configuration</h1>
          <p className="text-sm text-muted-foreground">
            Configure SAML 2.0 and OIDC for enterprise single sign-on.
          </p>
        </div>

        {/* SAML 2.0 Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>SAML 2.0 Configuration</CardTitle>
            <CardDescription>
              Connect your identity provider using SAML 2.0 protocol.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSamlSave} className="space-y-5">
              {/* Entity ID */}
              <div className="space-y-2">
                <Label htmlFor="entity-id">Entity ID</Label>
                <Input
                  id="entity-id"
                  type="text"
                  value={entityId}
                  onChange={(e) => setEntityId(e.target.value)}
                  placeholder="https://your-idp.example.com/entity"
                  disabled={updateSamlConfig.isPending}
                  className="sm:max-w-md"
                />
                <p className="text-sm text-muted-foreground">
                  The unique identifier for your identity provider.
                </p>
              </div>

              {/* SSO URL */}
              <div className="space-y-2">
                <Label htmlFor="sso-url">SSO URL</Label>
                <Input
                  id="sso-url"
                  type="url"
                  value={ssoUrl}
                  onChange={(e) => setSsoUrl(e.target.value)}
                  placeholder="https://your-idp.example.com/sso"
                  disabled={updateSamlConfig.isPending}
                  className="sm:max-w-md"
                />
                <p className="text-sm text-muted-foreground">
                  The SSO endpoint URL from your identity provider.
                </p>
              </div>

              {/* X.509 Certificate */}
              <div className="space-y-2">
                <Label htmlFor="certificate">X.509 Certificate</Label>
                <Textarea
                  id="certificate"
                  value={certificate}
                  onChange={(e) => setCertificate(e.target.value)}
                  placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
                  disabled={updateSamlConfig.isPending}
                  rows={5}
                  className="font-mono text-xs sm:max-w-md"
                  aria-describedby="certificate-hint"
                />
                <p id="certificate-hint" className="text-sm text-muted-foreground">
                  The X.509 certificate from your identity provider.
                </p>
              </div>

              {/* Read-only: ACS URL */}
              {samlConfig?.acs_url && (
                <div className="space-y-2">
                  <Label>ACS URL (read-only)</Label>
                  <div className="flex items-center gap-2">
                    <code className="rounded bg-muted px-2 py-1 text-xs font-mono">
                      {samlConfig.acs_url}
                    </code>
                    <CopyButton value={samlConfig.acs_url} label="Copy ACS URL" />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Configure this as the ACS URL in your identity provider.
                  </p>
                </div>
              )}

              {samlError_ && (
                <p className="text-sm text-destructive" role="alert">
                  {samlError_}
                </p>
              )}

              <Button
                type="submit"
                disabled={updateSamlConfig.isPending}
                aria-busy={updateSamlConfig.isPending}
              >
                {updateSamlConfig.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                )}
                {updateSamlConfig.isPending ? 'Saving...' : 'Save SAML Config'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* OIDC / OAuth 2.0 Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>OIDC / OAuth 2.0 Configuration</CardTitle>
            <CardDescription>Configure an OIDC-compatible identity provider.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleOidcSave} className="space-y-5">
              {/* Provider selector */}
              <div className="space-y-2">
                <Label htmlFor="oidc-provider">Provider</Label>
                <Select
                  value={oidcProvider}
                  onValueChange={(v) => setOidcProvider(v as OidcProvider)}
                >
                  <SelectTrigger id="oidc-provider" className="sm:max-w-xs">
                    <SelectValue placeholder="Select provider" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="google">Google Workspace</SelectItem>
                    <SelectItem value="azure">Azure AD</SelectItem>
                    <SelectItem value="okta">Okta</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Client ID */}
              <div className="space-y-2">
                <Label htmlFor="client-id">Client ID</Label>
                <Input
                  id="client-id"
                  type="text"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  placeholder="Your OIDC client ID"
                  disabled={updateOidcConfig.isPending}
                  className="sm:max-w-md"
                />
              </div>

              {/* Client Secret */}
              <div className="space-y-2">
                <Label htmlFor="client-secret">Client Secret</Label>
                <Input
                  id="client-secret"
                  type="password"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                  placeholder="Your OIDC client secret"
                  disabled={updateOidcConfig.isPending}
                  className="sm:max-w-md"
                  autoComplete="new-password"
                />
              </div>

              {/* Issuer URL — shown only for Azure/Okta */}
              {(oidcProvider === 'azure' || oidcProvider === 'okta') && (
                <div className="space-y-2">
                  <Label htmlFor="issuer-url">Issuer URL</Label>
                  <Input
                    id="issuer-url"
                    type="url"
                    value={issuerUrl}
                    onChange={(e) => setIssuerUrl(e.target.value)}
                    placeholder={
                      oidcProvider === 'azure'
                        ? 'https://login.microsoftonline.com/{tenant}/v2.0'
                        : 'https://your-domain.okta.com'
                    }
                    disabled={updateOidcConfig.isPending}
                    className="sm:max-w-md"
                  />
                </div>
              )}

              {oidcError && (
                <p className="text-sm text-destructive" role="alert">
                  {oidcError}
                </p>
              )}

              <Button
                type="submit"
                disabled={updateOidcConfig.isPending}
                aria-busy={updateOidcConfig.isPending}
              >
                {updateOidcConfig.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                )}
                {updateOidcConfig.isPending ? 'Saving...' : 'Save OIDC Config'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Role Claim Mapping */}
        <Card>
          <CardHeader>
            <CardTitle>Role Claim Mapping</CardTitle>
            <CardDescription>
              Map SSO claim values to workspace roles automatically.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleMappingSave} className="space-y-5">
              {/* Claim Key */}
              <div className="space-y-2">
                <Label htmlFor="claim-key">Claim Key</Label>
                <Input
                  id="claim-key"
                  type="text"
                  value={claimKey}
                  onChange={(e) => setClaimKey(e.target.value)}
                  placeholder="groups"
                  disabled={updateRoleMapping.isPending}
                  className="sm:max-w-xs"
                  aria-describedby="claim-key-hint"
                />
                <p id="claim-key-hint" className="text-sm text-muted-foreground">
                  The name of the claim in the SSO token (e.g., &ldquo;groups&rdquo;).
                </p>
              </div>

              {/* Mapping rows */}
              {mappingRows.length > 0 && (
                <div className="space-y-2">
                  <Label>Claim Value Mappings</Label>
                  <div className="space-y-2">
                    {mappingRows.map((row) => (
                      <div key={row.id} className="flex items-center gap-2">
                        <Input
                          type="text"
                          value={row.claim_value}
                          onChange={(e) => updateMappingRow(row.id, 'claim_value', e.target.value)}
                          placeholder="Claim value (e.g., admin-group)"
                          className="flex-1"
                          aria-label="Claim value"
                        />
                        <Input
                          type="text"
                          value={row.role_id}
                          onChange={(e) => updateMappingRow(row.id, 'role_id', e.target.value)}
                          placeholder="Role ID"
                          className="flex-1"
                          aria-label="Role ID"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-9 w-9 p-0 text-muted-foreground hover:text-destructive"
                          onClick={() => removeMappingRow(row.id)}
                          aria-label="Remove mapping row"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3">
                <Button type="button" variant="outline" size="sm" onClick={addMappingRow}>
                  <Plus className="mr-1.5 h-3.5 w-3.5" />
                  Add Mapping
                </Button>

                {mappingRows.length > 0 && (
                  <Button
                    type="submit"
                    disabled={updateRoleMapping.isPending}
                    aria-busy={updateRoleMapping.isPending}
                  >
                    {updateRoleMapping.isPending && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    )}
                    {updateRoleMapping.isPending ? 'Saving...' : 'Save Mapping'}
                  </Button>
                )}
              </div>
            </form>
          </CardContent>
        </Card>

        {/* SSO Enforcement */}
        <Card>
          <CardHeader>
            <CardTitle>SSO Enforcement</CardTitle>
            <CardDescription>
              Control whether workspace members must authenticate via SSO.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <Switch
                  id="sso-required"
                  checked={ssoRequired}
                  onCheckedChange={handleSsoToggle}
                  disabled={ssoRequiredMutation.isPending}
                  aria-label="Require SSO login for all workspace members"
                />
                <div className="space-y-0.5">
                  <Label htmlFor="sso-required" className="cursor-pointer font-medium">
                    Require SSO login for all workspace members
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    All members will be required to sign in through SSO.
                  </p>
                </div>
              </div>

              {showSsoWarning && (
                <Alert
                  variant="destructive"
                  className="border-amber-500/50 bg-amber-50 text-amber-900 dark:bg-amber-950/20 dark:text-amber-300"
                >
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Warning</AlertTitle>
                  <AlertDescription>
                    Email/password login will be disabled for all workspace members. Make sure SSO
                    is fully configured before enabling this.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </CardContent>
        </Card>

        {/* SSO Badge summary */}
        {samlConfig && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted-foreground">Configuration status:</span>
            {samlConfig.entity_id && <Badge variant="outline">SAML Configured</Badge>}
            {ssoRequired && <Badge className="bg-amber-500 hover:bg-amber-600">SSO Required</Badge>}
          </div>
        )}
      </div>
    </div>
  );
}
