import os

BASE_DIR = os.path.dirname(__file__)

DB_PATH = os.path.join(BASE_DIR, 'api_test.db')

REPORT_DIR = os.path.join(BASE_DIR, 'static', 'reports')
os.makedirs(REPORT_DIR, exist_ok=True)

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DEBUG = True