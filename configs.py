import pathlib

API_KEYS = {
    "PrintMIPT": 'API key'
}

logger_name = 'PrintMIPT_API'

DB_PATH = pathlib.Path('.db/database.db')
DB_PATH_TEST = pathlib.Path('.db/database_test.db')
DDL_FILES = pathlib.Path('db_scripts/ddl')

email_pattern = r"^\w+[\w.-]*@phystech\.(?:edu|su)$"
