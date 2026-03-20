import type { NextConfig } from 'next';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${BACKEND_URL}/api/v1/:path*`,
      },
    ];
  },

  async redirects() {
    return [
      {
        source: '/:slug/settings/skills',
        destination: '/:slug/roles',
        permanent: true,
      },
      {
        source: '/:slug/settings/members',
        destination: '/:slug/members',
        permanent: true,
      },
    ];
  },

  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            // frame-src: allow only youtube-nocookie and vimeo player iframes.
            // 'self' preserves any same-origin iframe usage.
            // youtube-nocookie.com: used by YoutubeExtension (nocookie: true config).
            // player.vimeo.com: used by VimeoNode embed URLs.
            value: "frame-src 'self' https://www.youtube-nocookie.com https://player.vimeo.com",
          },
        ],
      },
    ];
  },

  // Enable standalone output for Docker deployment
  // This creates a self-contained build with minimal node_modules
  output: 'standalone',

  // Include docs markdown content in standalone output so fs.readFileSync works in production
  outputFileTracingIncludes: {
    '/[workspaceSlug]/docs/[slug]': ['./src/features/docs/content/*.md'],
  },

  // Performance optimizations
  poweredByHeader: false,

  // Strict mode for better React debugging
  reactStrictMode: true,

  // Image optimization configuration
  images: {
    // Allow images from Supabase storage
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.supabase.co',
        pathname: '/storage/v1/object/public/**',
      },
    ],
  },

  // Experimental features
  experimental: {
    // Optimize package imports for faster builds
    optimizePackageImports: [
      'lucide-react',
      '@radix-ui/react-avatar',
      '@radix-ui/react-dialog',
      '@radix-ui/react-dropdown-menu',
      '@radix-ui/react-popover',
      '@radix-ui/react-scroll-area',
      '@radix-ui/react-separator',
      '@radix-ui/react-slot',
      '@radix-ui/react-tooltip',
      'date-fns',
      '@tiptap/core',
      '@tiptap/react',
      '@tiptap/pm',
      '@tiptap/starter-kit',
      '@tiptap/extension-placeholder',
      '@tiptap/extension-character-count',
      '@tiptap/extension-youtube', // added for Phase 33 video embeds
      'recharts',
    ],
  },
};

export default nextConfig;
