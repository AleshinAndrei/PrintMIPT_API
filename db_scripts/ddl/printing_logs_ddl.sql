CREATE TABLE IF NOT EXISTS printing_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           VARCHAR(64) NOT NULL,
    amount          REAL NOT NULL,
    page_count      INTEGER,
    is_color        BOOLEAN,
    task_number     TEXT,
    print_date      TIMESTAMP DEFAULT (DATETIME(CURRENT_TIMESTAMP, 'localtime'))
);
