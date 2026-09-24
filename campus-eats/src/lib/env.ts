// Central place to read environment variables so a missing key fails loudly
// with a helpful message instead of an obscure error deep in a request.

function required(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(
      `Missing environment variable ${name}. Copy .env.example to .env.local and fill it in.`,
    );
  }
  return value;
}

// NEXT_PUBLIC_ vars must be referenced literally so Next.js can inline them
// into the browser bundle.
export const publicEnv = {
  supabaseUrl: () =>
    required("NEXT_PUBLIC_SUPABASE_URL", process.env.NEXT_PUBLIC_SUPABASE_URL),
  supabaseAnonKey: () =>
    required(
      "NEXT_PUBLIC_SUPABASE_ANON_KEY",
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    ),
};

// Server-only secrets. Never import these from a client component.
export const serverEnv = {
  googlePlacesApiKey: () =>
    required("GOOGLE_PLACES_API_KEY", process.env.GOOGLE_PLACES_API_KEY),
};
