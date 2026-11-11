import os
from datetime import timedelta
from urllib.parse import urlparse
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def resolve_db_settings():
    host = os.getenv("DB_HOST") or os.getenv("MYSQLHOST") or "localhost"
    port = os.getenv("DB_PORT") or os.getenv("MYSQLPORT") or "3306"
    user = os.getenv("DB_USER") or os.getenv("MYSQLUSER") or "root"
    password = os.getenv("DB_PASS")
    if password is None:
        password = os.getenv("MYSQLPASSWORD", "")
    name = os.getenv("DB_NAME") or "smartmeter"

    mysql_url = os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL")
    if mysql_url and not os.getenv("DB_HOST") and not os.getenv("MYSQLHOST"):
        parsed = urlparse(mysql_url)
        if parsed.hostname:
            host = parsed.hostname
        if parsed.port:
            port = str(parsed.port)
        if parsed.username:
            user = parsed.username
        if parsed.password is not None:
            password = parsed.password

    return {
        "host": host,
        "port": int(port),
        "user": user,
        "password": password,
        "database": name,
    }


_DB = resolve_db_settings()


class Config:
    DB_HOST = _DB["host"]
    DB_PORT = _DB["port"]
    DB_USER = _DB["user"]
    DB_PASS = _DB["password"]
    DB_NAME = _DB["database"]

    JWT_SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_volttrack_jwt_key_2026_x8934")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)

    SIMULATOR_API_KEY = os.getenv("SIMULATOR_API_KEY", "volttrack_simulator_api_key_secure_2026")
    MYSQL_BIN_PATH = os.getenv("MYSQL_BIN_PATH", r"C:\Program Files\MySQL\MySQL Server 8.0\bin").strip('"').strip("'")

    FLASK_PORT = int(os.getenv("PORT") or os.getenv("FLASK_PORT", 5000))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False" if os.getenv("PORT") else "True").lower() in ("true", "1", "t")
