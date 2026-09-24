# Campus Eats

A mobile-friendly web app that recommends restaurants to college students,
ranked by a **student score** that blends food quality with value. Starting
with Boston/Cambridge.

The full project brief (decisions, data model, scoring, build order) is in
[`../CLAUDE.md`](../CLAUDE.md).

**Stack:** Next.js 16 (App Router, TypeScript, Tailwind) · Supabase (Postgres) ·
Google Places API (New) · Vercel.

## Getting started

### 1. Install Node.js

Node 22 LTS or newer. If you use [nvm](https://github.com/nvm-sh/nvm):

```bash
nvm install 22
```

### 2. Install dependencies

```bash
cd campus-eats
npm install
```

### 3. Set up environment variables

```bash
cp .env.example .env.local
```

Then fill in `.env.local`:

| Variable | Where to get it |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase dashboard → Project Settings → API |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Same page (the anon or publishable key) |
| `GOOGLE_PLACES_API_KEY` | Google Cloud Console → APIs & Services → Credentials. Enable **Places API (New)** first. |

`.env.local` is gitignored. **Never commit it.** The Google key has no
`NEXT_PUBLIC_` prefix on purpose, so it stays on the server.

### 4. Run it

```bash
npm run dev
```

Open http://localhost:3000. To check your env setup, visit
http://localhost:3000/api/health. It reports which services are configured
without showing the keys.

## Project layout

```
src/
  app/
    page.tsx              Home page (placeholder until the search UI)
    api/health/route.ts   Config check endpoint
  lib/
    env.ts                Reads env vars, fails loudly if one is missing
    supabase/client.ts    Supabase client for the browser
    supabase/server.ts    Supabase client for server code
```

## Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | Start the dev server |
| `npm run build` | Production build |
| `npm run start` | Serve the production build |
| `npm run lint` | Run ESLint |

## Deploying

Import the repo into [Vercel](https://vercel.com), set the **Root Directory**
to `campus-eats`, and add the three env vars under Project Settings →
Environment Variables.

## Roadmap

1. ~~Project scaffold~~
2. Data layer: places schema, Google Places fetch + caching
3. Scoring function with unit tests
4. Search UI
5. Detail view
6. Admin/curation page
7. Later: Yelp, map view, more cities, saved places, deal alerts
