'use client';

import { motion } from 'motion/react';
import { Settings, User, Bell, Palette, Key, Plug } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const settingsSections = [
  {
    id: 'profile',
    icon: User,
    title: 'Profile',
    description: 'Manage your personal information',
  },
  {
    id: 'notifications',
    icon: Bell,
    title: 'Notifications',
    description: 'Configure how you receive updates',
  },
  {
    id: 'appearance',
    icon: Palette,
    title: 'Appearance',
    description: 'Customize the look and feel',
  },
  {
    id: 'ai',
    icon: Key,
    title: 'AI Providers',
    description: 'Configure your AI API keys (BYOK)',
  },
  {
    id: 'integrations',
    icon: Plug,
    title: 'Integrations',
    description: 'Connect GitHub, Slack, and more',
  },
];

export default function SettingsPage() {
  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <Settings className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Settings</h1>
            <p className="text-sm text-muted-foreground">Manage your workspace preferences</p>
          </div>
        </div>
      </div>

      {/* Settings Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-2xl space-y-4">
          {settingsSections.map((section, index) => (
            <motion.div
              key={section.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Card
                className={cn(
                  'group cursor-pointer transition-all duration-200',
                  'hover:shadow-warm-md hover:-translate-y-0.5'
                )}
              >
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted transition-colors group-hover:bg-primary/10">
                    <section.icon className="h-5 w-5 text-muted-foreground transition-colors group-hover:text-primary" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-foreground transition-colors group-hover:text-primary">
                      {section.title}
                    </h3>
                    <p className="text-sm text-muted-foreground">{section.description}</p>
                  </div>
                  <Button variant="ghost" size="sm">
                    Configure
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
