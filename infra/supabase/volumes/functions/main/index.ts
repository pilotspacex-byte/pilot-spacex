/**
 * Pilot Space - Edge Functions Main Entry Point
 *
 * This is the main service worker that routes requests to individual functions.
 * Each function is loaded dynamically based on the request path.
 */

import { serve } from 'https://deno.land/std@0.177.0/http/server.ts'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  const url = new URL(req.url)
  const pathParts = url.pathname.split('/').filter(Boolean)

  // Extract function name from path
  const functionName = pathParts[0] || 'health'

  try {
    // Dynamic function routing
    switch (functionName) {
      case 'health':
        return new Response(
          JSON.stringify({
            status: 'ok',
            timestamp: new Date().toISOString(),
            version: '1.0.0',
          }),
          {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          }
        )

      case 'embed':
        // Import and execute embed function
        const embedModule = await import('../embed/index.ts')
        return embedModule.default(req)

      default:
        return new Response(
          JSON.stringify({ error: `Function '${functionName}' not found` }),
          {
            status: 404,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          }
        )
    }
  } catch (error) {
    console.error(`Error in function '${functionName}':`, error)
    return new Response(
      JSON.stringify({
        error: error instanceof Error ? error.message : 'Internal server error',
      }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    )
  }
})
