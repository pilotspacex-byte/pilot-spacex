'use client';

import { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';

export type SettingsSection =
  | 'general'
  | 'features'
  | 'ai-providers'
  | 'mcp-servers'
  | 'integrations'
  | 'sso'
  | 'encryption'
  | 'ai-governance'
  | 'audit'
  | 'roles'
  | 'usage'
  | 'billing'
  | 'profile'
  | 'skills'
  | 'security'
  | 'memory';

interface SettingsModalContextValue {
  open: boolean;
  activeSection: SettingsSection;
  openSettings: (section?: SettingsSection) => void;
  closeSettings: () => void;
  setActiveSection: (section: SettingsSection) => void;
}

const SettingsModalContext = createContext<SettingsModalContextValue | null>(null);

export function SettingsModalProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<SettingsSection>('general');

  const openSettings = useCallback((section: SettingsSection = 'general') => {
    setActiveSection(section);
    setOpen(true);
  }, []);

  const closeSettings = useCallback(() => {
    setOpen(false);
  }, []);

  return (
    <SettingsModalContext.Provider
      value={{ open, activeSection, openSettings, closeSettings, setActiveSection }}
    >
      {children}
    </SettingsModalContext.Provider>
  );
}

export function useSettingsModal() {
  const ctx = useContext(SettingsModalContext);
  if (!ctx) {
    throw new Error('useSettingsModal must be used within SettingsModalProvider');
  }
  return ctx;
}
