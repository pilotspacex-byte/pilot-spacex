/**
 * Application Shell Layout
 *
 * Main layout wrapper with sidebar, header, and content area.
 * Follows Web Interface Guidelines:
 * - Skip to main content link
 * - Safe area insets for mobile
 * - Proper color-scheme for native elements
 * - Keyboard navigation support
 */

import * as React from 'react';
import {
  IconLayoutSidebar,
  IconLayoutSidebarRight,
  IconSearch,
  IconBell,
  IconPlus,
  IconSettings,
  IconMoon,
  IconSun,
  IconChevronDown,
  IconLogout,
  IconUser,
  IconHome,
  IconFolder,
  IconListDetails,
  IconCalendarEvent,
  IconStack2,
  IconFile,
  IconGitPullRequest,
  IconBrandSlack,
  IconBrandGithub,
} from '@tabler/icons-react';
import { cn } from '@/lib/utils';
import { Button } from '../components/button';
import { UserAvatar } from '../components/avatar';
import { Badge } from '../components/badge';

// =============================================================================
// TYPES
// =============================================================================

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  logoUrl?: string;
}

export interface Project {
  id: string;
  name: string;
  identifier: string;
  emoji?: string;
  color?: string;
}

export interface User {
  name: string;
  email: string;
  avatarUrl?: string;
  role: 'owner' | 'admin' | 'member' | 'guest';
}

export interface AppShellProps {
  workspace: Workspace;
  projects: Project[];
  currentProject?: Project;
  user: User;
  unreadNotifications?: number;
  children: React.ReactNode;
  onWorkspaceSwitch?: () => void;
  onProjectSelect?: (project: Project) => void;
  onCreateIssue?: () => void;
  onSearch?: () => void;
  onNotificationsClick?: () => void;
  onSettingsClick?: () => void;
  onLogout?: () => void;
}

// =============================================================================
// SIDEBAR NAVIGATION
// =============================================================================

interface SidebarProps {
  workspace: Workspace;
  projects: Project[];
  currentProject?: Project;
  isCollapsed: boolean;
  onToggle: () => void;
  onWorkspaceSwitch?: () => void;
  onProjectSelect?: (project: Project) => void;
}

