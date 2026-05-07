create table if not exists public.assets (
  asset_id text primary key,
  region_id text,
  bioma text,
  label text,
  last_sync bigint
);

create table if not exists public.stats (
  asset_id text not null references public.assets(asset_id) on delete cascade,
  year integer not null,
  class_id text not null,
  area_ha double precision not null,
  primary key (asset_id, year, class_id)
);

create table if not exists public.stats_agricultura (
  asset_id text not null references public.assets(asset_id) on delete cascade,
  year integer not null,
  metric text not null,
  value double precision not null,
  primary key (asset_id, year, metric)
);

create table if not exists public.control_sincro (
  id integer primary key,
  ultima_fecha bigint,
  total_nuevos integer default 0,
  nombres_nuevos text default ''
);

create table if not exists public.sync_lock (
  id integer primary key default 1,
  owner text,
  locked_until bigint not null default 0,
  updated_at timestamptz not null default now()
);

create index if not exists idx_stats_asset_year on public.stats(asset_id, year);
create index if not exists idx_assets_bioma_region on public.assets(bioma, region_id);
create index if not exists idx_agri_asset on public.stats_agricultura(asset_id);
create index if not exists idx_agri_year on public.stats_agricultura(year);

insert into public.control_sincro (id, ultima_fecha, total_nuevos, nombres_nuevos)
values (1, null, 0, '')
on conflict (id) do nothing;

insert into public.sync_lock (id, owner, locked_until)
values (1, null, 0)
on conflict (id) do nothing;

create or replace function public.acquire_sync_lock(p_owner text, p_ttl_seconds integer default 90)
returns boolean
language plpgsql
security definer
as $$
declare
  now_ts bigint := extract(epoch from now())::bigint;
begin
  update public.sync_lock
  set owner = p_owner,
      locked_until = now_ts + p_ttl_seconds,
      updated_at = now()
  where id = 1 and (locked_until < now_ts or owner = p_owner);

  if found then
    return true;
  end if;

  return false;
end;
$$;

create or replace function public.release_sync_lock(p_owner text)
returns void
language plpgsql
security definer
as $$
begin
  update public.sync_lock
  set owner = null,
      locked_until = 0,
      updated_at = now()
  where id = 1 and owner = p_owner;
end;
$$;

alter table public.assets enable row level security;
alter table public.stats enable row level security;
alter table public.stats_agricultura enable row level security;
alter table public.control_sincro enable row level security;
alter table public.sync_lock enable row level security;

drop policy if exists "anon_shared_assets_rw" on public.assets;
create policy "anon_shared_assets_rw" on public.assets for all to anon using (true) with check (true);

drop policy if exists "anon_shared_stats_rw" on public.stats;
create policy "anon_shared_stats_rw" on public.stats for all to anon using (true) with check (true);

drop policy if exists "anon_shared_stats_agri_rw" on public.stats_agricultura;
create policy "anon_shared_stats_agri_rw" on public.stats_agricultura for all to anon using (true) with check (true);

drop policy if exists "anon_shared_control_sincro_rw" on public.control_sincro;
create policy "anon_shared_control_sincro_rw" on public.control_sincro for all to anon using (true) with check (true);

drop policy if exists "anon_shared_sync_lock_rw" on public.sync_lock;
create policy "anon_shared_sync_lock_rw" on public.sync_lock for all to anon using (true) with check (true);
