/**
 * Pilot Space Design Tokens v2.0
 *
 * Design Direction: Warm, Capable, Collaborative
 * Inspirations: Craft, Apple, Things 3
 *
 * Key changes from v1:
 * - Warm off-white background instead of pure white
 * - Teal-green primary accent instead of orange
 * - Dusty blue for AI (collaborative partner)
 * - Apple-style squircle corners
 * - Geist font family
 * - Lucide icons
 */

// =============================================================================
// COLOR TOKENS
// =============================================================================

export const colors = {
  // Base colors (Warm Neutrals)
  background: {
    DEFAULT: 'hsl(40 20% 98%)',      // Warm off-white #FDFCFA
    subtle: 'hsl(40 15% 96%)',       // Slightly darker warm
    dark: 'hsl(0 0% 10%)',           // Soft dark #1A1A1A
    darkSubtle: 'hsl(0 0% 12%)',     // Elevated dark #1F1F1F
  },
  foreground: {
    DEFAULT: 'hsl(0 0% 9%)',         // Near-black #171717
    muted: 'hsl(0 0% 45%)',          // Muted text #737373
    dark: 'hsl(0 0% 93%)',           // Soft white #EDEDED
    darkMuted: 'hsl(0 0% 60%)',      // Muted light #999999
  },

  // Muted backgrounds
  muted: {
    DEFAULT: 'hsl(40 15% 95%)',      // Warm muted #F5F4F2
    dark: 'hsl(0 0% 14%)',           // Dark muted #242424
    foreground: 'hsl(0 0% 45%)',
    foregroundDark: 'hsl(0 0% 60%)',
  },

  // Card surfaces
  card: {
    DEFAULT: 'hsl(40 20% 99%)',      // Slightly warmer than bg
    dark: 'hsl(0 0% 12%)',
  },

  // Popover surfaces (frosted glass base)
  popover: {
    DEFAULT: 'hsl(40 20% 99%)',
    dark: 'hsl(0 0% 12%)',
  },

  // Border colors (warm tint)
  border: {
    DEFAULT: 'hsl(40 10% 90%)',      // Warm border #E8E6E3
    dark: 'hsl(0 0% 18%)',           // Dark border #2E2E2E
  },

  // Input borders
  input: {
    DEFAULT: 'hsl(40 10% 88%)',
    dark: 'hsl(0 0% 20%)',
  },

  // Primary (Teal-Green - fresh, natural)
  primary: {
    DEFAULT: 'hsl(165 60% 40%)',     // Fresh teal-green #29A386
    foreground: 'hsl(0 0% 100%)',
    hover: 'hsl(165 60% 35%)',
    muted: 'hsl(165 40% 90%)',
    50: 'hsl(165 50% 96%)',
    100: 'hsl(165 50% 90%)',
    200: 'hsl(165 50% 80%)',
    300: 'hsl(165 55% 65%)',
    400: 'hsl(165 58% 50%)',
    500: 'hsl(165 60% 40%)',
    600: 'hsl(165 62% 35%)',
    700: 'hsl(165 65% 28%)',
    800: 'hsl(165 68% 22%)',
    900: 'hsl(165 70% 16%)',
    950: 'hsl(165 75% 10%)',
  },

  // Secondary
  secondary: {
    DEFAULT: 'hsl(40 15% 95%)',
    dark: 'hsl(0 0% 16%)',
    foreground: 'hsl(0 0% 15%)',
    foregroundDark: 'hsl(0 0% 90%)',
  },

  // Accent
  accent: {
    DEFAULT: 'hsl(40 15% 95%)',
    dark: 'hsl(0 0% 16%)',
    foreground: 'hsl(0 0% 15%)',
    foregroundDark: 'hsl(0 0% 90%)',
  },

  // Destructive (Warm red - softer)
  destructive: {
    DEFAULT: 'hsl(5 65% 55%)',       // Warm red #D9534F
    dark: 'hsl(5 60% 40%)',          // Darker warm red #B84743
    foreground: 'hsl(0 0% 100%)',
  },

  // Ring (focus states - uses primary teal)
  ring: {
    DEFAULT: 'hsl(165 60% 40%)',
    dark: 'hsl(165 50% 50%)',
  },

  // Semantic colors for issue states (softened palette)
  state: {
    backlog: 'hsl(30 5% 55%)',        // Warm gray - unstarted
    todo: 'hsl(210 60% 55%)',         // Soft blue - ready
    inProgress: 'hsl(35 85% 50%)',    // Amber - active
    inReview: 'hsl(260 50% 60%)',     // Soft purple - review
    done: 'hsl(165 60% 40%)',         // Teal-green - completed (matches primary)
    cancelled: 'hsl(5 65% 55%)',      // Warm red - cancelled
  },

  // Priority colors (warm palette)
  priority: {
    urgent: 'hsl(5 65% 55%)',         // Warm red #D9534F
    high: 'hsl(25 70% 55%)',          // Amber #D9853F
    medium: 'hsl(45 70% 48%)',        // Gold #C4A035
    low: 'hsl(210 55% 55%)',          // Soft blue #5B8FC9
    none: 'hsl(30 5% 58%)',           // Warm gray #9C9590
  },

  // AI collaborative partner colors (Dusty Blue)
  ai: {
    DEFAULT: 'hsl(210 40% 55%)',      // Calm dusty blue #6B8FAD
    foreground: 'hsl(0 0% 100%)',
    muted: 'hsl(210 30% 94%)',        // Light blue tint
    border: 'hsl(210 40% 75%)',       // Soft blue border
    confidence: {
      high: 'hsl(165 60% 40%)',       // Teal (matches primary)
      medium: 'hsl(45 70% 48%)',      // Gold
      low: 'hsl(5 65% 55%)',          // Warm red
    },
  },
} as const;

