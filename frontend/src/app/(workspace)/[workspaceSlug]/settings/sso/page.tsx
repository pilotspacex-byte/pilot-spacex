/**
 * SSO settings page — App Router entry point.
 *
 * AUTH-01, AUTH-02: Renders SsoSettingsPage for admin SSO configuration.
 */

import { SsoSettingsPage } from '@/features/settings/pages';

export default function SsoPage() {
  return <SsoSettingsPage />;
}
