create table if not exists public.rental_checks (
  member_key text not null,
  item_key text not null,
  checked boolean not null default false,
  updated_at timestamptz not null default now(),
  primary key (member_key, item_key)
);

create table if not exists public.rental_config (
  id text primary key default 'main',
  members jsonb not null default '[]'::jsonb,
  items jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.rental_checks enable row level security;
alter table public.rental_config enable row level security;

grant usage on schema public to anon;
grant select, insert, update, delete on public.rental_checks to anon;
grant select, insert, update, delete on public.rental_config to anon;

drop policy if exists "Allow shared read access" on public.rental_checks;
create policy "Allow shared read access"
on public.rental_checks
for select
to anon
using (true);

drop policy if exists "Allow shared write access" on public.rental_checks;
create policy "Allow shared write access"
on public.rental_checks
for all
to anon
using (true)
with check (true);

drop policy if exists "Allow shared config read access" on public.rental_config;
create policy "Allow shared config read access"
on public.rental_config
for select
to anon
using (true);

drop policy if exists "Allow shared config write access" on public.rental_config;
create policy "Allow shared config write access"
on public.rental_config
for all
to anon
using (true)
with check (true);

insert into public.rental_config (id, members, items)
values (
  'main',
  '[
    {"key":"nakamura","name":"中村"},
    {"key":"kurihara","name":"栗原"},
    {"key":"yushi","name":"ゆーし"},
    {"key":"kuronuma","name":"黒沼"},
    {"key":"inoue","name":"井上"},
    {"key":"manji","name":"まんじ"},
    {"key":"manji_friend","name":"まんじ友達"},
    {"key":"lee","name":"リー"},
    {"key":"taniyone","name":"谷米"}
  ]'::jsonb,
  '[
    {"key":"full_set","label":"フルセット"},
    {"key":"bishi","label":"ビシのみ"},
    {"key":"iwashi","label":"イワシ"},
    {"key":"rod_holder","label":"ロッドホルダーだけ"}
  ]'::jsonb
)
on conflict (id) do nothing;

do $$
begin
  if not exists (
    select 1
    from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'rental_checks'
  ) then
    alter publication supabase_realtime add table public.rental_checks;
  end if;

  if not exists (
    select 1
    from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'rental_config'
  ) then
    alter publication supabase_realtime add table public.rental_config;
  end if;
end $$;
