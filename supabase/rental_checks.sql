create table if not exists public.rental_checks (
  member_key text not null,
  item_key text not null,
  checked boolean not null default false,
  updated_at timestamptz not null default now(),
  primary key (member_key, item_key)
);

alter table public.rental_checks enable row level security;

grant usage on schema public to anon;
grant select, insert, update, delete on public.rental_checks to anon;

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
end $$;
