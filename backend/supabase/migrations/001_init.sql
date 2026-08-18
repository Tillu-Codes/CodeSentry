-- CodeSentry initial schema: scan history per user.

create table if not exists public.scans (
    id bigint generated always as identity primary key,
    scan_id text not null,
    user_id uuid not null references auth.users(id) on delete cascade,
    filename text not null default '',
    source_type text not null default 'snippet',
    total_issues integer not null default 0,
    risk_score integer not null default 0,
    created_at timestamptz not null default now(),
    unique (user_id, scan_id)
);

create index if not exists scans_user_id_idx on public.scans (user_id, created_at desc);

create table if not exists public.findings (
    id bigint generated always as identity primary key,
    scan_id bigint not null references public.scans(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    type text not null,
    severity text not null,
    file text not null default '',
    line integer not null default 0,
    explanation text not null default '',
    suggested_fix text,
    confidence text not null default 'high',
    source text not null default '',
    code_snippet text,
    finding_order integer not null default 0
);

create index if not exists findings_scan_id_idx on public.findings (scan_id, finding_order);

alter table public.scans enable row level security;
alter table public.findings enable row level security;

create policy "users can manage own scans"
    on public.scans for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "users can manage own findings"
    on public.findings for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);