function Sidebar({
  workspace,
  projects,
  currentProject,
  isCollapsed,
  onToggle,
  onWorkspaceSwitch,
  onProjectSelect,
}: SidebarProps) {
  const navItems = [
    { icon: IconHome, label: 'Home', href: '/' },
    { icon: IconListDetails, label: 'My Issues', href: '/my-issues' },
  ];

  const projectNavItems = [
    { icon: IconListDetails, label: 'Issues', href: 'issues' },
    { icon: IconCalendarEvent, label: 'Cycles', href: 'cycles' },
    { icon: IconStack2, label: 'Modules', href: 'modules' },
    { icon: IconFile, label: 'Pages', href: 'pages' },
    { icon: IconGitPullRequest, label: 'PR Reviews', href: 'pr-reviews' },
    { icon: IconSettings, label: 'Settings', href: 'settings' },
  ];

  return (
    <aside
      className={cn(
        'flex h-full flex-col border-r bg-background transition-all duration-200',
        isCollapsed ? 'w-sidebar-collapsed' : 'w-sidebar'
      )}
    >
      {/* Workspace header */}
      <div className="flex h-header items-center justify-between border-b px-4">
        <button
          onClick={onWorkspaceSwitch}
          className={cn(
            'flex items-center gap-2 rounded-md p-1 hover:bg-accent',
            isCollapsed && 'justify-center'
          )}
        >
          {workspace.logoUrl ? (
            <img
              src={workspace.logoUrl}
              alt={workspace.name}
              className="h-6 w-6 rounded"
            />
          ) : (
            <div className="flex h-6 w-6 items-center justify-center rounded bg-primary text-xs font-bold text-primary-foreground">
              {workspace.name.charAt(0)}
            </div>
          )}
          {!isCollapsed && (
            <>
              <span className="text-sm font-semibold">{workspace.name}</span>
              <IconChevronDown className="h-4 w-4 text-muted-foreground" />
            </>
          )}
        </button>

        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onToggle}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? (
            <IconLayoutSidebarRight className="h-4 w-4" />
          ) : (
            <IconLayoutSidebar className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Main navigation */}
      <nav className="flex-1 overflow-y-auto p-2">
        <ul className="space-y-1">
          {navItems.map((item) => (
            <li key={item.href}>
              <a
                href={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium',
                  'text-muted-foreground hover:bg-accent hover:text-foreground',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  isCollapsed && 'justify-center px-2'
                )}
              >
                <item.icon className="h-4 w-4 flex-shrink-0" />
                {!isCollapsed && <span>{item.label}</span>}
              </a>
            </li>
          ))}
        </ul>

        {/* Projects */}
        <div className="mt-6">
          {!isCollapsed && (
            <h3 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Projects
            </h3>
          )}
          <ul className="space-y-1">
            {projects.map((project) => (
              <li key={project.id}>
                <button
                  onClick={() => onProjectSelect?.(project)}
                  className={cn(
                    'flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium',
                    'text-muted-foreground hover:bg-accent hover:text-foreground',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    currentProject?.id === project.id && 'bg-accent text-foreground',
                    isCollapsed && 'justify-center px-2'
                  )}
                >
                  {project.emoji ? (
                    <span className="text-base">{project.emoji}</span>
                  ) : (
                    <IconFolder
                      className="h-4 w-4 flex-shrink-0"
                      style={{ color: project.color }}
                    />
                  )}
                  {!isCollapsed && (
                    <span className="truncate">{project.name}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Current project navigation */}
        {currentProject && !isCollapsed && (
          <div className="mt-6 rounded-lg bg-muted/50 p-2">
            <h3 className="mb-2 px-2 text-xs font-semibold text-muted-foreground">
              {currentProject.identifier}
            </h3>
            <ul className="space-y-0.5">
              {projectNavItems.map((item) => (
                <li key={item.href}>
                  <a
                    href={`/projects/${currentProject.id}/${item.href}`}
                    className={cn(
                      'flex items-center gap-2 rounded-md px-2 py-1.5 text-sm',
                      'text-muted-foreground hover:bg-accent hover:text-foreground',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                    )}
                  >
                    <item.icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </nav>

      {/* Integrations */}
      {!isCollapsed && (
        <div className="border-t p-2">
          <div className="flex items-center justify-center gap-2">
            <a
              href="/integrations/github"
              className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground"
              aria-label="GitHub integration"
            >
              <IconBrandGithub className="h-4 w-4" />
            </a>
            <a
              href="/integrations/slack"
              className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground"
              aria-label="Slack integration"
            >
              <IconBrandSlack className="h-4 w-4" />
            </a>
          </div>
        </div>
      )}
    </aside>
  );
}

// =============================================================================
// HEADER
// =============================================================================

interface HeaderProps {
  user: User;
  unreadNotifications?: number;
  onCreateIssue?: () => void;
  onSearch?: () => void;
  onNotificationsClick?: () => void;
  onSettingsClick?: () => void;
  onLogout?: () => void;
}

function Header({
  user,
  unreadNotifications = 0,
  onCreateIssue,
  onSearch,
  onNotificationsClick,
  onSettingsClick,
  onLogout,
}: HeaderProps) {
  const [isDarkMode, setIsDarkMode] = React.useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = React.useState(false);

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
    document.documentElement.classList.toggle('dark');
  };

  return (
    <header className="flex h-header items-center justify-between border-b bg-background px-4">
      {/* Search */}
      <button
        onClick={onSearch}
        className={cn(
          'flex items-center gap-2 rounded-md border bg-muted/50 px-3 py-1.5 text-sm text-muted-foreground',
          'hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          'w-64'
        )}
      >
        <IconSearch className="h-4 w-4" />
        <span>Search...</span>
        <kbd className="ml-auto rounded bg-background px-1.5 py-0.5 text-xs font-mono">
          ⌘K
        </kbd>
      </button>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Create issue */}
        <Button size="sm" onClick={onCreateIssue}>
          <IconPlus className="mr-1 h-4 w-4" />
          New Issue
        </Button>

        {/* Notifications */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onNotificationsClick}
          className="relative"
          aria-label={`Notifications${unreadNotifications > 0 ? `, ${unreadNotifications} unread` : ''}`}
        >
          <IconBell className="h-5 w-5" />
          {unreadNotifications > 0 && (
            <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-destructive-foreground tabular-nums">
              {unreadNotifications > 9 ? '9+' : unreadNotifications}
            </span>
          )}
        </Button>

        {/* Theme toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {isDarkMode ? (
            <IconSun className="h-5 w-5" />
          ) : (
            <IconMoon className="h-5 w-5" />
          )}
        </Button>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            className="flex items-center gap-2 rounded-full p-1 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-expanded={isUserMenuOpen}
            aria-haspopup="true"
          >
            <UserAvatar user={user} size="sm" />
          </button>

          {isUserMenuOpen && (
            <div
              className="absolute right-0 top-full z-50 mt-1 w-56 rounded-md border bg-popover py-1 shadow-lg"
              role="menu"
            >
              <div className="border-b px-3 py-2">
                <p className="text-sm font-medium">{user.name}</p>
                <p className="text-xs text-muted-foreground">{user.email}</p>
                <Badge variant="outline" className="mt-1 text-xs">
                  {user.role}
                </Badge>
              </div>
              <button
                onClick={() => {
                  setIsUserMenuOpen(false);
                  // Navigate to profile
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent"
                role="menuitem"
              >
                <IconUser className="h-4 w-4" />
                Profile
              </button>
              <button
                onClick={() => {
                  setIsUserMenuOpen(false);
                  onSettingsClick?.();
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent"
                role="menuitem"
              >
                <IconSettings className="h-4 w-4" />
                Settings
              </button>
              <div className="border-t">
                <button
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    onLogout?.();
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-accent"
                  role="menuitem"
                >
                  <IconLogout className="h-4 w-4" />
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

// =============================================================================
// MAIN APP SHELL
// =============================================================================

export function AppShell({
  workspace,
  projects,
  currentProject,
  user,
  unreadNotifications,
  children,
  onWorkspaceSwitch,
  onProjectSelect,
  onCreateIssue,
  onSearch,
  onNotificationsClick,
  onSettingsClick,
  onLogout,
}: AppShellProps) {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = React.useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Skip to main content link - accessibility */}
      <a
        href="#main-content"
        className="skip-to-main"
      >
        Skip to main content
      </a>

      {/* Sidebar */}
      <Sidebar
        workspace={workspace}
        projects={projects}
        currentProject={currentProject}
        isCollapsed={isSidebarCollapsed}
        onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        onWorkspaceSwitch={onWorkspaceSwitch}
        onProjectSelect={onProjectSelect}
      />

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <Header
          user={user}
          unreadNotifications={unreadNotifications}
          onCreateIssue={onCreateIssue}
          onSearch={onSearch}
          onNotificationsClick={onNotificationsClick}
          onSettingsClick={onSettingsClick}
          onLogout={onLogout}
        />

        {/* Main content */}
        <main
          id="main-content"
          className="flex-1 overflow-y-auto p-6"
          tabIndex={-1}
        >
          {children}
        </main>
      </div>
    </div>
  );
}

// =============================================================================
// PAGE HEADER COMPONENT
// =============================================================================

export interface PageHeaderProps {
  title: string;
  description?: string;
  breadcrumbs?: Array<{ label: string; href?: string }>;
  actions?: React.ReactNode;
}

export function PageHeader({
  title,
  description,
  breadcrumbs,
  actions,
}: PageHeaderProps) {
  return (
    <div className="mb-6">
      {/* Breadcrumbs */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="mb-2">
          <ol className="flex items-center gap-1 text-sm text-muted-foreground">
            {breadcrumbs.map((crumb, index) => (
              <li key={index} className="flex items-center gap-1">
                {index > 0 && <span>/</span>}
                {crumb.href ? (
                  <a href={crumb.href} className="hover:text-foreground">
                    {crumb.label}
                  </a>
                ) : (
                  <span className="text-foreground">{crumb.label}</span>
                )}
              </li>
            ))}
          </ol>
        </nav>
      )}

      {/* Title and actions */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-balance">{title}</h1>
          {description && (
            <p className="mt-1 text-muted-foreground">{description}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
