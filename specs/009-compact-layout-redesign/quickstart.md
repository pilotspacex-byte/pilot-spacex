# Quickstart — 009 Compact Layout Redesign

## Smoke Test Scenarios

### Scenario 1: Sidebar Controls Functional

1. Start dev server: `pnpm dev`
2. Navigate to `http://localhost:3000/pilot-space-demo`
3. Look at sidebar bottom — notification bell and user avatar (TD) should be visible
4. Click notification bell — dropdown opens to the right with "No notifications yet"
5. Click user avatar (TD) — dropdown opens with user info, Profile, Settings, Keyboard shortcuts, Sign out
6. **Verify**: Both dropdowns open correctly and are fully visible (no viewport clipping)

### Scenario 2: Header Stripped Down

1. Navigate to any note page (e.g., `/pilot-space-demo/notes/[noteId]`)
2. **Verify**: Header height is 40px (inspect element or visual comparison)
3. **Verify**: Header contains only breadcrumb/page context
4. **Verify**: No search bar, AI sparkle button, +New button, notification bell, or user avatar in header

### Scenario 3: Collapsed Sidebar Controls

1. Click sidebar collapse toggle (chevron at bottom)
2. **Verify**: Sidebar collapses to 60px
3. **Verify**: Notification bell shows as stacked icon
4. **Verify**: User avatar shows as stacked icon
5. Hover over notification icon — tooltip "Notifications" appears to the right
6. Hover over user avatar — tooltip "Account" appears to the right
7. Click notification icon — dropdown opens to the right
8. Click user avatar — dropdown opens to the right

### Scenario 4: Keyboard Shortcuts Preserved

1. Press `Cmd+K` (or `Ctrl+K` on Linux)
2. **Verify**: Search modal opens as before
3. Close search modal
4. Press `Cmd+N`
5. **Verify**: New note is created and navigated to
6. Navigate to issues page
7. Press `C`
8. **Verify**: Create issue flow triggers

### Scenario 5: Font & Spacing Compaction

1. Navigate to Notes list
2. **Verify**: Sidebar nav items use smaller text (~12px)
3. **Verify**: Sidebar note items use smaller text (~12px)
4. **Verify**: Section labels (PINNED, RECENT) are smaller (~9px)
5. **Verify**: All text remains legible on 13-16 inch laptop screens
6. **Verify**: Visual spacing is tighter but not cramped

### Scenario 6: Notification Badge

1. If notification store has unread count > 0, verify badge appears on sidebar bell
2. If unread count > 99, verify badge shows "99+"
3. Click "Mark all read" in notification dropdown
4. **Verify**: Badge disappears
