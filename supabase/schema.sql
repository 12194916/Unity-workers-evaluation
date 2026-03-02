-- ============================================
-- Best Worker Bot — Supabase Schema
-- Run this in Supabase SQL Editor
-- ============================================

-- Categories (e.g., "Best Dispatch", "Best Update")
create table categories (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz default now()
);

-- Workers per category
create table workers (
  id uuid primary key default gen_random_uuid(),
  category_id uuid not null references categories(id) on delete cascade,
  name text not null,
  created_at timestamptz default now()
);

-- Polls (one per category per month)
create table polls (
  id uuid primary key default gen_random_uuid(),
  category_id uuid not null references categories(id) on delete cascade,
  month int not null check (month between 1 and 12),
  year int not null check (year >= 2024),
  status text not null default 'active' check (status in ('active', 'closed')),
  telegram_message_id bigint,
  telegram_chat_id bigint,
  broadcast_at timestamptz,
  worker_ids_order jsonb,
  created_at timestamptz default now(),
  closed_at timestamptz,
  unique (category_id, month, year)
);

-- Votes
create table votes (
  id uuid primary key default gen_random_uuid(),
  poll_id uuid not null references polls(id) on delete cascade,
  worker_id uuid not null references workers(id) on delete cascade,
  voter_telegram_id bigint not null,
  voter_username text,
  voter_first_name text,
  voted_at timestamptz default now(),
  unique (poll_id, voter_telegram_id)
);

-- Bot users (everyone who pressed /start)
create table bot_users (
  telegram_id bigint primary key,
  chat_id bigint not null,
  username text,
  first_name text,
  joined_at timestamptz default now()
);

-- Track which poll message was sent to which user (for stopping polls later)
create table poll_messages (
  id uuid primary key default gen_random_uuid(),
  poll_id uuid not null references polls(id) on delete cascade,
  chat_id bigint not null,
  message_id bigint not null,
  telegram_poll_id text,
  sent_at timestamptz default now()
);

-- Indexes for fast queries
create index idx_workers_category on workers(category_id);
create index idx_polls_month_year on polls(month, year);
create index idx_polls_status on polls(status);
create index idx_votes_poll on votes(poll_id);
create index idx_votes_worker on votes(worker_id);
create index idx_poll_messages_poll on poll_messages(poll_id);

-- ============================================
-- Row Level Security (RLS)
-- For now, disable RLS so both the web app
-- (using supabase anon key) and bot can access.
-- In production, tighten these policies.
-- ============================================
alter table categories enable row level security;
alter table workers enable row level security;
alter table polls enable row level security;
alter table votes enable row level security;
alter table bot_users enable row level security;
alter table poll_messages enable row level security;

-- Allow authenticated users (admin) full access
create policy "Admin full access on categories" on categories
  for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

create policy "Admin full access on workers" on workers
  for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

create policy "Admin full access on polls" on polls
  for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

create policy "Admin full access on votes" on votes
  for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

-- Allow anon (bot using service_role key) to read/write polls and votes
create policy "Service can manage polls" on polls
  for all using (true) with check (true);

create policy "Service can manage votes" on votes
  for all using (true) with check (true);

-- Bot tables — service_role (bot) has full access
create policy "Service can manage bot_users" on bot_users
  for all using (true) with check (true);

create policy "Service can manage poll_messages" on poll_messages
  for all using (true) with check (true);

create policy "Admin full access on bot_users" on bot_users
  for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

create policy "Admin full access on poll_messages" on poll_messages
  for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

-- Allow anon to read categories and workers (bot needs to read them)
create policy "Anyone can read categories" on categories
  for select using (true);

create policy "Anyone can read workers" on workers
  for select using (true);
