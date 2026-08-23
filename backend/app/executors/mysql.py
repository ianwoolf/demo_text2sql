import os
from urllib.parse import urlparse
from app.models import QueryResult
from .base import QueryExecutorError


class MySQLExecutor:
    def __init__(self, config: dict):
        self.dsn = config.get("dsn") or os.getenv(config.get("dsn_env", "MYSQL_DSN"), "")

    def execute(self, sql: str, limit: int = 200) -> QueryResult:
        if not self.dsn:
            raise QueryExecutorError("MySQL DSN is not configured.")
        try:
            import pymysql
        except ImportError as exc:
            raise QueryExecutorError("Install pymysql to connect to MySQL.") from exc
        parsed = urlparse(self.dsn)
        try:
            connection = pymysql.connect(
                host=parsed.hostname or "localhost", port=parsed.port or 3306,
                user=parsed.username, password=parsed.password,
                database=parsed.path.lstrip("/"), connect_timeout=5,
                read_timeout=10, write_timeout=10,
                cursorclass=pymysql.cursors.DictCursor, autocommit=False,
            )
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute(sql)
                rows = list(cursor.fetchmany(limit + 1))
                columns = [item[0] for item in cursor.description or []]
            connection.rollback()
            return QueryResult(columns=columns, rows=rows[:limit], truncated=len(rows) > limit)
        except Exception as exc:
            raise QueryExecutorError(f"MySQL query failed: {exc}") from exc
        finally:
            if "connection" in locals():
                connection.close()
