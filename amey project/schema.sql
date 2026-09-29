CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    roll_no       TEXT,
    department    TEXT,
    year          TEXT,
    phone         TEXT,
    role          TEXT    NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'admin', 'club_admin')),
    club_id       INTEGER REFERENCES clubs(id) ON DELETE CASCADE,    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clubs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL UNIQUE,
    category      TEXT    NOT NULL,
    description   TEXT    NOT NULL,
    coordinator   TEXT,
    contact_email TEXT,
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memberships (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    club_id   INTEGER NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    status    TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    joined_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, club_id)
);

CREATE TABLE IF NOT EXISTS events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT    NOT NULL,
    fest_name        TEXT    NOT NULL,
    club_id          INTEGER REFERENCES clubs(id) ON DELETE SET NULL,
    description      TEXT    NOT NULL,
    venue            TEXT    NOT NULL,
    event_date       TEXT    NOT NULL,
    event_time       TEXT    NOT NULL,
    max_participants INTEGER NOT NULL DEFAULT 100,
    created_at       TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registrations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_id      INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    registered_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, event_id)
);
