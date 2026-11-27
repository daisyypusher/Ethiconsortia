-- Run once in Supabase SQL Editor.

create table users (
  user_id       bigint generated always as identity primary key,
  full_name     text not null default '',
  username      text not null,
  password_hash text not null,
  role          text not null default 'student'
                check (role in ('student','professor','admin')),
  created_at    timestamptz not null default now()
);
create unique index users_username_lower on users (lower(username));

create table verification_codes (
  code_id   bigint generated always as identity primary key,
  role      text not null check (role in ('professor','admin')),
  code      text not null unique,
  is_active boolean not null default true
);

-- Discord-style sessions: only a hash of the token is stored.
create table sessions (
  session_id   bigint generated always as identity primary key,
  user_id      bigint not null references users(user_id) on delete cascade,
  token_hash   text not null unique,
  device       text not null default '',
  created_at   timestamptz not null default now(),
  last_used_at timestamptz not null default now(),
  expires_at   timestamptz not null
);
create index sessions_user on sessions (user_id);

create table rooms (
  room_id         bigint generated always as identity primary key,
  room_name       text not null,
  description     text not null default '',
  host_id         bigint references users(user_id) on delete set null,
  invite_code     text not null unique,
  department_id   text,
  department_name text,
  is_archived     boolean not null default false,
  archived_at     timestamptz,
  created_at      timestamptz not null default now()
);

create table room_members (
  room_id            bigint not null references rooms(room_id) on delete cascade,
  user_id            bigint not null references users(user_id) on delete cascade,
  room_role          text not null default 'member' check (room_role in ('host','member')),
  can_send_messages  boolean not null default true,
  can_read_history   boolean not null default true,
  can_manage_members boolean not null default false,
  joined_at          timestamptz not null default now(),
  primary key (room_id, user_id)
);
create index room_members_user on room_members (user_id);

create table sub_rooms (
  sub_room_id   bigint generated always as identity primary key,
  room_id       bigint not null references rooms(room_id) on delete cascade,
  name          text not null,
  kind          text not null default 'text' check (kind in ('text','announcement')),
  visibility    text not null default 'public' check (visibility in ('public','private')),
  position      int  not null default 0,
  dm_user_a     bigint references users(user_id) on delete cascade,
  dm_user_b     bigint references users(user_id) on delete cascade,
  everyone_read boolean not null default true,
  everyone_send boolean not null default true,
  is_deleted    boolean not null default false,
  deleted_at    timestamptz,
  deleted_by    bigint references users(user_id) on delete set null
);
create index sub_rooms_room on sub_rooms (room_id);
create unique index sub_rooms_dm_pair on sub_rooms (room_id, dm_user_a, dm_user_b)
  where visibility = 'private';

create table messages (
  message_id    bigint generated always as identity primary key,
  sub_room_id   bigint not null references sub_rooms(sub_room_id) on delete cascade,
  sender_id     bigint not null references users(user_id),
  receiver_id   bigint references users(user_id) on delete set null,
  receiver_read boolean not null default false,
  content       text not null,
  tag           text not null default 'none'
                check (tag in ('none','announcement','question','emergency','wrong_sent','other')),
  tag_label     text,
  is_edited     boolean not null default false,
  edited_at     timestamptz,
  created_at    timestamptz not null default now()
);
-- "give me messages after id X" (catch-up after a sleep) uses this index
create index messages_sub_room_id on messages (sub_room_id, message_id);

create table message_edits (
  edit_id     bigint generated always as identity primary key,
  message_id  bigint not null references messages(message_id) on delete cascade,
  old_content text not null,
  new_content text not null,
  edited_at   timestamptz not null default now()
);

create table message_tag_edits (
  tag_edit_id bigint generated always as identity primary key,
  message_id  bigint not null references messages(message_id) on delete cascade,
  old_tag     text not null,
  old_label   text,
  new_tag     text not null,
  new_label   text,
  edited_at   timestamptz not null default now()
);