// =============================================================================
// TYPOGRAPHY TOKENS
// =============================================================================

export const typography = {
  fontFamily: {
    sans: ['Geist', 'system-ui', '-apple-system', 'sans-serif'],
    mono: ['Geist Mono', 'SF Mono', 'Monaco', 'monospace'],
  },

  fontSize: {
    xs: ['0.6875rem', { lineHeight: '1rem' }],      // 11px
    sm: ['0.8125rem', { lineHeight: '1.25rem' }],   // 13px
    base: ['0.9375rem', { lineHeight: '1.5rem' }],  // 15px
    lg: ['1.0625rem', { lineHeight: '1.625rem' }],  // 17px
    xl: ['1.25rem', { lineHeight: '1.75rem' }],     // 20px
    '2xl': ['1.5rem', { lineHeight: '2rem' }],      // 24px
    '3xl': ['1.875rem', { lineHeight: '2.375rem' }], // 30px
    '4xl': ['2.25rem', { lineHeight: '2.5rem' }],   // 36px
  },

  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },

  // AI voice uses italic
  aiVoice: {
    fontStyle: 'italic',
    fontWeight: '400',
  },

  // Tabular numbers for metrics
  fontVariantNumeric: 'tabular-nums',
} as const;

// =============================================================================
// SPACING TOKENS
// =============================================================================

export const spacing = {
  px: '1px',
  0: '0',
  0.5: '0.125rem',   // 2px
  1: '0.25rem',      // 4px
  1.5: '0.375rem',   // 6px
  2: '0.5rem',       // 8px
  2.5: '0.625rem',   // 10px
  3: '0.75rem',      // 12px
  3.5: '0.875rem',   // 14px
  4: '1rem',         // 16px
  5: '1.25rem',      // 20px
  6: '1.5rem',       // 24px
  7: '1.75rem',      // 28px
  8: '2rem',         // 32px
  9: '2.25rem',      // 36px
  10: '2.5rem',      // 40px
  11: '2.75rem',     // 44px
  12: '3rem',        // 48px
  14: '3.5rem',      // 56px
  16: '4rem',        // 64px
  20: '5rem',        // 80px
  24: '6rem',        // 96px
  28: '7rem',
  32: '8rem',
  36: '9rem',
  40: '10rem',
  44: '11rem',
  48: '12rem',
  52: '13rem',
  56: '14rem',
  60: '15rem',
  64: '16rem',
  72: '18rem',
  80: '20rem',
  96: '24rem',
} as const;

// =============================================================================
// BORDER RADIUS TOKENS (Apple Squircle Style)
// =============================================================================

export const borderRadius = {
  none: '0',
  sm: '0.375rem',    // 6px - badges, small elements
  DEFAULT: '0.625rem', // 10px - buttons, inputs
  md: '0.625rem',    // 10px
  lg: '0.875rem',    // 14px - cards, containers
  xl: '1.125rem',    // 18px - modals, large cards
  '2xl': '1.5rem',   // 24px - hero elements
  '3xl': '2rem',     // 32px
  full: '9999px',    // Avatars, pills
} as const;

// =============================================================================
// SHADOW TOKENS (Soft, Tinted)
// =============================================================================

