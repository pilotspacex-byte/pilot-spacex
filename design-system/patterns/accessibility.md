# Accessibility Patterns

This document outlines accessibility patterns followed in the Pilot Space design system, based on Web Interface Guidelines and WCAG 2.2 AA compliance.

## Keyboard Navigation

### Focus Management

```tsx
// Always use visible focus states
className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"

// Never remove outlines without providing replacement
// BAD: outline: none
// GOOD: Use :focus-visible with ring styles
```

### Interactive Elements

All interactive elements must be keyboard accessible:

```tsx
// Buttons and clickable elements
<button
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }}
  tabIndex={0}
>
```

### Skip to Main Content

Every page includes a skip link:

```tsx
<a href="#main-content" className="skip-to-main">
  Skip to main content
</a>

<main id="main-content" tabIndex={-1}>
  {/* Content */}
</main>
```

## ARIA Patterns

### Icon Buttons

Icon-only buttons require aria-label:

```tsx
<Button
  variant="ghost"
  size="icon"
  aria-label="Close dialog"
>
  <IconX className="h-4 w-4" aria-hidden="true" />
</Button>
```

### Live Regions

Async updates use aria-live:

```tsx
// Toast notifications
<div aria-live="polite">
  {notification}
</div>

// Form errors
<p role="alert" aria-live="polite">
  {error}
</p>
```

### Form Labels

All form controls have associated labels:

```tsx
// Using htmlFor
<label htmlFor="email">Email</label>
<input id="email" type="email" />

// Or aria-label for visually hidden labels
<input aria-label="Search issues" type="search" />
```

## Color and Contrast

### State Indicators

Never rely on color alone:

```tsx
// Priority indicators use both color AND shape/icons
<PriorityIcon priority="urgent" />  // Red + 4 bars

// Status badges include text
<Badge variant="done">Completed</Badge>  // Green + text
```

### AI Content Indicators

AI-generated content is visually distinct:

```tsx
<AIBadge type="generated">AI</AIBadge>

// Styling
.ai-badge {
  background: var(--ai-suggestion) / 0.1;
  color: var(--ai-suggestion);
}
.ai-badge::before {
  content: '✨';  // Visual indicator
}
```

## Motion and Animation

### Reduced Motion

Respect user preferences:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

### Performant Animations

Only animate transform and opacity:

```tsx
// GOOD
transition: transform 150ms ease, opacity 150ms ease;

// BAD - avoid transition: all
transition: all 200ms;
```

## Form Patterns

### Input Types

Use correct input types:

```tsx
<input type="email" autoComplete="email" />
<input type="tel" autoComplete="tel" />
<input type="url" autoComplete="url" />
```

### Never Prevent Paste

```tsx
// NEVER do this
<input onPaste={(e) => e.preventDefault()} />

// Paste should always work
```

### Error Handling

Surface errors inline with proper ARIA:

```tsx
<input
  aria-invalid={!!error}
  aria-describedby={error ? `${id}-error` : undefined}
/>
{error && (
  <p id={`${id}-error`} role="alert">
    {error}
  </p>
)}
```

## Modal/Dialog Patterns

### Focus Trapping

Dialogs trap focus within:

```tsx
// Using Radix UI primitives handles this automatically
<Dialog>
  <DialogContent>
    {/* Focus is trapped here */}
  </DialogContent>
</Dialog>
```

### Scroll Containment

Prevent background scrolling:

```tsx
// Modal content
className="overscroll-contain"
```

### Escape to Close

All modals close on Escape key (handled by Radix).

## Touch Interactions

### Touch Optimization

```tsx
// Disable double-tap zoom
className="touch-manipulation"

// Disable tap highlight
style={{ WebkitTapHighlightColor: 'transparent' }}
```

### Drag and Drop

During drag operations:

```tsx
// Disable text selection
document.body.classList.add('no-select');

// Mark elements as inert if needed
element.setAttribute('inert', '');
```

## Semantic Structure

### Heading Hierarchy

Maintain proper heading order:

```tsx
<h1>Page Title</h1>
  <h2>Section</h2>
    <h3>Subsection</h3>
```

### Landmark Regions

Use semantic landmarks:

```tsx
<header>Navigation</header>
<nav>Sidebar</nav>
<main>Content</main>
<aside>Sidebar</aside>
<footer>Footer</footer>
```

### Lists

Use semantic lists for groups:

```tsx
// Issue list
<ul role="list">
  {issues.map(issue => (
    <li key={issue.id}>{issue.title}</li>
  ))}
</ul>

// Navigation
<nav aria-label="Main">
  <ul>
    <li><a href="/">Home</a></li>
  </ul>
</nav>
```

## Responsive Design

### Mobile Safe Areas

Account for notches and home indicators:

```css
padding-bottom: max(env(safe-area-inset-bottom), 1rem);
```

### Touch Targets

Minimum 44x44px touch targets:

```tsx
// Icon buttons have minimum size
size="icon"  // 40x40px minimum
```

## Testing Checklist

- [ ] Keyboard navigation works for all interactive elements
- [ ] Focus order is logical
- [ ] Skip link works correctly
- [ ] Screen reader announces content correctly
- [ ] Color contrast meets WCAG AA (4.5:1 text, 3:1 UI)
- [ ] Information not conveyed by color alone
- [ ] Reduced motion preference respected
- [ ] Forms have proper labels and error messages
- [ ] Modals trap focus and close on Escape
- [ ] Touch targets are at least 44x44px
