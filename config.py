import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "1234")
    MYSQL_DB = os.environ.get("MYSQL_DB", "counter_pos")

    TAX_RATE = float(os.environ.get("TAX_RATE", 0.0))  # e.g. 0.08 for 8%
    CURRENCY_SYMBOL = os.environ.get("CURRENCY_SYMBOL", "$")
    STORE_NAME = os.environ.get("STORE_NAME", "Counter")
