/**
 * ProfileSettingsPage - User profile management.
 *
 * T013: Display name editing, read-only email, save via authStore.updateProfile.
 * FR-009: Display name editing.
 * FR-011: Read-only email display.
 * FR-012: Save profile changes.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { Loader2, Upload } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { useStore } from '@/stores';

export const ProfileSettingsPage = observer(function ProfileSettingsPage() {
  const { authStore } = useStore();
  const user = authStore.user;

  const [displayName, setDisplayName] = React.useState(user?.name ?? '');
  const [bio, setBio] = React.useState(user?.bio ?? '');
  const [isSaving, setIsSaving] = React.useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = React.useState(false);
  const [hasChanges, setHasChanges] = React.useState(false);

  // AI Model Defaults state
  const [modelSonnet, setModelSonnet] = React.useState('');
  const [modelHaiku, setModelHaiku] = React.useState('');
  const [modelOpus, setModelOpus] = React.useState('');
  const [baseUrl, setBaseUrl] = React.useState('');
  const [isSavingAI, setIsSavingAI] = React.useState(false);
  const [hasAIChanges, setHasAIChanges] = React.useState(false);

  React.useEffect(() => {
    if (user) {
      setDisplayName(user.name ?? '');
      setBio(user.bio ?? '');
      setModelSonnet(user.aiSettings?.model_sonnet ?? '');
      setModelHaiku(user.aiSettings?.model_haiku ?? '');
      setModelOpus(user.aiSettings?.model_opus ?? '');
      setBaseUrl(user.aiSettings?.base_url ?? '');
    }
  }, [user]);

  // Fetch backend profile to get AI settings on mount
  React.useEffect(() => {
    if (user) {
      void authStore.fetchBackendProfile();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  React.useEffect(() => {
    setHasChanges(displayName !== (user?.name ?? '') || bio !== (user?.bio ?? ''));
  }, [displayName, bio, user?.name, user?.bio]);

  React.useEffect(() => {
    const currentSonnet = user?.aiSettings?.model_sonnet ?? '';
    const currentHaiku = user?.aiSettings?.model_haiku ?? '';
    const currentOpus = user?.aiSettings?.model_opus ?? '';
    const currentBaseUrl = user?.aiSettings?.base_url ?? '';
    setHasAIChanges(
      modelSonnet !== currentSonnet ||
        modelHaiku !== currentHaiku ||
        modelOpus !== currentOpus ||
        baseUrl !== currentBaseUrl
    );
  }, [modelSonnet, modelHaiku, modelOpus, baseUrl, user?.aiSettings]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!hasChanges) return;

    setIsSaving(true);
    const success = await authStore.updateProfile({
      name: displayName,
      bio: bio.trim() || undefined,
    });
    setIsSaving(false);

    if (success) {
      toast.success('Profile updated', {
        description: 'Your display name has been saved.',
      });
    } else {
      toast.error('Failed to update profile', {
        description: authStore.error ?? 'An unexpected error occurred. Please try again.',
      });
    }
  };

  const handleSaveAI = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasAIChanges) return;

    setIsSavingAI(true);

    // Build settings object with only non-empty values
    const settings: Record<string, string> = {};
    if (modelSonnet.trim()) settings.model_sonnet = modelSonnet.trim();
    if (modelHaiku.trim()) settings.model_haiku = modelHaiku.trim();
    if (modelOpus.trim()) settings.model_opus = modelOpus.trim();
    if (baseUrl.trim()) settings.base_url = baseUrl.trim();

    // If all fields are blank, send null to clear overrides
    const payload = Object.keys(settings).length > 0 ? settings : null;

    const success = await authStore.updateAiSettings(payload);
    setIsSavingAI(false);

    if (success) {
      toast.success('AI settings updated', {
        description: 'Your model defaults have been saved.',
      });
    } else {
      toast.error('Failed to update AI settings', {
        description: authStore.error ?? 'An unexpected error occurred. Please try again.',
      });
    }
  };

  React.useEffect(() => {
    if (!hasChanges && !hasAIChanges) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = ''; // Required for Chromium browsers
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [hasChanges, hasAIChanges]);

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const MAX_SIZE = 5 * 1024 * 1024; // 5MB
    if (file.size > MAX_SIZE) {
      toast.error('File too large', { description: 'Avatar must be smaller than 5MB.' });
      e.target.value = '';
      return;
    }
    const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!ALLOWED_TYPES.includes(file.type)) {
      toast.error('Invalid file type', {
        description: 'Please upload a JPEG, PNG, GIF, or WebP image.',
      });
      e.target.value = '';
      return;
    }

    setIsUploadingAvatar(true);
    const result = await authStore.uploadAvatar(file);
    setIsUploadingAvatar(false);
    // Reset so the same file can be re-selected after a failed upload
    e.target.value = '';

    if (result) {
      toast.success('Avatar updated');
    } else {
      toast.error('Failed to upload avatar', {
        description: authStore.error ?? 'Please try again.',
      });
    }
  };

  if (!user) {
    return (
      <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="space-y-6">
          <div className="space-y-1">
            <Skeleton className="h-7 w-24" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Card>
            <CardHeader>
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-4 w-72" />
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center gap-4">
                <Skeleton className="h-16 w-16 rounded-full" />
                <div className="space-y-1">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-48" />
                </div>
              </div>
              <Skeleton className="h-px w-full" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-10 w-full sm:max-w-md" />
              </div>
              <div className="space-y-2">
                <Skeleton className="h-4 w-10" />
                <Skeleton className="h-20 w-full sm:max-w-md" />
              </div>
              <div className="space-y-2">
                <Skeleton className="h-4 w-12" />
                <Skeleton className="h-10 w-full sm:max-w-md" />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const initials = authStore.userInitials;

  return (
    <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Profile</h1>
          <p className="text-sm text-muted-foreground">
            Manage your personal information and account settings.
          </p>
        </div>

        {/* Profile Card */}
        <Card>
          <CardHeader>
            <CardTitle>Personal Information</CardTitle>
            <CardDescription>
              Update your profile details visible to workspace members.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSave} className="space-y-6">
              {/* Avatar Upload */}
              <div className="flex items-center gap-4">
                <div className="relative group">
                  <Avatar className="h-16 w-16">
                    {user.avatarUrl && (
                      <AvatarImage src={user.avatarUrl} alt={user.name || 'User avatar'} />
                    )}
                    <AvatarFallback className="text-lg">{initials}</AvatarFallback>
                  </Avatar>
                  <label
                    htmlFor="avatar-upload"
                    className="absolute inset-0 flex cursor-pointer items-center justify-center rounded-full bg-black/40 opacity-0 transition-opacity group-hover:opacity-100"
                    aria-label="Upload avatar"
                  >
                    <Upload className="h-5 w-5 text-white" />
                  </label>
                  <input
                    id="avatar-upload"
                    type="file"
                    accept="image/*"
                    className="sr-only"
                    onChange={handleAvatarUpload}
                    disabled={isUploadingAvatar}
                  />
                </div>
                <div>
                  <p className="font-medium text-foreground">{user.name || user.email}</p>
                  <p className="text-sm text-muted-foreground">
                    {isUploadingAvatar ? 'Uploading...' : 'Click avatar to upload a new photo'}
                  </p>
                </div>
              </div>

              <Separator />

              {/* Display Name — FR-009 */}
              <div className="space-y-2">
                <Label htmlFor="display-name">Display Name</Label>
                <Input
                  id="display-name"
                  type="text"
                  placeholder="Enter your display name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  disabled={isSaving}
                  aria-describedby="display-name-hint"
                  className="w-full sm:max-w-md"
                />
                <p id="display-name-hint" className="text-sm text-muted-foreground">
                  This is how your name appears to other workspace members.
                </p>
              </div>

              {/* Bio — optional, max 200 chars */}
              <div className="space-y-2">
                <Label htmlFor="bio">Bio</Label>
                <Textarea
                  id="bio"
                  placeholder="Tell your teammates about yourself..."
                  value={bio}
                  onChange={(e) => setBio(e.target.value.slice(0, 200))}
                  disabled={isSaving}
                  rows={3}
                  maxLength={200}
                  className="w-full sm:max-w-md"
                  aria-describedby="bio-hint"
                />
                <p id="bio-hint" className="text-sm text-muted-foreground">
                  {bio.length}/200 characters
                </p>
              </div>

              {/* Email — FR-011 (read-only) */}
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={user.email}
                  disabled
                  readOnly
                  aria-describedby="email-hint"
                  className="w-full sm:max-w-md"
                />
                <p id="email-hint" className="text-sm text-muted-foreground">
                  Your email address cannot be changed here. Contact support if needed.
                </p>
              </div>

              {/* Save Button — FR-012 */}
              <div className="flex items-center gap-3">
                <Button
                  type="submit"
                  disabled={isSaving || !hasChanges}
                  aria-busy={isSaving}
                  className="min-w-[120px]"
                >
                  {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
                  {isSaving ? 'Saving...' : 'Save Changes'}
                </Button>
                {hasChanges && (
                  <p className="text-sm text-muted-foreground" role="status">
                    You have unsaved changes.
                  </p>
                )}
              </div>
            </form>
          </CardContent>
        </Card>

        {/* AI Model Defaults Card */}
        <Card>
          <CardHeader>
            <CardTitle>AI Model Defaults</CardTitle>
            <CardDescription>
              Override the system default model IDs for each tier. Leave blank to use system
              defaults.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSaveAI} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="model-sonnet">Sonnet Model</Label>
                <Input
                  id="model-sonnet"
                  type="text"
                  placeholder="claude-sonnet-4-20250514"
                  value={modelSonnet}
                  onChange={(e) => setModelSonnet(e.target.value)}
                  disabled={isSavingAI}
                  className="w-full sm:max-w-md"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="model-haiku">Haiku Model</Label>
                <Input
                  id="model-haiku"
                  type="text"
                  placeholder="claude-haiku-4-5-20251001"
                  value={modelHaiku}
                  onChange={(e) => setModelHaiku(e.target.value)}
                  disabled={isSavingAI}
                  className="w-full sm:max-w-md"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="model-opus">Opus Model</Label>
                <Input
                  id="model-opus"
                  type="text"
                  placeholder="claude-opus-4-5-20251101"
                  value={modelOpus}
                  onChange={(e) => setModelOpus(e.target.value)}
                  disabled={isSavingAI}
                  className="w-full sm:max-w-md"
                />
              </div>

              <Separator />

              <div className="space-y-2">
                <Label htmlFor="base-url">API Base URL</Label>
                <Input
                  id="base-url"
                  type="text"
                  placeholder="System default"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  disabled={isSavingAI}
                  className="w-full sm:max-w-md"
                />
                <p className="text-sm text-muted-foreground">
                  Custom Anthropic API base URL for proxy or staging environments.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  type="submit"
                  disabled={isSavingAI || !hasAIChanges}
                  aria-busy={isSavingAI}
                  className="min-w-[120px]"
                >
                  {isSavingAI && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                  )}
                  {isSavingAI ? 'Saving...' : 'Save AI Settings'}
                </Button>
                {hasAIChanges && (
                  <p className="text-sm text-muted-foreground" role="status">
                    You have unsaved AI settings changes.
                  </p>
                )}
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
});
