import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASS = os.getenv("DB_PASS", "")
    DB_NAME = os.getenv("DB_NAME", "smartmeter")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_volttrack_jwt_key_2026_x8934")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)

    SIMULATOR_API_KEY = os.getenv("SIMULATOR_API_KEY", "volttrack_simulator_api_key_secure_2026")
    MYSQL_BIN_PATH = os.getenv("MYSQL_BIN_PATH", r"C:\Program Files\MySQL\MySQL Server 8.0\bin").strip('"').strip("'")
    
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "t")
