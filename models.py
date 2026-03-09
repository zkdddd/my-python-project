import sqlite3
import json
import time
from config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 测试用例表
    c.execute('''
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            method TEXT NOT NULL,
            url TEXT NOT NULL,
            headers TEXT,
            body TEXT,
            expected_status INTEGER,
            expected_body TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 运行记录表
    c.execute('''
        CREATE TABLE IF NOT EXISTS test_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER,
            status TEXT,
            response_status INTEGER,
            response_body TEXT,
            error_message TEXT,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration REAL,
            report_path TEXT,
            FOREIGN KEY(case_id) REFERENCES test_cases(id)
        )
    ''')

    c.execute('''
          CREATE TABLE IF NOT EXISTS data_sources (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              file_path TEXT NOT NULL,
              columns TEXT,          -- JSON 数组，存储列名
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
          )
      ''')
    try:
        c.execute('ALTER TABLE test_cases ADD COLUMN data_source_id INTEGER')
    except:
        pass
    try:
        c.execute('ALTER TABLE test_cases ADD COLUMN data_mapping TEXT')  # 例如 {"username":"col1","password":"col2"}
    except:
        pass
    conn.commit()
    conn.close()

# ---------- 用例操作 ----------
def add_case(name, method, url, headers, body, expected_status, expected_body, description):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO test_cases (name, method, url, headers, body, expected_status, expected_body, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, method, url, headers, body, expected_status, expected_body, description))
    conn.commit()
    case_id = c.lastrowid
    conn.close()
    return case_id

def get_all_cases():
    conn = get_db_connection()
    cases = conn.execute('SELECT * FROM test_cases ORDER BY id DESC').fetchall()
    conn.close()
    return cases

def get_case(case_id):
    conn = get_db_connection()
    case = conn.execute('SELECT * FROM test_cases WHERE id = ?', (case_id,)).fetchone()
    conn.close()
    return case

def update_case(case_id, name, method, url, headers, body, expected_status, expected_body, description):
    conn = get_db_connection()
    conn.execute('''
        UPDATE test_cases
        SET name=?, method=?, url=?, headers=?, body=?, expected_status=?, expected_body=?, description=?
        WHERE id=?
    ''', (name, method, url, headers, body, expected_status, expected_body, description, case_id))
    conn.commit()
    conn.close()

def delete_case(case_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM test_cases WHERE id = ?', (case_id,))
    conn.commit()
    conn.close()

# ---------- 运行记录操作 ----------
def add_test_run(case_id, status, response_status, response_body, error_message, start_time, end_time, duration, report_path):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO test_runs (case_id, status, response_status, response_body, error_message, start_time, end_time, duration, report_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (case_id, status, response_status, response_body, error_message, start_time, end_time, duration, report_path))
    conn.commit()
    run_id = c.lastrowid
    conn.close()
    return run_id

def get_test_runs(limit=50):
    conn = get_db_connection()
    runs = conn.execute('''
        SELECT r.*, c.name as case_name
        FROM test_runs r
        JOIN test_cases c ON r.case_id = c.id
        ORDER BY r.id DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return runs

def get_run_detail(run_id):
    conn = get_db_connection()
    run = conn.execute('''
        SELECT r.*, c.name as case_name, c.method, c.url, c.headers, c.body, c.expected_status, c.expected_body
        FROM test_runs r
        JOIN test_cases c ON r.case_id = c.id
        WHERE r.id = ?
    ''', (run_id,)).fetchone()
    conn.close()
    return run

def get_run_statistics(days=30):
    """获取最近 days 天的每日通过率统计数据"""
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT date(start_time) as run_date,
               COUNT(*) as total,
               SUM(CASE WHEN status='PASS' THEN 1 ELSE 0 END) as passed
        FROM test_runs
        WHERE start_time >= date('now', ?)
        GROUP BY run_date
        ORDER BY run_date
    ''', (f'-{days} days',)).fetchall()
    conn.close()
    return [{'date': r['run_date'], 'total': r['total'], 'passed': r['passed']} for r in rows]

# 数据源管理
def add_data_source(name, file_path, columns):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO data_sources (name, file_path, columns) VALUES (?, ?, ?)',
              (name, file_path, columns))
    conn.commit()
    source_id = c.lastrowid
    conn.close()
    return source_id

def get_all_data_sources():
    conn = get_db_connection()
    sources = conn.execute('SELECT * FROM data_sources ORDER BY id DESC').fetchall()
    conn.close()
    return sources

def get_data_source(source_id):
    conn = get_db_connection()
    source = conn.execute('SELECT * FROM data_sources WHERE id = ?', (source_id,)).fetchone()
    conn.close()
    return source