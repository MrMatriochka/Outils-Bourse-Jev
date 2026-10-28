-- Lot 1 : catalogue des titres, cours journaliers (ajout seul) et journal des exécutions.

create table titre (
    id bigint generated always as identity primary key,
    symbole text not null,
    place text not null,
    nom text not null,
    devise text not null,
    actif boolean not null default true,
    panel_temoin boolean not null default false,
    est_reference boolean not null default false,
    unique (symbole, place)
);

create table cours_journalier (
    titre_id bigint not null references titre (id),
    jour date not null,
    ouverture numeric(18, 6) not null,
    haut numeric(18, 6) not null,
    bas numeric(18, 6) not null,
    cloture numeric(18, 6) not null,
    volume bigint not null,
    source text not null,
    recupere_le timestamptz not null,
    primary key (titre_id, jour)
);

-- Ajout seul garanti par la base, en plus du code : toute modification est refusée.
create function refuser_modification() returns trigger
language plpgsql as $$
begin
    raise exception 'table % en ajout seul : % interdit', tg_table_name, tg_op;
end;
$$;

create trigger cours_journalier_ajout_seul
    before update or delete on cours_journalier
    for each row execute function refuser_modification();

create trigger cours_journalier_sans_vidage
    before truncate on cours_journalier
    for each statement execute function refuser_modification();

create table execution (
    id bigint generated always as identity primary key,
    date_marche date not null unique,
    declencheur text not null check (declencheur in ('cron', 'manuel', 'rattrapage')),
    statut text not null
        check (statut in ('en_cours', 'ok', 'partielle', 'sans_objet', 'echec')),
    debut timestamptz not null,
    fin timestamptz,
    nb_cours_enregistres integer not null default 0,
    erreurs jsonb not null default '[]',
    titres_en_retard jsonb not null default '[]',
    credits_consommes integer not null default 0
);
