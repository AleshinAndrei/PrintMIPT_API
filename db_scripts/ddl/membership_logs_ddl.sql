CREATE TABLE IF NOT EXISTS membership_logs (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    email                   VARCHAR(64) NOT NULL,
    api_key_hash            VARCHAR(128),
    found_in_db             BOOLEAN NOT NULL,
    in_union                BOOLEAN,
    request_time            TIMESTAMP DEFAULT (DATETIME(CURRENT_TIMESTAMP, 'localtime'))
);
