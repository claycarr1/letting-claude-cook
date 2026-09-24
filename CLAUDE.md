# Project Brief — Student Restaurant Recommender (working name: Campus Eats)

This file summarizes all decisions made so far. Read it fully before making changes. Ask the user before deviating from any decision below.

## What we're building

A mobile-friendly web app for college students in college towns. The user picks a city (start: Boston/Cambridge), optionally a cuisine or "what's popular," and gets a short list of great restaurants with photos, price, and a blended **student score** that balances food quality against value.

Core differentiator: cross-referencing multiple rating sources (Google Places, later Yelp) with a **hand-curated Beli layer** and **student-value signals**, ranked under one fair scoring rule.

The project started as a student-discount tracker. That idea is now folded in as one tag among several, not a headline feature.

## Decisions already made

- **Platform:** mobile-friendly web app (user has no preference between web/native; web chosen for speed and shareability).
- **Stack:** Next.js (React) with API routes, Supabase (Postgres) for the database, Google Places API (New) for live restaurant data, deployed on Vercel. All work lives in a GitHub repo.
- **First city:** Boston/Cambridge only. Multi-city is a later phase.
- **Beli:** no public API, no connector, and scraping violates their terms. **Do not scrape Beli.** Beli scores are entered manually via an admin/curation page, or transcribed from the user's screenshots into seed data. Expect 20–40 curated places per city.
- **Student discounts:** kept as a tag/filter, not the main feature. Most Beli-ranked (nicer) places won't have one, so a discount-only filter would be nearly empty.
- **Value:** the app must keep value picks in mind. Budget is a user setting (cheap eats / worth the splurge / any) that shifts scoring weights, not a hard filter.

## Data model (proposed)

**places**
- id, google_place_id, name, address, lat, lng
- cuisine (array), price_level (1–4, from Google)
- google_rating, google_review_count
- beli_score (nullable, manual), beli_url (nullable)
- nearest_campus (enum: Harvard Sq, Central/Kendall, Fenway/Kenmore, Allston/Brighton, Downtown/Chinatown, Other)
- photo refs (from Google Places), hours
- cached_at (Google data is cached; don't call the API on every search)

**value_tags** (many-to-many with places)
- student_discount, lunch_special, happy_hour, byob, late_night, big_portions

**deals** (optional detail for student_discount)
- place_id, description, verification (student_id | edu_email | unidays | school_specific), expires_at (nullable), last_confirmed, works_votes, fails_votes, source_url

## Scoring (the heart of the app)

- **Quality score (0–10):** Google rating weighted by review count (a 4.6 with 1,200 reviews beats a 4.8 with 40), boosted when a Beli score exists.
- **Value score (0–10):** starts from price_level, bumped up for each value tag present. A $$$ place with a lunch special can rank near a $$ place with none.
- **Student score:** blend of the two. User's budget setting shifts the weights — "cheap eats" leans value, "worth the splurge" leans quality, "any" is balanced.
- Show both sub-scores on each result card so users see *why* it ranked where it did.

Keep scoring in one pure, testable function.

## Build order

1. Project scaffold (Next.js, Supabase client, env setup, README).
2. Data layer: places schema, Google Places fetch + caching.
3. Scoring function with unit tests.
4. Search UI: city picker, cuisine chips, "what's popular," budget toggle. Results as photo cards with student score, price, distance to campus, tags.
5. Detail view: photos, hours, score breakdown, deal details if any, links out to Google/Beli.
6. Admin/curation page: look up a place via Google, add Beli score, value tags, and deals. This is how new cities get launched.
7. Later: Yelp Fusion as a second rating source, map view, more cities, saved places, expiration alerts for deals.

## Things the user still needs to do

- Create a Google Cloud project, enable Places API (New), get an API key (needs a card on file; free credit covers a student project).
- Set up a Supabase project and share the URL + anon key via `.env.local` (never commit it).
- Provide their Beli list (screenshots are fine) for the Boston/Cambridge seed — aim for 20–30 places.
- Identify 10–15 real Boston student deals to seed.

## Open questions

- Final app name.
- Whether to require accounts for submitting deals/votes (leaning no for v1; show new submissions as "unverified").
- Whether to add Yelp in v1 or hold for v2 (leaning v2).
