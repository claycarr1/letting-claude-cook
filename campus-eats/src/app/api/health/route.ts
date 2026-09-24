// GET /api/health reports which services are configured (never the values).
// Handy for checking .env.local setup and Vercel env vars after a deploy.
export function GET() {
  return Response.json({
    ok: true,
    configured: {
      supabase: Boolean(
        process.env.NEXT_PUBLIC_SUPABASE_URL &&
          process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
      ),
      googlePlaces: Boolean(process.env.GOOGLE_PLACES_API_KEY),
    },
  });
}
