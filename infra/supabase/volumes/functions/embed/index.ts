/**
 * Pilot Space - Automatic Embedding Generation Edge Function
 *
 * Processes embedding jobs from the pgmq queue:
 * 1. Reads job from queue (schema, table, id, content function)
 * 2. Fetches content using the specified function
 * 3. Generates embedding via OpenAI text-embedding-3-large
 * 4. Updates the record with the embedding vector
 * 5. Deletes the job from the queue
 *
 * Configuration:
 *   OPENAI_API_KEY: Required - User's BYOK key
 *   SUPABASE_DB_URL: Database connection string
 */

import { z } from 'npm:zod'

// Initialize Postgres client lazily
let sql: ReturnType<typeof postgres> | null = null

async function getPostgres() {
  if (!sql) {
    const postgres = (await import('https://deno.land/x/postgresjs@v3.4.5/mod.js')).default
    sql = postgres(Deno.env.get('SUPABASE_DB_URL')!)
  }
  return sql
}

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

// Job schema validation
const jobSchema = z.object({
  jobId: z.number(),
  id: z.string().or(z.number()),
  schema: z.string(),
  table: z.string(),
  contentFunction: z.string(),
  embeddingColumn: z.string(),
})

const failedJobSchema = jobSchema.extend({
  error: z.string(),
})

type Job = z.infer<typeof jobSchema>
type FailedJob = z.infer<typeof failedJobSchema>

interface Row {
  id: string
  content: unknown
}

// Embedding configuration (matches Pilot Space AI layer)
const EMBEDDING_MODEL = 'text-embedding-3-large'
const EMBEDDING_DIMENSIONS = 3072
const QUEUE_NAME = 'embedding_jobs'

/**
 * Generate embedding using OpenAI API
 */
async function generateEmbedding(text: string, apiKey: string): Promise<number[]> {
  const response = await fetch('https://api.openai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: EMBEDDING_MODEL,
      input: text,
      dimensions: EMBEDDING_DIMENSIONS,
    }),
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`OpenAI API error: ${response.status} - ${error}`)
  }

  const data = await response.json()

  if (!data.data?.[0]?.embedding) {
    throw new Error('Failed to generate embedding: no data returned')
  }

  return data.data[0].embedding
}

/**
 * Process a single embedding job
 */
async function processJob(job: Job, apiKey: string): Promise<void> {
  const { jobId, id, schema, table, contentFunction, embeddingColumn } = job

  const sql = await getPostgres()

  // Fetch content using the specified function
  const rows = await sql`
    SELECT
      id,
      ${sql(contentFunction)}(t) AS content
    FROM
      ${sql(schema)}.${sql(table)} t
    WHERE
      id = ${String(id)}
  `

  const row = rows[0] as Row | undefined

  if (!row) {
    throw new Error(`Row not found: ${schema}.${table}/${id}`)
  }

  if (typeof row.content !== 'string') {
    throw new Error(`Invalid content - expected string: ${schema}.${table}/${id}`)
  }

  // Skip empty content
  if (!row.content.trim()) {
    console.log(`Skipping empty content: ${schema}.${table}/${id}`)
    await sql`SELECT pgmq.delete(${QUEUE_NAME}, ${jobId}::bigint)`
    return
  }

  // Generate embedding
  const embedding = await generateEmbedding(row.content, apiKey)

  // Update the record with the embedding
  await sql`
    UPDATE ${sql(schema)}.${sql(table)}
    SET ${sql(embeddingColumn)} = ${JSON.stringify(embedding)}
    WHERE id = ${String(id)}
  `

  // Delete the job from the queue
  await sql`SELECT pgmq.delete(${QUEUE_NAME}, ${jobId}::bigint)`

  console.log(`Processed embedding: ${schema}.${table}/${id}`)
}

/**
 * Promise that rejects if the worker is terminating
 */
function catchUnload(): Promise<never> {
  return new Promise((_, reject) => {
    addEventListener('beforeunload', (ev: Event) => {
      const detail = (ev as CustomEvent).detail
      reject(new Error(detail?.reason ?? 'Worker terminating'))
    })
  })
}

/**
 * Main handler for the embed function
 */
export default async function handler(req: Request): Promise<Response> {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  // Validate request method
  if (req.method !== 'POST') {
    return new Response(
      JSON.stringify({ error: 'Expected POST request' }),
      {
        status: 405,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    )
  }

  // Validate content type
  const contentType = req.headers.get('content-type')
  if (!contentType?.includes('application/json')) {
    return new Response(
      JSON.stringify({ error: 'Expected JSON body' }),
      {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    )
  }

  // Get OpenAI API key
  const apiKey = Deno.env.get('OPENAI_API_KEY')
  if (!apiKey) {
    return new Response(
      JSON.stringify({ error: 'OPENAI_API_KEY not configured' }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    )
  }

  // Parse and validate request body
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return new Response(
      JSON.stringify({ error: 'Invalid JSON body' }),
      {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    )
  }

  const parseResult = z.array(jobSchema).safeParse(body)
  if (!parseResult.success) {
    return new Response(
      JSON.stringify({
        error: 'Invalid request body',
        details: parseResult.error.message,
      }),
      {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    )
  }

  const pendingJobs = parseResult.data
  const completedJobs: Job[] = []
  const failedJobs: FailedJob[] = []

  // Process jobs
  async function processJobs(): Promise<void> {
    let currentJob: Job | undefined
    while ((currentJob = pendingJobs.shift()) !== undefined) {
      try {
        await processJob(currentJob, apiKey!)
        completedJobs.push(currentJob)
      } catch (error) {
        console.error(`Job failed: ${currentJob.schema}.${currentJob.table}/${currentJob.id}`, error)
        failedJobs.push({
          ...currentJob,
          error: error instanceof Error ? error.message : String(error),
        })
      }
    }
  }

  // Race between job processing and worker termination
  try {
    await Promise.race([processJobs(), catchUnload()])
  } catch (error) {
    // Mark remaining jobs as failed
    failedJobs.push(
      ...pendingJobs.map((job) => ({
        ...job,
        error: error instanceof Error ? error.message : String(error),
      }))
    )
  }

  console.log('Embedding processing complete:', {
    completed: completedJobs.length,
    failed: failedJobs.length,
  })

  return new Response(
    JSON.stringify({ completedJobs, failedJobs }),
    {
      status: 200,
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json',
        'x-completed-jobs': completedJobs.length.toString(),
        'x-failed-jobs': failedJobs.length.toString(),
      },
    }
  )
}