create table filtered_words (
  word_id    bigint generated always as identity primary key,
  room_id    bigint references rooms(room_id) on delete cascade,  -- null = all rooms
  word       text not null,
  added_by   bigint references users(user_id) on delete set null,
  created_at timestamptz not null default now()
);

create table flagged_messages (
  id          bigint generated always as identity primary key,
  user_id     bigint not null references users(user_id) on delete cascade,
  sub_room_id bigint not null references sub_rooms(sub_room_id) on delete cascade,
  original    text not null,
  censored    text not null,
  category    text not null default 'filtered' check (category in ('filtered','suspicious')),
  flagged_at  timestamptz not null default now()
);

create table flagged_reads (
  flag_id  bigint not null references flagged_messages(id) on delete cascade,
  admin_id bigint not null references users(user_id) on delete cascade,
  read_at  timestamptz not null default now(),
  primary key (flag_id, admin_id)
);

create table room_bans (
  room_id   bigint not null references rooms(room_id) on delete cascade,
  user_id   bigint not null references users(user_id) on delete cascade,
  banned_by bigint references users(user_id) on delete set null,
  banned_at timestamptz not null default now(),
  primary key (room_id, user_id)
);

create table room_warnings (
  room_id    bigint not null references rooms(room_id) on delete cascade,
  user_id    bigint not null references users(user_id) on delete cascade,
  warn_count int not null default 0,
  primary key (room_id, user_id)
);

-- SECURITY: Supabase can expose tables in "public" through its own API.
-- We only use our own server, so lock every table. With RLS on and no
-- policies, Supabase's public API can read nothing.
alter table users              enable row level security;
alter table verification_codes enable row level security;
alter table sessions           enable row level security;
alter table rooms              enable row level security;
alter table room_members       enable row level security;
alter table sub_rooms          enable row level security;
alter table messages           enable row level security;
alter table message_edits      enable row level security;
alter table message_tag_edits  enable row level security;
alter table filtered_words     enable row level security;
alter table flagged_messages   enable row level security;
alter table flagged_reads      enable row level security;
alter table room_bans          enable row level security;
alter table room_warnings      enable row level security;

-- Access codes for professor / admin sign-up. CHANGE THESE.
insert into verification_codes (role, code) values
  ('professor', 'CHANGE-ME-PROF'),
  ('admin',     'CHANGE-ME-ADMIN');

create table dm_threads (
  thread_id  bigint generated always as identity primary key,
  room_id    bigint not null references rooms(room_id) on delete cascade,
  user_a     bigint not null references users(user_id) on delete cascade,  -- lower id
  user_b     bigint not null references users(user_id) on delete cascade,  -- higher id
  created_by bigint not null references users(user_id) on delete cascade,
  created_at timestamptz not null default now(),
  check (user_a < user_b),
  unique (room_id, user_a, user_b)
);
create index dm_threads_a on dm_threads (user_a);
create index dm_threads_b on dm_threads (user_b);

create table dm_messages (
  message_id bigint generated always as identity primary key,
  thread_id  bigint not null references dm_threads(thread_id) on delete cascade,
  sender_id  bigint not null references users(user_id),
  content    text not null,
  tag        text not null default 'none'
             check (tag in ('none','announcement','question','emergency','wrong_sent','other')),
  tag_label  text,
  is_edited  boolean not null default false,
  edited_at  timestamptz,
  read_at    timestamptz,                -- set when the other person opens it
  created_at timestamptz not null default now()
);
create index dm_messages_thread on dm_messages (thread_id, message_id);
create index dm_messages_unread on dm_messages (thread_id) where read_at is null;

create table dm_message_edits (
  edit_id     bigint generated always as identity primary key,
  message_id  bigint not null references dm_messages(message_id) on delete cascade,
  old_content text not null,
  new_content text not null,
  edited_at   timestamptz not null default now()
);
create index dm_message_edits_msg on dm_message_edits (message_id);

alter table dm_threads       enable row level security;
alter table dm_messages      enable row level security;
alter table dm_message_edits enable row level security;