export const shadows = {
  sm: [
    '0 1px 2px hsl(30 10% 10% / 0.04)',
    '0 1px 1px hsl(30 10% 10% / 0.02)',
  ].join(', '),
  DEFAULT: [
    '0 2px 4px hsl(30 10% 10% / 0.04)',
    '0 4px 8px hsl(30 10% 10% / 0.04)',
  ].join(', '),
  md: [
    '0 4px 8px hsl(30 10% 10% / 0.04)',
    '0 8px 16px hsl(30 10% 10% / 0.06)',
  ].join(', '),
  lg: [
    '0 8px 16px hsl(30 10% 10% / 0.06)',
    '0 16px 32px hsl(30 10% 10% / 0.08)',
  ].join(', '),
  xl: [
    '0 12px 24px hsl(30 10% 10% / 0.08)',
    '0 24px 48px hsl(30 10% 10% / 0.1)',
  ].join(', '),
  elevated: [
    '0 12px 24px hsl(30 10% 10% / 0.08)',
    '0 24px 48px hsl(30 10% 10% / 0.1)',
  ].join(', '),
  inner: 'inset 0 2px 4px 0 hsl(30 10% 10% / 0.05)',
  none: 'none',
} as const;

// =============================================================================
// ANIMATION TOKENS
// =============================================================================

export const animation = {
  // Timing
  duration: {
    instant: '0ms',
    fast: '100ms',
    normal: '200ms',
    slow: '300ms',
    slower: '400ms',
  },

  // Apple-style easing curves
  easing: {
    DEFAULT: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
    linear: 'linear',
    in: 'cubic-bezier(0.4, 0, 1, 1)',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
    spring: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
  },

  // Only animate transform and opacity for performance
  properties: ['transform', 'opacity', 'box-shadow'] as const,
} as const;

// =============================================================================
// Z-INDEX TOKENS
// =============================================================================

export const zIndex = {
  auto: 'auto',
  0: '0',
  10: '10',    // Dropdowns
  20: '20',    // Sticky headers
  30: '30',    // Fixed elements
  40: '40',    // Modals backdrop
  50: '50',    // Modals
  60: '60',    // Popovers
  70: '70',    // Tooltips
  80: '80',    // Notifications/toasts
  90: '90',    // Command palette
  100: '100',  // Dev tools
} as const;

// =============================================================================
// BREAKPOINTS
// =============================================================================

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// =============================================================================
// COMPONENT-SPECIFIC TOKENS
// =============================================================================

export const components = {
  // Sidebar
  sidebar: {
    width: '260px',
    collapsedWidth: '60px',
  },

  // Header
  header: {
    height: '56px',
  },

  // Content
  content: {
    maxWidth: '1200px',
    padding: '32px',
  },

  // Issue card
  issueCard: {
    minHeight: '80px',
    maxWidth: '320px',
  },

  // Board column
  boardColumn: {
    minWidth: '280px',
    maxWidth: '320px',
  },

  // Modal sizes
  modal: {
    sm: '400px',
    md: '500px',
    lg: '640px',
    xl: '800px',
    full: '100%',
  },

  // Button sizes
  button: {
    sm: { height: '32px', padding: '12px', fontSize: '13px', iconSize: '16px' },
    default: { height: '38px', padding: '16px', fontSize: '14px', iconSize: '18px' },
    lg: { height: '44px', padding: '24px', fontSize: '15px', iconSize: '20px' },
    icon: { size: '38px', iconSize: '18px' },
    iconSm: { size: '32px', iconSize: '16px' },
  },

  // AI components
  ai: {
    avatarSize: '24px',
    borderWidth: '3px',
  },
} as const;

// =============================================================================
// EFFECTS
// =============================================================================

export const effects = {
  // Frosted glass
  frostedGlass: {
    backdropFilter: 'blur(20px) saturate(180%)',
    background: 'hsl(var(--background) / 0.72)',
    border: '1px solid hsl(var(--border) / 0.5)',
  },

  // Noise texture
  noiseTexture: {
    opacity: 0.02,
    mixBlendMode: 'multiply',
  },

  // Focus ring
  focusRing: {
    width: '3px',
    color: 'hsl(var(--primary) / 0.3)',
  },

  // Interactive hover
  interactiveHover: {
    transform: 'scale(1.02)',
    shadow: 'var(--shadow-elevated)',
  },

  // Interactive active
  interactiveActive: {
    transform: 'scale(0.98)',
  },
} as const;
