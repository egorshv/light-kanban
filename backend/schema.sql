-- Схема из docs.md §5. Расширения: columns.is_final (ADR-006), users + boards.owner_id (auth).

CREATE TABLE users (
    id            TEXT PRIMARY KEY,              -- uuid v4
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT,                          -- NULL для google-only пользователей
    google_sub    TEXT UNIQUE,                   -- NULL для email-пользователей
    name          TEXT DEFAULT '',
    created_at    TEXT NOT NULL                  -- ISO 8601 UTC
);

CREATE TABLE boards (
    id          TEXT PRIMARY KEY,            -- uuid v4
    owner_id    TEXT REFERENCES users(id),   -- NULL только у досок, созданных до auth
    name        TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 100),
    description TEXT DEFAULT '',
    created_at  TEXT NOT NULL,               -- ISO 8601 UTC
    updated_at  TEXT NOT NULL,
    archived_at TEXT
);
CREATE INDEX idx_boards_owner ON boards(owner_id);

CREATE TABLE columns (
    id        TEXT PRIMARY KEY,
    board_id  TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    name      TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 50),
    position  INTEGER NOT NULL,
    wip_limit INTEGER CHECK(wip_limit IS NULL OR wip_limit > 0),
    color     TEXT,
    is_final  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_columns_board ON columns(board_id, position);

CREATE TABLE tasks (
    id           TEXT PRIMARY KEY,
    board_id     TEXT NOT NULL REFERENCES boards(id)  ON DELETE CASCADE,
    -- column_id намеренно без ON DELETE CASCADE: удаление колонки —
    -- два явных сценария API (?move_tasks_to= либо 409), см. docs.md §5
    column_id    TEXT NOT NULL REFERENCES columns(id),
    title        TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 200),
    description  TEXT DEFAULT '',
    position     INTEGER NOT NULL,
    priority     TEXT NOT NULL DEFAULT 'normal'
                 CHECK(priority IN ('low','normal','high','urgent')),
    due_date     TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX idx_tasks_column ON tasks(column_id, position);
CREATE INDEX idx_tasks_board  ON tasks(board_id);

CREATE TABLE task_links (
    id             TEXT PRIMARY KEY,
    source_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    target_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    link_type      TEXT NOT NULL
                   CHECK(link_type IN ('blocks','subtask_of','relates_to','duplicates')),
    created_at     TEXT NOT NULL,
    UNIQUE(source_task_id, target_task_id, link_type),
    CHECK(source_task_id <> target_task_id)
);
