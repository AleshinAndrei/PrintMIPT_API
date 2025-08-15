import sqlite3
from configs import DB_PATH, DDL_FILES


def setup_database(db_path, conn=None):
    if not db_path.parent.exists():
        db_path.parent.mkdir()
    if not db_path.exists():
        with open(db_path, 'w') as f:
            pass
    if not conn:
        conn = sqlite3.connect(db_path)
        make_database(conn)
        conn.close()
    else:
        make_database(conn)

def make_database(connection):
    for file_path in DDL_FILES.iterdir():
        if file_path.is_file():
            with file_path.open('r', encoding='utf-8') as ddl_script:
                connection.executescript(ddl_script.read())
    connection.commit()