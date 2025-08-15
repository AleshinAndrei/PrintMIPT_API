from flask import Flask, request, jsonify
import sqlite3
from re import fullmatch
from functools import wraps
from configs import API_KEYS, logger_name, DB_PATH, email_pattern
import logging
import traceback
from logger import setup_logger
from database import setup_database

logger = logging.getLogger(logger_name)
app = Flask(__name__)


def email_verify(email: str):
    return fullmatch(email_pattern, email)



def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('API-Key')
        if api_key not in API_KEYS.values():
            logger.error(f'Invalid API Key: {api_key}, ip: {request.remote_addr}')
            return jsonify({"error": "Invalid API key"}), 401
        response = f(*args, **kwargs)
        return response

    return decorated_function


@app.route('/membership', methods=['GET'])
@api_key_required
def check_membership():
    db_path = app.config['DB_PATH']
    single_email_param = request.args.getlist('email')
    multi_email_param_str = request.args.get('emails')
    api_key = request.headers.get('API-Key')

    if not single_email_param and not multi_email_param_str:
        return jsonify({"error": "email or emails parameter is required"}), 400
    if single_email_param and multi_email_param_str:
        return jsonify({"error": "Only one of the email or emails parameters is supported."}), 400
    if len(single_email_param) > 100:
        return jsonify({"error": "Too big request"}), 400
    if len(single_email_param) > 1500:
        return jsonify({"error": "Too big request"}), 400

    if isinstance(single_email_param, list) and len(single_email_param) != 0:
        if not isinstance(single_email_param[0], str):
            return jsonify({"error": "email parameter should be string"}), 400
        emails = single_email_param  # Преобразуем одиночный email в список
    elif isinstance(multi_email_param_str, str):
        emails = list(multi_email_param_str.split(','))
    else: # multi_email_param is not None
        return jsonify({"error": "emails in emails parameter should be divided by a comma"}), 400

    valid_emails_match = [email_verify(email) for email in emails]
    invalid_emails = [email for email, match in zip(emails, valid_emails_match) if match is None]
    if len(invalid_emails) != 0:
        return jsonify({
            "error": "Invalid email format. Use email@phystech.edu or email@phystech.su",
            "invalid_emails": invalid_emails
        }), 400

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("CREATE TEMPORARY TABLE temp_emails(email TEXT PRIMARY KEY)")
        cursor.executemany(
            "INSERT OR IGNORE INTO temp_emails(email) VALUES (?)",
            [(email,) for email in emails]
        )

        cursor.execute("""
            SELECT t.email 
            FROM temp_emails AS t
            LEFT JOIN students AS st ON t.email = st.email
            WHERE st.email IS NULL
            """)
        missing_emails = [row[0] for row in cursor.fetchall()]

        if len(missing_emails) != 0:
            cursor.executemany(
                """INSERT INTO membership_logs 
                (email, api_key_hash, found_in_db) 
                VALUES (?, ?, ?)""",
                [(email, hash(api_key), False) for email in missing_emails]
            )
            logger.info(f"missing_emails: {len(missing_emails)}, see membership_logs")


        cursor.execute("""
            SELECT t.email, st.in_union
            FROM temp_emails AS t
            LEFT JOIN students AS st ON t.email = st.email
            WHERE st.email IS NOT NULL
            """)
        db_results = cursor.fetchall()
        if len(db_results) != 0:
            cursor.executemany(
                """INSERT INTO membership_logs 
                (email, api_key_hash, found_in_db, in_union) 
                VALUES (?, ?, ?, ?)""",
                [(email, hash(api_key), True, in_union) for email, in_union in db_results]
            )
            logger.info(f"found emails: {len(db_results)}")
        results_map = dict(db_results)

        results = []
        for email in emails:
            results.append({
                "email": email,
                "in_union": bool(results_map.get(email, False))
            })

        return jsonify({"results": results})

    except sqlite3.Error as e:
        logger.error(str(e))
        logger.error("Exception traceback:\n%s", traceback.format_exc())
        return jsonify({"error": "Internal Database error"}), 500
    except Exception as e:
        logger.error(str(e))
        logger.error("Exception traceback:\n%s", traceback.format_exc())
        return jsonify({"error": "Unknown error"}), 500
    finally:
        if conn:
            conn.commit()
            conn.close()


# POST метод для записи данных о печати
@app.route('/printing', methods=['POST'])
@api_key_required
def record_printing():
    db_path = app.config['DB_PATH']
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Проверка обязательных полей
    required_fields = ['email', 'amount']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing_fields
        }), 400

    email = data['email']
    amount = data['amount']
    page_count = data.get('page_count')
    is_color = data.get('is_color')
    task_number = data.get('task_number')

    # Валидация данных
    if not isinstance(email, str) or not email_verify(email):
        return jsonify({"error": "Invalid email format. Use email@phystech.edu"}), 400

    if not isinstance(amount, (int, float)) or amount < 0:
        return jsonify({"error": "Amount must be a positive number"}), 400

    if page_count and (not isinstance(page_count, int) or page_count < 1):
        return jsonify({"error": "Page count must be positive integer"}), 400

    if is_color and not isinstance(is_color, bool):
        return jsonify({"error": "is_color must be boolean"}), 400

    if task_number and not isinstance(task_number, (str, int)):
        return jsonify({"error": "Task number must be string or integer"}), 400

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO printing_logs 
            (email, amount, page_count, is_color, task_number) 
            VALUES (?, ?, ?, ?, ?)""",
            (email, amount, page_count, is_color, str(task_number))
        )

        return jsonify({
            "success": True,
            "record": {
                "email": email,
                "amount": amount,
                "page_count": page_count,
                "is_color": is_color,
                "task_number": task_number
            }
        }), 201

    except sqlite3.Error as e:
        logger.error(str(e))
        logger.error("Exception traceback:\n%s", traceback.format_exc())
        return jsonify({"error": "Internal Database error"}), 500
    except Exception as e:
        logger.error(str(e))
        logger.error("Exception traceback:\n%s", traceback.format_exc())
        return jsonify({"error": "Unknown error"}), 500
    finally:
        if conn:
            conn.commit()
            conn.close()


if __name__ == '__main__':
    setup_logger(logger)
    setup_database(DB_PATH)
    app.config['DB_PATH'] = DB_PATH
    app.run(host='0.0.0.0', port=4444)
