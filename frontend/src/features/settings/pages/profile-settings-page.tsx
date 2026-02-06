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
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useStore } from '@/stores';

export const ProfileSettingsPage = observer(function ProfileSettingsPage() {
  const { authStore } = useStore();
  const user = authStore.user;

  const [displayName, setDisplayName] = React.useState(user?.name ?? '');
  const [isSaving, setIsSaving] = React.useState(false);
  const [hasChanges, setHasChanges] = React.useState(false);

  React.useEffect(() => {
    if (user?.name) {
      setDisplayName(user.name);
    }
  }, [user?.name]);

  React.useEffect(() => {
    setHasChanges(displayName !== (user?.name ?? ''));
  }, [displayName, user?.name]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!hasChanges) return;

    setIsSaving(true);
    const success = await authStore.updateProfile({ name: displayName });
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

  if (!user) {
    return null;
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
              {/* Avatar Preview */}
              <div className="flex items-center gap-4">
                <Avatar className="h-16 w-16">
                  {user.avatarUrl && (
                    <AvatarImage src={user.avatarUrl} alt={user.name || 'User avatar'} />
                  )}
                  <AvatarFallback className="text-lg">{initials}</AvatarFallback>
                </Avatar>
                <div>
                  <p className="font-medium text-foreground">{user.name || user.email}</p>
                  <p className="text-sm text-muted-foreground">
                    Your avatar is synced from your auth provider.
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
      </div>
    </div>
  );
});
