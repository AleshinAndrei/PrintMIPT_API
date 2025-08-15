import pytest
import sqlite3
import os
from app import app
from configs import DB_PATH_TEST, API_KEYS, logger_name
from database import setup_database
import logging
from logger import setup_logger

logger = logging.getLogger(logger_name)

headers = {'API-Key': API_KEYS['PrintMIPT']}


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['DB_PATH'] = DB_PATH_TEST
    with app.test_client() as client:
        with app.app_context():
            setup_test_db(DB_PATH_TEST)
        setup_logger(logger)
        yield client
        with app.app_context():
            cleanup_test_db(DB_PATH_TEST)


def setup_test_db(db_path):
    """Создаем тестовую БД с примерами данных"""
    cleanup_test_db(db_path)
    setup_database(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        email TEXT PRIMARY KEY,
        in_union BOOLEAN NOT NULL
    )""")

    # Тестовые данные
    cursor.executemany(
        "INSERT INTO students (email, in_union) VALUES (?, ?)",
        [
            ('member1@phystech.edu', True),
            ('member2@phystech.edu', False),
            ('member3@phystech.edu', True)
        ]
    )

    conn.commit()
    conn.close()


def cleanup_test_db(db_path):
    """Очищаем тестовую БД"""
    if os.path.exists(db_path):
        os.remove(db_path)


### 2. Тесты для GET /membership
def test_get_membership_valid(client):
    # Успешный запрос для существующего пользователя
    response = client.get('/membership?email=member1@phystech.edu', headers=headers)
    assert response.status_code == 200
    assert response.json == {
        "results": [{
            "email": "member1@phystech.edu",
            "in_union": True
        }]
    }

    data = ['member1@phystech.edu', 'member2@phystech.edu', 'member3@phystech.edu']
    response = client.get(f'/membership?{"&".join(map(lambda email: "email="+email, data))}',
                          headers=headers)
    assert response.status_code == 200
    assert response.json == {
        "results": [{
            "email": "member1@phystech.edu",
            "in_union": True
        }, {
            "email": "member2@phystech.edu",
            "in_union": False
        }, {
            "email": "member3@phystech.edu",
            "in_union": True
        }
        ]
    }

    data = ['member1@phystech.edu', 'member2@phystech.edu', 'member3@phystech.edu']
    response = client.get(f'/membership?emails={",".join(data)}', headers=headers)
    assert response.status_code == 200
    assert response.json == {
        "results": [{
            "email": "member1@phystech.edu",
            "in_union": True
        },{
            "email": "member2@phystech.edu",
            "in_union": False
        },{
            "email": "member3@phystech.edu",
            "in_union": True
        }
        ]
    }

    data = ['member3@phystech.edu']
    response = client.get(f'/membership?emails={",".join(data)}', headers=headers)
    assert response.status_code == 200
    assert response.json == {
        "results": [{
            "email": "member3@phystech.edu",
            "in_union": True
        }]
    }


def test_get_membership_multiple_emails(client):
    # Запрос для нескольких email

    response = client.get(
        '/membership?email=member1@phystech.edu&email=member2@phystech.edu&email=unknown@phystech.edu',
        headers=headers
    )
    assert response.status_code == 200
    assert len(response.json['results']) == 3
    assert response.json['results'][2]['in_union'] is False  # Для неизвестного email


def test_get_membership_invalid_email(client):
    # Неправильный формат email
    response = client.get('/membership?email=invalid_email', headers=headers)
    assert response.status_code == 400


### 3. Тесты для POST /printing
def test_post_printing_valid(client):
    # Успешная запись данных о печати
    data = {
        "email": "member1@phystech.edu",
        "amount": 15.5,
        "page_count": 10,
        "is_color": False,
        "task_number": "HW-2023-05"
    }
    response = client.post('/printing', json=data, headers=headers)
    assert response.status_code == 201
    assert response.json['success'] is True


def test_post_printing_invalid_data(client):
    # Неправильные данные
    # Отсутствует обязательное поле amount
    data = {
        "email": "member1@phystech.edu",
        "is_color": False,
        "task_number": "HW-2023-05"
    }
    response = client.post('/printing', json=data, headers=headers)
    assert response.status_code == 400
    assert 'missing' in response.json


### 4. Тесты аутентификации
def test_auth_missing_api_key(client):
    # Отсутствует API-ключ
    response = client.get('/membership?email=member1@phystech.edu')
    assert response.status_code == 401


def test_auth_invalid_api_key(client):
    # Неправильный API-ключ
    wrong_headers = {'API-Key': 'invalid_key'}
    response = client.get('/membership?email=member1@phystech.edu', headers=wrong_headers)
    assert response.status_code == 401


### 5. Проверка логирования (дополнительные тесты)
def test_get_request_logging(client):
    # Проверяем, что запросы логируются
    conn = sqlite3.connect(DB_PATH_TEST)
    cursor = conn.cursor()

    initial_count = cursor.execute("SELECT COUNT(*) FROM membership_logs").fetchone()[0]
    client.get('/membership?email=member1@phystech.edu', headers=headers)
    new_count = cursor.execute("SELECT COUNT(*) FROM membership_logs").fetchone()[0]
    assert new_count == initial_count + 1

    initial_count = cursor.execute("SELECT COUNT(*) FROM printing_logs").fetchone()[0]
    data = {
        "email": "member1@phystech.edu",
        "amount": 15.5,
        "is_color": False,
        "task_number": "HW-2023-05"
    }
    client.post('/printing', json=data, headers=headers)
    new_count = cursor.execute("SELECT COUNT(*) FROM printing_logs").fetchone()[0]
    assert new_count == initial_count + 1

    conn.close()