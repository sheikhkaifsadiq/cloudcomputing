# Supabase Setup

## 1. Table Creation
Run the following SQL in the Supabase SQL Editor:

```sql
create table if not exists public.employees (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  department text not null,
  email text not null,
  phone text not null,
  position text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Enable RLS
alter table public.employees enable row level security;

-- Basic policy for Service Role to access everything (actually Service Role bypasses RLS, but it's good practice)
-- If frontend needs read access, add policies here. But for HM2, CRUD is via backend tools!

create table if not exists public.operation_history (
  id uuid primary key default gen_random_uuid(),
  conversation_id text not null,
  timestamp timestamptz not null default now(),
  operation text not null,
  entity text not null,
  target text not null,
  status text not null,
  result text not null
);

alter table public.operation_history enable row level security;
```

## 2. Dummy Data
Run this to insert initial records:

```sql
insert into public.employees (name, department, email, phone, position)
values
('Ali Ahmed', 'HR', 'ali.hr@example.com', '03001234567', 'HR Officer'),
('Ali Raza', 'IT', 'ali.it@example.com', '03001234568', 'IT Admin'),
('Sara Khan', 'IT', 'sara@example.com', '03001234569', 'Developer'),
('Ahmed Raza', 'Finance', 'ahmed@example.com', '03001234570', 'Accountant'),
('Hamza Malik', 'HR', 'hamza@example.com', '03001234571', 'Recruiter');
```

## 3. Environment Variables
You need to set these in `.env`:
```env
SUPABASE_URL=your_project_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.8-flash
```

Obtain the `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from Settings -> API in your Supabase dashboard. Do NOT expose `SUPABASE_SERVICE_ROLE_KEY` to the frontend.
