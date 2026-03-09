import os

BASE_DIR = os.path.dirname(__file__)

DB_PATH = os.path.join(BASE_DIR, 'api_test.db')

REPORT_DIR = os.path.join(BASE_DIR, 'static', 'reports')
os.makedirs(REPORT_DIR, exist_ok=True)

DEBUG = True