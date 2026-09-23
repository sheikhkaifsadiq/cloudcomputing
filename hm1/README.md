# HM1 — Contacts (React + Supabase)

A small React (Vite) app with two fields — **Name** and **Contact number**. Submitting
stores the record permanently in Supabase (Postgres). The history list below shows all
records and never resets. Full CRUD: Create, Read, Update, Delete.

## 1. Create the Supabase table

In your Supabase project → **SQL Editor**, run:

```sql
create table if not exists public.contacts (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  contact text not null,
  created_at timestamptz not null default now()
);

alter table public.contacts enable row level security;

-- Assignment/demo policy: allow anon CRUD. Tighten for real apps.
create policy "anon full access" on public.contacts
  for all to anon using (true) with check (true);
```

Then copy **Project URL** and **anon public key** from Settings → API.

## 2. Local run

```bash
cp .env.example .env
```

Fill `.env` with your `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`, then:

```bash
npm install
npm run dev
```

## 3. Push to GitHub (as sheikhkaifsadiq)

This lives in the `hm1/` folder of `https://github.com/sheikhkaifsadiq/cloudcomputing`.
Run these yourself so the commit is authored by your account:

```bash
git clone https://github.com/sheikhkaifsadiq/cloudcomputing.git
```

Copy this whole `hm1` folder into the cloned repo, then:

```bash
cd cloudcomputing
git add hm1
git commit -m "Add hm1: React + Supabase contacts CRUD app"
git push origin main
```

> **Dependabot:** move `hm1/.github/dependabot.yml` to the **repo root** at
> `.github/dependabot.yml` (GitHub only reads it there). It is already scoped to
> the `/hm1` directory, so other homeworks are unaffected.

## 4. Deploy on Vercel

1. Vercel → **Add New → Project** → import `cloudcomputing`.
2. Set **Root Directory** = `hm1`.
3. Framework preset auto-detects **Vite** (build `npm run build`, output `dist`).
4. Add Environment Variables: `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
5. **Deploy.**

Any later push to `hm1/` triggers a redeploy automatically.

## Stack / versions

- React 19.1, Vite 6.3, @supabase/supabase-js 2.58 (pinned, current at build time)
- Node 18+ recommended
