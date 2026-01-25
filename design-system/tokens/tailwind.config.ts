/**
 * Tailwind CSS Configuration for Pilot Space v2.0
 *
 * Design Direction: Warm, Capable, Collaborative
 * Key Features:
 * - Warm off-white backgrounds
 * - Teal-green primary accent
 * - Dusty blue for AI collaborative partner
 * - Apple-style squircle corners
 * - Geist font family
 * - Lucide icons
 */

import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: {
          DEFAULT: 'hsl(var(--background))',
          subtle: 'hsl(var(--background-subtle))',
        },
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
          hover: 'hsl(var(--primary-hover))',
          muted: 'hsl(var(--primary-muted))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        // Issue state colors (softened palette)
        state: {
          backlog: 'hsl(var(--state-backlog))',
          todo: 'hsl(var(--state-todo))',
          'in-progress': 'hsl(var(--state-in-progress))',
          'in-review': 'hsl(var(--state-in-review))',
          done: 'hsl(var(--state-done))',
          cancelled: 'hsl(var(--state-cancelled))',
        },
        // Priority colors (warm palette)
        priority: {
          urgent: 'hsl(var(--priority-urgent))',
          high: 'hsl(var(--priority-high))',
          medium: 'hsl(var(--priority-medium))',
          low: 'hsl(var(--priority-low))',
          none: 'hsl(var(--priority-none))',
        },
        // AI collaborative partner colors (dusty blue)
        ai: {
          DEFAULT: 'hsl(var(--ai))',
          foreground: 'hsl(var(--ai-foreground))',
          muted: 'hsl(var(--ai-muted))',
          border: 'hsl(var(--ai-border))',
          'confidence-high': 'hsl(var(--ai-confidence-high))',
          'confidence-medium': 'hsl(var(--ai-confidence-medium))',
          'confidence-low': 'hsl(var(--ai-confidence-low))',
        },
      },
      // Apple-style squircle border radius
      borderRadius: {
        lg: 'var(--radius-lg)',
        md: 'var(--radius)',
        sm: 'var(--radius-sm)',
        xl: 'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
      },
      // Geist font family
      fontFamily: {
        sans: ['Geist', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['Geist Mono', 'SF Mono', 'Monaco', 'monospace'],
      },
      // Refined type scale
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
      // Soft, tinted shadows
      boxShadow: {
        sm: 'var(--shadow-sm)',
        DEFAULT: 'var(--shadow)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        elevated: 'var(--shadow-elevated)',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'fade-out': {
          from: { opacity: '1' },
          to: { opacity: '0' },
        },
        'slide-up': {
          from: { transform: 'translateY(10px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-down': {
          from: { transform: 'translateY(-10px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-in-from-right': {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },
        'slide-out-to-right': {
          from: { transform: 'translateX(0)' },
          to: { transform: 'translateX(100%)' },
        },
        'scale-in': {
          from: { transform: 'scale(0.95)', opacity: '0' },
          to: { transform: 'scale(1)', opacity: '1' },
        },
        shimmer: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s var(--ease-out)',
        'accordion-up': 'accordion-up 0.2s var(--ease-out)',
        'fade-in': 'fade-in 0.2s var(--ease-out)',
        'fade-out': 'fade-out 0.15s var(--ease-in)',
        'slide-up': 'slide-up 0.2s var(--ease-out)',
        'slide-down': 'slide-down 0.2s var(--ease-out)',
        'slide-in-right': 'slide-in-from-right 0.2s var(--ease-out)',
        'slide-out-right': 'slide-out-to-right 0.2s var(--ease-out)',
        'scale-in': 'scale-in 0.2s var(--ease-out)',
        shimmer: 'shimmer 1.5s ease-in-out infinite',
      },
      // Transition timing
      transitionDuration: {
        instant: 'var(--duration-instant)',
        fast: 'var(--duration-fast)',
        normal: 'var(--duration-normal)',
        slow: 'var(--duration-slow)',
      },
      transitionTimingFunction: {
        DEFAULT: 'var(--ease-default)',
        out: 'var(--ease-out)',
        in: 'var(--ease-in)',
        'in-out': 'var(--ease-in-out)',
      },
      // Component-specific sizing
      width: {
        sidebar: 'var(--sidebar-width)',
        'sidebar-collapsed': 'var(--sidebar-collapsed)',
        'board-column': '320px',
      },
      minWidth: {
        'board-column': '280px',
      },
      maxWidth: {
        'board-column': '320px',
        'modal-sm': '400px',
        'modal-md': '500px',
        'modal-lg': '640px',
        'modal-xl': '800px',
        content: '1200px',
      },
      height: {
        header: 'var(--header-height)',
      },
      // Safe area insets for mobile
      spacing: {
        'safe-top': 'env(safe-area-inset-top)',
        'safe-bottom': 'env(safe-area-inset-bottom)',
        'safe-left': 'env(safe-area-inset-left)',
        'safe-right': 'env(safe-area-inset-right)',
      },
    },
  },
  plugins: [
    require('tailwindcss-animate'),
    require('@tailwindcss/typography'),
    // Custom plugin for utilities
    function ({ addUtilities }: { addUtilities: (utilities: Record<string, Record<string, string>>) => void }) {
      addUtilities({
        '.text-balance': {
          'text-wrap': 'balance',
        },
        '.tabular-nums': {
          'font-variant-numeric': 'tabular-nums',
        },
        '.touch-manipulation': {
          'touch-action': 'manipulation',
        },
        '.no-select': {
          'user-select': 'none',
          '-webkit-user-select': 'none',
        },
      });
    },
  ],
};

export default config;
